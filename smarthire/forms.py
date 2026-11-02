from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from .models import Profile,Job,Application
class SignUpForm(UserCreationForm):
    email=forms.EmailField(required=True); role=forms.ChoiceField(choices=Profile.ROLE_CHOICES,widget=forms.RadioSelect); first_name=forms.CharField(max_length=150,required=True); last_name=forms.CharField(max_length=150,required=True)
    class Meta: model=User; fields=('first_name','last_name','username','email','role','password1','password2')
    def clean_username(self):
        username=self.cleaned_data.get('username','').strip()
        if username and User.objects.filter(username__iexact=username).exists(): raise forms.ValidationError('That username is already taken. Please choose another.')
        return username
    def clean_email(self):
        email=self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError('An account with this email already exists.')
        return email
    def save(self,commit=True):
        user=super().save(commit=False); user.email=self.cleaned_data['email']; user.first_name=self.cleaned_data['first_name'].strip(); user.last_name=self.cleaned_data['last_name'].strip()
        if commit: user.save(); Profile.objects.create(user=user,role=self.cleaned_data['role'])
        return user
class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model=Profile; fields=('headline','location','phone','bio')
        widgets={'bio':forms.Textarea(attrs={'rows':4,'placeholder':'Describe your experience and skills. Include skill names for matching.'})}
class JobForm(forms.ModelForm):
    class Meta:
        model=Job; fields=('title','company','location','employment_type','salary_min','salary_max','description','required_skills')
        widgets={'description':forms.Textarea(attrs={'rows':5}),'required_skills':forms.TextInput(attrs={'placeholder':'Python, Django, SQL'})}
    def clean(self):
        data=super().clean(); low,high=data.get('salary_min'),data.get('salary_max')
        if low is not None and high is not None and low>high: self.add_error('salary_max','Maximum salary must be at least the minimum.')
        return data
class ApplicationForm(forms.ModelForm):
    resume=forms.FileField(required=False,validators=[FileExtensionValidator(['pdf','doc','docx'])],help_text='PDF, DOC or DOCX; maximum 5 MB')
    class Meta:
        model=Application; fields=('cover_letter','resume'); widgets={'cover_letter':forms.Textarea(attrs={'rows':5,'placeholder':'Tell the employer why you are a good fit.'})}
    def clean_resume(self):
        f=self.cleaned_data.get('resume')
        if f and f.size>5*1024*1024: raise forms.ValidationError('Resume must be 5 MB or smaller.')
        return f


