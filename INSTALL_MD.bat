@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo   MD-App v2026 - einmalige Installation
echo =======================================================
echo.

set "PYTHON_EXE="
set "PYTHON_ARGS="

py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3.11"
)

if not defined PYTHON_EXE (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo FEHLER: Python 3.11 oder neuer wurde nicht gefunden.
    echo Bitte Python zuerst ueber das AFI Service Portal installieren.
    pause
    exit /b 1
)

echo Verwende:
"%PYTHON_EXE%" %PYTHON_ARGS% --version
echo.
echo Installiere die festgelegten Pakete fuer das aktuelle Windows-Konto ...

if defined MD_PIP_PROXY (
    "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --user --proxy "%MD_PIP_PROXY%" -r requirements.txt
) else (
    "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install --user -r requirements.txt
)

if errorlevel 1 (
    echo.
    echo FEHLER: Die Pakete konnten nicht installiert werden.
    echo Falls der kantonale Proxy erforderlich ist, zuerst in PowerShell ausfuehren:
    echo   $env:MD_PIP_PROXY = "http://gateway.swisscom.zscloud.net:9400"
    echo und INSTALL_MD.bat aus derselben PowerShell erneut starten.
    pause
    exit /b 1
)

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import flask, waitress, pandas, openpyxl, pypdf; print('Alle benoetigten Pakete sind vorhanden.')"
if errorlevel 1 (
    echo FEHLER: Die Installationspruefung ist fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo Installation abgeschlossen.
echo Die App kann jetzt mit MD-Web.bat gestartet werden.
pause
endlocal
