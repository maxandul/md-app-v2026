# Prototyp: eine MD-HTML-Datei pro vorgesetzter Person

Dieser Prototyp prüft, ob die heutigen Word-Dateien durch eine selbständige,
offline funktionsfähige HTML-Arbeitsdatei pro vorgesetzter Person ersetzt
werden können. Die HTML-Datei enthält alle direkt unterstellten Mitarbeitenden,
Vorjahresziele, Rückblick, Ausblick, Prozessausnahmen und den Bearbeitungsstand.

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
- kompakte, dokumentbezogene Fortschrittsblöcke mit verlinkten offenen Punkten
- freiwilliger Dokumentstand für die persönliche Arbeitsorganisation
- Erzeugung einer eigenständigen, personalisierten Datei `Vorbereitung MA`, die
  der Gesprächseinladung beigelegt werden kann
- fallabhängige Vorbereitung: Rückblickreflexion und Feedback nur bei Rückblick,
  Ausblickvorbereitung nur bei Ausblick
- getrennte PDF-Ausgaben für die private Gesprächsvorbereitung und das Feedback
  an die vorgesetzte Person
- manuelles Abschliessen und Wiedereröffnen eines Falls; abgeschlossene Fälle
  werden schreibgeschützt am Ende der aktiven Liste angezeigt
- Druckansichten für ein Rückblick- oder Ausblick-PDF je Person
- eigener Rückblick auf die Probezeit mit Anstellungsentscheid
- administratives PDF für «Kein MD», wenn dadurch ein Pflichtteil entfällt
- Begründung für einen weggelassenen Pflichtteil direkt im verbleibenden PDF
- Stammdaten bestimmen nur den Mindestumfang; zusätzliche Gesprächsteile bleiben möglich
- übernommene Vorjahresziele werden als unveränderter Quelltext angezeigt; für
  Korrekturen werden sie entfernt und bei Bedarf neu erfasst
- direktes Speichern in eine ausdrücklich ausgewählte Datei, «Kopie speichern unter …» und HTML-Download als Rückfalllösung
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

Die Arbeitsmappe führt pro Person über die Schritte `Grundlagen`,
`Vorbereitung MA`, `Rückblick`, `Ausblick` und `Prüfen und PDF`. Nicht benötigte
Schritte werden ausgeblendet.

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

### Verhalten bei Stammdaten-Updates

Die Update-Funktion ist im selbständigen HTML-Prototyp noch nicht implementiert.
Für die spätere Umsetzung gelten folgende Regeln:

- Bestehende Fälle werden anhand ihrer Fall-ID aktualisiert und nie allein wegen
  eines neuen SAP-Imports gelöscht.
- Gehört eine Person gemäss dem neuen Import nicht mehr zur vorgesetzten Person,
  werden ihre bisherigen Fälle mit allen Eingaben automatisch in den
  Archivbereich verschoben.
- Ein zukünftiges Ende der Probezeit führt nicht zur Archivierung. Der Fall bleibt
  als noch nicht fälliger Fall erhalten und soll später in einem eingeklappten
  Bereich «Später fällig» erscheinen.
- Ein manuell abgeschlossener Fall bleibt abgeschlossen, bis die vorgesetzte
  Person ihn wieder öffnet. Ein Stammdaten-Update darf diesen Zustand nicht
  zurücksetzen.

## Empfohlener Funktionstest in Microsoft Edge

1. Die erzeugte HTML-Datei auf dem persönlichen Geschäftsgerät öffnen.
2. Für eine Person den vorgeschlagenen Umfang übernehmen.
3. Pflichtfelder ausfüllen und den Fortschritt beobachten.
4. Eine Kompetenzbeobachtung und ein zusätzliches Ziel ergänzen.
5. Unter `Vorbereitung MA` die personalisierte Vorbereitungsdatei erzeugen und
   darin die zum Fallumfang passenden Abschnitte prüfen.
6. In der Vorbereitungsdatei Gesprächsvorbereitung und – bei einem Rückblick –
   Feedback getrennt als PDF ausgeben.
7. `Arbeitsmappe speichern` wählen.
8. Die gespeicherte Datei schliessen und erneut öffnen. Beim Download die neu heruntergeladene Datei verwenden.
9. Prüfen, ob Eingaben und Fortschritt erhalten geblieben sind.
10. `Rückblick als PDF` beziehungsweise `Ausblick als PDF` wählen.
11. Im Edge-Druckdialog `Als PDF speichern` verwenden und Seitenumbrüche, lange
    Texte, Umlaute sowie die vorgeschlagenen Dateinamen prüfen.

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
- Direktes Speichern benötigt die File System Access API und eine ausdrückliche Dateiauswahl. Ein Doppelklick auf die HTML-Datei gewährt noch keinen Schreibzugriff. In unterstützten Browsern wird während derselben Sitzung dieselbe gewählte Datei aktualisiert; nach erneutem Öffnen kann eine neue Auswahl nötig sein. Bei fehlender Unterstützung oder Schreibfehlern wird eine neue HTML-Datei heruntergeladen.
- Der PDF-Export verwendet vorerst den Edge-Druckdialog.
- Die technische Paketkennung steht am Dokumentende und wird nicht als
  wiederholte Browser-Fusszeile ausgegeben.
- Digital oder handschriftlich unterzeichnete PDFs bleiben separate Dateien.
- Es gibt noch keinen SQLite-Import und keine automatische Zuordnung der
  unterschriebenen PDFs.
- Die Vorbereitungsdatei versendet keine Daten automatisch. Die separate Rückgabedatei enthält ausgewählte Rückblick-/Ausblick-Vorbereitungen und Feedback, aber keine persönliche Reflexion. Das Feedback-PDF wird nach dem Gespräch separat an die Führungskraft übergeben.

Diese Punkte werden erst nach dem Edge-/Outlook-/S/MIME-Test entschieden.

## Vorbereitung mit Rückgabe und Import (1. Oktober 2026)

Unter «Vorbereitung MA» wählt die Führungskraft Reflexion, Rückblick und Ausblick aus.
«Alles auswählen» und «Auswahl aufheben» gelten für die optionalen Teile; das Feedback
ist bei einem Rückblick immer enthalten. Standardmässig ist nur die freiwillige Reflexion
ausgewählt. Vorjahresziele werden ohne bisherige Beurteilungen mitgegeben.

Mitarbeitende speichern ihren eigenen vollständigen Stand mit «Eigenen Stand speichern».
«Datei für die Führungskraft erstellen» erzeugt eine separate HTML-Datei mit `_RUECKGABE`
im Namen. Private Reflexionen werden aus dem JSON-Datenblock, gerenderten Formularen
und einer etwaigen Druckvorschau entfernt. Nur die Rückgabedatei ist zum Zurücksenden bestimmt.

«Vorbereitung importieren» prüft die Zuordnung und zeigt eine Vorschau. Nicht leere
vorhandene Angaben sind nie vorausgewählt. Eine Auswahl ersetzt den betreffenden Text
oder Ziel-/Kompetenzbereich ausdrücklich. Leere Angaben löschen keine vorhandenen Inhalte.
Die ursprünglichen Beiträge und das Feedback bleiben unter «Vorbereitung MA» erhalten.
Gesamtbewertung, Anstellungsentscheid, Gesprächsdaten und Abschluss bleiben bei der Führungskraft.

Für lokale Browsertests mit separat installiertem Playwright:

```bash
python prototype/html_dialog/create_demo.py
node --test prototype/html_dialog/test_offline_workflow.cjs
```

Optional bestimmt `MD_TEST_CHROMIUM` den Chromium-Pfad. Die Tests verwenden ausschliesslich
synthetische Demo-Daten und prüfen unter anderem Datenschutz, selektiven Import,
Zuordnungsfehler, wiederholten Import, direktes Speichern und Download-Rückfalllösungen.

Auf dem kantonalen Gerät weiterhin konkret prüfen: lokale HTML-Datei in Edge öffnen,
Arbeitsordner wählen, bestehende Datei ersetzen, mehrfach speichern, neu öffnen,
Rückgabedatei erstellen und importieren. Browserrichtlinien können direkte Schreibzugriffe sperren.
