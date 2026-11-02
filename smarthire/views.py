from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import SignUpForm, JobForm, ApplicationForm, CandidateProfileForm
from .models import Job, Application

User = get_user_model()

def account_required(view):
    """Send signed-out visitors to signup, preserving the page they wanted."""
    def check_account(user):
        return user.is_authenticated

    # Resolve by route name at request time, after URL patterns finish loading.
    protected_view = user_passes_test(check_account, login_url='signup', redirect_field_name='next')(view)
    return protected_view

def safe_next(request, fallback='dashboard'):
    destination = request.POST.get('next') or request.GET.get('next', '')
    if destination and url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destination
    return reverse(fallback)

def welcome(request): return render(request,'smarthire/welcome.html')
@account_required
def home(request): return render(request,'smarthire/home.html',{'jobs':Job.objects.filter(is_active=True).order_by('-created_at')[:6]})
@account_required
def job_list(request):
    jobs=Job.objects.filter(is_active=True).select_related('employer'); q=request.GET.get('q','').strip(); location=request.GET.get('location','').strip()
    if q: jobs=jobs.filter(Q(title__icontains=q)|Q(company__icontains=q)|Q(required_skills__icontains=q)|Q(description__icontains=q))
    if location: jobs=jobs.filter(location__icontains=location)
    return render(request,'smarthire/job_list.html',{'jobs':jobs,'q':q,'location':location})
@account_required
def job_detail(request,pk):
    job=get_object_or_404(Job,pk=pk,is_active=True); applied=request.user.is_authenticated and Application.objects.filter(job=job,candidate=request.user).exists()
    return render(request,'smarthire/job_detail.html',{'job':job,'applied':applied})
def signup(request):
    if request.user.is_authenticated: return redirect(safe_next(request))
    form=SignUpForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                user=form.save()
        except IntegrityError:
            username=form.cleaned_data.get('username','')
            if User.objects.filter(username__iexact=username).exists():
                form.add_error('username','That username is already taken. Please choose another.')
                return render(request,'smarthire/signup.html',{'form':form,'next':request.POST.get('next','')})
            raise
        login(request,user); messages.success(request,'Your account is ready. Welcome to SmartHire!'); return redirect(safe_next(request))
    return render(request,'smarthire/signup.html',{'form':form,'next':request.GET.get('next','')})
@account_required
def dashboard(request):
    if request.user.profile.role=='employer':
        return render(request,'smarthire/employer_dashboard.html',{'jobs':Job.objects.filter(employer=request.user).order_by('-created_at'),'applications':Application.objects.filter(job__employer=request.user).select_related('job','candidate').order_by('-match_score','-created_at')})
    profile=request.user.profile; profile_form=CandidateProfileForm(request.POST or None,instance=profile)
    if request.method=='POST' and profile_form.is_valid(): profile_form.save(); messages.success(request,'Your candidate profile has been updated.'); return redirect('dashboard')
    return render(request,'smarthire/candidate_dashboard.html',{'applications':Application.objects.filter(candidate=request.user).select_related('job').order_by('-created_at'),'profile_form':profile_form})
@account_required
def job_create(request):
    if request.user.profile.role!='employer': return HttpResponseForbidden('Employer account required.')
    form=JobForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        job=form.save(commit=False); job.employer=request.user; job.save(); messages.success(request,'Your job is live.'); return redirect('dashboard')
    return render(request,'smarthire/job_form.html',{'form':form})
@account_required
def apply_job(request,pk):
    if request.user.profile.role!='candidate': return HttpResponseForbidden('Candidate account required.')
    job=get_object_or_404(Job,pk=pk,is_active=True)
    if Application.objects.filter(job=job,candidate=request.user).exists(): messages.info(request,'You have already applied to this job.'); return redirect('job_detail',pk=pk)
    form=ApplicationForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        app=form.save(commit=False); app.job=job; app.candidate=request.user; profile=request.user.profile
        skills=[s.strip().lower() for s in job.required_skills.split(',') if s.strip()]; text=f'{profile.headline} {profile.bio}'.lower()
        matches=[s for s in skills if s in text]; app.match_score=round(100*len(matches)/len(skills)) if skills else 0; app.save()
        messages.success(request,f'Application submitted. Skill overlap: {app.match_score}% ({len(matches)} of {len(skills)} listed skills).'); return redirect('dashboard')
    return render(request,'smarthire/apply.html',{'form':form,'job':job})
@account_required
@require_POST
def update_application(request,pk):
    if request.user.profile.role!='employer': return HttpResponseForbidden('Employer account required.')
    app=get_object_or_404(Application,pk=pk,job__employer=request.user); status=request.POST.get('status')
    if status in dict(Application.STATUS): app.status=status; app.save(update_fields=['status']); messages.success(request,'Application status updated.')
    return redirect('dashboard')



