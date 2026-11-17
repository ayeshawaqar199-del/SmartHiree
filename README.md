# SmartHire

SmartHire is a Django recruitment prototype for candidates and employers. It includes account registration and sign-in, searchable job listings, employer job posting, candidate applications, resume uploads, application status updates, and a transparent skills-overlap score.

## Run locally with WampServer

1. Start WampServer and make sure its MySQL service is running. The default connection is `127.0.0.1:3306`, user `root`, blank password. If you use WampServer's MariaDB service instead, set `DB_PORT=3307` in `.env`.
2. Open phpMyAdmin and import `sql/create_database.sql`, or run that SQL in the MySQL console. It creates `smarthire_app_db`. The older `smarthire_db` is left untouched.
3. If this project does not already have a virtual environment, open a terminal in the project folder and create one, then install dependencies:

   ```powershell
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe manage.py migrate
   .venv\Scripts\python.exe manage.py createsuperuser
   .venv\Scripts\python.exe manage.py runserver
   ```

4. Run `run.bat`. It selects WampServer/MySQL, applies migrations, and starts the server at http://127.0.0.1:8000. `run-local.bat` selects SQLite for an offline local run.

Copy `.env.example` to `.env` to customize the database name, user, password, host, or port. Project environment variables take precedence over `.env` values.

## First use

Create a Candidate account to explore and apply for jobs. Create an Employer account to post roles and manage incoming applications. Candidate profiles include a headline, bio, and skills. SmartHire extracts skills from text-based PDF and DOCX CVs and shows the matched and missing job skills beside an explainable score.

Registration requires names, a unique valid email, and Django's strong password validation. Job pay is numeric and min/max values are checked. CV uploads accept text-based PDF or DOCX files up to 5 MB; scanned PDFs need OCR and are not parsed. Candidates may apply once per role; employers can only change applications for their own jobs.

The project uses Django migrations to create all tables in WampServer. Resume downloads are available only to the candidate, the employer handling their application, or an administrator.

## Welcome flow and demo jobs

The site opens on the welcome page at `/`. Use **How it works** to continue to the original SmartHire landing page at `/home/`, or search roles directly from the welcome page. Six clearly marked demo jobs are available in Find jobs; their descriptions state that they are illustrative, not real vacancies. To recreate or refresh them in the configured database, run:

```powershell
.venv\Scripts\python.exe manage.py seed_demo_jobs
```

## Run locally without MySQL

For a quick local run, set up the Python environment once:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then run `run-local.bat`. It uses a project-local SQLite database at `db.sqlite3`, applies migrations, and starts the site at http://127.0.0.1:8000. The normal configuration continues to use MySQL unless `SMARTHIRE_DB=sqlite` is set.
### Proposal requirements covered

The current SmartHire flows cover these functional requirements:

1. Candidate, employer, and administrator roles with role-checked pages and actions.
2. Candidate profile management, including headline, location, bio, and self-entered skills.
3. CV upload to a candidate profile or an individual application.
4. Text extraction from PDF and DOCX CVs with a 5 MB upload limit.
5. Skill extraction from CV text using a maintained skill catalog plus role-specific skill phrases.
6. Employer job creation with role requirements, employment type, location, and salary range.
7. Job discovery by title, company, skills, description, and location.
8. Candidate applications with an optional cover letter and CV.
9. Explainable match scores with the matched and missing skills displayed.
10. Candidate recommendations ordered by skill match.
11. Employer applicant rankings per job, including skill evidence and CV review status.
12. Application status updates, with notifications for employers and candidates.
13. Administrator review of CV status from Django Admin.

Matching is transparent keyword and skill phrase matching; it is not a trained AI model. Scanned PDFs without selectable text need OCR and are reported as unsupported. To use CV extraction, install all project dependencies with `python -m pip install -r requirements.txt`, apply migrations, and sign in as a candidate. Create an administrator with `python manage.py createsuperuser` to review CVs in `/admin/`.


## Coursework implementation checklist

### User interfaces
The browser interface includes the welcome and job-discovery pages, job details and application form, candidate and employer dashboards, registration and login, job-posting forms, notifications, company reports, and contact. Shared templates and responsive styling are in `smarthire/templates/smarthire/` and `smarthire/static/smarthire/style.css`.

### Database connectivity and validation
Django ORM models persist candidate profiles, jobs, applications, notifications, company reports, and contact messages. Registration uses Django authentication and creates a profile. The candidate profile, job, application, company-report, and contact forms are connected to their respective database models. Server-side validation covers required fields, email and username uniqueness, password strength, numeric experience (0–60 years), salary ordering, CV file type and 5 MB size, and valid application-status choices. The database also prevents duplicate applications for the same candidate and job.

### Design patterns
SmartHire now demonstrates two explicit patterns in resume processing:
- **Strategy Pattern:** `PdfResumeParser` and `DocxResumeParser` provide interchangeable implementations behind the `ResumeParserStrategy` interface.
- **Factory Pattern:** `ResumeParserFactory` selects the appropriate parser using the uploaded file extension. A new parser can be added without changing the view or matching workflow.

Implementation: `smarthire/patterns.py`; integration point: `extract_resume_text()` in `smarthire/matching.py`.

### Threads
`calculate_match_batch()` uses Python's `ThreadPoolExecutor` with the `smarthire-match` thread-name prefix to calculate independent job/profile matches concurrently. Database queries are performed by the request thread before the worker pool is called; the workers only process the supplied objects.

### Automated checks
Run the project tests after installing requirements and applying migrations:

```powershell
python manage.py test smarthire
```

The tests cover parser selection and extraction, database persistence for the model-backed forms, server-side validation, and execution of batched matching in worker threads.
