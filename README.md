# MD-App v2026

Lokale Flask-/SQLite-Anwendung zur administrativen Verarbeitung des jährlichen
Mitarbeitenden-Dialogs (MD). Der aktuelle Stand ist ein lauffähiger MVP für
gemeinsame Tests und die schrittweise Weiterentwicklung.

## Was bereits funktioniert

- SAP-Stammdaten als XLSX importieren und versioniert in SQLite speichern
- einen Jahresprozess mit Rückblick- und Ausblickjahr eröffnen
- den Jahresprozess sichtbar durch Vorbereitung, Versand, Rücklauf/Verarbeitung
  und Abschluss führen; die Phase kann kontrolliert vor- und zurückgesetzt werden
- den regulären und den unterjährigen Ablauf sowie Auswirkungen auf Outlook,
  Roboter-Input, Personaldossier und SAP direkt im Cockpit erklären
- pro vorgesetzter Person eine eigenständige Offline-HTML-Datei erzeugen
- START-Dateien und notwendige Updates einzeln oder gesammelt bereitstellen
- S/MIME-markierte Nachrichten direkt versenden oder als Outlook-Entwürfe erzeugen
- Outlook-Posteingang einlesen, MD-Dokumente verarbeiten und reine MD-Mails
  idempotent verschieben
- mehrere Mitarbeitende, Spezialfälle und «Kein MD» in einer Datei bearbeiten
- Bearbeitungsfortschritt und Vollständigkeit in der Offline-Datei anzeigen
- Rückblick und Ausblick je Person mit Jahr und Personalnummer als PDF drucken
- elektronisch unterzeichnete PDFs einlesen und ihren MD-Datenblock übernehmen
- Einzelfälle mit Dokumentpflichten, PDF-Versionen und Audit-Verlauf prüfen
- fehlerhaft übernommene Angaben vor der Freigabe begründet korrigieren
- korrigierte PDF-Versionen kontrolliert ersetzen, ohne die Vorversion zu löschen
- Rückblick- und Ausblickfristen für den Durchlauf, eine Führungslinie oder einen
  Einzelfall begründet anpassen und jede betroffene Pflicht protokollieren
- überfällige Pflichten als Vorschau bündeln und ausgewählte oder alle
  Erinnerungen als S/MIME-markierte Outlook-Entwürfe vorbereiten
- bei Gesamtbewertung D/E oder Uneinigkeit einen zusätzlichen handschriftlich
  unterzeichneten Scan nachverfolgen
- nur den massgebenden Beleg für die nachgelagerte Dossier-RPA bereitstellen
- protokollierte SAP-Exportbatches aus abgeschlossenen Rückblicken erzeugen;
  Doppelverarbeitung wird verhindert und der Zeitraum auf Eintritts- und
  Austrittsdatum begrenzt
- Gesprächszeitpunkte personenbezogen sowie Gesamtbeurteilungen und Kompetenzen
  aggregiert auswerten und als Excel-kompatible CSV-Dateien exportieren
- aggregierte Auswertungen bei Unterschreitung der konfigurierten
  Mindestgruppengrösse automatisch unterdrücken
- kritische Aktionen in einer geschützten Administrationsansicht prüfen
- vollständige, prüfsummengesicherte Backups erstellen und kontrolliert
  wiederherstellen
- Ziele aus früheren Word-Ausblickformularen zunächst als Vorschau prüfen und
  danach idempotent in den nächsten Rückblick übernehmen

## Lokal unter Windows starten

Voraussetzung: Python 3.11 oder neuer.

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Anschliessend `MD-Web.bat` doppelklicken oder im aktivierten Terminal starten:

```powershell
python run_web.py
```

Die Anwendung ist danach unter <http://127.0.0.1:5050> erreichbar. Beim ersten
Start wird die lokale SQLite-Datenbank automatisch unter `instance/` angelegt.
Systemadministrationen finden Benutzerkonten, Audit, Backup und Restore unter
`Administration`. Backups enthalten Personaldaten und müssen unmittelbar auf ein
genehmigtes, verschlüsseltes und getrenntes Medium übertragen werden.

## Erster Testlauf

1. Die App starten.
2. Den SAP-Export über die Startseite hochladen.
3. Für diesen Import einen Jahresprozess eröffnen.
4. In der Prozessübersicht eine vorgesetzte Person auswählen.
5. Deren `_START.html` erzeugen und lokal im Browser testen.

Das Repository enthält bewusst keine SAP-Exporte, Personendaten, ausgefüllten
Dialoge, PDFs oder lokale Datenbank. Solche Dateien bleiben auf dem geschützten
HR-Gerät und sind durch `.gitignore` vom Commit ausgeschlossen.

## Wichtige Sicherheitsgrenze des MVP

Der Server bindet absichtlich nur an `127.0.0.1` und ist für den Betrieb auf
einem einzelnen HR-Laptop gedacht. Vor einem Zugriff weiterer Arbeitsplätze
müssen mindestens Windows-Authentisierung, Rollen/Berechtigungen, TLS, Backup,
Protokollierung und die Betriebsverantwortung festgelegt werden. Den Server mit
Personaldaten nicht ungeschützt über `0.0.0.0` im Netzwerk freigeben.

Der Versand und Rückversand von Dateien mit Personaldaten erfolgt gemäss dem
vorgesehenen Prozess S/MIME-verschlüsselt. Die Anwendung prüft die gespeicherte
Verschlüsselungsmarkierung vor jedem Direktversand. Alternativ können weiterhin
Outlook-Entwürfe erzeugt und vor dem manuellen Versand kontrolliert werden. Der
vollständige Nachweis ist mit dem produktiven HR-Postfach, den Zertifikaten und
der konkreten Outlook-Version durchzuführen.

Für die Entwurfserstellung sind Windows, klassisches Outlook und `pywin32`
erforderlich. Das Absenderpostfach kann vor dem Start gesetzt werden:

```powershell
$env:MD_HR_MAILBOX_EMAIL = "hr@vd.zh.ch"
$env:MD_OUTLOOK_MAILBOX = "VD-GS HR"
$env:MD_OUTLOOK_TARGET_FOLDER = "12 Mitarbeitenden-Dialog"
$env:MD_ROBOT_INPUT_ROOT = "K:\VD-GS-PUO-Personal\100 Roboter\Input"
$env:MD_ANALYTICS_MIN_GROUP_SIZE = "5"
```

Das Einlesen ignoriert Mails ohne MD-Bezug. Erfolgreich verarbeitete reine
MD-Mails werden nach «12 Mitarbeitenden-Dialog» verschoben. Bei gemischten Mails
werden die MD-Dokumente verarbeitet, die Fremdanlagen aber nicht gespeichert;
die Mail bleibt bis zur manuellen Prüfung im Posteingang.

## Dateinamen

- Versand: `MD_Dialog_2025_2026_Nachname_Rufname_123456_START.html`
- Zwischenstand: `MD_Dialog_2025_2026_Nachname_Rufname_123456_BEARBEITET_v01_YYYYMMDD_HHMM.html`
- Rückblick: `Rueckblick_2025_Nachname_Rufname_123456.pdf`
- Ausblick: `Ausblick_2026_Nachname_Rufname_123456.pdf`
- Handschriftlicher Scan: `Rueckblick_2025_Nachname_Rufname_HANDSCAN_123456.pdf`
- Kein MD: `Kein_MD_2025_Nachname_Rufname_123456.pdf`

Die Personalnummer steht bei dossierrelevanten PDFs am Ende des Dateinamens.

## Tests

Die Tests erzeugen ausschliesslich synthetische SAP-Daten in temporären Ordnern.

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m unittest discover -s prototype/html_dialog -p "test_*.py" -v
```

Weitere Architektur- und Prozesshinweise stehen in
[`docs/FLASK_SQLITE_MVP.md`](docs/FLASK_SQLITE_MVP.md). Die betrieblichen
Schutzmassnahmen, Restore-Schritte und noch notwendigen Freigaben stehen im
[`docs/BETRIEBSKONZEPT.md`](docs/BETRIEBSKONZEPT.md).
Die kontrollierte Prüfung mit SAP, Word-Formularen, Outlook und Restore ist in
[`docs/BUEROTEST.md`](docs/BUEROTEST.md) beschrieben.
