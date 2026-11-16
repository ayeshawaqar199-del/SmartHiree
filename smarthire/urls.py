from django.urls import path
from . import views

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("home/", views.home, name="home"),
    path("employers/", views.employers, name="employers"),
    path("mobile-app/", views.mobile_app, name="mobile_app"),
    path("reported-companies/", views.reported_companies, name="reported_companies"),
    path("contact/", views.contact, name="contact"),
    path("post-a-job/", views.post_job_entry, name="post_job_entry"),
    path("jobs/", views.job_list, name="job_list"),
    path("skills/suggest/", views.skill_suggestions, name="skill_suggestions"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
    path("jobs/<int:pk>/close/", views.job_close, name="job_close"),
    path("signup/", views.signup, name="signup"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("notifications/", views.notification_center, name="notifications"),
    path("notifications/<int:pk>/open/", views.notification_open, name="notification_open"),
    path("applications/<int:pk>/resume/", views.application_resume, name="application_resume"),
    path("profiles/<int:pk>/resume/", views.profile_resume, name="profile_resume"),
    path("jobs/new/", views.job_create, name="job_create"),
    path("jobs/<int:pk>/apply/", views.apply_job, name="apply_job"),
    path("applications/<int:pk>/status/", views.update_application, name="update_application"),
]
