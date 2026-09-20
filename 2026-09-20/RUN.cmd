@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM  Fire strategier, 2026-09-20. Gjoer det RUN_ALL.cmd gjoer, med
REM  rettelsene: masteren henter ned sitt eget datagrunnlag, mailen leder
REM  med datastatus per strategi, og handelen modelleres uten kostnader.
REM
REM    RUN.cmd                    full kjoering, sender mail
REM    RUN.cmd --mail-kladd       bygg mailen, ikke send
REM    RUN.cmd --preflight        hva blokkerer akkurat naa?
REM    RUN.cmd --tving-datahent   bygg grunnlagsfilene paa nytt
REM    RUN.cmd --kostnadstest     ta med kostnadstabellen som opplysning
REM    RUN.cmd --vis-patcher      list patchene, kjoer ingenting
REM    RUN.cmd --selvtest         kjoer testene
REM
REM  Filene i rotmappen skrives aldri til.
REM ═══════════════════════════════════════════════════════════════════════
setlocal
set "HER=%~dp0"
set "ROT=%HER%.."
set "PY=%ROT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=py -3.12"
pushd "%ROT%"
%PY% "%HER%run.py" %*
set "KODE=%ERRORLEVEL%"
popd
if %KODE% NEQ 0 echo.
if %KODE% EQU 2 echo Kjoeringen var ufullstendig - se datastatus oeverst i mailen.
if %KODE% EQU 3 echo Mailen kunne ikke sendes - HTML-kopien ligger i data\7_master.
exit /b %KODE%
