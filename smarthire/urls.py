from django.urls import path
from . import views
urlpatterns=[
    path('',views.welcome,name='welcome'),
    path('home/',views.home,name='home'),
    path('jobs/',views.job_list,name='job_list'),
    path('jobs/<int:pk>/',views.job_detail,name='job_detail'),
    path('signup/',views.signup,name='signup'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('jobs/new/',views.job_create,name='job_create'),
    path('jobs/<int:pk>/apply/',views.apply_job,name='apply_job'),
    path('applications/<int:pk>/status/',views.update_application,name='update_application'),
]
