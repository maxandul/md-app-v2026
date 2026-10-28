# Umstellung auf Word-Vorlagen und PDF-Rücklauf

> Entwicklungsnachweis: Startangaben und Zwischenstände in diesem Dokument sind historisch.
> Aktuell: [MD-Web.bat und Einrichtung](START_NEUE_HR_VERSION.md).

Entscheid vom 09.10.2026: Word-Vorlagen pro Mitarbeitenden für den aktuellen
Durchlauf. Das bestehende Repository wird weitergeführt; die HTML-Arbeitsmappe
bleibt technisch erhalten und ist standardmässig ausgeblendet. Der aktuelle Teststand liegt auf `plan-b-word-pdf`.

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

## Oberfläche und Serveradresse (9. Oktober 2026)

Die Standardoberfläche verwendet Word/PDF auch in der Durchlaufübersicht. Alte
Arbeitsmappen-Einstiege und Importmasken werden nur mit `LEGACY_WORKBOOKS: "enabled"`
in der Organisationskonfiguration eingeblendet (Umgebung: `MD_LEGACY_WORKBOOKS`).
Daten und technische Kompatibilitätsrouten bleiben erhalten; dies ist keine
Berechtigungseinstellung.

`PUBLIC_BASE_URL` bzw. `MD_PUBLIC_BASE_URL` enthält den vereinbarten vollständigen
Zugriffslink für HR. Unter Administration stehen dieser Link, der Server-Rechnername
und die vom Starter gemeldete Bindung/Port. Ein abgeleiteter Rechnernamen-Link ist
nicht auf Erreichbarkeit geprüft. DNS und Serverbindung werden dadurch nicht geändert.
Weitere Angaben: [Technik](FLASK_SQLITE_MVP.md).


## Eigenständige HR-Betreuung

Im Cockpit stehen **Hilfe → Einrichtung**, die **vollständige Arbeitsliste** und
konkrete Hinweise zur Fehlerbehebung zur Verfügung. PDF-Prüfungen lassen sich als
Entwurf speichern, begründet zurückstellen und wieder öffnen. Die Warteschlange
ist durchsuchbar und in Seiten unterteilt; parallele Änderungen werden erkannt.
Eingegangene Dokumente lösen keine Nachforderung wegen offener HR-Prüfung aus.
Ungeprüfte PDF-Eingänge pausieren die Erstellung von Erinnerungen.

Unter **Stammdaten** können frühere DOCX-Ausblicke mit Vorschau importiert und
konkurrierende Zielquellen begründet ausgewählt werden. Ereignisse ohne Durchlauf
können zugeordnet, Fehlanlagen ohne Belege aufgehoben und verspätete Rückläufe
inaktiven Fällen begründet zugeordnet werden. Vor Bearbeitung geschlossener
Durchläufe diese wieder öffnen. Unterbrochene Outlook-Vorgänge dürfen erst nach
Prüfung in Outlook und Beendigung alter Serverprozesse geklärt werden.

Der Jahresabschluss verlangt eine Prüfung der externen Verarbeitung; offene
Aufgaben benötigen eine Restfallbegründung und eine verantwortliche Person.
Der Folgejahreslink bereitet das nächste Rückblickjahr vor. Die neuen Tabellen
werden beim App-Start ergänzt; bestehende Fachdaten bleiben erhalten.

Bedienung, Grenzen und Zuständigkeiten: [HR_BETREUUNG.md](HR_BETREUUNG.md).
Die Anwendung bestätigt weder SAP-Import noch Dossier-RPA-Verarbeitung automatisch.


## Beilagen und Konfiguration (10. Oktober 2026)

Jedes Word-Paket enthält zusätzlich genau eine `MD_Reflexion.docx` und eine
`NameMA_Feedback_an_{NachnameVG}_{VornameVG}_{PersonalnummerVG}.docx`.
Die Feedbackvorlage ist mit Name und Personalnummer der empfangenden Führungskraft
gefüllt. Mitarbeitendenname, Gesprächsdatum und Antworten bleiben zur Bearbeitung
offen. `NameMA` ist der Platzhalter, den Mitarbeitende beim Speichern ersetzen.
Die Führungskraft kann beide Vorlagen zur Vorbereitung weiterleiten.

Die bereitgestellten leeren Vorlagen werden unter `templates/preparation/`
mitgeliefert. Für eigene Varianten können unter `templates` in
`instance/word_config.json` zusätzlich die Schlüssel `reflection` und `feedback`
mit lokalen Dateipfaden gesetzt werden. Beim Feedback werden die Inhaltssteuerelemente
`fb_name_vg` und `fb_pn_vg` benötigt. Die anderen Felder bleiben erhalten.
Fehlende/defekte Beilagen brechen die gesamte Paketerzeugung ab. Änderungen an den
Beilagen machen bereits vorbereitete Versandpakete veraltet; diese neu erzeugen.

Unter «Geladene Konfiguration und Ablageorte» auf Versand, Rückläufe, Einrichtung
und Administration stehen der tatsächlich gelesene Pfad und die wirksamen Werte.
Standarddatei ist `instance/organisation.json`; ersatzweise werden
`organisation_config.json` und `organisatio_config.json` erkannt. Bei mehreren
Dateien wird der Start mit einer Klärungsaufforderung abgebrochen. `MD_ORG_CONFIG`
legt bei Bedarf ausdrücklich eine Datei fest. Änderungen erst nach Serverneustart
wirksam; mögliche Umgebungsvariablen-Übersteuerungen werden angezeigt. UTF-8 mit
Windows-BOM wird unterstützt. Keine zusätzliche `.txt`-Endung verwenden.

`SPECIAL_CASES_URL` ist ein optionaler HTTP(S)-Link zu den internen Spezialfallregeln.
Ein leerer Wert verhindert weder Paketerzeugung noch Outlook-Nutzung.

Word-Versandpakete liegen automatisch unter `instance/data/word_dispatch/`
(bzw. unter dem konfigurierten Prozessspeicher); einzelne Fallausgaben unter
`word_packages/`. Outlook verwendet die serverseitigen Dateien. Downloads sind
zusätzliche Kopien und müssen nicht zurückkopiert werden.
`DOSSIER_HANDOFF_ROOT` nimmt ausschliesslich freigegebene Rücklauf-PDFs auf.
Die Einstellung `data/dossier_ready` in `instance/organisation.json` bedeutet
`instance/data/dossier_ready`, da relative Pfade zur Konfigurationsdatei gehören.
Dort keine Versand-ZIPs ablegen. Die App stellt die PDFs nach der entsprechenden
Unterschriften-/Scanfreigabe selbst bereit.

## Vorjahresziele aus einem Ordner importieren

Unter **Stammdaten → Vorjahresziele aus Ordner importieren** das Zieljahr angeben
und einen Ordner oder einzelne Dateien auswählen. Unterordner werden einbezogen;
unterstützt sind alte und aktuelle DOCX-/DOCM-Ausblicke sowie textbasierte PDFs.
Die Dateien werden einzeln mit Fortschrittsanzeige übertragen (maximal 20 MB je
Datei, 5000 Dateien und 1 GB pro Auswahl). Es wird erst nach bestätigter Vorschau
in die Zieldatentabellen geschrieben.

Die Vorschau zeigt Personalnummer, Anstellung, erkanntes Zieljahr und die vier
Zielfelder. Vor der Übernahme am Original prüfen. Identische Dateien und
inhaltlich identische Ziele werden nicht doppelt übernommen. Abweichende Quellen
für dieselbe Person/Anstellung verlangen eine Auswahl. Bereits gespeicherte
abweichende Quellen bleiben erhalten; die massgebende Quelle kann anschliessend
unter «Vorjahresziele und Quellen klären» bestimmt werden.

Ein erkennbar abweichendes Zieljahr wird nicht durch die Eingabe übersteuert.
Mehrdeutige Anstellungen, Rückblicke, unlesbare Dateien und nicht sicher
zugeordnete Zielzeilen werden nicht importiert. Bild-PDFs ohne Text benötigen
Texterkennung oder das ursprüngliche Word-Dokument. Das Verfahren übernimmt die
Zieltabellen; allgemeine Bemerkungen und ergänzende Freitexte sind keine
strukturierten Vorjahresziele.

Nach dem Import die Word-Dossiers neu erzeugen. Bestehende Word-Dateien bleiben
unverändert. Die Funktion erzeugt keine offiziellen Rückläufe und löst keine
Dossier-/SAP-Übergabe aus. Das Kommandozeilenskript `import_legacy_forms.py` bleibt
verfügbar und verwendet dieselbe Word-/PDF-Erkennung.

## Feedback-Rücklauf

Word-Feedbacks haben eine eigene HR-Prüfung und Sammlung pro Führungskraft und Rückblickjahr.
Bedienung, Korrekturen, Bündelung und Nachträge: [Feedback-Rücklauf](FEEDBACK_WORD_PDF.md).

## Versandtext und Dateinamen (14. Oktober 2026)

Unter «Versand» ist die Standardmail sichtbar und für den jeweiligen Versand
bearbeitbar. Die Vorschau funktioniert bereits vor der Paketerzeugung: Führungskraft
wählen und nach Änderungen «E-Mail-Vorschau aktualisieren» anklicken. Sie erzeugt
keinen Outlook-Entwurf. Vorschau und Versand verwenden dieselbe Textaufbereitung.
Änderungen am Text gelten für den aktuellen Seitenaufruf; sie werden nicht als
neue dauerhafte Standardvorlage gespeichert.

Betreff, Dateibeispiele, Rückgabefristen und KNF-Jahr werden aus dem gewählten
Durchlauf eingesetzt (KNF: Ausblickjahr). Die Rückgabefristen werden als TT.MM.JJJJ
angezeigt. Die Standardmail orientiert sich am jährlichen Durchlauf; für
unterjährige Einzelereignisse kann HR sie vor dem Versand anpassen.

Word-Dateien tragen keine Anstellungsnummer mehr im Namen. Beispiel:
`Rückblick_2026_Nachname_Vorname_123456.docx`. Bei mehreren aktiven Fällen derselben
Person in einem Führungskraftpaket liegen die Formulare in getrennten Ordnern
`Fall_1`, `Fall_2` usw. Die internen Fall- und Anstellungszuordnungen bleiben erhalten;
bei mehrdeutigen PDF-Rückläufen muss HR die Zuordnung weiterhin prüfen.
Bereits erzeugte Versandpakete müssen neu erzeugt werden, um die neuen Dateinamen
zu erhalten. Offene Outlook-Entwürfe zuerst wie bisher klären.

## Versehentlich neu erzeugte Versandpakete

Unter «Versand» werden der letzte bestätigte Versand und die aktuelle Ausgabe
getrennt angezeigt. Die tatsächlich versendete Ausgabe bleibt dort herunterladbar.
Mit «Neue Ausgabe verwerfen» kann eine noch nicht an Outlook übergebene Ausgabe
aus der Versandauswahl genommen werden. Dateien und Versandnachweise bleiben
unverändert gespeichert. Die vorherige nicht verworfene Ausgabe ist danach wieder
massgebend; bei mehreren versehentlichen Ausgaben kann der Schritt wiederholt werden.

Offene, fehlgeschlagene oder laufende Outlook-Vorgänge können nicht auf diesem Weg
verworfen werden. Zuerst Outlook prüfen und einen vorhandenen Entwurf löschen,
dann den Entwurf in der App als verworfen markieren. Anschliessend lässt sich auch
die Ausgabe verwerfen. Bestätigte Versände lassen sich nicht verwerfen.
