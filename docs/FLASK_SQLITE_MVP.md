# Flask-/SQLite-MVP für den Mitarbeitenden-Dialog

Stand: 20. September 2026

## Zielbild

SQLite ist die administrative Quelle für SAP-Datenstände, Jahresprozesse,
Führungslinien, MD-Fälle und offizielle Dokumente. Die vorgesetzten Personen
arbeiten offline in einer einzigen, längerlebigen HTML-Arbeitsmappe und spielen
neue HR-Datenstände als Update ein. Pro Mitarbeitenden werden daraus getrennte
Rückblick- und Ausblick-PDFs für Unterzeichnung und Personaldossier erzeugt.

Als offizieller Rücklauf an HR sind nur die PDFs vorgesehen. Die HTML-Arbeitsmappe
bleibt bei der vorgesetzten Person. Damit das trotzdem eine belastbare Datenquelle
für SQLite ist, enthält jedes erzeugte PDF einen kleinen sichtbaren, versionierten
MD-Datenblock mit Fall-ID, Paket-ID, Personalnummer, Ans., Jahren, Gesprächsdatum,
Zeitraum, Gesamtbeurteilung, Einigkeitsstatus und Umfang. Der Datenblock blieb im
Test nach Adobe Fill & Sign vollständig auslesbar. Inhalte wie die Ziele werden
aus den fest bezeichneten PDF-Abschnitten übernommen.

## Unterzeichnung und Rücklauf

- Rückblick und Ausblick werden in Adobe einfach elektronisch unterzeichnet und
  S/MIME-verschlüsselt an HR gesendet.
- Bei Gesamtbeurteilung D (genügend), E (ungenügend) oder Uneinigkeit müssen beide
  Parteien die erzeugten Dokumente zusätzlich handschriftlich unterzeichnen und
  den Scan beilegen.
- Die elektronischen PDFs bleiben auch in diesen Fällen die maschinenlesbare
  Originalquelle. Der Scan ist ein zusätzlicher Nachweis und wird nicht ausgelesen.
- Eine einfache Adobe-Unterschrift ist nicht zwingend eine kryptografisch
  prüfbare digitale Signatur. Deshalb wird der Eingang technisch protokolliert;
  die sichtbare Unterzeichnung wird von HR kontrolliert und bestätigt.
- Ohne Scanpflicht wird das elektronische PDF nach der HR-Prüfung in den
  Übergabeordner für die Personaldossier-Ablage verschoben.
- Mit Scanpflicht bleibt das elektronische PDF als Datenquelle im geschützten
  Verarbeitungsarchiv. Erst der handschriftlich unterzeichnete Scan wird in den
  Übergabeordner für die Personaldossier-Ablage verschoben; das elektronische Exemplar gelangt nicht
  zusätzlich ins Personaldossier.
- Fehlt ein erforderlicher Scan, wird dies im HR-Cockpit pro Rückblick und
  Ausblick ausgewiesen.
- Für «Kein MD» erzeugt die Arbeitsmappe eine administrative PDF-Bestätigung.
  Sie schliesst den Fall im Cockpit ab, wird aber nicht an das Personaldossier
  übergeben.

## Umgesetzter Durchstich

1. HR importiert einen SAP-Export im Format XLSX.
2. Die Anwendung historisiert den Import und normalisiert Personen und
   Führungslinien.
3. HR eröffnet einen Jahresprozess, zum Beispiel Rückblick 2025 und Ausblick
   2026.
4. Pro vorgesetzter Person wird eine HTML-Startdatei erzeugt.
5. Die vorgesetzte Person bearbeitet alle zugeordneten Fälle, sieht den
   Fortschritt, speichert versionierte Bearbeitungsstände und erstellt die PDFs.
6. HR liest die elektronisch unterzeichneten PDFs ein. Paket-ID, Führungslinie,
   Jahre, Fall-ID, Personalnummer, Ans. und Scanpflicht werden geprüft; die
   offiziellen Daten werden in SQLite übernommen.
7. HR bestätigt die sichtbaren Unterschriften. Die Anwendung stellt danach
   entweder das elektronische PDF oder - bei Scanpflicht - ausschliesslich den
   handschriftlichen Scan für die Personaldossier-Ablage bereit.
8. Der HTML-Rücklauf bleibt vorläufig als technischer Übergangsweg vorhanden,
   ist aber nicht Teil des Zielprozesses.

## Dateinamenskonzept

- Startdatei: `MD_Dialog_RÜCKBLICKJAHR_AUSBLICKJAHR_NACHNAME_VORNAME_PN_START.html`
- Bearbeitungsstand: gleicher Stamm plus
  `_BEARBEITET_vNN_YYYYMMDD_HHMM.html`
- Rückblick-PDF: `Rueckblick_JAHR_NACHNAME_VORNAME_PN.pdf`
- Ausblick-PDF: `Ausblick_JAHR_NACHNAME_VORNAME_PN.pdf`
- Handschriftlicher Scan: `Rueckblick_JAHR_NACHNAME_VORNAME_HANDSCAN_PN.pdf`
  beziehungsweise `Ausblick_JAHR_NACHNAME_VORNAME_HANDSCAN_PN.pdf`
- Administrative Bestätigung: `Kein_MD_RÜCKBLICKJAHR_NACHNAME_VORNAME_PN.pdf`

Bei PDFs steht die Personalnummer immer am Schluss des Dateistamms. Umlaute
werden nur im Dateinamen technisch transliteriert; in der Anwendung und den
Dokumenten bleiben sie erhalten.

## Datenmodell

- `sap_imports`: unveränderter Importnachweis mit SHA-256 und Hinweisen
- `employees`: aktueller Personenstamm pro Personalnummer
- `reporting_lines`: Führungslinien je SAP-Datenstand
- `manager_assignments`: zeitlich zugeordnete Führungsverantwortung je Anstellung
- `cycles`: Rückblick-/Ausblickjahr und verwendeter SAP-Datenstand
- `dialog_cases`: bestehender Jahresfall und Kompatibilitätsschicht für Arbeitsmappen
- `dialog_events`: fachliches Dialogereignis pro Person, Anstellung, Führungskraft
  und Zeitraum
- `document_obligations`: getrennte Pflicht und Frist für Rückblick, Ausblick
  oder Kein-MD-Bestätigung
- `package_events`: Versand- und Rücklaufhistorie inklusive Version und SHA-256
- `official_documents`: elektronische PDFs, handschriftliche Scans und
  administrative Kein-MD-Bestätigungen samt Prüf- und Übergabestatus

Das Fallmodell unterstützt mehrere Dialogereignisse pro Person. Reguläre Fälle
werden beim Eröffnen eines Durchlaufs automatisch erzeugt; Probezeit, Übertritt,
Standortgespräch und weitere unterjährige Ereignisse kann HR manuell ergänzen.
Rückblick und Ausblick werden als eigene Dokumentpflichten mit getrennten Fristen
geführt. Für den SAP-Upload lässt sich bei mehreren relevanten Rückblicken genau
ein führendes Ereignis bestimmen.

Mehrfachzeilen derselben Führungslinie werden beim Import zusammengeführt. Eine
Person kann in einem SAP-Datenstand mehreren Führungslinien zugeordnet bleiben;
dies wird nicht stillschweigend überschrieben.

## Fachliche Leitlinien aus den Vorlagen

- Rückblick: drei bis fünf relevante Kompetenzen auswählen, nicht dreizehn
  dauerhaft leere Textfelder anzeigen.
- Ausblick: ein bis zwei Entwicklungsziele als Richtwert.
- Kompetenzmodell: Kategorie, Kompetenz, Teilkompetenz und Deskriptoren. Die
  Deskriptoren werden als optionale Formulierungshilfe angezeigt.
- Vorjahresziele werden aus dem Rücklauf des vorherigen Jahres übernommen,
  sobald dieser in SQLite vorhanden ist.
- Der Umfang pro Person bleibt explizit wählbar; SAP-Daten liefern nur einen
  Vorschlag.

## Schutz und Betrieb

- Die aktuelle Version bindet ausschliesslich an `127.0.0.1` und ist für den
  Test auf einem verwalteten HR-Gerät gedacht.
- Erst- und Rückversand erfolgen S/MIME-verschlüsselt.
- S/MIME schützt nicht die lokal gespeicherte Datei. Dafür gelten Geräteschutz,
  Berechtigungen und Laufwerksverschlüsselung.
- `instance/` enthält SQLite und Prozessdateien und wird nicht in Git
  aufgenommen.
- Der Übergabeordner für die Personaldossier-Ablage liegt standardmässig unter
  `instance/data/dossier_ready`. Mit `MD_DOSSIER_HANDOFF_ROOT` kann ein anderer
  definierter lokaler oder gemounteter Ordner konfiguriert werden.
- Netzwerkzugriff wird erst nach Festlegung von Windows-Authentisierung, TLS,
  Berechtigungsmodell, Backup, Protokollierung und Betriebsverantwortung
  freigegeben.

## SAP-Massenupload IT9075

Der Export übernimmt die Spaltenstruktur der Vorlage unverändert. Befüllt werden
nur `PersNr`, `Beurteilungsart` (immer numerisch 1), `Beginndatum IT9075`,
`Endedatum IT9075`, `Ans.`, `Datum MAB`, `Beurteilungszeitraum von`,
`Beurteilungszeitraum bis` und `Gesamtbeurteilung` (nur A bis E). Die Spalten
`Zielerreichung` bis `Nächster Termin` bleiben leer.

Für den vorläufigen Gültigkeitszeitraum gilt:

- Beginn = späteres Datum aus 1. Januar des Rückblickjahres und Eintritt
- Ende = früheres Datum aus 31. Dezember des Rückblickjahres und Austritt
- dieselben Grenzen werden für IT9075 und Beurteilungszeitraum verwendet
- fehlt das Eintrittsdatum oder `Ans.`, wird der Export für den Fall blockiert
- liegt kein Tag des Rückblickjahres innerhalb der Anstellung, wird der Fall blockiert

Sobald das technische SAP-Anstellungsdatum beziehungsweise dessen Gültigkeitslogik
geklärt ist, wird diese Regel an einer zentralen Stelle ergänzt.

## Nächste Iterationen

1. Inhalte und Ziele aus den fest bezeichneten PDF-Abschnitten normalisiert
   übernehmen und für den nächsten Jahresdurchlauf bereitstellen.
2. Die vorbereitete Outlook-Integration mit dem produktiven HR-Postfach,
   Zertifikaten und der eingesetzten klassischen Outlook-Version testen und
   freigeben. Bis dahin bleibt der automatische Versand gesperrt.
3. Das vorbereitete read-only Einlesen des Outlook-Postfachs im Büro testen und
   danach das Verschieben vollständig verarbeiteter Nachrichten freigeben.
4. Einzelfallprüfung für Fremdbeilagen und fehlerhafte Zuordnungen ergänzen.
5. Backup-/Restore-Test und Rollen-/Berechtigungskonzept festlegen.
6. Barrierefreiheit und Drucklayout mit den finalen CD-Assets prüfen.
