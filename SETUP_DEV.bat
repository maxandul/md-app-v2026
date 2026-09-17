@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo   MD-App v2026 - Entwicklungsumgebung einrichten
echo =======================================================
echo.

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Erstelle virtuelle Python-Umgebung unter .venv ...
    py -3 -m venv .venv
    if errorlevel 1 python -m venv .venv
)

if not exist "%VENV_PYTHON%" (
    echo.
    echo FEHLER: Die virtuelle Python-Umgebung konnte nicht erstellt werden.
    echo Bitte pruefen, ob Python 3.11 oder neuer installiert ist.
    pause
    exit /b 1
)

echo Installiere Python-Pakete ...
"%VENV_PYTHON%" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo FEHLER: Die Python-Pakete konnten nicht installiert werden.
    echo Bitte Netzwerk-, VPN- und allfaellige Proxyeinstellungen pruefen.
    pause
    exit /b 1
)

echo.
echo === Einrichtung abgeschlossen ===
echo Die Umgebung muss nicht aktiviert werden.
echo Starte die App anschliessend mit START_DEV.bat.
pause
endlocal
