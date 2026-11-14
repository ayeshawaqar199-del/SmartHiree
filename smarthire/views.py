from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .forms import ApplicationForm, CandidateProfileForm, JobForm, SignUpForm
from .matching import ResumeParseError, calculate_match, extract_resume_text, extract_skills, split_skills
from .models import Application, Job, Notification, Profile

User = get_user_model()


def welcome(request):
    return render(request, "smarthire/welcome.html")


def home(request):
    return render(request, "smarthire/home.html", {"jobs": Job.objects.filter(is_active=True).order_by("-created_at")[:6]})


def job_list(request):
    jobs = Job.objects.filter(is_active=True).select_related("employer")
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(company__icontains=q) | Q(required_skills__icontains=q) | Q(description__icontains=q))
    if location:
        jobs = jobs.filter(location__icontains=location)
    return render(request, "smarthire/job_list.html", {"jobs": jobs, "q": q, "location": location})


def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)
    applied = request.user.is_authenticated and Application.objects.filter(job=job, candidate=request.user).exists()
    return render(request, "smarthire/job_detail.html", {"job": job, "applied": applied})


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
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
    matches = []
    for job in Job.objects.filter(is_active=True).exclude(pk__in=applied_ids).select_related("employer"):
        result = calculate_match(job, profile)
        matches.append({"job": job, "match": result})
    matches.sort(key=lambda item: (item["match"]["score"], item["job"].created_at), reverse=True)
    return matches[:limit]


@login_required
def dashboard(request):
    profile = request.user.profile
    if profile.role == "employer":
        jobs = list(Job.objects.filter(employer=request.user).order_by("-created_at"))
        ranked_jobs = []
        for job in jobs:
            applicants = list(Application.objects.filter(job=job).select_related("candidate", "candidate__profile").order_by("-match_score", "created_at"))
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
        if new_resume:
            try:
                resume_text = extract_resume_text(new_resume)
                all_job_skills = [skill for job in Job.objects.filter(is_active=True).only("required_skills") for skill in split_skills(job.required_skills)]
                found_skills = extract_skills(resume_text, extra_skills=all_job_skills)
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
        elif removing_resume:
            profile.resume_skills = ""
            profile.resume_verification = "not_uploaded"
        profile.save()
        if removing_resume:
            messages.success(request, "Your CV was removed from your profile.")
            return redirect("dashboard")
        if new_resume:
            skill_message = ", ".join(found_skills) if found_skills else "No catalogued skills were detected; add your skills manually."
            messages.success(request, f"CV text checked. Extracted skills: {skill_message} Verification is pending review.")
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
    return render(request, "smarthire/job_form.html", {"form": form})


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
            link=reverse("dashboard"),
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
    return render(request, "smarthire/notifications.html", {"notifications": request.user.notifications.all()})


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
        target = reverse("dashboard")
    return redirect(target)
