@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "NLTK_DATA=%CD%\.venv\nltk_data"
if exist ".venv\Scripts\python.exe" goto install
py -3.12 -m venv .venv
if errorlevel 1 (
    echo Install Python 3.12 with the Python launcher, then run SETUP.cmd again.
    goto failed
)
:install
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m nltk.downloader -d "%NLTK_DATA%" punkt punkt_tab
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo Setup complete. Next run CHECK_SETUP.cmd, then RUN_ALL.cmd.
if not defined AKSJE_NO_PAUSE pause
exit /b 0
:failed
echo Setup failed. See the error above; rerun SETUP.cmd after correcting it.
if not defined AKSJE_NO_PAUSE pause
exit /b 1
