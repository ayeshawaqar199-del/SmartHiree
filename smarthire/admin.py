from django.contrib import admin
from .models import Profile,Job,Application
admin.site.register(Profile)
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display=('title','company','location','employer','is_active','created_at')
    list_filter=('is_active','employment_type')
    search_fields=('title','company','required_skills')
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display=('job','candidate','status','match_score','created_at')
    list_filter=('status',)
    search_fields=('job__title','candidate__username')
