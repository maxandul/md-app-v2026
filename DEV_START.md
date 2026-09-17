# Entwicklungsmodus unter Windows starten

Auf verwalteten Windows-Geräten kann PowerShell die nicht signierte Datei
`.venv\Scripts\Activate.ps1` blockieren. Für diese App muss die virtuelle
Umgebung nicht aktiviert werden.

## Start per Doppelklick

1. Einmalig `SETUP_DEV.bat` ausführen.
2. Danach `START_DEV.bat` ausführen.
3. Die App öffnet sich unter <http://127.0.0.1:5050>.

Beide Starter rufen `.venv\Scripts\python.exe` direkt auf und ändern keine
PowerShell-Ausführungsrichtlinie.

## Start im PowerShell-Terminal

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_web.py --dev
```

Zum Beenden im Terminal `Ctrl+C` drücken.
