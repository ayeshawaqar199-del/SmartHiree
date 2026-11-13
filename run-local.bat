@echo off
setlocal
cd /d "%~dp0"
set SMARTHIRE_DB=sqlite

if not exist ".venv\Scripts\python.exe" (
    echo SmartHire's local Python environment is missing.
    echo Set it up with Python installed, then run:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

".venv\Scripts\python.exe" manage.py migrate
if errorlevel 1 exit /b %errorlevel%
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
