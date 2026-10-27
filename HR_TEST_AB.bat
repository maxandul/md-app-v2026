@echo off
setlocal
cd /d "%~dp0"
echo HR-Test A/B mit erfundenen Personen. Kein Outlook und keine produktiven Daten.
echo Nach dem Start im Browser oeffnen: http://127.0.0.1:5056/arbeit/ziele
echo Zum Beenden in diesem Fenster Strg+C druecken.
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" review_hr_ab.py
) else (
  python review_hr_ab.py
)
if errorlevel 1 (
  echo.
  echo Der Test konnte nicht gestartet werden. Bitte die Fehlermeldung weitergeben.
  pause
)
