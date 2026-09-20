# Projektstand MD-App v2026

**Stand:** 20. September 2026  
**Zweck:** Übergabe zwischen Arbeitssitzungen und Ausgangspunkt für die Weiterentwicklung des HR-Cockpits

## Ziel und Architektur

Die Anwendung ist eine eigenständig betreibbare Übergangslösung für die administrative
Verarbeitung des Mitarbeitenden-Dialogs. Das HR-Cockpit läuft lokal mit Flask und
SQLite. Vorgesetzte Personen arbeiten mit einer eigenständigen, offlinefähigen
HTML-Arbeitsmappe. Als offizieller Rücklauf an HR dienen die daraus erzeugten PDFs.

Das Repository muss ohne Laufzeitabhängigkeit zu `abw_tool` oder `md_app` funktionieren.
Erprobte Lösungen aus diesen Projekten dürfen übernommen werden, insbesondere für
Anmeldung und Outlook-Verarbeitung.

## Fachlich bestätigte Leitplanken

- HR importiert regelmässig vollständige SAP-Exporte und synchronisiert damit den
  aktuellen Personenbestand.
- Eine Arbeitsmappe enthält alle Direct Reports einer vorgesetzten Person und kann
  später mit HR-Updates aktualisiert werden.
- Rückblick, Ausblick, Probezeitdialoge und unterjährige Gespräche müssen als eigene
  Dialogereignisse abbildbar sein. Pro Person und Jahr können mehrere Ereignisse und
  mehrere verantwortliche Führungskräfte vorkommen.
- HR erhält immer das maschinenlesbare digitale PDF. Bei Gesamtbeurteilung D oder E
  oder bei Uneinigkeit wird zusätzlich ein handschriftlich unterzeichneter Scan benötigt.
- Ohne Scanpflicht wird das digitale PDF für die Dossier-RPA bereitgestellt. Bei
  Scanpflicht wird ausschliesslich der Scan an die RPA übergeben.
- Versand und Rückversand mit Personaldaten erfolgen S/MIME-verschlüsselt.
- Die Personalnummer steht bei dossierrelevanten PDF-Dateien am Ende des Dateinamens;
  Dokumenttyp und fachlich richtiges Jahr sind ebenfalls enthalten.
- Analysen gehören zum Muss-Umfang. Mindestens Gesprächszeitpunkte, Verteilung der
  Gesamtbeurteilungen sowie thematisierte Kompetenzen und Entwicklungsziele werden
  auswertbar gemacht.

## Umgesetzter Stand

### HR-Cockpit

- lokales Flask-/SQLite-Grundsystem
- Ersteinrichtung, Anmeldung, Passwortwechsel und Benutzerverwaltung
- SAP-XLSX-Import mit Historisierung
- Erkennung von BG 0, identischen und widersprüchlichen Duplikaten,
  Mehrfachanstellungen und mehreren Bewilligungen
- Inaktivsetzung nicht mehr enthaltener Personen
- Eröffnung eines Jahresdurchlaufs
- Übersicht nach Führungskräften und Fällen
- Erzeugung einer START-Arbeitsmappe pro Führungskraft
- manueller Import maschinenlesbarer PDF-Rückläufe
- Bestätigung der sichtbaren elektronischen Unterzeichnung
- Nachverfolgung und Import erforderlicher handschriftlicher Scans
- Bereitstellung des massgebenden Dokuments für die Dossier-RPA
- grundlegender SAP-Massenupload mit Begrenzung auf Ein- und Austrittsdatum

### Arbeitsmappe

- offline und ohne externe Ressourcen lauffähig
- mehrere Mitarbeitende mit eingeklapptem Archiv
- geführter Ablauf für Umfang, Rückblick, Ausblick und PDF-Erstellung
- Probezeitfälle und abweichender Gesprächsumfang
- Vollständigkeitsanzeige und verlinkte offene Punkte
- versioniertes Speichern als neue HTML-Datei
- Abschluss und Wiedereröffnung eines Falls
- Ziele und Entwicklungsziele aus dem Vorjahr als übernommene Quelleninformation
- dynamische Kompetenzbeobachtungen mit Kompetenzmodell und Formulierungshilfen
- ruhige, flache Zielbereiche mit aufklappbaren Einträgen
- PDF-Dateinamen und maschinenlesbarer MD-Datenblock

Die fachliche und funktionale Gestaltung der Arbeitsmappe ist für den aktuellen Stand
ausreichend. Die typografische Harmonisierung mit dem HR-Cockpit und dem kantonalen CD
wird in einer späteren Feinbearbeitung vorgenommen.

## Nächstes Arbeitspaket: HR-Cockpit

Das bestehende Cockpit ist ein technischer Durchstich und wird nun zu einer operativen
Arbeitsoberfläche für HR weiterentwickelt.

### 1. Informationsarchitektur und Übersicht

- klare Hauptnavigation für Übersicht, Durchläufe, Stammdaten, Versand, Rückläufe,
  SAP-Export, Auswertungen und Administration
- operative Startseite mit offenen Aufgaben statt primär technischen Formularen
- Kennzahlen für offene, überfällige, eingegangene, zu prüfende und für RPA bereite Fälle
- Aufgabenliste für fehlende Scans sowie Import-, Mail-, PDF-, Export- und RPA-Fehler
- direkte Einstiege in die jeweils erforderliche Bearbeitung

### 2. Fall- und Dialogmodell

- mehrere Dialogereignisse pro Person, Anstellung, Führungskraft und Zeitraum
- regulärer MD, Probezeit, unterjähriger MD, Standortgespräch, Übertritt, Austritt und Kein MD
- Pflicht, freiwilliger zusätzlicher Umfang und begründete Abweichung
- getrennte Fristen und Bearbeitungsstände für Rückblick und Ausblick
- genau ein führendes SAP-Ereignis bei mehreren relevanten Rückblicken

### Danach

1. SAP-Prüfung und manuelle Führungslinien vervollständigen
2. START-/Update-Dateien einzeln und gesammelt erzeugen
3. Outlook-Versand mit erzwungener S/MIME-Prüfung integrieren
4. E-Mail-Rückläufe und sämtliche Anhänge automatisiert einlesen
5. Dokumentprüfung, Korrekturen und Versionen vervollständigen
6. Erinnerungen und Fristverlängerungen umsetzen
7. SAP-Exportbatches gegen Doppelverarbeitung absichern
8. drei Muss-Auswertungen und tabellarische Exporte umsetzen
9. Audit, Backup/Restore und Betriebskonzept vervollständigen

## Empfohlener Einstieg für die nächste Sitzung

Zuerst die bestehende Oberfläche und die verfügbaren Datenfelder prüfen. Anschliessend
einen konkreten Entwurf für Navigation und operative Startseite erstellen. Noch keine
umfangreiche visuelle Feinpolitur vornehmen. Die Oberfläche soll das kantonale CD
aufgreifen, schlank bleiben und HR jeweils nur die für den nächsten Arbeitsschritt
notwendigen Informationen zeigen.

## Prüfen und starten

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s prototype/html_dialog -p "test_*.py" -v
python run_web.py
```

Beim Übergabestand waren alle 28 automatisierten Tests erfolgreich.

Weitere fachliche Details und Abnahmekriterien stehen in
[`docs/ANFORDERUNGEN.md`](docs/ANFORDERUNGEN.md).
