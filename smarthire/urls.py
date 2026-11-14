from django.urls import path
from . import views

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("home/", views.home, name="home"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
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
