import json

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .forms import ApplicationForm, CandidateProfileForm, CompanyReportForm, ContactMessageForm, JobForm, SignUpForm
from .matching import ResumeParseError, calculate_match, calculate_match_batch, extract_resume_facts, extract_resume_text, extract_skills, split_skills, suggest_skills
from .models import Application, CompanyReport, ContactMessage, Job, Notification, Profile

User = get_user_model()


def welcome(request):
    jobs = Job.objects.filter(is_active=True).select_related("employer").order_by("-created_at")[:8]
    return render(request, "smarthire/welcome.html", {
        "jobs": jobs,
        "active_job_count": Job.objects.filter(is_active=True).count(),
        "employer_count": Profile.objects.filter(role="employer").count(),
    })


def home(request):
    return render(request, "smarthire/home.html", {"jobs": Job.objects.filter(is_active=True).order_by("-created_at")[:6]})


def employers(request):
    return render(request, "smarthire/employers.html")


def mobile_app(request):
    return render(request, "smarthire/mobile_app.html")


def reported_companies(request):
    form = CompanyReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        if request.user.is_authenticated:
            report.submitted_by = request.user
        report.save()
        messages.success(request, "Your report was submitted privately for review.")
        return redirect("reported_companies")
    return render(request, "smarthire/reported_companies.html", {"form": form})


def contact(request):
    form = ContactMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thanks for reaching out. Your message has been sent to the SmartHire team.")
        return redirect("contact")
    return render(request, "smarthire/contact.html", {"form": form})


def post_job_entry(request):
    if request.user.is_authenticated and request.user.profile.role == "employer":
        return redirect("job_create")
    if request.user.is_authenticated:
        messages.info(request, "Job posting is available to employer accounts. Create a separate employer account to continue.")
    return redirect("employers")


def job_list(request):
    jobs = Job.objects.filter(is_active=True).select_related("employer")
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    employment_type = request.GET.get("type", "").strip()
    minimum_salary = request.GET.get("minimum_salary", "").strip()
    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(company__icontains=q) | Q(required_skills__icontains=q) | Q(preferred_skills__icontains=q) | Q(description__icontains=q))
    if location:
        jobs = jobs.filter(location__icontains=location)
    if employment_type in dict(Job.EMPLOYMENT_TYPES):
        jobs = jobs.filter(employment_type=employment_type)
    if minimum_salary.isdigit():
        jobs = jobs.filter(Q(salary_max__gte=int(minimum_salary)) | Q(salary_max__isnull=True))
    return render(request, "smarthire/job_list.html", {
        "jobs": jobs, "q": q, "location": location, "employment_type": employment_type,
        "minimum_salary": minimum_salary, "employment_types": Job.EMPLOYMENT_TYPES,
    })


def job_search_suggestions(request):
    """Return live job titles, employers, skills, or cities for the home search fields."""
    kind = request.GET.get("kind", "job")
    query = request.GET.get("q", "").strip()[:80]
    active_jobs = Job.objects.filter(is_active=True)

    if kind == "location":
        locations = active_jobs.order_by("location").values_list("location", flat=True).distinct()
        suggestions = [location for location in locations if not query or query.casefold() in location.casefold()][:10]
    else:
        matches = active_jobs.order_by("-created_at").values_list("title", "company", "required_skills", "preferred_skills")[:60]
        suggestions = []
        seen = set()
        for title, company, required, preferred in matches:
            for value in (title, company, *split_skills(f"{required},{preferred}")):
                value = value.strip()
                key = value.casefold()
                if value and key not in seen and (not query or query.casefold() in key):
                    seen.add(key)
                    suggestions.append(value)
                    if len(suggestions) == 10:
                        break
            if len(suggestions) == 10:
                break
    return JsonResponse({"suggestions": suggestions})


def skill_suggestions(request):
    query = request.GET.get("q", "").strip()
    return JsonResponse({"suggestions": suggest_skills(query)})


def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)
    applied = request.user.is_authenticated and Application.objects.filter(job=job, candidate=request.user).exists()
    candidate_match = None
    if request.user.is_authenticated and request.user.profile.role == "candidate":
        candidate_match = calculate_match(job, request.user.profile)
    return render(request, "smarthire/job_detail.html", {"job": job, "applied": applied, "candidate_match": candidate_match})


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    initial = {"role": request.GET.get("role")} if request.GET.get("role") in ("candidate", "employer") else None
    form = SignUpForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            username = form.cleaned_data.get("username", "")
            if User.objects.filter(username__iexact=username).exists():
                form.add_error("username", "That username is already taken. Please choose another.")
                return render(request, "smarthire/signup.html", {"form": form})
            raise
        login(request, user)
        messages.success(request, "Your account is ready. Welcome to SmartHire!")
        return redirect("dashboard")
    return render(request, "smarthire/signup.html", {"form": form})


def _recommendations(profile, limit=5):
    applied_ids = Application.objects.filter(candidate=profile.user).values_list("job_id", flat=True)
    jobs = list(Job.objects.filter(is_active=True).exclude(pk__in=applied_ids).select_related("employer"))
    results = calculate_match_batch((job, profile) for job in jobs)
    matches = [{"job": job, "match": result} for job, result in zip(jobs, results)]
    matches.sort(key=lambda item: (item["match"]["score"], item["job"].created_at), reverse=True)
    return matches[:limit]


@require_POST
def guidance_chat(request):
    """Answer common candidate and employer questions without sending chat text to a third party."""
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Please send a valid message."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Please send a valid message."}, status=400)
    prompt = str(payload.get("message", "")).strip()[:500]
    if not prompt:
        return JsonResponse({"error": "Type a message first."}, status=400)

    words = prompt.casefold()
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    role = profile.role if profile else "guest"
    jobs_url = reverse("job_list")
    signup_url = reverse("signup")
    dashboard_url = reverse("dashboard") if request.user.is_authenticated else f"{reverse('login')}?next={reverse('dashboard')}"
    actions = []
    jobs = []

    if any(word in words for word in ("resume", "cv", "curriculum", "upload")):
        reply = "Add a PDF or DOCX CV to your candidate profile (up to 5 MB). SmartHire can extract skills and experience details; review them before saving."
        actions = [{"label": "Open my profile", "url": dashboard_url}] if role == "candidate" else [{"label": "Create candidate account", "url": f"{signup_url}?role=candidate"}]
    elif any(word in words for word in ("skill", "profile", "bio", "education", "experience")):
        reply = "A complete candidate profile helps explain your fit. Add skills, education, experience and a short bio, then explore your recommendations."
        actions = [{"label": "Open my profile", "url": dashboard_url}] if role == "candidate" else [{"label": "Create candidate account", "url": f"{signup_url}?role=candidate"}]
    elif any(word in words for word in ("match", "recommend", "suggest", "fit")):
        if role == "candidate":
            matches = _recommendations(profile, limit=3)
            jobs = [{"title": item["job"].title, "company": item["job"].company, "location": item["job"].location, "match": item["match"]["score"], "url": reverse("job_detail", args=[item["job"].pk])} for item in matches]
            reply = "Here are a few open roles ranked against your profile." if jobs else "I couldn’t find an open role to recommend right now. Add more skills to your profile or browse all current openings."
        else:
            reply = "Candidates see skill match explanations on their dashboard. Create or complete a candidate profile to get personalized role recommendations."
        actions = [{"label": "Browse open jobs", "url": jobs_url}]
    elif any(word in words for word in ("apply", "application", "applied")):
        reply = "Open a job listing and choose Apply. You can add a cover letter and use a saved CV or attach a PDF/DOCX. Your applications and status updates appear on your dashboard."
        actions = [{"label": "Find open jobs", "url": jobs_url}]
    elif any(word in words for word in ("employer", "hire", "hiring", "post a job", "recruit")):
        reply = "Employers can create an employer account, post a role, and review applicants ranked by listed skills from the dashboard."
        actions = [{"label": "Employer information", "url": reverse("employers")}, {"label": "Create employer account", "url": f"{signup_url}?role=employer"}]
    elif any(word in words for word in ("report", "scam", "fraud", "suspicious")):
        reply = "If a company or job seems suspicious, send a private report with the company name and details so the SmartHire team can review it."
        actions = [{"label": "Report a company", "url": reverse("reported_companies")}]
    elif any(word in words for word in ("contact", "human", "person", "support", "help desk")):
        reply = "For help from the SmartHire team, use the contact page. This guidance chat is an automated helper and does not connect to a live human agent."
        actions = [{"label": "Contact SmartHire", "url": reverse("contact")}]
    elif any(word in words for word in ("job", "search", "salary", "location", "city", "remote", "internship")):
        reply = "Use the job search filters for keywords, location, employment type and minimum salary. Open a role to see its details and listed skills."
        actions = [{"label": "Search jobs", "url": jobs_url}]
    elif any(word in words for word in ("login", "sign in", "account", "register", "sign up")):
        reply = "Candidates and employers have separate account roles. Choose the role that fits you when creating an account, then sign in with your username or email."
        actions = [{"label": "Create account", "url": signup_url}, {"label": "Sign in", "url": reverse("login")}]
    else:
        reply = "I can guide you with job search, applications, profile and CV setup, skill matches, or employer hiring. What would you like help with?"
        actions = [{"label": "Search jobs", "url": jobs_url}, {"label": "Contact SmartHire", "url": reverse("contact")}]

    return JsonResponse({"reply": reply, "actions": actions, "jobs": jobs})


@login_required
def dashboard(request):
    profile = request.user.profile
    if profile.role == "employer":
        jobs = list(Job.objects.filter(employer=request.user).order_by("-created_at"))
        ranked_jobs = []
        for job in jobs:
            applicants = list(Application.objects.filter(job=job).select_related("candidate", "candidate__profile"))
            match_results = calculate_match_batch((job, application.candidate.profile) for application in applicants)
            for application, current_match in zip(applicants, match_results):
                application.match_score = current_match["score"]
                application.matched_skills = ", ".join(current_match["matched"])
                application.missing_skills = ", ".join(current_match["missing"])
                application.match_explanation = current_match["explanation"]
            applicants.sort(key=lambda application: (application.match_score, application.created_at), reverse=True)
            for rank, application in enumerate(applicants, start=1):
                application.rank = rank
            ranked_jobs.append({"job": job, "applicants": applicants})
        return render(request, "smarthire/employer_dashboard.html", {
            "jobs": jobs,
            "ranked_jobs": ranked_jobs,
        })

    profile_form = CandidateProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and profile_form.is_valid():
        new_resume = request.FILES.get("resume")
        removing_resume = profile_form.cleaned_data.get("resume") is False
        resume_text = ""
        found_skills = []
        resume_facts = {"education_level": "", "experience_years": None}
        if new_resume:
            try:
                resume_text = extract_resume_text(new_resume)
                all_job_skills = [skill for job in Job.objects.filter(is_active=True).only("required_skills", "preferred_skills") for skill in split_skills(f"{job.required_skills},{job.preferred_skills}")]
                found_skills = extract_skills(resume_text, extra_skills=all_job_skills)
                resume_facts = extract_resume_facts(resume_text)
            except ResumeParseError as error:
                profile_form.add_error("resume", str(error))
                return render(request, "smarthire/candidate_dashboard.html", {
                    "profile_form": profile_form,
                    "applications": Application.objects.filter(candidate=request.user).select_related("job"),
                    "recommendations": _recommendations(profile),
                })
        profile = profile_form.save(commit=False)
        if new_resume:
            profile.resume_skills = ", ".join(found_skills)
            profile.resume_verification = "pending"
            if not profile.education_level and resume_facts["education_level"]:
                profile.education_level = resume_facts["education_level"]
            if profile.experience_years is None and resume_facts["experience_years"] is not None:
                profile.experience_years = resume_facts["experience_years"]
        elif removing_resume:
            profile.resume_skills = ""
            profile.resume_verification = "not_uploaded"
        profile.save()
        if removing_resume:
            messages.success(request, "Your CV was removed from your profile.")
            return redirect("dashboard")
        if new_resume:
            skill_message = ", ".join(found_skills) if found_skills else "No catalogued skills were detected; add your skills manually."
            fact_message = []
            if resume_facts["education_level"]:
                fact_message.append(f"education: {resume_facts['education_level']}")
            if resume_facts["experience_years"] is not None:
                fact_message.append(f"experience: {resume_facts['experience_years']} years")
            extracted = f" Profile details detected: {', '.join(fact_message)}." if fact_message else " Add or correct education and experience in your profile if needed."
            messages.success(request, f"CV text checked. Extracted skills: {skill_message}.{extracted} Verification is pending review.")
        else:
            messages.success(request, "Your candidate profile has been updated.")
        return redirect("dashboard")

    return render(request, "smarthire/candidate_dashboard.html", {
        "applications": Application.objects.filter(candidate=request.user).select_related("job"),
        "profile_form": profile_form,
        "recommendations": _recommendations(profile),
    })


@login_required
def job_create(request):
    if request.user.profile.role != "employer":
        return HttpResponseForbidden("Employer account required.")
    form = JobForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.employer = request.user
        job.save()
        messages.success(request, "Your job is live.")
        return redirect("dashboard")
    return render(request, "smarthire/job_form.html", {"form": form, "is_edit": False})


@login_required
def job_edit(request, pk):
    if request.user.profile.role != "employer":
        return HttpResponseForbidden("Employer account required.")
    job = get_object_or_404(Job, pk=pk, employer=request.user)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your job posting has been updated.")
        return redirect("dashboard")
    return render(request, "smarthire/job_form.html", {"form": form, "is_edit": True, "job": job})


@login_required
@require_POST
def job_close(request, pk):
    if request.user.profile.role != "employer":
        return HttpResponseForbidden("Employer account required.")
    job = get_object_or_404(Job, pk=pk, employer=request.user)
    job.is_active = not job.is_active
    job.save(update_fields=["is_active"])
    messages.success(request, "Your job listing is now open." if job.is_active else "Your job listing has been closed. Past applications are preserved.")
    return redirect("dashboard")


@login_required
def apply_job(request, pk):
    if request.user.profile.role != "candidate":
        return HttpResponseForbidden("Candidate account required.")
    job = get_object_or_404(Job, pk=pk, is_active=True)
    if Application.objects.filter(job=job, candidate=request.user).exists():
        messages.info(request, "You have already applied to this job.")
        return redirect("job_detail", pk=pk)
    form = ApplicationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        profile = request.user.profile
        resume_file = request.FILES.get("resume")
        resume_text = ""
        if resume_file:
            try:
                resume_text = extract_resume_text(resume_file)
            except ResumeParseError as error:
                form.add_error("resume", str(error))
                return render(request, "smarthire/apply.html", {"form": form, "job": job})

        result = calculate_match(job, profile, resume_text=resume_text)
        application = form.save(commit=False)
        application.job = job
        application.candidate = request.user
        application.match_score = result["score"]
        application.matched_skills = ", ".join(result["matched"])
        application.missing_skills = ", ".join(result["missing"])
        application.match_explanation = result["explanation"]
        application.candidate_skills = ", ".join(result["candidate_skills"])
        if resume_file:
            application.resume_verification = "pending"
        elif profile.resume:
            application.resume = profile.resume.name
            application.resume_verification = profile.resume_verification if profile.resume_verification != "not_uploaded" else "pending"
        application.save()

        if resume_file:
            all_job_skills = [skill for row in Job.objects.filter(is_active=True).only("required_skills") for skill in split_skills(row.required_skills)]
            profile.resume = application.resume.name
            profile.resume_skills = ", ".join(extract_skills(resume_text, extra_skills=all_job_skills))
            profile.resume_verification = "pending"
            profile.save(update_fields=["resume", "resume_skills", "resume_verification"])
        Notification.objects.create(
            user=job.employer,
            message=f"{request.user.get_full_name() or request.user.username} applied for {job.title}.",
            link=f"{reverse('dashboard')}#application-{application.pk}",
        )
        matched = ", ".join(result["matched"]) or "none of the listed skills yet"
        missing = ", ".join(result["missing"]) or "none"
        messages.success(request, f"Application submitted. Match: {result['score']}% — matched: {matched}; still to show: {missing}.")
        return redirect("dashboard")
    return render(request, "smarthire/apply.html", {"form": form, "job": job})


@login_required
@require_POST
def update_application(request, pk):
    if request.user.profile.role != "employer":
        return HttpResponseForbidden("Employer account required.")
    application = get_object_or_404(Application, pk=pk, job__employer=request.user)
    new_status = request.POST.get("status")
    if new_status in dict(Application.STATUS) and new_status != application.status:
        application.status = new_status
        application.save(update_fields=["status"])
        Notification.objects.create(
            user=application.candidate,
            message=f"Your application for {application.job.title} is now {application.get_status_display().lower()}.",
            link=reverse("dashboard"),
        )
        messages.success(request, "Application status updated and candidate notified.")
    return redirect("dashboard")


@login_required
def notification_center(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        messages.success(request, "Notifications marked as read.")
        return redirect("notifications")
    unread_notifications = request.user.notifications.filter(is_read=False)
    return render(request, "smarthire/notifications.html", {"notifications": unread_notifications})


@login_required
def application_resume(request, pk):
    application = get_object_or_404(Application.objects.select_related("job", "candidate"), pk=pk)
    allowed = request.user.is_staff or request.user == application.candidate or request.user == application.job.employer
    if not allowed:
        return HttpResponseForbidden("This CV is private to the candidate and hiring team.")
    if not application.resume:
        messages.info(request, "No CV was attached to this application.")
        return redirect("dashboard")
    filename = application.resume.name.rsplit("/", 1)[-1]
    return FileResponse(application.resume.open("rb"), as_attachment=True, filename=filename)


@login_required
def profile_resume(request, pk):
    profile = get_object_or_404(Profile.objects.select_related("user"), pk=pk)
    allowed = request.user.is_staff or request.user == profile.user or Application.objects.filter(candidate=profile.user, job__employer=request.user).exists()
    if not allowed:
        return HttpResponseForbidden("This CV is private to the candidate and hiring team.")
    if not profile.resume:
        messages.info(request, "No profile CV is available.")
        return redirect("dashboard")
    filename = profile.resume.name.rsplit("/", 1)[-1]
    return FileResponse(profile.resume.open("rb"), as_attachment=True, filename=filename)


@login_required
def notification_open(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    target = notification.link
    if not target.startswith("/") or target.startswith("//"):
        target = ""
    return render(request, "smarthire/notification_detail.html", {
        "notification": notification,
        "target": target,
    })
