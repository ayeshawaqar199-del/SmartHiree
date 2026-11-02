# SmartHire

SmartHire is a Django recruitment prototype for candidates and employers. It includes account registration and sign-in, searchable job listings, employer job posting, candidate applications, resume uploads, application status updates, and a transparent skills-overlap score.

## Run locally with WampServer

1. Start WampServer and make sure its MySQL/MariaDB service is running (green Wamp icon). The default connection is `127.0.0.1:3306`, user `root`, blank password.
2. Open phpMyAdmin and import `sql/create_database.sql`, or run that SQL in the MySQL console. It creates `smarthire_db`.
3. In a terminal opened in this project folder, create the Python environment and install dependencies:

   ```powershell
   py -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe manage.py migrate
   .venv\Scripts\python.exe manage.py createsuperuser
   .venv\Scripts\python.exe manage.py runserver
   ```

4. Visit http://127.0.0.1:8000. `run.bat` performs migrations and starts the server (after the environment and dependencies are set up).

If your WampServer MySQL root account has a password or uses another port, set `DB_PASSWORD` / `DB_PORT` in your terminal before starting Django, or update the defaults in `smarthire_project/settings.py`.

## First use

Create a Candidate account to explore and apply for jobs. Create an Employer account to post roles and manage incoming applications. Candidate profiles include a headline and bio that are compared with comma-separated job skills. The score shows the percentage of listed skills found in the profile, so it is understandable and easy to improve.

Registration requires names, a unique valid email, and Django's strong password validation. Job pay is numeric and min/max values are checked. Resume uploads accept PDF/DOC/DOCX up to 5 MB. Candidates may apply once per role; employers can only change applications for their own jobs.

The project uses Django migrations to create all tables in WampServer. The original SQLite file from the supplied project is not used.

## Welcome flow and demo jobs

The site opens on the welcome page at `/`. Use **How it works** to continue to the original SmartHire landing page at `/home/`, or search roles directly from the welcome page. Six clearly marked demo jobs are available in Find jobs; their descriptions state that they are illustrative, not real vacancies. To recreate or refresh them in the configured database, run:

```powershell
.venv\Scripts\python.exe manage.py seed_demo_jobs
```
