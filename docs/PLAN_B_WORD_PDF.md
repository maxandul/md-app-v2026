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
einen Scan.

Nicht durchgeführte Rückblicke und Ausblicke können direkt mit der Begründung aus
dem PDF bestätigt werden. Sie werden als administrative Nachweise gespeichert,
ohne Gesprächsdatum, Beurteilung, Unterschrift oder Dossier-Bereitstellung zu
erfinden. Nur die Pflicht des eingereichten Gesprächsteils wird abgeschlossen;
der übrige Umfang bleibt erhalten. Erst wenn alle erforderlichen Teile als nicht
durchgeführt bestätigt sind, erhält der Fall den Status «Kein MD». Ein ausgefallener
Rückblick wird auch bei abgeschlossenem Ausblick nicht als SAP-Beurteilung exportiert.
Bestehende Gesprächsdokumente und widersprechende Zielquellen können dabei nicht
überschrieben werden; solche Widersprüche erfordern eine separate Fallklärung.
Nicht durchgeführte Ausblicke werden nicht als neue Zielquelle verwendet.

Die Prüfmaske erfasst auch den Wunsch nach einem Gespräch mit der nächsthöheren
Führungskraft, die Aktualität der aufgeführten Bewilligungen für Nebenbeschäftigungen
und öffentliche Ämter sowie den Laufbahnwunsch im Ausblick. Das Bewilligungsfeld ist
keine Bestätigung sämtlicher SAP-Stammdaten. «Nein» weist Klärungsbedarf aus; fehlende
Antworten bleiben offen. Die neue operative Auswertung und ihr CSV enthalten die
geprüften Angaben, Zeiträume, Leistungszielanzahl, Kompetenzen und Zeichenanzahlen.
Freitexte werden im CSV nicht ausgegeben. Gezählt werden normalisierte Textzeichen
inklusive Leerzeichen und Zeilenumbrüchen, ohne Rand-Leerraum. Ein unbekanntes oder
nicht erkanntes Feld bleibt leer; nur ein erkanntes bzw. bestätigtes leeres Feld
zählt als 0. HR kann Freitexte ergänzen und leere Felder ausdrücklich bestätigen.
Die automatische Freitextzuordnung ist layoutabhängig; nicht erkannte Felder müssen
am Original geprüft werden. Einigkeit wird auch in der Einzelfallmaske für
Word-PDF-Fälle nicht abgefragt.

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

## Word-Versand und lokale Organisation

Unter Versand ist die Word-Variante der Standard. Die Sammelauswahl unterstützt
markierte Führungskräfte, Organisationseinheiten einschliesslich Untereinheiten
und den ganzen Durchlauf. Pro Führungskraft wird ein eigenes ZIP erzeugt; das
zusätzliche Sammel-ZIP ist für HR. Eine fehlgeschlagene Sammelerzeugung hinterlässt
keine teilweise registrierte Ausgabe. Einzelne Personendownloads bleiben reine
Erzeugungen; die vollständige Führungslinien-Ausgabe steht auch für Outlook bereit.

Die Tabellen `word_dispatch_packages` und `word_mail_deliveries` protokollieren
die Word-Ausgaben unabhängig vom bisherigen Arbeitsmappenweg. Erzeugt,
Outlook-Übernahme läuft, Entwurf erstellt, Versand bestätigt und fehlgeschlagen
sind unterschiedliche Zustände. Für manuell versendete Entwürfe bestätigt HR den
tatsächlichen Outlook-Versand. Ein offener Entwurf oder fehlgeschlagener Versuch muss vor einer neuen Ausgabe
versendet oder in Outlook gelöscht und hier als verworfen markiert werden.
Die App löscht keine Outlook-Nachrichten. Bei einem nach einem Abbruch hängenden
Status «Outlook-Übernahme läuft» ist eine manuelle Klärung erforderlich; es erfolgt
keine automatische Wiederholung mit möglicher Doppelzustellung.

Vor Outlook werden Empfänger, Paketprüfsumme, Vorlage und Quelldaten geprüft.
Später eingegangene Vorjahresziele oder geänderte Stammdaten verlangen eine neue
Ausgabe. Bereits übernommene oder abgelöste Pakete sind serverseitig gesperrt.
Fehlgeschlagene Outlook-Aufrufe dürfen erst nach bestätigter Prüfung in Outlook
wiederholt werden. Der Standardtext beschreibt Word und PDF-Rücklauf, verwendet
die Du-Form und kann vor der Zustellung angepasst werden. Ein Sammelpaket wird
niemals als Anhang an alle Führungskräfte verwendet.

Organisationswerte stehen in `instance/organisation.json`; eine neutrale Vorlage
liegt unter `config/organisation.example.json`. Absender, Outlook-Postfach,
Zielordner, Dossierpfad und Spezialfälle-Link sind konfigurierbar. Die vorhandenen
Umgebungsvariablen bleiben als Overrides unterstützt. Die HTML-Alternative nutzt
dieselben konfigurierten Kontaktdaten. Die öffentliche Demo verwendet ausdrücklich
neutrale Werte und übernimmt keine lokalen Organisationsdaten.

Outlook-Zustellung wurde mit einem Testadapter geprüft. Es wurden keine echten
Nachrichten oder Entwürfe erzeugt. Der S/MIME-Nachweis mit klassischem Outlook,
Produktivpostfach und Zertifikaten bleibt Teil des Bürotests.

## Nächste Schritte

1. Echte alte PDF-Vorlagen sowie ausgefüllte Ausblick- und Probezeit-PDFs beider
   Microsoft-Exportwege für die Layoutfreigabe prüfen. Bis dahin bleibt die
   Kontrolle am Original verpflichtend. Unbekannte Vorlagen werden manuell ergänzt.
2. Gemeinsamer fachlicher Abnahmetest von Versand bis Dossier und SAP-Export.
