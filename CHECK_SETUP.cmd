@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "NLTK_DATA=%CD%\.venv\nltk_data"
if not exist ".venv\Scripts\python.exe" (
    echo Run SETUP.cmd first.
    if not defined AKSJE_NO_PAUSE pause
    exit /b 1
)
".venv\Scripts\python.exe" master.py --preflight %*
set check_result=%errorlevel%
if not defined AKSJE_NO_PAUSE pause
exit /b %check_result%
