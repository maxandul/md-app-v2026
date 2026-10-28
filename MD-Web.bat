@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo   MD-Verwaltung - HR-Arbeitsuebersicht
echo =======================================================
echo.

set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3.11"
    )
)

if not defined PYTHON_EXE (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo Python 3.11 oder neuer wurde nicht gefunden.
    echo Bitte Python zuerst ueber das AFI Service Portal installieren.
    pause
    exit /b 1
)

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import flask, waitress, pandas, openpyxl, pypdf, reportlab" >nul 2>nul
if errorlevel 1 (
    echo Die Python-Pakete fuer die MD-App fehlen oder sind unvollstaendig.
    echo Bitte zuerst INSTALL_MD.bat ausfuehren.
    echo Bei Verwendung von .venv: .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

"%PYTHON_EXE%" %PYTHON_ARGS% -c "import socket; s=socket.socket(); s.settimeout(1); code=s.connect_ex(('127.0.0.1',5050)); s.close(); raise SystemExit(1 if code == 0 else 0)" >nul 2>nul
if errorlevel 1 (
    echo Port 5050 wird bereits verwendet.
    echo Falls die MD-App schon laeuft, wird sie jetzt im Browser geoeffnet.
    echo Andernfalls muss der Portkonflikt mit der anderen Anwendung geklaert werden.
    start "" http://127.0.0.1:5050/arbeit
    pause
    exit /b 1
)

start "" http://127.0.0.1:5050/arbeit
"%PYTHON_EXE%" %PYTHON_ARGS% run_web.py --host 127.0.0.1 --port 5050

echo.
echo MD-Verwaltung wurde beendet.
pause
endlocal
