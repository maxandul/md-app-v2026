@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Direkter Einstieg mit neuer Oberflaeche und manueller Ruecklaufpruefung.
set "MD_HR_GOAL_WORKFLOW=1"
set "MD_HR_RETURN_AUTOMATION=0"

echo Neue HR-Oberflaeche - vorhandener Datenbestand im App-Ordner.
echo Ruecklaeufe werden vor der Uebernahme manuell geprueft.
echo Vor dem ersten Versionswechsel Daten, Konfiguration und Vorlagen sichern.
echo.
call "%~dp0MD-Web.bat"
endlocal
