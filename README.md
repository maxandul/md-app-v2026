# MD-App v2026

Lokale HR-Anwendung für Mitarbeitenden-Dialoge mit Word-Vorlagen und PDF-Rücklauf.
Die neue Arbeitsübersicht mit den Etappen A–F und E2 ist der einzige Standardablauf.

## Start unter Windows

1. Das ZIP von `main` vollständig entpacken.
2. Einmalig **INSTALL_MD.bat** ausführen. Voraussetzung: Python 3.11 oder neuer.
3. **MD-Web.bat** starten und <http://127.0.0.1:5050/arbeit> öffnen.
4. Beim ersten Start ein Administrationskonto anlegen und die Einrichtung abschliessen.

**Node.js und npm sind für Installation und Betrieb nicht erforderlich.** Die
fertigen CSS- und JavaScript-Dateien liegen unter [`webapp/static`](webapp/static)
im Repository und sind im ZIP bereits enthalten. Es gibt keinen zusätzlichen
Build-Schritt und keinen Download von Oberflächen-Dateien beim Start.

[START_HIER.txt](START_HIER.txt) enthält die kurze Anleitung;
[Einrichtung und Betrieb](docs/START_NEUE_HR_VERSION.md) erklärt Konfiguration,
Word-Vorlagen, SAP-Import, Sicherung und Updates. Das Konsolenfenster muss während
der Arbeit geöffnet bleiben. Zum Beenden Strg+C drücken.

Beide Windows-Dateien verwenden eine vorhandene `.venv`, andernfalls das
installierte Python. `python run_web.py` startet dieselbe neue Oberfläche.
Die PDF-Automatik bleibt standardmässig aus; HR bestätigt die ausgelesenen Daten.

## Arbeitsablauf

- SAP-Export unter **Stammdaten** zunächst in der Vorschau prüfen und ausgewählte Änderungen übernehmen.
- Durchläufe und unterjährige Dialoge planen; Verantwortung, Zeitraum und Formular-OE je Gesprächsteil festlegen.
- Vorjahresziele direkt prüfen und versionieren; passende Rückblicke erzeugen und den Versand nachhalten.
- Personalisierte Word-Dateien als Pakete bereitstellen; Outlook-Entwurf und tatsächlichen Versand getrennt dokumentieren.
- Eingehende PDFs am Original prüfen, zuordnen und übernehmen. Erforderliche Unterschriften getrennt bestätigen.
- Feedback je Führungskraft und Jahr sammeln; Dossierbereitstellung und SAP-Export getrennt nachhalten.
- Offene Aufgaben über alle Jahre in **Arbeit**, **Mitarbeitende** und **Führungskräfte** bearbeiten.

Die bisherige HTML-Arbeitsmappe mit START-/Update-Dateien, Demo und Generator ist
entfernt. Erhalten bleiben benötigte Word-/PDF-Importformate, Vorjahresziele,
Originale, Datenmigrationen und Prüfnachweise. Fachregeln und bisherige
Implementierungsnachweise stehen in der [Dokumentation](docs/README.md).

## Lokaler Betrieb

Die Anwendung bindet an `127.0.0.1:5050` und verlangt ein persönliches Konto.
Netzwerkbetrieb auf mehreren HR-Geräten braucht eine passende Authentisierung,
TLS und geklärte Betriebsverantwortung. Keine Personaldaten ungeschützt freigeben.

Lokale Daten und Konfiguration liegen unter `instance`; externe Word-Vorlagen und
Dossierpfade werden dort konfiguriert. Diese Dateien gehören nicht ins öffentliche
Repository. Backups enthalten Personaldaten und sind entsprechend zu schützen.

Word, klassisches Outlook/S-MIME und die externe Dossier-/SAP-Verarbeitung beim
ersten echten Vorgang auf dem vorgesehenen Gerät kontrollieren. Lokal
bereitgestellt bedeutet noch nicht extern verarbeitet.

## Entwicklung und Prüfungen

Die folgenden Befehle sind für die Entwicklung, nicht für die Installation der
App. Die JavaScript-Tests mit Node laufen auch automatisch auf GitHub; auf dem
Arbeitsplatz muss Node dafür nicht installiert werden.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/run_tests_offline.py tests -q --tb=short
node --test tests/test_action_position.cjs tests/test_dispatch_download.cjs tests/test_goal_import.cjs
```

Für lokale Entwicklung: `.\.venv\Scripts\python.exe run_web.py --dev`.
Die Tests verwenden synthetische Daten; historische Datenbank-Fixtures prüfen
Migration und unterstützte Altformate. Die neue App benötigt keinen Umschalter.
Der CI-Lauf prüft `main` und HR-Arbeitsbranches ohne Netzwerkzugriff im Testprozess.

Die sechs anonymisierten Originaldateien der E2-Prüfung werden nicht mitgeliefert:
`python scripts/validate_e2_samples.py --input-dir "C:\Pfad\zu\Testdateien"`.
