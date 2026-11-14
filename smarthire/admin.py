from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Application, Job, Notification, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "resume_verification", "location")
    list_filter = ("role", "resume_verification")
    search_fields = ("user__username", "user__email", "skills", "resume_skills")
    exclude = ("resume",)
    readonly_fields = ("resume_download",)

    @admin.display(description="CV file")
    def resume_download(self, obj):
        if not obj or not obj.resume:
            return "No CV uploaded"
        return format_html('<a href="{}">Download candidate CV</a>', reverse("profile_resume", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        previous = Profile.objects.filter(pk=obj.pk).values_list("resume_verification", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if previous and previous != obj.resume_verification:
            Notification.objects.create(
                user=obj.user,
                message=f"Your CV review is now: {obj.get_resume_verification_display()}.",
                link=reverse("dashboard"),
            )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "location", "employer", "is_active", "created_at")
    list_filter = ("is_active", "employment_type")
    search_fields = ("title", "company", "required_skills")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "candidate", "status", "match_score", "resume_verification", "created_at")
    list_filter = ("status", "resume_verification")
    search_fields = ("job__title", "candidate__username", "candidate_skills")
    exclude = ("resume",)
    readonly_fields = ("match_score", "matched_skills", "missing_skills", "candidate_skills", "resume_download")

    @admin.display(description="CV file")
    def resume_download(self, obj):
        if not obj or not obj.resume:
            return "No CV submitted"
        return format_html('<a href="{}">Download application CV</a>', reverse("application_resume", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        previous = Application.objects.filter(pk=obj.pk).values_list("resume_verification", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if obj.resume_verification in ("verified", "rejected"):
            Profile.objects.filter(user=obj.candidate).update(resume_verification=obj.resume_verification)
        if previous and previous != obj.resume_verification:
            Notification.objects.create(
                user=obj.candidate,
                message=f"Your CV review for {obj.job.title} is now: {obj.get_resume_verification_display()}.",
                link=reverse("dashboard"),
            )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "message")
