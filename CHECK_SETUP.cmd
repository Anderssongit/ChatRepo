@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run SETUP.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" master.py --preflight %*
set check_result=%errorlevel%
pause
exit /b %check_result%
