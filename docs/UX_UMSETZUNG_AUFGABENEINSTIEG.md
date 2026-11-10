# Aufgabeneinstieg – erster integrierter Stand

Der Entwurf ist in die bestehende Flask-Anwendung übertragen. Einstieg ist `/start`;
`/arbeit` bleibt der filterbare Arbeitsvorrat, bestehende Detailadressen bleiben gültig.

## Enthalten

- Startseite mit Aufgaben für ordentlichen Durchlauf, laufende Arbeit und Änderungen.
- Navigation: Start, Gespräche, Eingänge, Versand, Daten & Auswertung. Ergänzende
  Links erscheinen im jeweiligen Bereich. Hilfe und Administration bleiben separat.
- Namen, OE, Funktion und aktuelle direkte Vorgesetzte in den Personenlisten,
  Gesprächsteilen, Zielquellen und im Arbeitsvorrat. Technische Nummern sind aufklappbar.
- Aktuelle Vorgesetzte stammen aus gültigen aktiven Zuordnungen je Anstellung.
  Mehrfachanstellungen werden nicht auf eine beliebige erste Zuordnung reduziert.
  Die Verantwortung für einen Gesprächsteil wird separat aus der bestehenden
  Fachzuordnung angezeigt; ein Wechsel der direkten Vorgesetzten verändert sie nicht.
- Gesprächsübersicht mit Namenssuche, Verantwortungssuche, Sortierung nach
  Mitarbeitenden oder verantwortlicher Führungskraft, Arbeitsstand, Überfälligkeit,
  Jahr, OE und serverseitiger Seitennavigation.
- Zielübernahme mit bestehendem Ablauf von Prüfung über Dateierstellung und
  Dateiprüfung bis zum dokumentierten Versand im neuen Anwendungsrahmen.
- Kompaktere Formulare und Tabellen; mobile Navigation bei schmalen Ansichten.

## Bewusst noch bestehende Bedienwege

Fristen und Erinnerungen lassen sich jetzt direkt aus einer seitenübergreifenden
Gesprächsauswahl vorbereiten. Die bisherigen Durchlaufansichten bleiben erreichbar.
Der genaue Umfang und die Schutzmechanismen sind unter «Zweite Etappe» beschrieben.

Die Verwaltung von Formularversionen und erwarteten Steuerelementen bleibt V01
im Aufgaben- und UX-Konzept. Die einzelnen alten Fachformulare sind noch nicht
vollständig neu gestaltet. Es gibt keine neue Versandpflicht für Intranet-Rückläufe,
keine Änderung der fachlichen Rücklaufzuordnung und keine Datenmigration.

## Prüfung

Gezielte Integrationstests prüfen insbesondere aktuelle gegenüber historischer
Gesprächsverantwortung, Mehrfachanstellungen, Namenssuche, Status-/Fristfilter und
den Rückweg in die aufrufende Liste. Die bestehenden Tests zu Zielübernahme,
Rücklauf, Word-Erstellung, Versand und Berechtigungen bleiben massgeblich.
Browserprüfung mit isolierter synthetischer Datenbank: Startseite, Zielübersicht
und Suche nach verantwortlicher Führungskraft. Keine echten HR-Daten und keine
Outlook-Aktionen während der Prüfung.

## Zweite Etappe: gemeinsame Gesprächsauswahl und Aktionen

- Checkboxen dieser Seite werden beim Seitenwechsel oder beim Öffnen der
  Aktionsvorschau gespeichert. «Alle gefilterten Gesprächsteile auswählen» hält
  genau die aktuelle Treffermenge fest. Später neu hinzukommende Treffer werden
  nicht automatisch ergänzt. Ein neuer Filterlauf beginnt eine neue Auswahl.
- Die Auswahl ist an die Browsersitzung gebunden, revisioniert und 24 Stunden
  gültig. Eine zweite Registerkarte kann eine veraltete Auswahl nicht überschreiben.
- Die Vorschau zeigt Namen, betroffene Teile, Verantwortung und alte/neue Frist
  beziehungsweise Empfänger und vollständige Nachrichten. Berücksichtigte und
  ausgeschlossene Teile werden getrennt gezählt und mit Gründen angezeigt.
  Vorschautabellen zeigen höchstens 50 Einträge pro Seite.
- Änderungen an Frist, Zustand, Zuständigkeit, Empfänger oder ungeklärten Eingängen
  machen eine Vorschau ungültig. Vor der Ausführung wird die unveränderte Grundlage
  nochmals unter der bestehenden Prozesssperre geprüft.
- Fristen werden für genau die geprüfte zulässige Teilmenge geändert. Änderung und
  Protokoll je bestehender Pflicht werden gemeinsam in einer Datenbanktransaktion
  gespeichert. Die reguläre Durchlauffrist bleibt unverändert. Im bestehenden
  Fristprotokoll wird der Geltungsbereich `case` je betroffener Pflicht verwendet.
- Erinnerungen verwenden dieselben Fachregeln und denselben Outlook-Adapter wie
  die bisherigen Ansichten, eingeschränkt auf die konkrete Auswahl. Gruppierung
  nach Durchlauf und tatsächlicher Gesprächsverantwortung. Ein fehlender erfasster
  Vorlagenversand verhindert die Anerkennung eines Rücklaufs nicht.
- Bereits eingegangene oder abgeschlossene Unterlagen werden nicht erneut als
  fehlend angefordert. Offene Scanpflichten behalten ihre spezifische Anforderung.
  Ungeklärte Eingänge und offene Outlook-Vorgänge bleiben fachliche Sperren.
- Vor Outlook wird ein dauerhafter Vorgang reserviert und mit der Aktion verknüpft.
  Bekannte Ergebnisse werden je Empfänger festgehalten. Bei Teilfehlern zeigt das
  Ergebnis die tatsächlich dokumentierten Entwürfe. Ein unklarer Ausgang führt
  zu keiner automatischen Wiederholung. Der tatsächliche Versand wird separat
  geprüft und bestätigt; die Erstellung eines Entwurfs ist kein Versandnachweis.
- Migration `006_part_actions` ergänzt Auswahlen, Vorschauen und die Zuordnung zu
  Erinnerungsvorgängen. Bestehende Pflichten und fachliche Status werden weder
  kopiert noch in eine zweite Aufgabenverwaltung überführt.

Prüfung: 365 Python-Tests und elf JavaScript-Tests erfolgreich. Die neuen Tests
prüfen unter anderem Seitenwechsel, festgehaltene Treffermengen, Sitzungsgrenzen,
veraltete Revisionen, CSRF, atomare Friständerungen, Rückläufe ohne Versand,
getrennte Verantwortung, späte Eingänge, Outlook-Fehler und Teilergebnisse.
Browserprüfung mit erfundenen Personen: Checkboxen, Auswahlanzeige, Fristvorschau,
Ausführung und Ergebnisrückmeldung sowie Erinnerungsausschlüsse. Der echte
Outlook-Zugriff ist in der Browser-Testumgebung gesperrt.

![Ergebnis einer Fristanpassung mit ausschliesslich erfundenen Testpersonen](images/ux-fristen-test.png)

## Dritte Etappe: Eingänge und Prüfung nach Aufgaben

Die bisherige lange Eingangsseite ist im regulären HR-Modus in drei Ansichten
aufgeteilt: «Dokumente prüfen», «Nachweise & Ablage» und «Postfach». Ihre offenen
Zähler gelten über alle Jahre und Durchläufe. Die jeweilige Liste bleibt
serverseitig paginiert. Feedback-Bündel und alte Zielquellen sind direkt verlinkt.

Die Dokumentliste lässt sich nach Name oder Datei durchsuchen. Sie zeigt Name,
OE und aktuelle direkte Führungskraft; ausgelesene Angaben bleiben ausdrücklich
als ungeprüfte Vorschläge gekennzeichnet. Übernommene Rückläufe führen zur
bestehenden Nachweis-/Ablagebearbeitung, historische Ziele zur Zielbearbeitung.
Daten und Zeitpunkte werden im Eingangsbereich in Schweizer Schreibweise gezeigt.

In der PDF-Prüfung werden Person und Anstellung über eine Namenssuche gewählt.
Die Beschriftung enthält OE, Funktion und aktuelle direkte Führungskraft;
technische Nummern stehen separat. Der Server leitet Personal- und
Anstellungsnummer aus der gewählten Anstellung ab. Manipulierte versteckte
Nummern können diese Auswahl nicht übersteuern. Eine leere oder ungültige Auswahl
kann nicht bestätigt werden. Mehrfachanstellungen ohne eindeutige Grundlage
werden nicht automatisch auf eine beliebige erste Anstellung reduziert. Die
Gesprächsvorschläge nennen die tatsächlich zugeordnete Gesprächsverantwortung.

Ein Rücklauf aus einer Intranet-Vorlage benötigt keinen erfassten Vorlagenversand.
Die bestehenden fachlichen Prüfungen der Person, Anstellung, Zeiträume und Inhalte
bleiben erhalten. Es wird kein Versand nachgetragen und keine neue Zuordnung
allein aus einem Dateinamen abgeleitet. Fehlt ein passender Gesprächsvorgang,
bleibt die bestehende manuelle Klärung notwendig.

«Kein MD-Dokument» bleibt eine eigene reversible Aktion ohne Pflichtfelder für
MD-Daten. Auch der Mailanhang zeigt den Ausschluss ausdrücklich. Die übrigen
Anhänge und das Mailanliegen werden dadurch nicht automatisch abgeschlossen.
Bei gesperrten Erinnerungen sind die ungeprüften PDF-Dateien konkret verlinkt;
nach ihrer Bearbeitung ist die Erinnerungsvorschau erneut zu prüfen.

Der Postfachbereich zeigt standardmässig alle offenen Mailanliegen einschliesslich
Fehlern. Einstellungen und Verarbeitungserklärungen sind dort gebündelt.
«Prüfung erledigt» verschiebt weiterhin keine Mail. Mailaktionen erhalten einen
lokalen gefilterten Rückweg, externe Rücksprungziele werden verworfen. Alte
Postfach-Lesezeichen und Suchparameter bleiben erreichbar.

Validierung: zwölf zusätzliche Integrationstests zu getrennten Ansichten,
Namenssuche, Seitennavigation, Mehrfachanstellungen, kanonischer Personenauswahl,
Ausschluss und Originalerhalt, Rückläufen ohne Versand, offenen Mailfehlern sowie
sicheren Rückwegen. Browserprüfung der Ansichten, Namenssuche, PDF-Personenwahl
und alten Postfach-Lesezeichen mit ausschliesslich erfundenen Testpersonen.
Keine Postfachprüfung, Nachricht oder externe Dossierübergabe im Browser ausgelöst.

![Eingangsbereich mit ausschliesslich erfundenen Testpersonen](images/ux-eingaenge-test.png)

## Vierte Etappe: Versand fortsetzen und Nachweise erhalten

«Versand» öffnet eine gemeinsame, serverseitig paginierte Übersicht über reguläre
Pakete, Einzelausgaben und Rückblicke mit nachgereichten Zielen. Gesucht wird nach
Namen, Empfänger oder OE; Versandstand, Art und Rückblickjahr sind filterbar.
Die aktuelle Versandadresse ist vor der Outlook-Übergabe sichtbar, danach die
zum Vorgang gespeicherte Adresse. Einzelausgaben verwenden die tatsächlich im
Manifest gespeicherte Gesprächszuständigkeit statt der ursprünglichen Führungslinie.

Für ein reguläres Paket gibt es eine eigene Detailansicht: Dateien herunterladen,
enthaltene Personen und Gesprächsteile prüfen, personalisierte Nachricht ansehen
oder bearbeiten, genau diesen Outlook-Entwurf erstellen und anschliessend den
wirklichen Versand dokumentieren. Die Prüfaussage benennt Dateien, Empfänger und
Nachricht ausdrücklich. Sie führt keinen zusätzlichen dauerhaften Freigabestatus
ein. Dateiliste und Versandübersicht haben getrennte Seitennavigation.

Fehlgeschlagene und unterbrochene Outlook-Vorgänge haben konkrete Klärungsaktionen.
Die Detailansicht verschickt keine Nachricht direkt. Die bestehende Sammelbearbeitung
bleibt für den regulären Durchlauf erreichbar. Die Nachrichtenvorschau berücksichtigt
auch Führungskräfte, die nur für einen neu zugewiesenen Gesprächsteil zuständig sind.

Eine erneut erzeugte Ausgabe setzt einen früher bestätigten Versand nicht zurück.
Die neue Ausgabe verlinkt den bisherigen Nachweis; der Verlauf enthält auch
abgelöste und ausdrücklich verworfene Dateien. «Offen» bezeichnet die gespeicherten
Versandvorgänge. Spätere Stammdatenänderungen sind weiterhin im Durchlauf zu prüfen;
ein früherer Versand ist keine Bestätigung dieser späteren Änderungen.

Die neue Oberfläche nutzt die bestehenden Versand-, Datei- und Quellenprüfungen
sowie Outlook-Sperren. Vor jeder Entwurfserstellung werden diese erneut ausgeführt.
Unbekannte Aktionen und fehlende explizite Prüfaussagen werden abgewiesen. Neue
POST-Aktionen sind mit CSRF geschützt. Gefilterte Rückwege bleiben bei Paket-,
Einzel- und Zielversand erhalten; externe Rücksprungziele werden verworfen.

Validierung: 395 Python-Tests und elf JavaScript-Tests erfolgreich. Zwölf neue
Integrationstests zu den drei Versandarten, Namen und
abweichender Gesprächszuständigkeit, Zustandsübergängen, erhaltenem Versandnachweis,
veralteten Quelldaten, manipulierten Dateien, abgelösten Ausgaben, Seitenwechseln,
CSRF, Sandbox-Sperre und Rückwegen. Browserprüfung der Namenssuche, Versandart,
Paketansicht, enthaltenen Personen, bearbeiteten personalisierten Vorschau und
des gefilterten Rückwegs mit ausschliesslich erfundenen Personen. Keine Nachricht
oder externe Übergabe im Browser ausgelöst.

![Versandübersicht mit ausschliesslich erfundenen Testpersonen](images/ux-versand-test.png)

## Fünfte Etappe: Durchlaufstart und Stammdatenfolgen verbinden

«Durchlauf beginnen oder fortsetzen» führt zu `/durchlauf`. Die Ansicht verbindet
Stammdatenprüfung, Gesprächsaufträge/Fristen und Vorlagenversand. Vorhandene Jahre
werden zur Fortsetzung angeboten. Eine erneute Anlage desselben Jahres öffnet den
bestehenden Durchlauf; es entsteht kein zweiter Auftrag. Neue Durchläufe verwenden
den zuletzt übernommenen Datenstand. Hat er sich seit dem Öffnen geändert, ist die
Grundlage neu zu prüfen. Die vorhandene Fachfunktion legt Aufträge und Fristen an;
dabei entstehen keine Word-Dateien oder Versandnachweise.

Die Übersicht zeigt vorhandene Gesprächsteile und reguläre Ausgaben getrennt.
Zählungen gelten nicht als inhaltliche Freigabe und ein früherer Versand bestätigt
keine späteren Datenänderungen. Die Gesprächsliste lässt sich für das Rückblickjahr
öffnen. Die SAP-Zähler beziehen sich ausdrücklich auf alle Abgleiche; der gewählte
Durchlauf ist ein Arbeitskontext, keine Beschränkung der allgemeinen Datenübernahme.

Der SAP-Abgleich hat getrennte Einstiege für «Datenprüfung offen» und «Daten
übernommen – Gesprächsfolgen offen». Zähler und Filter folgen den bestehenden
Abgleicheinträgen und berücksichtigen abgelöste Vorschauen nicht als offene Arbeit.
In Vorschau, Einzelauswahl und Vergleich werden OE, Funktion und die Namen der
Führungskräfte gezeigt; Nummern stehen in den Zuordnungsdetails. Im neuen Export
enthaltene Namen werden als solche verwendet. Unbekannte Zuordnungen werden nicht
geraten. Fehlende Exportpersonen werden mit ihrem bisherigen Kontext bezeichnet.

Die Personendetailansicht führt von den geänderten Angaben über Gesprächsbedarf
und Zuständigkeit zum dokumentierten Prüfergebnis. Geeignete Personendaten können
von dort einzeln zur bestehenden Übernahmeprüfung gewählt werden. Gesprächsfolgen
zeigen die betroffenen Personen und Jahre sowie die tatsächlich zugewiesene
Verantwortung je Teil. Vorlagenaktualisierung, Versandprüfung und zusätzliche
unterjährige Aufträge sind direkt erreichbar. Datenübernahme allein ändert oder
schliesst diese Gesprächsaufträge nicht und stellt keine Unterlagen zu.

Der Abschluss einer Folgeprüfung benennt ausdrücklich die fachlich zu prüfenden
Wirkungen und verlangt ein konkretes Ergebnis. Er dokumentiert diese Prüfung;
er führt weder Zuweisung noch Erstellung oder Versand automatisch aus. Die
vorhandene Kontext-/Revisionsprüfung verhindert einen Abschluss auf veraltetem
Daten- oder Gesprächsstand. Durchlaufkontext und gefilterter Rückweg bleiben bei
Einzelauswahl, Übernahme und weiterer Bearbeitung erhalten. Nach Anlage eines
zusätzlichen Ereignisses kann zur aufrufenden SAP-Folgeprüfung zurückgekehrt
werden; diese bleibt dabei offen. Externe Rücksprungziele werden verworfen.

Validierung: vollständige Python-Suite erfolgreich (405 Tests im Gesamtlauf),
zwölf gezielte Integrationstests im abschliessenden Lauf sowie elf JavaScript-Tests.
Geprüft wurden unter anderem unveränderte Leseansichten, Anlage/Wiederaufnahme,
veralteter Importstand, kanonische Fortschrittszähler, abgelöste Einträge,
Namenskontext, Einzelübernahme, erhaltene Gesprächsverantwortung, konkrete
Abschlussvermerke und sichere Rückwege. Browserprüfung mit erfundenen Personen:
Durchlaufeinstieg, Übernahme eines Führungs-/OE-Wechsels, weiterhin offene
Gesprächsfolgen und Anschluss an die unterjährige Erfassung. Keine echte Nachricht,
Postfachverarbeitung oder externe Dossierübergabe ausgelöst.

Noch offen im umfassenden Aufgabenmodell: unveränderte Wiederzustellung,
geführtes Ersetzen bestehender Gesprächsaufträge und die weitere Vereinheitlichung
der übrigen Arbeitswege. Die Vorlagen-/Steuerelementverwaltung bleibt V01.

![Stammdatenfolgeprüfung mit ausschliesslich erfundenen Testpersonen](images/ux-stammdaten-test.png)

## Sechste Etappe: gespeicherte Unterlagen unverändert nochmals zustellen

Aus einer als versandt bestätigten regulären Ausgabe lässt sich das ganze Paket
oder der gespeicherte Formularumfang einer einzelnen Person erneut bereitstellen.
Die Links stehen bei der Ausgabe und in der personenbezogenen Formularansicht.
Die Vorschau nennt Empfänger, enthaltene Personen, konkrete Dateien und Beilagen.
Bei einer Gesamtzustellung kann direkt zur Prüfung einer einzelnen Person
gewechselt werden. Es gibt keine frei eingegebene Empfängeradresse.

Das vollständige Paket wird bytegleich kopiert. Bei der einzelnen Person werden
nur ihre vorhandenen Word-Dateien und die gemeinsamen Beilagen aus dem Original
in ein neues Versand-ZIP übernommen; die Bytes jedes Dokuments bleiben gleich.
Es wird keine Word-Vorlage neu befüllt, auch nicht während der Versandprüfung.
Lokale Bearbeitungen der Führungskraft sind ausdrücklich nicht enthalten und
werden durch die Wiederzustellung nicht automatisch ersetzt.

Neue Versandvorgänge nutzen die vorhandenen Paket- bzw. Einzelausgaberecords mit
Herkunftsverweis und Anlass im Manifest. Die frühere Ausgabe und ihr Versandnachweis
bleiben bestehen. Es entstehen keine neuen Gesprächsaufträge oder Pflichten und
keine neue Datenbankmigration. Wiederholte Vorbereitung desselben Auftrags findet
seinen Vorgang wieder, auch nach einem bereits bestätigten Versand. Bereits offene
Wiederzustellungen werden zur Fortsetzung angeboten.

Nur die aktuelle, nicht verworfene und bereits versandte Ausgangsausgabe ist
geeignet. Die aktuelle Grundlage wird vor Vorbereitung und erneut vor Outlook
geprüft. Bei einer Person wird ihr gespeicherter Grundlagenumfang verglichen;
eine sachfremde Änderung bei einer anderen Person blockiert sie nicht pauschal.
Geänderte eigene Namen, Ziele, Zuständigkeit oder Vorlagen, veränderte Dateien und
neuere Ausgaben führen zur konkreten Klärung. Ältere Personenausgaben ohne
prüfbaren gespeicherten Grundlagenstand werden nicht als unverändert bestätigt.

Vorhandene Rückläufe, abgeschlossene oder nicht mehr vorgesehene Teile sowie
möglicherweise passende ungeprüfte Eingänge verhindern die leere Wiederzustellung.
Die Eingangsprüfung wird für Rückblick und Ausblick getrennt angewandt. Konkrete
PDF-Dateien und Rückläufe sind verlinkt. Ein unbekannter Eingang bleibt ungeklärt;
er wird keiner Person als belegter Rücklauf zugeschrieben. Ein ausdrücklich
fachfremd ausgeschlossener Eingang blockiert die Wiederzustellung nicht mehr.

Die vorhandenen Outlook-Sperren, Verschlüsselungsprüfung, Entwurfs-/Fehlerklärung
und tatsächliche Versandbestätigung gelten auch für diese Vorgänge. Neue Eingänge
zwischen Vorbereitung und Outlook verhindern einen veralteten Versand. Die
Vorbereitungsvorschau ist signiert, zeitlich begrenzt, an die Sitzung und den
geprüften Umfang gebunden und mit CSRF geschützt. Sie löst keinen Outlook-Aufruf
aus. Der Anlass bleibt intern; die Nachricht nennt die unveränderte Wiederzustellung.

Validierung: Gesamtlauf mit 421 Python-Tests und 70 Subtests sowie elf
JavaScript-Tests erfolgreich; vierzehn zusätzliche Integrationstests decken
Bytegleichheit, exakt begrenzte Personenauswahl, Originalerhalt, Wiederholungen,
Versandzustände, geänderte Grundlagen, späte und fachfremde Eingänge, Dateimanipulation,
Sitzungsgrenzen, CSRF und übergreifende Outlook-Sperren ab. Der abschliessende
gezielte Lauf ist ebenfalls erfolgreich. Die Tests verbieten das erneute Rendern
von Word-Dateien während Vorbereitung und Zustellung ausdrücklich per Mock.
Browserprüfung mit erfundenen Personen: gesperrte Gesamtzustellung, Auswahl einer
zulässigen Person, Dateiumfang, Beilagen, Anlass und Übergang in den eigenen
vorbereiteten Versandvorgang. Keine echte Nachricht ausgelöst.

Umfang dieser Etappe: gespeicherte reguläre Pakete und personenbezogene Auswahl
daraus. Eigenständige Zielnachreichungs-Versandgruppen und frühere Einzelausgaben
sind noch keine auswählbaren Quellen dieser unveränderten Wiederzustellung.
Das geführte Ersetzen bestehender Gesprächsaufträge und die übrigen noch offenen
Bedienwege bleiben weitere Arbeit. V01 bleibt wie vereinbart später.

![Vorbereitung einer Wiederzustellung mit ausschliesslich erfundenen Testpersonen](images/ux-wiederzustellung-test.png)
