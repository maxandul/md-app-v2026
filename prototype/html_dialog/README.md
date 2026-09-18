# Prototyp: eine MD-HTML-Datei pro vorgesetzter Person

Dieser Prototyp prüft, ob die heutigen Word-Dateien durch eine selbständige,
offline funktionsfähige HTML-Arbeitsdatei pro vorgesetzter Person ersetzt
werden können. Die HTML-Datei enthält alle direkt unterstellten Mitarbeitenden,
Vorjahresziele, Rückblick, Ausblick, Prozessausnahmen und den Bearbeitungsstand.

Die bestehende produktive Anwendung wird dadurch noch nicht verändert.

## Enthaltene Funktionen

- Teamübersicht und Gesamtfortschritt
- kompakte Teamübersicht mit eingeklapptem Archiv
- vier mögliche Fallumfänge:
  - Rückblick und Ausblick
  - nur Rückblick
  - nur Ausblick
  - kein MD
- Hinweise auf erkennbare Spezialfälle sowie Link zur vollständigen Dokumentation
- Vorjahresziele mit Zielerreichung und Rückblick
- manuelles Ergänzen fehlender Leistungs- und Entwicklungsziele des Vorjahres
- dynamisch ergänzbare Kompetenzbeobachtungen
- dynamisch ergänzbare Leistungs- und Entwicklungsziele
- getrennte Vollständigkeitsprüfung für Rückblick und Ausblick
- Druckansichten für ein Rückblick- oder Ausblick-PDF je Person
- eigener Rückblick auf die Probezeit mit Anstellungsentscheid
- administratives PDF für «Kein MD», wenn dadurch ein Pflichtteil entfällt
- Begründung für einen weggelassenen Pflichtteil direkt im verbleibenden PDF
- Stammdaten bestimmen nur den Mindestumfang; zusätzliche Gesprächsteile bleiben möglich
- Speichern als neue, aktualisierte HTML-Datei
- eindeutige Dateistände: Versanddatei mit `_START`, gespeicherte Rücksendungen
  mit `_BEARBEITET_vNN_YYYYMMDD_HHMM`
- PDF-Namen mit dem fachlich passenden Jahr und der Personalnummer am Schluss
- maschinenlesbarer JSON-Datenblock für den späteren SQLite-Import
- Prüfung einer zurückgesendeten HTML-Datei
- keine externen Schriften, Skripte, Bilder oder Datenabrufe; einzig der Link zur
  internen Dokumentation der Spezialfälle führt ins ZHub

## Prototyp erzeugen

### Direkt verfügbare Demo

Die Datei `demo/MD_Arbeitsmappe_Demo.html` kann ohne Installation direkt im
Browser geöffnet werden. Sie enthält ausschliesslich synthetische Fälle:

- regulärer MD in Bearbeitung
- vollständiger MD mit D-Beurteilung und Uneinigkeit
- Probezeitfall mit Probezeitrückblick und Anstellungsentscheid
- Pensionierung mit «Kein MD»
- freiwillig ergänzter regulärer Rückblick nach einem Probezeitdialog
- unterjährige Standortnotizen
- archivierte Person

Die Demo wird reproduzierbar neu erzeugt mit:

```powershell
python prototype/html_dialog/create_demo.py
```

Die Arbeitsmappe führt pro Person über die Schritte `Grundlagen`, `Rückblick`,
`Ausblick` und `Prüfen und PDF`. Nicht benötigte Schritte werden ausgeblendet.

### Arbeitsmappe aus SAP-Beispieldaten erzeugen

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

### Probezeit-Arbeitsmappe erzeugen

Der Probezeitrückblick ist eine eigene Gesprächsart innerhalb desselben
Kalenderjahres. Dadurch kann für dieselbe Person zusätzlich ein regulärer MD
bestehen. Für einen Probezeit-Test kann eine entsprechende Arbeitsmappe erzeugt
werden:

```powershell
python prototype/html_dialog/generate_package.py `
  --rb-year 2026 `
  --manager-pn 123456 `
  --dialog-type probation
```

Die Probezeit-Arbeitsmappe verwendet den abweichenden Aufbau der bestehenden
Vorlage: Leistung und Einführungsziele, ausgewählte Kompetenzen, Bemerkungen zum
Gespräch und Anstellungsentscheid. Sie enthält keine reguläre Gesamtbeurteilung.
Die aus den Stammdaten abgeleitete Vorgabe ist auch hier ein Mindestumfang. Ein
zusätzlicher Ausblick kann freiwillig geführt werden. Nur wenn ein verpflichtender
Probezeitrückblick oder Ausblick weggelassen wird, ist nach vorgängiger Absprache
mit HR eine Begründung erforderlich.

### Zusammenspiel von Probezeit und Jahresdialog

- Ein Stammdaten-Update ergänzt für einen Neueintritt einen eigenständigen
  Probezeitfall. Der Fall bleibt beim nächsten Update erhalten.
- Der reguläre Jahresdurchlauf ergänzt später einen separaten Jahresfall und
  ersetzt den Probezeitfall nicht.
- Endet die Probezeit in der zweiten Jahreshälfte, ist im Jahresdialog nur der
  Ausblick verpflichtend. Die vorgesetzte Person darf freiwillig auch einen
  regulären Rückblick durchführen.
- Fällt das Probezeitende in die Bearbeitungszeit des Jahresdialogs von November
  bis Februar, dürfen beide Anlässe im selben Gespräch behandelt werden. In der
  Arbeitsmappe bleiben sie als zwei Fälle erkennbar und erzeugen getrennte PDFs:
  den Probezeitrückblick und den regulären Ausblick.
- Die spätere SQLite-Umsetzung muss deshalb mehrere Fälle je Kombination aus
  Person, vorgesetzter Person und Jahr erlauben und Updates fallbezogen
  zusammenführen, statt bestehende Fälle zu überschreiben.

## Empfohlener Funktionstest in Microsoft Edge

1. Die erzeugte HTML-Datei auf dem persönlichen Geschäftsgerät öffnen.
2. Für eine Person den vorgeschlagenen Umfang übernehmen.
3. Pflichtfelder ausfüllen und den Fortschritt beobachten.
4. Eine Kompetenzbeobachtung und ein zusätzliches Ziel ergänzen.
5. `Arbeitsmappe speichern` wählen.
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
- Rückversand der unterzeichneten PDFs ebenfalls ausschliesslich S/MIME-verschlüsselt
- Bearbeitung nur auf dem persönlichen Geschäftsgerät
- keine Übertragung auf private oder mobile Geräte

Für den technischen Test werden ausschliesslich die Beispieldaten verwendet:

1. HTML-Datei an ein internes Testpostfach senden.
2. Vor dem Versand prüfen, ob Outlook die Nachricht tatsächlich verschlüsselt.
3. Anhang direkt aus Outlook und nach lokalem Speichern öffnen.
4. Prüfen, ob Skriptfunktionen, Download und Druckansicht verfügbar bleiben.
5. Ein Test-PDF S/MIME-verschlüsselt an das HR-Testpostfach zurücksenden.
6. Prüfen, ob Outlook oder die Sicherheitsinfrastruktur die versandte
   Arbeitsmappe oder die zurückgesendeten PDFs blockiert oder verändert.

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
