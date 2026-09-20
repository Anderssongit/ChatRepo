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

REM Dobbeltklikk i Utforsker starter "cmd /c "<sti til denne fila>"". Da maa
REM vinduet staa aapent til slutt, ellers lukker det seg foer du rekker aa lese
REM svaret. Startes den fra en konsoll som allerede er aapen, skal den ikke
REM pause - da ville en planlagt oppgave blitt haengende for alltid.
echo(%cmdcmdline%| find /i "%~f0" >nul
if not errorlevel 1 set "DOBBELTKLIKK=1"

set "HER=%~dp0"
set "ROT=%HER%.."
set "PY=%ROT%\.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo.
    echo  Fant ingen .venv i rotmappen.
    echo  Kjoer SETUP.cmd der foerst - den installerer Python-pakkene.
    echo.
    if defined DOBBELTKLIKK pause
    exit /b 1
)

pushd "%ROT%"
"%PY%" "%HER%run.py" %*
set "KODE=%ERRORLEVEL%"
popd

echo.
if "%KODE%"=="0" echo  Ferdig uten feil.
if "%KODE%"=="1" echo  Rettelsene kunne ikke paafoeres. Ingenting ble kjoert.
if "%KODE%"=="2" echo  Noe manglet. Se datastatus - oeverst i mailen, eller i utskriften over.
if "%KODE%"=="3" echo  Mailen kunne ikke sendes. HTML-kopien ligger i data\7_master.
echo.

if defined DOBBELTKLIKK pause
exit /b %KODE%
