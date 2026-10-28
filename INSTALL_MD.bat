@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo   MD-App v2026 - einmalige Installation
echo =======================================================
echo.
echo [1/3] Suche Python ...

set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    call py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3.11"
    )
)

if not defined PYTHON_EXE (
    call python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo FEHLER: Python 3.11 oder neuer wurde nicht gefunden.
    echo Bitte Python zuerst ueber das AFI Service Portal installieren.
    pause
    exit /b 1
)

echo Verwende:
call "%PYTHON_EXE%" %PYTHON_ARGS% --version
echo.
echo [2/3] Installiere die Pakete fuer diese Python-Umgebung ...
set "PIP_SCOPE=--user"
if exist ".venv\Scripts\python.exe" set "PIP_SCOPE="

if defined MD_PIP_PROXY (
    call "%PYTHON_EXE%" %PYTHON_ARGS% -u -m pip install %PIP_SCOPE% --proxy "%MD_PIP_PROXY%" -r requirements.txt
) else (
    call "%PYTHON_EXE%" %PYTHON_ARGS% -u -m pip install %PIP_SCOPE% -r requirements.txt
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

echo [3/3] Pruefe, ob sich die Pakete laden lassen ...
call "%PYTHON_EXE%" %PYTHON_ARGS% -u scripts\check_runtime.py
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
