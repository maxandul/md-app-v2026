@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE="
set "PYTHON_ARGS="
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not defined PYTHON_EXE (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
  )
)
if not defined PYTHON_EXE (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
  echo Python 3.11 oder neuer wurde nicht gefunden. Bitte zuerst installieren.
  pause
  exit /b 1
)
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import flask, pandas, openpyxl, pypdf, reportlab" >nul 2>nul
if errorlevel 1 (
  echo Die benoetigten Pakete fehlen. Bitte zuerst INSTALL_MD.bat ausfuehren.
  echo Bei Verwendung von .venv: .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
echo HR-Test A bis F einschliesslich E2 mit erfundenen Personen.
echo Kein Outlook und keine produktiven Daten.
echo Nach dem Start im Browser oeffnen: http://127.0.0.1:5056/arbeit
echo Zum Beenden in diesem Fenster Strg+C druecken.
echo.
"%PYTHON_EXE%" %PYTHON_ARGS% review_hr_ab.py
if errorlevel 1 (
  echo.
  echo Der Test konnte nicht gestartet werden. Bitte die Fehlermeldung weitergeben.
  pause
)
