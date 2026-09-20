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

## Weiterentwicklung HR-Cockpit

Das Cockpit besitzt nun die grundlegende Informationsarchitektur einer operativen
Arbeitsoberfläche. Als Nächstes wird das fachliche Fall- und Dialogmodell erweitert.

### 1. Informationsarchitektur und Übersicht – umgesetzt

- Hauptnavigation und fachliche Modul-Einstiege sind vorhanden.
- Die Startseite zeigt den gewählten Durchlauf, den SAP-Datenstand, heute bereits
  belastbar berechenbare Kennzahlen sowie direkte Aufgaben für SAP-Konflikte,
  START-Dateien, Unterschriftenprüfungen und fehlende Scans.
- Fristen, Überfälligkeit, Erinnerungen und Mail-/Exportfehler werden ergänzt,
  sobald das erweiterte Dialog-, Mail- und Exportmodell vorhanden ist.
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

### Danach

1. START-/Update-Dateien einzeln und gesammelt erzeugen
2. Outlook-Versand mit erzwungener S/MIME-Prüfung integrieren
3. E-Mail-Rückläufe und sämtliche Anhänge automatisiert einlesen
4. Dokumentprüfung, Korrekturen und Versionen vervollständigen
5. Erinnerungen und Fristverlängerungen umsetzen
6. SAP-Exportbatches gegen Doppelverarbeitung absichern
7. drei Muss-Auswertungen und tabellarische Exporte umsetzen
8. Audit, Backup/Restore und Betriebskonzept vervollständigen

## Empfohlener Einstieg für die nächste Sitzung

Als Nächstes die Erzeugung von START- und Update-Arbeitsmappen auf das neue
Dialogmodell umstellen. HR soll dabei einzelne Führungskräfte, Organisationseinheiten
oder den gesamten Durchlauf auswählen und vor der Erzeugung fehlende beziehungsweise
widersprüchliche Zuordnungen sehen können.

## Prüfen und starten

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s prototype/html_dialog -p "test_*.py" -v
python run_web.py
```

Beim aktuellen Stand waren alle 33 automatisierten Tests erfolgreich.

Weitere fachliche Details und Abnahmekriterien stehen in
[`docs/ANFORDERUNGEN.md`](docs/ANFORDERUNGEN.md).
