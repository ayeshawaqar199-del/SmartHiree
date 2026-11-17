# SmartHire — Viva and Code Modification Guide

## 1. Project architecture

SmartHire is a Django application. HTML templates and CSS form the user interface, Django views handle requests, Django forms validate submitted data, Django ORM models persist records, and the matching module calculates explainable candidate/job scores.

A normal form flow is:

1. The browser submits a POST request with a CSRF token.
2. A Django view constructs the relevant form with `request.POST` and, for uploads, `request.FILES`.
3. `form.is_valid()` performs server-side validation.
4. `form.save()` or `form.save(commit=False)` stores the model record.
5. The view redirects and displays a success message.

## 2. Design Pattern 1 — Strategy

**Where:** `smarthire/patterns.py`

`ResumeParserStrategy` defines the common parser interface. `PdfResumeParser` and `DocxResumeParser` implement the same `parse()` operation using different file-format rules.

**Why:** The matching workflow does not need to know whether a CV is a PDF or DOCX. It calls the common strategy interface instead.

**Viva explanation:** “Strategy lets us switch the resume parsing algorithm without changing the code that uses it. Each parser follows the same interface.”

## 3. Design Pattern 2 — Factory

**Where:** `ResumeParserFactory.create()` in `smarthire/patterns.py`

The factory inspects the file extension and returns the correct parser strategy. Unsupported file types produce a clear validation error.

**Viva explanation:** “The Factory centralizes object creation. The view does not use multiple if/else branches to build PDF and DOCX parser objects.”

## 4. Threads / multithreading

**Where:** `calculate_match_batch()` in `smarthire/matching.py`

The function uses Python's `ThreadPoolExecutor` to calculate several independent candidate/job match results concurrently. Each worker is named with the `smarthire-match` prefix. The request thread performs database queries first, then passes ready-to-use objects to the workers.

**Viva explanation:** “Each candidate/job match is independent, so a worker pool can calculate multiple matches concurrently. The results are returned in the same order as the input pairs.”

## 5. Database connectivity

The model-backed forms are:

- `SignUpForm` → Django User and Profile
- `CandidateProfileForm` → Profile
- `JobForm` → Job
- `ApplicationForm` → Application
- `CompanyReportForm` → CompanyReport
- `ContactMessageForm` → ContactMessage

Login uses Django authentication and the custom email-or-username backend. Notifications are created when an application is submitted or its status changes.

The database can be configured for WampServer MySQL through `.env`. Set `SMARTHIRE_DB=sqlite` for an offline local run.

## 6. Input validation examples

- Registration checks required names, alphabetic usernames, unique usernames/emails, and Django password rules.
- Candidate profiles and job posts limit experience to 0–60 years.
- Job posts reject a maximum salary below the minimum salary.
- CV uploads accept PDF/DOCX only and enforce the 5 MB limit.
- Contact messages use Django's email validation.
- Application creation has a database uniqueness constraint for each job/candidate pair.
- Employer status updates accept only the declared application status choices.

## 7. Easy code-modification exercise for the viva

**Example: add support for another CV format.**

1. Create a class such as `RtfResumeParser(ResumeParserStrategy)`.
2. Implement its `parse(upload)` method.
3. Add the `.rtf` mapping to `ResumeParserFactory._strategies`.
4. Add a parser test.
5. The view and `extract_resume_text()` do not need to change.

This demonstrates the benefit of Strategy and Factory: file-format support can be extended without modifying unrelated application workflows.

## 8. Run and test

Install dependencies, configure the database, apply migrations, and run:

```powershell
python manage.py test smarthire
python manage.py runserver
```

For the standard WampServer setup, follow the database steps in the root README. Use `run-local.bat` when testing with SQLite.
