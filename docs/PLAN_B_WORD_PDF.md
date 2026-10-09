# Umstellung auf Word-Vorlagen und PDF-Rücklauf

Entscheid vom 09.10.2026: Word-Vorlagen pro Mitarbeitenden für den aktuellen
Durchlauf. Das bestehende Repository wird weitergeführt; die HTML-Arbeitsmappe
bleibt erhalten. Die Implementierung beginnt auf `plan-b-word-pdf`.

## Implementierter Stand

In der Führungslinie erzeugt das Cockpit ein ZIP mit den benötigten Formularen
pro Person. Wahlweise kann eine einzelne Person gewählt werden. Der bestätigte
Umfang hat Vorrang vor dem SAP-Vorschlag; Fälle ohne Dokumentpflicht werden
übersprungen. Probezeit-Ereignisse verwenden die Probezeitvorlage. Bestehende
Spezialfall-/Umfangsregeln wurden in diesem Schritt nicht geändert.

Stammdaten, Zeitraum und vorhandene Nebenbeschäftigungen werden frisch aus der
Datenbank gelesen. Der Rückblick erhält die Ziele des zugehörigen Zieljahres und
der Anstellung. Bei mehreren konkurrierenden Quellen oder unbekannter Kompetenz
wird die Erzeugung angehalten, statt Ziele zu vermischen oder wegzulassen.
Bestätigte PDF-Ausblicke liefern versionierte Zielquellen; reine Uploads noch nicht.

Zusätzliche Zielzeilen werden dynamisch erzeugt. Leere Entwicklungszielzeilen
bleiben bei jeder Kompetenz bestehen. Zieltexte werden einheitlich in 9 pt mit
Zeilenumbrüchen und sichtbaren Listenzeichen ausgegeben. Tabellenüberschriften
einschliesslich Kompetenz werden bei Seitenfortsetzungen wiederholt. Alte,
unsichtbare Datumswerte der Vorlagen werden entfernt; Gesprächs- und
Unterschriftsdatum werden nicht vorbelegt.

Jede Ausgabe erhält ein eigenes Verzeichnis unter `STORAGE_ROOT/word_packages`
mit ZIP und Manifest (Fall, Zeitraum, Zielquelle und Prüfsummen). Sie wird als
Erzeugung im Administrationsprotokoll erfasst und verändert weder den Versand-
noch den Rücklaufstatus. Eine neue Erzeugung berücksichtigt nachträglich
importierte Ziele. Bereits ausgegebene oder lokal bearbeitete Word-Dateien
werden dadurch nicht verändert. Bei einem Fehler wird keine Teilausgabe
behalten.

Unter **Rückläufe → Word-PDFs einlesen** werden PDFs dauerhaft in einer
Prüfwarteschlange gespeichert. Die Erkennung liest Grundangaben und rekonstruiert
gefärbte Tabellenzellen aus den PDF-Zeichenoperationen. Beide Microsoft-Wege
(Rechtecke beim Speichern, Pfade beim Drucken) werden unterstützt. Texte werden
normalisiert; sichtbare Aufzählungen und nummerierte Schritte bleiben erhalten.
Schriftarten, Fettdruck und ursprüngliche Absatzabstände werden nicht zugesichert.
Silbentrennung am Zeilenende wird heuristisch bereinigt und muss mitgeprüft werden.
Original-PDF, Rohtext und erkannte Zellinhalte bleiben als Nachweis erhalten.

HR prüft und korrigiert Person, Anstellung, Zeitraum, Ziele und aktuelle
Kompetenz-Einschätzungen am Original. Die Gesamtbeurteilung und bei Probezeit der
Anstellungsentscheid werden ausdrücklich geprüft. Nur aktuelle, gefüllte
Einschätzungen gehen in die Kompetenzauswertung ein; Vorjahresziele nicht.
Einigkeit wird weder abgefragt noch abgeleitet. Ein zusätzlich benötigter
handschriftlicher Scan kann unabhängig davon angegeben werden.

Fallvorschläge verwenden PN und Dokumentzeitraum, nicht das Gesprächsjahr.
Anstellung und konkreter Fall müssen bestätigt werden. Abweichende Führungskraft,
Zeitraum oder unlesbare Grundangaben erfordern eine Prüfnotiz. Erst danach werden
Fachdaten übernommen. Die vorhandene Unterschriften-/Ablageprüfung bleibt ein
separater Schritt; Bewertungen D/E und negative Probezeitentscheide verlangen
einen Scan. Nicht durchgeführte Rückblicke bleiben vorerst in der Prüfung und
werden über die bestehende Kein-MD-Fallklärung erledigt.

Ausblicke lassen sich auch ohne damaligen Cockpit-Fall als nachgereichte Zielquelle
übernehmen. Sie gelten für PN, Anstellung und Zieljahr und werden bei der nächsten
Word-Erzeugung berücksichtigt. Frühere Zielversionen bleiben gespeichert;
Ersetzungen benötigen einen Grund. Konkurrierende Quellen aus alten DOCX-Importen
oder Arbeitsmappen werden weiterhin nicht automatisch zusammengeführt.
Doppelte Dateien werden anhand ihrer Prüfsumme erkannt; identische bestätigte
Fachinhalte werden auch bei unterschiedlichen PDF-Dateien als Dublette abgeschlossen, ohne erneut Fachdaten zu importieren.
Bereits zur Ablage bereitgestellte Fall-Dokumente können nicht ersetzt werden.

Postfacheingänge mit erkennbarer Word-MD-Überschrift oder MD-Dateinamen werden in
dieselbe Warteschlange geleitet. Solange die PDF-Prüfung offen ist, kann die
Mailprüfung nicht als erledigt markiert werden. Es erfolgt keine automatische
Ablagefreigabe für ungeprüfte Word-PDFs. Arbeitsmappen-PDFs behalten ihren Importweg.

**Verifikation:** Die beiden bereitgestellten Microsoft-PDFs ergeben dieselben
sechs Leistungsziele und vier Entwicklungsziele mit korrekten Kompetenzen.
Die aktuellen Einschätzungen sind in beiden Beispielen leer und zählen als null.
Automatisierte Tests prüfen Geometrie beider Zeichenwege, Listen, Fall-/Jahrprüfung,
Nachreichungen, Versionierung, inhaltliche Dubletten, Ablage und Postfachwarteschlange.

**Grenze bei Altvorlagen:** Unbekannte Layouts und Scans bleiben manuell prüfbar.
Ziele und Einschätzungen können in der Prüfmaske ergänzt werden. Es gibt keine
OCR und keine Freigabe einer automatischen Extraktion für beliebige Altvorlagen.
Ein synthetisch abweichendes Formular wurde für den manuellen Weg getestet;
echte historische Rücklauf-PDFs stehen für einen Layouttest noch aus.

## Lokale Word-Vorlagen einrichten

1. `config/word.example.json` nach `instance/word_config.json` kopieren.
2. Die drei freigegebenen DOCX-Vorlagen unter `instance/templates/` ablegen
   und die Dateinamen in der Konfiguration anpassen. Relative Pfade beziehen
   sich auf den Ordner der Konfigurationsdatei; absolute Pfade sind möglich.
3. App neu starten. Die Führungslinie zeigt an, welche Vorlagen noch fehlen.

Alternativ verweist die Umgebungsvariable `MD_WORD_CONFIG` auf eine andere
lokale JSON-Datei. `instance/` sowie DOCX/PDF-Dateien sind bereits vom Commit
ausgeschlossen. Die Beispieldatei enthält keine internen Links oder Pfade.
Die Originalvorlagen müssen die freigegebenen Feldkennungen enthalten; eine
falsche oder veraltete Vorlage führt zu einem verständlichen Fehler.

Die neuen Module benötigen nur die Python-Standardbibliothek und vorhandene
Projektabhängigkeiten. Word/LibreOffice ist zur Erzeugung auf dem HR-Gerät
nicht erforderlich; die Führungskraft öffnet und bearbeitet die DOCX in Word.

## Nächste Schritte

1. Word-Versand: Sammelauswahl über mehrere Führungslinien, Outlook-Anbindung
   und Versandstatus. Die reine Word-Erzeugung ist bereits umgesetzt.
2. Echte alte PDF-Vorlagen sowie ausgefüllte Ausblick- und Probezeit-PDFs beider
   Microsoft-Exportwege für die Layoutfreigabe prüfen. Bis dahin bleibt die
   Kontrolle am Original verpflichtend. Unbekannte Vorlagen werden manuell ergänzt.
3. Den Nichtdurchführungs-/Kein-MD-Weg direkt in die neue PDF-Prüfung integrieren.
4. Organisationsspezifische Links und Pfade aus bestehendem Code in lokale
   Konfiguration verschieben. Lokale Vorlagen, PDFs und Konfigurationen bleiben
   vom öffentlichen Repository ausgeschlossen.
5. Gemeinsamer fachlicher Abnahmetest von Versand bis Dossier und SAP-Export.
