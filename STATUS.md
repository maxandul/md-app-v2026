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
- Ohne Scanpflicht wird das digitale PDF im Übergabeordner für die
  Personaldossier-Ablage bereitgestellt. Bei Scanpflicht wird dort ausschliesslich
  der Scan bereitgestellt.
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
- durchgängige Hauptnavigation für Übersicht, Stammdaten, Dialoge, Versand,
  Rückläufe, SAP-Export und Auswertungen
- operative Startseite mit belastbaren Kennzahlen und priorisierter Aufgabenliste
- fachlich getrennte Einstiegsseiten statt technischer Formulare auf der Startseite
- SAP-XLSX-Import mit Historisierung
- Erkennung von BG 0, identischen und widersprüchlichen Duplikaten,
  Mehrfachanstellungen und mehreren Bewilligungen
- Inaktivsetzung nicht mehr enthaltener Personen
- Eröffnung eines Jahresdurchlaufs
- automatische Dialogereignisse mit getrennten Rückblick-/Ausblickpflichten und Fristen
- manuelle unterjährige Dialogereignisse für Probezeit, Übertritt, Austritt und Standortgespräch
- zeitbezogene Zuordnung der verantwortlichen Führungskraft je Ereignis
- explizite Wahl des führenden SAP-Ereignisses bei mehreren relevanten Rückblicken
- Übersicht nach Führungskräften und Fällen
- Erzeugung einer START-Arbeitsmappe pro Führungskraft
- manueller Import maschinenlesbarer PDF-Rückläufe
- Bestätigung der sichtbaren elektronischen Unterzeichnung
- Nachverfolgung und Import erforderlicher handschriftlicher Scans
- Bereitstellung des massgebenden Dokuments im Übergabeordner für die
  Personaldossier-Ablage
- protokollierte SAP-Exportbatches mit Quellversion und Datensatz-Snapshots;
  bereits exportierte Dialogereignisse werden nicht erneut ausgegeben
- operative Gesprächszeitpunkte sowie aggregierte Verteilungen der
  Gesamtbeurteilungen und Kompetenzen mit CSV-Export und Mindestgruppengrösse

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

## Weiterentwicklung HR-Cockpit

Das Cockpit besitzt nun die grundlegende Informationsarchitektur einer operativen
Arbeitsoberfläche. Als Nächstes wird das fachliche Fall- und Dialogmodell erweitert.

### 1. Informationsarchitektur und Übersicht – umgesetzt

- Hauptnavigation und fachliche Modul-Einstiege sind vorhanden.
- Die Startseite zeigt den gewählten Durchlauf, den SAP-Datenstand, heute bereits
  belastbar berechenbare Kennzahlen sowie direkte Aufgaben für SAP-Konflikte,
  START-Dateien, Unterschriftenprüfungen und fehlende Scans.
- Fristen, Überfälligkeit und Erinnerungsstatus werden aus den getrennten
  Dokumentpflichten berechnet und in der Dialogsteuerung angezeigt.
- Die Übergabe wird fachlich als Bereitstellung für die Personaldossier-Ablage
  bezeichnet. Der nachfolgende RPA-Prozess liegt ausserhalb des Scopes.

### 2. Fall- und Dialogmodell – umgesetzt

- mehrere Dialogereignisse pro Person, Anstellung, Führungskraft und Zeitraum
- regulärer MD, Probezeit, unterjähriger MD, Standortgespräch, Übertritt, Austritt und Kein MD
- Pflicht, freiwilliger zusätzlicher Umfang und begründete Abweichung
- getrennte Fristen und Bearbeitungsstände für Rückblick und Ausblick
- genau ein führendes SAP-Ereignis bei mehreren relevanten Rückblicken
- unveränderter SAP-Standardexport mit doppelten Spaltenüberschriften wird eingelesen
- Personen und Führungslinien mit Beschäftigungsgrad 0 werden ausgeschlossen

### 3. START- und Update-Arbeitsmappen – umgesetzt

- Einzel- und Sammelerzeugung nach Führungskraft, organisatorischem Teilbaum oder Gesamtdurchlauf
- automatische Unterscheidung zwischen fehlender START-Datei, erforderlichem Update und aktuellem Stand
- ZIP-Pakete mit getrennten Verzeichnissen für START- und Update-Dateien
- Update-Dateien mit Änderungsvorschau direkt in der Offline-Arbeitsmappe einlesbar
- neue Fälle werden ergänzt, weggefallene Fälle archiviert und vorhandene Gesprächsinhalte bewahrt
- offene blockierende SAP-Konflikte und fehlende Anstellungsnummern verhindern die Erzeugung
- neue SAP-Importe aktualisieren offene Durchläufe und lösen bei Änderungen Updates aus
- Führungskräfte, die selbst wegen BsGrd 0 nicht aktiv sind, erhalten keine Arbeitsmappe
- manuelle, einem Durchlauf zugeordnete Dialogereignisse werden in Arbeitsmappen aufgenommen

### Nächste Schritte

1. Audit, Backup/Restore und Betriebskonzept vervollständigen

## Empfohlener Einstieg für die nächste Sitzung

Als Nächstes Audit, Backup/Restore und Betriebskonzept vervollständigen. Die
vorbereiteten Outlook-Funktionen werden parallel im Büro mit dem produktiven
HR-Postfach, den Zertifikaten und der konkreten klassischen Outlook-Version geprüft.

## Prüfen und starten

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s prototype/html_dialog -p "test_*.py" -v
python run_web.py
```

Beim aktuellen Stand waren alle 36 automatisierten Tests erfolgreich; zusätzlich
wurde die JavaScript-Syntax der Offline-Arbeitsmappe geprüft.

Weitere fachliche Details und Abnahmekriterien stehen in
[`docs/ANFORDERUNGEN.md`](docs/ANFORDERUNGEN.md).
