# Prototyp: eine MD-HTML-Datei pro vorgesetzter Person

Dieser Prototyp prüft, ob die heutigen Word-Dateien durch eine selbständige,
offline funktionsfähige HTML-Arbeitsdatei pro vorgesetzter Person ersetzt
werden können. Die HTML-Datei enthält alle direkt unterstellten Mitarbeitenden,
Vorjahresziele, Rückblick, Ausblick, Prozessausnahmen und den Bearbeitungsstand.

Die bestehende produktive Anwendung wird dadurch noch nicht verändert.

## Enthaltene Funktionen

- Teamübersicht und Gesamtfortschritt
- Suche und Filter nach Bearbeitungsstand
- vier mögliche Fallumfänge:
  - Rückblick und Ausblick
  - nur Rückblick
  - nur Ausblick
  - kein MD
- Hinweis auf einen aus SAP abgeleiteten Umfang
- Vorjahresziele mit Zielerreichung und Rückblick
- dynamisch ergänzbare Kompetenzbeobachtungen
- dynamisch ergänzbare Leistungs- und Entwicklungsziele
- getrennte Vollständigkeitsprüfung für Rückblick und Ausblick
- Druckansichten für ein Rückblick- oder Ausblick-PDF je Person
- Speichern als neue, aktualisierte HTML-Datei
- eindeutige Dateistände: Versanddatei mit `_START`, gespeicherte Rücksendungen
  mit `_BEARBEITET_vNN_YYYYMMDD_HHMM`
- PDF-Namen mit dem fachlich passenden Jahr und der Personalnummer am Schluss
- maschinenlesbarer JSON-Datenblock für den späteren SQLite-Import
- Prüfung einer zurückgesendeten HTML-Datei
- keine externen Schriften, Skripte, Bilder oder Netzwerkaufrufe

## Prototyp erzeugen

Im Projektordner:

```powershell
python prototype/html_dialog/generate_package.py --rb-year 2025 --manager-pn 111116
```

Ohne `--manager-pn` wird automatisch die Führungslinie mit den meisten
eindeutigen direkt unterstellten Personen aus dem SAP-Beispielexport gewählt.
Die HTML-Datei wird im ignorierten Ordner `prototype/html_dialog/output`
erzeugt.

Ein anderer SAP-Export oder Zielpfad kann explizit angegeben werden:

```powershell
python prototype/html_dialog/generate_package.py `
  --sap "K:\Pfad\EXPORT.xlsx" `
  --rb-year 2026 `
  --manager-pn 123456 `
  --output "K:\Test\MD_Dialog_2026_2027.html"
```

Die im Prototyp angezeigten Vorjahresziele sind synthetische Platzhalter. In
der späteren Anwendung werden sie aus SQLite beziehungsweise aus dem Rücklauf
des Vorjahres übernommen.

## Empfohlener Funktionstest in Microsoft Edge

1. Die erzeugte HTML-Datei auf dem persönlichen Geschäftsgerät öffnen.
2. Für eine Person den vorgeschlagenen Umfang übernehmen.
3. Pflichtfelder ausfüllen und den Fortschritt beobachten.
4. Eine Kompetenzbeobachtung und ein zusätzliches Ziel ergänzen.
5. `Zwischenstand speichern` wählen.
6. Die neu heruntergeladene HTML-Datei schliessen und erneut öffnen.
7. Prüfen, ob Eingaben und Fortschritt erhalten geblieben sind.
8. `Rückblick als PDF` beziehungsweise `Ausblick als PDF` wählen.
9. Im Edge-Druckdialog `Als PDF speichern` verwenden.
10. PDF-Seitenumbrüche, lange Texte, Umlaute und vorgeschlagenen Dateinamen prüfen.

Jeder Speichervorgang erhöht die Versionsnummer und ergänzt einen Zeitstempel.
Damit bleiben Startdatei und Bearbeitungsstände auch ausserhalb der Anwendung
eindeutig unterscheidbar. Die offene Ursprungsdatei wird durch den Browser
nicht überschrieben.

## S/MIME- und Outlook-Test

Da die Arbeitsdatei Vorjahresdaten enthält, gelten für den produktiven Prozess:

- Erstversand durch HR ausschliesslich S/MIME-verschlüsselt
- Rückversand ebenfalls ausschliesslich S/MIME-verschlüsselt
- Bearbeitung nur auf dem persönlichen Geschäftsgerät
- keine Übertragung auf private oder mobile Geräte

Für den technischen Test werden ausschliesslich die Beispieldaten verwendet:

1. HTML-Datei an ein internes Testpostfach senden.
2. Vor dem Versand prüfen, ob Outlook die Nachricht tatsächlich verschlüsselt.
3. Anhang direkt aus Outlook und nach lokalem Speichern öffnen.
4. Prüfen, ob Skriptfunktionen, Download und Druckansicht verfügbar bleiben.
5. Gespeicherte HTML-Datei erneut S/MIME-verschlüsselt zurücksenden.
6. Prüfen, ob Outlook oder die Sicherheitsinfrastruktur den HTML-Anhang
   blockiert, umbenennt oder inhaltlich verändert.

S/MIME schützt den E-Mail-Transport und die Nachricht im Postfach. Eine lokal
gespeicherte HTML-Datei ist dadurch nicht zusätzlich verschlüsselt. Dafür sind
die Schutzmassnahmen des verwalteten Geschäftsgeräts massgebend.

## Rücklauf prüfen

```powershell
python prototype/html_dialog/validate_package.py "K:\Test\MD_Dialog_2025_2026.html"
```

Mit maschinenlesbarer Ausgabe:

```powershell
python prototype/html_dialog/validate_package.py "K:\Test\MD_Dialog_2025_2026.html" --json
```

Die Prüfung kontrolliert unter anderem:

- Schema- und Paketversion
- Paket-, VG- und Fallidentitäten
- doppelte Personalnummern
- S/MIME-Kennzeichnung
- Zeitpunkt des letzten Speicherns
- Vollständigkeit je Person und Fallumfang

## Bewusste Grenzen des Prototyps

- Outlook-Versand und S/MIME werden noch nicht automatisiert.
- Der Browser kann die geöffnete Datei nicht zuverlässig selbst überschreiben;
  Speichern erzeugt daher eine neue HTML-Datei.
- Der PDF-Export verwendet vorerst den Edge-Druckdialog.
- Die technische Paketkennung steht am Dokumentende und wird nicht als
  wiederholte Browser-Fusszeile ausgegeben.
- Digital oder handschriftlich unterzeichnete PDFs bleiben separate Dateien.
- Es gibt noch keinen SQLite-Import und keine automatische Zuordnung der
  unterschriebenen PDFs.
- Feedback an die vorgesetzte Person bleibt ausserhalb dieser Arbeitsdatei,
  damit die Vertraulichkeit des Feedbackprozesses nicht verändert wird.

Diese Punkte werden erst nach dem Edge-/Outlook-/S/MIME-Test entschieden.
