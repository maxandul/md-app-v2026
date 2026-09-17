@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo   MD-App v2026 - Entwicklungsmodus
echo =======================================================
echo.

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Die Entwicklungsumgebung fehlt.
    echo Bitte zuerst SETUP_DEV.bat ausfuehren.
    pause
    exit /b 1
)

"%VENV_PYTHON%" -c "import flask, pandas, openpyxl, pypdf" >nul 2>nul
if errorlevel 1 (
    echo Python-Pakete fehlen oder sind unvollstaendig.
    echo Bitte SETUP_DEV.bat erneut ausfuehren.
    pause
    exit /b 1
)

start "" http://127.0.0.1:5050
"%VENV_PYTHON%" run_web.py --dev

echo.
echo MD-App wurde beendet.
pause
endlocal
