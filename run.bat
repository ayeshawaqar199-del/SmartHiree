@echo off
setlocal
cd /d "%~dp0"

rem WampServer/MySQL is the normal local database for this launcher.
set "SMARTHIRE_DB=mysql"

if not exist ".venv\Scripts\python.exe" (
  echo SmartHire Python environment not found.
  echo Create it with the installed Python, then install requirements:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Using WampServer MySQL (default: 127.0.0.1:3306, database smarthire_app_db, user root with blank password).
echo Optional .env settings can override the connection defaults.
echo If the database is missing, import sql\create_database.sql in phpMyAdmin first.
.venv\Scripts\python manage.py migrate
if errorlevel 1 (
  echo Migration failed. Check WampServer MySQL is running and DB_* settings are correct.
  pause
  exit /b 1
)
.venv\Scripts\python manage.py runserver 127.0.0.1:8000
