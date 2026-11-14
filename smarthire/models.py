from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


CV_REVIEW_CHOICES = [
    ("not_uploaded", "Not uploaded"),
    ("pending", "Pending review"),
    ("verified", "Verified"),
    ("rejected", "Needs an updated CV"),
]
APPLICATION_CV_CHOICES = [
    ("not_submitted", "No CV submitted"),
    ("pending", "Pending review"),
    ("verified", "Verified"),
    ("rejected", "Needs an updated CV"),
]


class Profile(models.Model):
    ROLE_CHOICES = [("candidate", "Candidate"), ("employer", "Employer")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="candidate")
    phone = models.CharField(max_length=24, blank=True)
    location = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=160, blank=True)
    company_name = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    skills = models.TextField(blank=True, help_text="Add skills separated by commas.")
    resume = models.FileField(
        upload_to="resumes/profiles/%Y/%m/", blank=True,
        validators=[FileExtensionValidator(["pdf", "docx"])],
    )
    resume_skills = models.TextField(blank=True)
    resume_verification = models.CharField(max_length=16, choices=CV_REVIEW_CHOICES, default="not_uploaded")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Job(models.Model):
    EMPLOYMENT_TYPES = [("Full-time", "Full-time"), ("Part-time", "Part-time"), ("Contract", "Contract"), ("Internship", "Internship")]
    employer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=160)
    company = models.CharField(max_length=160)
    location = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default="Full-time")
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField()
    required_skills = models.CharField(max_length=500, help_text="Separate skills with commas")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Application(models.Model):
    STATUS = [("submitted", "Submitted"), ("reviewing", "Reviewing"), ("shortlisted", "Shortlisted"), ("rejected", "Rejected"), ("hired", "Hired")]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to="resumes/%Y/%m/", blank=True, validators=[FileExtensionValidator(["pdf", "docx"])])
    status = models.CharField(max_length=16, choices=STATUS, default="submitted")
    match_score = models.PositiveSmallIntegerField(default=0)
    matched_skills = models.TextField(blank=True)
    missing_skills = models.TextField(blank=True)
    candidate_skills = models.TextField(blank=True)
    resume_verification = models.CharField(max_length=16, choices=APPLICATION_CV_CHOICES, default="not_submitted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["job", "candidate"], name="unique_candidate_job_application")]

    def __str__(self):
        return f"{self.candidate} → {self.job}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=240)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.message[:60]}"
