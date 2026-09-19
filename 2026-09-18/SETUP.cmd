@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 (
    echo Install Python 3.12 with the Python launcher, then run SETUP.cmd again.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m nltk.downloader punkt punkt_tab
if errorlevel 1 exit /b 1
echo Setup complete. Next run CHECK_SETUP.cmd, then RUN_ALL.cmd.
pause
