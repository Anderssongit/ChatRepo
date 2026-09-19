@echo off
rem 2026-09-18 corrections. Uses the .venv created by the repository's SETUP.cmd
rem and leaves every file in the repository root untouched.
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    echo Run SETUP.cmd in the repository root first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "2026-09-18\run.py" %*
set run_result=%errorlevel%
pause
exit /b %run_result%
