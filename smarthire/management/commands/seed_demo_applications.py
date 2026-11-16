from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from smarthire.matching import calculate_match
from smarthire.models import Application, Job, Notification, Profile


LEGACY_TIPS = (
    "Tip: Add your skills and education to your profile to improve job recommendations.",
    "You can upload a PDF or DOCX CV and review the skills SmartHire detects.",
    "Use job type, location and minimum salary filters to narrow your search.",
    "Your application status changes will appear in this inbox.",
    "Tip: Add required and preferred skills to help candidates understand your role.",
    "Applicant rankings show related skill credit and explain each match score.",
    "Edit, close or reopen your job listings from the employer dashboard.",
    "Update application statuses from your dashboard to notify candidates.",
)

DEMO_CANDIDATES = (
    {"name": "Amina Sample", "username": "smarthire_sample_candidate_1", "skills": "Python, Django, SQL, REST API, Git", "experience": 3, "education": "bachelor"},
    {"name": "Bilal Sample", "username": "smarthire_sample_candidate_2", "skills": "Python, SQL, Git", "experience": 2, "education": "bachelor"},
    {"name": "Sana Sample", "username": "smarthire_sample_candidate_3", "skills": "JavaScript, React, HTML, CSS, SQL", "experience": 1, "education": "intermediate"},
    {"name": "Hamza Sample", "username": "smarthire_sample_candidate_4", "skills": "Communication, Customer Service, Excel", "experience": 0, "education": "secondary"},
)


class Command(BaseCommand):
    help = "Create clearly labelled demo applications and their employer inbox requests."

    def handle(self, *args, **options):
        User = get_user_model()
        employer_profiles = [
            profile for profile in Profile.objects.filter(role="employer").select_related("user")
            if profile.user.has_usable_password() and not profile.user.username.startswith("smarthire_demo_")
        ]
        if not employer_profiles:
            raise CommandError("Create or sign in to an employer account before seeding demo application requests.")

        employer = employer_profiles[0].user
        job, _ = Job.objects.get_or_create(
            employer=employer,
            title="Application Preview Role (Demo)",
            defaults={
                "company": "SmartHire Sample Company",
                "location": "Islamabad, Pakistan",
                "employment_type": "Full-time",
                "description": "Sample opening for previewing SmartHire applications and match explanations. This is demo content, not a real vacancy.",
                "required_skills": "Python, Django, SQL",
                "preferred_skills": "REST API, Git",
                "minimum_education": "bachelor",
                "experience_years": 1,
                "is_active": True,
            },
        )

        Notification.objects.filter(message__in=LEGACY_TIPS).delete()
        created_applications = 0
        created_requests = 0

        for entry in DEMO_CANDIDATES:
            candidate, created = User.objects.get_or_create(
                username=entry["username"],
                defaults={
                    "email": f"{entry['username']}@smarthire.local",
                    "first_name": entry["name"].split()[0],
                    "last_name": entry["name"].split()[1],
                },
            )
            if created:
                candidate.set_unusable_password()
                candidate.save(update_fields=["password"])
            profile, _ = Profile.objects.get_or_create(user=candidate, defaults={"role": "candidate"})
            profile.skills = entry["skills"]
            profile.experience_years = entry["experience"]
            profile.education_level = entry["education"]
            profile.headline = "Sample candidate profile for SmartHire demonstration"
            profile.save(update_fields=["skills", "experience_years", "education_level", "headline"])

            result = calculate_match(job, profile)
            application, created = Application.objects.get_or_create(
                job=job,
                candidate=candidate,
                defaults={
                    "cover_letter": "Sample application for previewing SmartHire. This is demo data, not a real applicant.",
                    "match_score": result["score"],
                    "matched_skills": ", ".join(result["matched"]),
                    "missing_skills": ", ".join(result["missing"]),
                    "candidate_skills": entry["skills"],
                    "match_explanation": result["explanation"],
                    "status": "submitted",
                },
            )
            created_applications += int(created)
            message = f"Demo application request: {entry['name']} applied for {job.title}."
            link = f"{reverse('dashboard')}#application-{application.pk}"
            _, created = Notification.objects.get_or_create(
                user=employer,
                message=message,
                link=link,
                defaults={"is_read": False},
            )
            created_requests += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Added {created_applications} sample applications and {created_requests} employer inbox requests."
        ))
