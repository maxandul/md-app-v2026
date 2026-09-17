@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo =======================================================
echo   MD-Verwaltung mit SQLite
echo =======================================================
echo.

python -c "import flask, waitress, pandas, openpyxl, pypdf" >nul 2>nul
if %errorlevel% neq 0 (
    echo Abhaengigkeiten fehlen.
    echo Bitte zuerst ausfuehren: python -m pip install -r requirements.txt
    pause
    exit /b 1
)

start "" http://127.0.0.1:5050
python run_web.py

echo.
echo MD-Verwaltung wurde beendet.
pause
endlocal
