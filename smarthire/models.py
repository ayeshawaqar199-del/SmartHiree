from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
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
    EDUCATION_CHOICES = [("", "Select education"), ("secondary", "Secondary school"), ("intermediate", "Intermediate / A levels"), ("bachelor", "Bachelor’s degree"), ("master", "Master’s degree"), ("doctorate", "Doctorate")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default="candidate")
    phone = models.CharField(max_length=24, blank=True)
    location = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=160, blank=True)
    education_level = models.CharField(max_length=16, choices=EDUCATION_CHOICES, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0)])
    company_name = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    skills = models.TextField(blank=True, help_text="Type at least 2 letters and choose a suggestion, or enter skills separated by commas.")
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
    required_skills = models.CharField(max_length=500, help_text="Type at least 2 letters and choose suggestions. Separate skills with commas.")
    preferred_skills = models.CharField(max_length=500, blank=True, help_text="Optional: type at least 2 letters for suggestions and separate skills with commas")
    minimum_education = models.CharField(max_length=16, choices=Profile.EDUCATION_CHOICES, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, validators=[MinValueValidator(0)], help_text="Minimum relevant experience in years")
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
    match_explanation = models.TextField(blank=True)
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


class CompanyReport(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("reviewing", "Under review"),
        ("confirmed", "Confirmed"),
        ("closed", "Closed without action"),
    ]
    company_name = models.CharField(max_length=160)
    website = models.URLField(blank=True)
    details = models.TextField(max_length=2000)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_reports",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.get_status_display()})"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField(max_length=3000)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"
