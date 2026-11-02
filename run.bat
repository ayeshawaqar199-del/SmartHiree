@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment not found. Create one with: py -m venv .venv
  echo Then install dependencies with: .venv\Scripts\python -m pip install -r requirements.txt
  pause
  exit /b 1
)
.venv\Scripts\python manage.py migrate
if errorlevel 1 pause & exit /b 1
.venv\Scripts\python manage.py runserver
