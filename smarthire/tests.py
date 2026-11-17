"""Automated checks for SmartHire's coursework requirements."""
from io import BytesIO
from threading import Lock, current_thread
from time import sleep
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from .forms import (
    ApplicationForm,
    CandidateProfileForm,
    CompanyReportForm,
    ContactMessageForm,
    JobForm,
    SignUpForm,
)
from .matching import calculate_match_batch
from .models import Application, CompanyReport, ContactMessage, Job, Profile
from .patterns import (
    DocxResumeParser,
    PdfResumeParser,
    ResumeParseError,
    ResumeParserFactory,
)


class ResumePatternTests(SimpleTestCase):
    def test_factory_selects_a_strategy_for_each_supported_type(self):
        self.assertIsInstance(ResumeParserFactory.create("candidate.pdf"), PdfResumeParser)
        self.assertIsInstance(ResumeParserFactory.create("candidate.docx"), DocxResumeParser)

    def test_factory_rejects_unsupported_extensions(self):
        with self.assertRaises(ResumeParseError):
            ResumeParserFactory.create("candidate.txt")

    def test_docx_strategy_extracts_text_and_resets_upload(self):
        document_xml = (
            b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            b'<w:body><w:p><w:r><w:t>Python and Django</w:t></w:r></w:p></w:body></w:document>'
        )
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", document_xml)

        upload = SimpleUploadedFile("candidate.docx", buffer.getvalue())
        parsed = ResumeParserFactory.create(upload.name).extract(upload)

        self.assertIn("Python and Django", parsed)
        self.assertEqual(upload.tell(), 0)


class FormDatabaseIntegrationTests(TestCase):
    def setUp(self):
        self.candidate = User.objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="CandidatePass!2026",
            first_name="Ayesha",
            last_name="Waqar",
        )
        self.candidate_profile = Profile.objects.create(user=self.candidate, role="candidate")
        self.employer = User.objects.create_user(
            username="employer",
            email="employer@example.com",
            password="EmployerPass!2026",
        )
        Profile.objects.create(user=self.employer, role="employer")
        self.job = Job.objects.create(
            employer=self.employer,
            title="Python Developer",
            company="Example Labs",
            location="Islamabad",
            employment_type="Full-time",
            description="Build and maintain Django applications.",
            required_skills="Python, Django",
        )

    def test_signup_form_creates_user_and_profile(self):
        form = SignUpForm(data={
            "first_name": "New",
            "last_name": "Candidate",
            "username": "newcandidate",
            "email": "newcandidate@example.com",
            "role": "candidate",
            "password1": "S7!plum#Cobalt",
            "password2": "S7!plum#Cobalt",
        })
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertEqual(user.profile.role, "candidate")

    def test_candidate_profile_form_updates_database(self):
        form = CandidateProfileForm(
            data={
                "headline": "Junior Python Developer",
                "location": "Rawalpindi",
                "phone": "+92 300 1234567",
                "education_level": "bachelor",
                "experience_years": "2.5",
                "skills": "Python, Django",
                "bio": "Interested in building useful web applications.",
            },
            instance=self.candidate_profile,
        )
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        self.candidate_profile.refresh_from_db()
        self.assertEqual(self.candidate_profile.skills, "Python, Django")
        self.assertEqual(float(self.candidate_profile.experience_years), 2.5)

    def test_job_form_creates_job_for_employer(self):
        form = JobForm(data={
            "title": "Backend Engineer",
            "company": "Example Labs",
            "location": "Islamabad",
            "employment_type": "Full-time",
            "salary_min": "60000",
            "salary_max": "90000",
            "required_skills": "Python, Django",
            "preferred_skills": "Docker",
            "minimum_education": "bachelor",
            "experience_years": "2.0",
            "description": "Develop and test backend services.",
        })
        self.assertTrue(form.is_valid(), form.errors)

        job = form.save(commit=False)
        job.employer = self.employer
        job.save()
        self.assertTrue(Job.objects.filter(pk=job.pk, employer=self.employer).exists())

    def test_application_form_creates_candidate_application(self):
        form = ApplicationForm(data={"cover_letter": "I have relevant Python experience."})
        self.assertTrue(form.is_valid(), form.errors)

        application = form.save(commit=False)
        application.job = self.job
        application.candidate = self.candidate
        application.save()
        self.assertTrue(
            Application.objects.filter(job=self.job, candidate=self.candidate).exists()
        )

    def test_company_report_form_persists_report(self):
        form = CompanyReportForm(data={
            "company_name": "Example Labs",
            "website": "https://example.com",
            "details": "Please review this company listing.",
        })
        self.assertTrue(form.is_valid(), form.errors)

        report = form.save(commit=False)
        report.submitted_by = self.candidate
        report.save()
        self.assertTrue(CompanyReport.objects.filter(pk=report.pk).exists())

    def test_contact_form_persists_message(self):
        form = ContactMessageForm(data={
            "name": "Test User",
            "email": "test.user@example.com",
            "subject": "A question",
            "message": "Please contact me about my account.",
        })
        self.assertTrue(form.is_valid(), form.errors)

        message = form.save()
        self.assertTrue(ContactMessage.objects.filter(pk=message.pk).exists())

    def test_email_and_salary_validations_reject_invalid_input(self):
        contact_form = ContactMessageForm(data={
            "name": "Test User",
            "email": "not-an-email",
            "subject": "A question",
            "message": "Please contact me.",
        })
        self.assertFalse(contact_form.is_valid())

        invalid_job = JobForm(data={
            "title": "Developer",
            "company": "Example Labs",
            "location": "Islamabad",
            "employment_type": "Full-time",
            "salary_min": "90000",
            "salary_max": "50000",
            "required_skills": "Python",
            "description": "A development role.",
            "experience_years": "2",
        })
        self.assertFalse(invalid_job.is_valid())
        self.assertIn("salary_max", invalid_job.errors)

    def test_experience_is_limited_on_the_server(self):
        profile_form = CandidateProfileForm(
            data={"experience_years": "60.1"},
            instance=self.candidate_profile,
        )
        self.assertFalse(profile_form.is_valid())
        self.assertIn("experience_years", profile_form.errors)

        job_form = JobForm(data={
            "title": "Developer",
            "company": "Example Labs",
            "location": "Islamabad",
            "employment_type": "Full-time",
            "required_skills": "Python",
            "description": "A development role.",
            "experience_years": "61",
        })
        self.assertFalse(job_form.is_valid())
        self.assertIn("experience_years", job_form.errors)

    def test_cv_extension_validation_rejects_txt_upload(self):
        upload = SimpleUploadedFile("resume.txt", b"plain text")
        form = CandidateProfileForm(
            data={},
            files={"resume": upload},
            instance=self.candidate_profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("resume", form.errors)


class MatchingThreadTests(SimpleTestCase):
    def test_batch_matching_runs_in_named_worker_threads_and_preserves_order(self):
        pairs = [
            (SimpleNamespace(score=index), SimpleNamespace())
            for index in range(3)
        ]
        worker_names = []
        lock = Lock()

        def fake_match(job, profile):
            with lock:
                worker_names.append(current_thread().name)
            sleep(0.03)
            return {"score": job.score}

        with patch("smarthire.matching.calculate_match", side_effect=fake_match):
            results = calculate_match_batch(pairs, max_workers=3)

        self.assertEqual([result["score"] for result in results], [0, 1, 2])
        self.assertTrue(worker_names)
        self.assertTrue(all(name.startswith("smarthire-match") for name in worker_names))
        self.assertGreaterEqual(len(set(worker_names)), 2)
