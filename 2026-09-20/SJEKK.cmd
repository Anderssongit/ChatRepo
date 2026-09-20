@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM  Dobbeltklikk denne fila. Den sier om rettelsene ligger riktig plassert
REM  og er klare til bruk. Den laster ikke ned noe og sender ingenting.
REM ═══════════════════════════════════════════════════════════════════════
setlocal
set "HER=%~dp0"
set "ROT=%HER%.."
set "FEIL=0"

echo.
echo  ============================================================
echo   SJEKK AV OPPSETTET
echo  ============================================================
echo.
echo   Denne mappen : %HER%
echo   Rotmappen    : %ROT%
echo.

if exist "%ROT%\master.py" (
    echo   [OK]    master.py ligger i rotmappen.
) else (
    echo   [FEIL]  Fant ikke master.py i rotmappen.
    echo           Mappen 2026-09-20 maa ligge RETT VED SIDEN AV master.py.
    echo           Flytt hele mappen dit og kjoer SJEKK.cmd igjen.
    set "FEIL=1"
)

if exist "%ROT%\.venv\Scripts\python.exe" (
    echo   [OK]    .venv finnes.
) else (
    echo   [FEIL]  Fant ingen .venv i rotmappen.
    echo           Kjoer SETUP.cmd i rotmappen foerst.
    set "FEIL=1"
)

if "%FEIL%"=="1" goto slutt

echo.
echo   Kontrollerer at rettelsene kan paafoeres ...
echo.
pushd "%ROT%"
".venv\Scripts\python.exe" "%HER%run.py" --vis-patcher
set "KODE=%ERRORLEVEL%"
popd
echo.
if "%KODE%"=="0" (
    echo   [OK]    Rettelsene er klare.
    echo.
    echo           Naa kan du dobbeltklikke RUN.cmd i denne mappen.
    echo           Foerste gang: aapne Ledetekst i rotmappen og kjoer
    echo             2026-09-20\RUN.cmd --preflight
    echo           for aa se om dataene er paa plass.
) else (
    echo   [FEIL]  Rettelsene kan ikke paafoeres - se meldingen over.
    echo           Som regel betyr det at en av rotfilene er endret.
    set "FEIL=1"
)

:slutt
echo.
echo  ============================================================
if "%FEIL%"=="1" (echo   Noe maa rettes foer du kjoerer.) else (echo   Alt klart.)
echo  ============================================================
echo.
pause
exit /b %FEIL%
