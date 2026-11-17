import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from .models import Application, CompanyReport, ContactMessage, Job, Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, widget=forms.RadioSelect)
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={"autocomplete": "given-name", "data-alpha-only": "words"}))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={"autocomplete": "family-name", "data-alpha-only": "words"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        username_field = self.fields["username"]
        username_field.min_length = 6
        username_field.max_length = 150
        username_field.widget.attrs.update({
            "minlength": "6",
            "maxlength": "150",
            "data-alpha-only": "username",
            "autocomplete": "username",
            "autocapitalize": "none",
            "spellcheck": "false",
            "placeholder": "6–150 characters: letters, numbers, . _ @ + -",
            "pattern": "[A-Za-z0-9_.@+\\-]{6,150}",
            "title": "Use 6 to 150 characters: letters, numbers, and . _ @ + -",
        })

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "role", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if len(username) < 6:
            raise forms.ValidationError("Username must contain at least 6 characters.")
        if len(username) > 150:
            raise forms.ValidationError("Username cannot exceed 150 characters.")
        if username and not re.fullmatch(r"[\w.@+-]+", username, flags=re.UNICODE):
            raise forms.ValidationError("Use letters, numbers, and . _ @ + - only; spaces are not allowed.")
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken. Please choose another.")
        return username

    def clean_first_name(self):
        return self._clean_person_name("first_name")

    def clean_last_name(self):
        return self._clean_person_name("last_name")

    def _clean_person_name(self, field_name):
        value = " ".join(self.cleaned_data.get(field_name, "").split())
        if value and any(not (part.isalpha()) for part in value.split(" ")):
            raise forms.ValidationError("Use letters only. Spaces between names are allowed.")
        return value

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
            Profile.objects.create(user=user, role=self.cleaned_data["role"])
        return user


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Username or email", widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Username or email", "autocomplete": "username"}))

    def clean_username(self):
        value = self.cleaned_data.get("username", "").strip()
        if value and "@" not in value and not re.fullmatch(r"[\w.+-]+", value, flags=re.UNICODE):
            raise forms.ValidationError("Enter a valid username or your full email address.")
        return value


class CandidateProfileForm(forms.ModelForm):
    experience_years = forms.DecimalField(
        required=False, min_value=0, max_value=60, max_digits=4, decimal_places=1,
        widget=forms.NumberInput(attrs={"min": "0", "max": "60", "step": "0.5", "placeholder": "e.g. 2.5"}),
    )
    resume = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(["pdf", "docx"])],
        help_text="Optional. PDF or DOCX, up to 5 MB. SmartHire extracts skills from text-based files.",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.docx"}),
    )

    class Meta:
        model = Profile
        fields = ("headline", "location", "phone", "education_level", "experience_years", "skills", "bio", "resume")
        widgets = {
            "skills": forms.TextInput(attrs={"placeholder": "Start typing a skill…", "autocomplete": "off"}),
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Describe your experience and strengths."}),
            "experience_years": forms.NumberInput(attrs={"min": "0", "max": "60", "step": "0.5", "placeholder": "e.g. 2.5"}),
        }

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("CV files must be 5 MB or smaller.")
        return resume


class JobForm(forms.ModelForm):
    experience_years = forms.DecimalField(
        required=False, min_value=0, max_value=60, max_digits=4, decimal_places=1,
        widget=forms.NumberInput(attrs={"min": "0", "max": "60", "step": "0.5", "placeholder": "e.g. 2"}),
    )

    class Meta:
        model = Job
        fields = ("title", "company", "location", "employment_type", "salary_min", "salary_max", "required_skills", "preferred_skills", "minimum_education", "experience_years", "description")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "required_skills": forms.TextInput(attrs={"placeholder": "Type to find skills…", "autocomplete": "off"}),
            "preferred_skills": forms.TextInput(attrs={"placeholder": "Type to find optional skills…", "autocomplete": "off"}),
            "experience_years": forms.NumberInput(attrs={"min": "0", "max": "60", "step": "0.5", "placeholder": "e.g. 2"}),
        }

    def clean(self):
        data = super().clean()
        low, high = data.get("salary_min"), data.get("salary_max")
        if low is not None and high is not None and low > high:
            self.add_error("salary_max", "Maximum salary must be at least the minimum.")
        return data


class ApplicationForm(forms.ModelForm):
    resume = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(["pdf", "docx"])],
        help_text="Optional if you already saved a CV to your profile. PDF or DOCX, up to 5 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.docx"}),
    )

    class Meta:
        model = Application
        fields = ("cover_letter", "resume")
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 5, "placeholder": "Tell the employer why you are a good fit."})}

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if resume and resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("CV files must be 5 MB or smaller.")
        return resume


class CompanyReportForm(forms.ModelForm):
    class Meta:
        model = CompanyReport
        fields = ("company_name", "website", "details")
        widgets = {
            "company_name": forms.TextInput(attrs={"placeholder": "Company name"}),
            "website": forms.URLInput(attrs={"placeholder": "https://example.com"}),
            "details": forms.Textarea(attrs={"rows": 5, "placeholder": "Describe what happened and when."}),
        }


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name", "autocomplete": "name", "data-alpha-only": "words"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "subject": forms.TextInput(attrs={"placeholder": "How can we help?"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "Write your message here."}),
        }

    def clean_message(self):
        return self.cleaned_data["message"].strip()

    def clean_name(self):
        value = " ".join(self.cleaned_data.get("name", "").split())
        if value and any(not part.isalpha() for part in value.split(" ")):
            raise forms.ValidationError("Use letters only. Spaces between names are allowed.")
        return value
