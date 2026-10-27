# Gemeinsame Nutzerführung: Rücklauf und Stammdatenabgleich

Stand: 27. Oktober 2026  
Status: Fachlicher Seitenentwurf; keine Änderung der produktiven App.  
Grundlage: [Prozessübersicht](PROZESSUEBERSICHT_NUTZERFUEHRUNG.md) und [Zielnachreichung](SEITENENTWURF_ZIELNACHREICHUNG.md).

## 1. Gemeinsames Bedienmuster

Alle drei Abläufe verwenden dieselbe Struktur:
1. Konkrete Aufgabe in der Arbeitsübersicht öffnen.
2. Betroffene Dokumente oder Personen mit ihrem Einzelstatus sehen.
3. Details prüfen und nötige Entscheidungen direkt treffen.
4. Freigegebene Einträge gemeinsam weiterbearbeiten.
5. Ergebnis und offene Folgearbeiten sehen; später genau dort fortsetzen.

Die Arbeitsübersicht ist der zentrale Einstieg. Dokumenteneingang, Importergebnisse und Versandansichten zeigen dieselben verknüpften Aufgaben aus ihrem Kontext, keine unabhängig zu schliessenden Kopien.

## 2. PDF-Rücklauf: Vom Eingang zur Bereitstellung

**Bestätigte Automatik (26. Oktober 2026):** Reguläre PDF-Rückläufe, die eindeutig zugeordnet werden können und die definierten Auslese-, Vollständigkeits- und Plausibilitätsprüfungen bestehen, werden automatisch übernommen und – sofern keine ausdrückliche Unterschriftenprüfung erforderlich ist – für die Dossierablage bereitgestellt. HR bearbeitet Ausnahmen; eine routinemässige Bestätigung jedes PDFs entfällt.

Voraussetzungen sind eine eindeutige Dokumentart/Verwendung, Person/Anstellung, Gesprächsteil und zeitliche Zuordnung, keine erkannten unklaren Textstellen oder fehlenden Pflichtangaben und kein Konflikt mit einer bestehenden Version. „Lesbar“ allein genügt nicht. Die konkreten Kriterien sind vor Implementierung je unterstütztem Formularformat zu definieren und mit repräsentativen Dokumenten zu prüfen; fehlende Warnungen sind kein garantierter Nachweis einer fehlerfreien Extraktion.

Identische Dubletten verweisen auf die vorhandene Verarbeitung und werden nicht erneut bereitgestellt. Abweichende Versionen, ungeklärte Zuordnungen und Ausleseprobleme erzeugen konkrete HR-Aufgaben. Technische Ablagefehler lassen die fachliche Übernahme bestehen und führen zur gezielten Wiederholung der Übergabe.

Automatisch erledigte Eingänge bleiben im Verlauf mit Original, übernommenen Angaben und Verarbeitungsergebnis auffindbar; sie erzeugen keine offene Prüfaufgabe. Der Verlauf nennt „automatisch übernommen“, nicht „von HR geprüft“. Die lokale Bereitstellung bestätigt keine tatsächliche externe Roboterverarbeitung. Die Einholung der Unterschriften bleibt in der Verantwortung der Führungskräfte; HR prüft deren Vorhandensein bei den ausdrücklich dafür vorgesehenen Fällen.

Diese Entscheidung betrifft reguläre PDF-Rückläufe. Die ausdrücklich beschriebene Freigabe korrigierter Zielquellen und das manuelle Bündeln von Feedbacks werden dadurch nicht aufgehoben. Das genaue Verhalten nach manueller Klärung einer Ausnahme wird im UI ausdrücklich benannt; ein Entwurfsspeichern löst keine Bereitstellung aus.

### Einstieg und Seitenkopf

Beispielaufgabe: „Rückblick von Person A: Zeitraum nicht eindeutig erkannt“. Erfolgreich automatisch verarbeitete Rückläufe erscheinen im Verlauf, nicht als offene HR-Prüfaufgaben. Die folgende Prüfmaske dient den Ausnahmen.

Nach dem Öffnen zeigt der Kopf Dokumentart, Person/Anstellung, Gesprächsanlass, Zeitraum, verantwortliche Führungskraft und Herkunft. Bei fehlender Zuordnung steht genau diese Klärung an erster Stelle. Ein Sprung zu einer allgemeinen Personenliste ist nicht nötig.

Bei mehreren Dokumenten im Eingang bleibt links eine kompakte Liste mit Einzelstatus. Ein Mix aus Rückblick, Ausblick und Feedback führt jeweils zur passenden Prüfung. Die folgenden Abschnitte betreffen reguläre Rückblicke/Ausblicke; Zielquellen und Feedbacks behalten ihre eigenen Fachabläufe.

### Prüfbereich

| Bereich | Inhalt | Aktion |
|---|---|---|
| Zuordnung | Person, Anstellung, Gesprächsteil, Anlass, Zeitraum, MD-Verantwortlichkeit | Vorschlag bestätigen oder korrigieren |
| Original und erkannte Angaben | PDF neben übernommenen Feldern; Fundstellen/Unsicherheiten | Angaben am Original prüfen und korrigieren |
| Vorhandene Versionen | Früherer Eingang, aktuelle gültige Fassung, bisherige Übergaben | Dublette bestätigen oder Korrekturweg wählen |
| Bereitstellungsvoraussetzungen | Angaben-/Zuordnungsprüfung abgeschlossen; gegebenenfalls unabhängig erforderliche Dokumente vorhanden | Offenen fachlichen Punkt klären; bei Prüfpflicht Unterschriften am PDF bestätigen |
| Ergebnis | Fachlich übernommen, weitere Prüfung offen oder bereitgestellt | Nächste zulässige Aktion direkt ausführen |

**Aktuelle Fachregel (27. Oktober 2026; ersetzt den generellen Verzicht auf HR-Unterschriftenkontrolle vom 26. Oktober):** Bei den wenigen ausdrücklich unterschriftspflichtigen Fällen öffnet HR das konkrete PDF und bestätigt, dass die erforderlichen Unterschriften vorhanden sind. Mögliche Zustände: „Prüfung offen“, „Unterschrift fehlt“, „Nachgefordert“ und „Unterschriften vorhanden“. Nur diese Fälle warten vor der Dossierbereitstellung auf die Bestätigung. Andere eindeutig zugeordnete und erfolgreich validierte Rückläufe werden weiterhin automatisch verarbeitet.

Die Prüfung ist an die konkrete Dokumentversion gebunden, mit Bearbeiter und Zeitpunkt. Eine neue Version ist erneut zu prüfen. „Unterschrift fehlt“ bezeichnet den Befund; „Nachgefordert“ dokumentiert eine tatsächlich erfolgte Anforderung mit Datum und Adressat, nicht bloss einen erzeugten Entwurf. Die Aufgabe wechselt dann zu „Warten auf Führungskraft“. Eine nachgereichte Datei öffnet die Prüfung erneut. Identische Dubletten erzeugen keine neue Prüfung. Unbekannte Prüfpflicht wird zur Klärung vorgelegt, nicht als „nicht erforderlich“ behandelt. Die Einholung der Unterschriften bleibt Aufgabe der Führungskräfte.

**Noch zu bestätigen:** Welche Dokumentarten/Konstellationen genau unterschriftspflichtig sind und welche Unterschriften jeweils erforderlich sind. Die bisher im Code verwendete D/E- bzw. Scanregel wird nicht automatisch als aktuelle fachliche Vorgabe übernommen. Eine eigenständige Scan-Dateipflicht ist ebenfalls separat zu klären.

Die fachliche Übernahme ist eine eigene nachvollziehbare Aktion. Sind danach weitere Prüfungen nötig, erscheinen sie auf derselben Bearbeitungsseite. Der bisherige Wechsel zwischen PDF-Prüfung und separat gesuchtem Fall soll entfallen.

### Aktionen und Wirkung

| Aktion | Wirkung |
|---|---|
| „Prüfentwurf speichern“ | Änderungen sichern; keine fachliche Übernahme oder Ablage |
| „Rückfrage vermerken“ | Konkreten offenen Punkt festhalten; kein automatischer Versand |
| „Angaben übernehmen“ | Bestätigte Daten dem Gesprächsteil zuordnen; Bereitstellung bzw. noch offene fachliche Voraussetzung anzeigen |
| „Unterschriften vorhanden“ | Prüfung der konkreten PDF-Version mit Bearbeiter und Zeitpunkt bestätigen; anschliessend Bereitstellung bei erfüllten übrigen Voraussetzungen |
| „Unterschrift fehlt“ | Fehlende Unterschrift festhalten; Bereitstellung bleibt offen |
| „Nachforderung dokumentieren“ | Tatsächlich erfolgte Anforderung mit Datum und Adressat erfassen; auf Führungskraft warten, kein Versand durch diesen Statuswechsel |
| „Für Dossier bereitstellen“ | Nur bei erfüllten Voraussetzungen die Übergabe auslösen und Ergebnis anzeigen |
| „Als Dublette abschliessen“ | Vorhandene Verarbeitung verlinken; keine zusätzliche Ablage |
| „Begründet zurückstellen“ | Entscheidung nachvollziehbar speichern; benötigtes Dokument bleibt als fachlicher Bedarf erkennbar |

Im eindeutigen Standardfall ohne Unterschriftenprüfpflicht erfolgen Übernahme und Bereitstellung automatisch. Die beschriebenen Prüfaktionen gelten für Ausnahmen; „Für Dossier bereitstellen“ ist dort eine ausdrückliche Abschluss- oder Wiederholungsaktion bei erfüllten Voraussetzungen. Entwurfsspeichern und Rückfrage lösen keine Übergabe aus.

### Status und Abschluss

„Rückblick eingegangen“ ist bereits vor Abschluss der HR-Prüfung sichtbar. Die App unterscheidet „Dokument fehlt“ von „Dokument liegt vor, HR prüft“. Dadurch darf eine offene interne Prüfung nicht als fehlender Rücklauf angemahnt werden.

Die Anzeige trennt:
- fachliche Übernahme;
- gegebenenfalls eigenständige Dokumentpflichten und die erforderliche Unterschriftenprüfung;
- lokale Bereitstellung;
- tatsächliche externe Verarbeitung, soweit ein Nachweis vorhanden ist.

Beispiel: „Rückblick übernommen · Bereitstellung ausstehend“. Nach erfolgreicher Übergabe: „Für Dossier bereitgestellt · Ausblick noch ausstehend“. Bei prüfpflichtigen Fällen erscheint zusätzlich „Unterschriftenprüfung offen“, „Unterschrift fehlt“ oder „Nachgefordert“. Ohne Rückmeldung des externen Systems wird keine erfolgte Personaldossier-Ablage behauptet.

### Fehler und Wiederaufnahme

- Unlesbares PDF: Original bleibt zugänglich; fehlende Angaben bzw. bessere Datei konkret anfordern.
- Mehrfachanstellung: passende Anstellung und historische Konstellation im selben Vorgang auswählen.
- Ablagefehler: fachliche Prüfung bleibt erhalten; nur Bereitstellung erneut versuchen.
- Neue Version nach bereits erfolgter Übergabe: bisherigen Beleg und externe Wirkung zeigen; keine stille Ersetzung.
- Bereits verschobene Mail: gesichertes Dokument bleibt bearbeitbar.
- Quellen- oder Zuständigkeitsänderung während der Prüfung: veraltete Entscheidung nicht ungeprüft übernehmen.

### Mailablage und offene Folgearbeiten

**Bestätigte Mailablage-Regel (26. Oktober 2026):**
- Reine MD-Mails werden nach erfolgreicher Verarbeitung aller MD-Anhänge automatisch in den konfigurierten Outlook-Zielordner «12 Mitarbeitenden-Dialog» verschoben, sofern keine zusätzlichen ungeklärten Anliegen bestehen.
- Ungeklärte Anhänge, zusätzliche Anliegen im Mailtext oder Fremdanlagen verhindern das automatische Verschieben; die Mail bleibt zunächst im Posteingang.
- Nach manueller Klärung verschiebt HR die Mail bei Bedarf selbst in Outlook. „Prüfung erledigt“ in der App markiert nur die Klärung und verschiebt keine Mail. Ein späterer Scan darf diese manuell abgeschlossene Prüfung nicht als neuen automatischen Verschiebeauftrag behandeln.
- Folgearbeiten wie Neuerstellung und Versand korrigierter Rückblicke bleiben in der App offen, auch wenn die ursprüngliche Mail bereits abgelegt wurde.
- Eine bekannte Dublette zählt nur dann als verarbeitet, wenn der vorhandene Verarbeitungsstand dies belegt; ein identischer noch ungeklärter Eingang bleibt ungeklärt.
- Bei einem Verschiebefehler bleiben erfolgreich verarbeitete Dokumente erhalten. Eine erneute Ablageklärung darf keine erneute fachliche Übernahme oder Dossierübergabe auslösen.

**Technisch zu prüfen:** Wie zusätzliche Anliegen im Mailtext zuverlässig erkannt bzw. zur manuellen Klärung vorgelegt werden. Erfolgreiche Anhangsverarbeitung allein ist kein Nachweis, dass die Nachricht kein weiteres Anliegen enthält. Die Regel ist eine Sollanforderung, keine Behauptung über eine bereits vorhandene automatische Inhaltsprüfung.

### Korrekturweg bei später nachgereichten Zielen

**Bestätigte Regel (26. Oktober 2026):** Der Bearbeitungsstand des Rückblicks bestimmt die Folgeaktion. Die bestätigte Zielquelle wird gespeichert, ersetzt aber keinen bereits eingegangenen Rückblick.

| Stand des Rückblicks | Folgeaktion | Voraussetzung für Abschluss |
|---|---|---|
| Noch ausstehend | Aktualisierte Rückblickvorlage zur Erstellung und Übermittlung anbieten | Ausgabe übermittelt oder begründeter Verzicht |
| Bereits eingegangen, auch wenn noch ungeprüft | Aufgabe „Korrekturbedarf klären“; keine automatische Neuerstellung einer Vorlage | HR hat entschieden, dass keine Korrektur nötig ist, oder ein erforderlicher korrigierter Rücklauf ist bearbeitet |
| Bereits für Dossier bereitgestellt | Korrekturbedarf klären und erfolgte Übergabe deutlich anzeigen; keine automatische Ersetzung | Gegebenenfalls korrigierten Rücklauf bearbeiten und externe Korrektur mit zuständiger Stelle klären |

**Entscheidungen in der Klärung:**
- „Keine Korrektur nötig“ mit kurzer Begründung: Rückblick bleibt bestehen, Zielquelle und Entscheidung bleiben nachvollziehbar.
- „Korrigierten Rücklauf anfordern“: benötigte Änderung festhalten; verantwortliche Führungskraft und vorhandenen Rückblick verknüpfen. Die Anforderung bzw. ein Mailentwurf ist noch kein Eingang des korrigierten Dokuments.
- „Rückfrage offen“: fehlende Klärung konkret vermerken und Aufgabe offen halten.

Ein bereits eingegangener Rückblick wird nicht durch eine neu erzeugte leere Vorlage ersetzt. Der korrigierte Rücklauf wird als neue Version geprüft; Original und bisherige Verarbeitung bleiben erhalten. Er ist wegen des Versionskonflikts kein Fall für ungeprüfte automatische Ersetzung.

**Folgen für Sammelaktionen:** Personen mit bereits eingegangenem Rückblick werden nicht in die gemeinsame Vorlagenerstellung aufgenommen. Die Auswahl zeigt stattdessen „Korrekturbedarf klären“. Freigegebene noch ausstehende Rückblicke anderer Personen können parallel erstellt werden.

**Erneute Prüfung vor Erstellung:** Trifft ein Rückblick ein, nachdem die Auswahl vorbereitet wurde, muss der betreffende Eintrag in die Klärung wechseln. Ein veralteter Listenstand darf keine neue Vorlage für einen inzwischen eingegangenen Rückblick erzeugen.

**Grenze:** „Noch ausstehend“ beweist nicht, dass die Führungskraft die bisherige Vorlage noch nicht bearbeitet hat. Der Hinweis zum Abgleichen bereits bearbeiteter Inhalte bleibt erhalten. Wie eine notwendige Korrektur nach erfolgter externer Dossier- oder SAP-Verarbeitung praktisch bestätigt wird, ist noch mit dem entsprechenden Ablauf zu konkretisieren.

## 3. SAP-Stammdaten: Vom Upload zur Folgeaufgabe

### Einstieg und Seitenkopf

Einstieg „SAP-Daten aktualisieren“ aus der Arbeitsübersicht. Nach Upload erscheint die Änderungsprüfung mit:
- Dateiname und Datenstand;
- bisherigem Vergleichsstand;
- Prüfergebnis zu Struktur und auffälliger Vollständigkeit;
- Anzahl geänderter Personen/Anstellungen sowie offenen Konflikten, jeweils mit genannter Zähleinheit.

Ohne verlässlichen Vergleichsstand wird der Import als Ausgangsstand gekennzeichnet. Fehlende Historie wird nicht als Abwesenheit früherer Wechsel interpretiert.

### Änderungsliste

Filter: „Neue Anstellungen“, „Austritte“, „OE/Führungskraft“, „Weitere Angaben“, „Konflikte“. Unveränderte Personen sind standardmässig ausgeblendet, bleiben bei Bedarf auffindbar.

| Zeile | Sichtbares Ergebnis | Direkte Folgeaktion |
|---|---|---|
| Person A, Eintritt | Neue Anstellung; noch kein passender Dialog | „Dialogbedarf prüfen“ |
| Person B, Führungswechsel | Rückblick bisher bei anderer Führungskraft | „Auswirkungen prüfen“ |
| Person C, manuelle Vertretung | Bewusste Abweichung unverändert | Kein neuer Konflikt; Entscheidung ansehen |
| Person D, Formularangabe geändert | Zwei Ausgaben betroffen | „Aktualisierung prüfen“ |
| Person E fehlt | Ursache nicht eindeutig | „Fehlenden Datensatz klären“ |

Die Liste zeigt vorgeschlagene Folgen vor der Übernahme und den tatsächlichen Bearbeitungsstand danach. Sie ist keine zweite unabhängige Arbeitsliste.

### Detailbereich pro Person/Anstellung

Beim Öffnen einer Änderung stehen bisherige und neue Angaben nebeneinander. Darunter erscheinen die betroffenen Dialoge mit getrennten Zeilen für Rückblick und Ausblick:

- Anlass und Zeitraum;
- bisher bestätigte MD-Verantwortlichkeit;
- aktuelle SAP-Führungskraft;
- verwendete Formular-OE;
- Ausgabe-/Versand-/Rücklaufstand;
- konkrete Auswirkung und mögliche nächste Entscheidung.

**Beispiel Übertritt:** HR bestätigt die aktuelle SAP-Zuordnung. Der historische Rückblick bleibt bei der alten Führungskraft, der Ausblick wird der neuen zugeordnet. Die passenden Formular-OE werden je Teil geprüft. Stammdatenübernahme allein führt diese Fachentscheidung nicht stillschweigend aus.

### Gemeinsame Übernahme und Folgearbeiten

1. Eindeutige zulässige Änderungen auswählen.
2. Vor Ausführung Umfang und zurückgehaltene Konflikte anzeigen.
3. Änderungen übernehmen und verknüpfte Folgeaufgaben erzeugen.
4. Ergebnisliste zeigt „Daten übernommen“ getrennt von „Dialogentscheidung offen“ oder „Formularaktualisierung offen“.
5. Eine Folgeaktion öffnet den konkreten Dialog oder die passende Sammelerstellung mit dem betroffenen Kontext.

Der mögliche Teilimport muss technisch gegen die bestehende Synchronisierung geprüft werden. Die Oberfläche darf keine erfolgreiche teilweise Übernahme als vollständig abgeglichenen SAP-Gesamtstand darstellen.

### Wiederholter Import

Eine bekannte manuelle Abweichung erzeugt keine neue Prüfpflicht, solange keine neue relevante Änderung vorliegt. Ein identischer Import erzeugt keine doppelten Aufgaben oder Dialoge. Neuere Daten aktualisieren offene Prüfvorschläge nachvollziehbar.

## 4. Gemeinsame Oberfläche und fachliche Unterschiede

| Eigenschaft | Zielnachreichung | Regulärer Rücklauf | Stammdatenabgleich |
|---|---|---|---|
| Gruppenkontext | Nachreichung / ausgewählte Quellen | Mail / Upload / ausgewählte Eingänge | SAP-Import |
| Einzelarbeit | Zielquelle je Person/Anstellung/Jahr | Dokument und Gesprächsteil | Änderung je Anstellung |
| Vergleich | Original und erkannte Ziele | Original und erkannte Angaben | Bisheriger und neuer Datenstand |
| Entscheidung | Zielversion bestätigen | Angaben und erforderliche Prüfungen bestätigen | Änderung und ihre fachlichen Auswirkungen klären |
| Gemeinsame Folgearbeit | Rückblicke erstellen und versenden | Zulässige nächste Bearbeitung bzw. Bereitstellung | Änderungen übernehmen, Dialoge oder Korrekturen vorbereiten |
| Abschluss des Schritts | Quelle bestätigt | Prüfung erledigt | Daten übernommen / Auswirkungen geklärt |
| Mögliche Restarbeit | Korrekturversand | Rückfrage, gegebenenfalls separate Dokumentpflicht, Bereitstellung, externer Nachweis | Dialoganlage, Zuständigkeitsklärung, Korrekturversand |

Damit genügt ein wiederkehrender Aufbau aus Kopf, Liste, Detailprüfung und nächster Aktion. Es braucht keine identischen Fachformulare für alle Abläufe.

## 5. Vorschlag für die Navigation

Dies ist ein erster Vorschlag, noch keine beschlossene Menüstruktur.

- **Arbeitsübersicht:** Handlungsbedarf und Warten auf Rückmeldung; enthält den gemeinsamen Eingang als filterbare Sicht.
- **Personen & Dialoge:** Suche, historische und aktuelle Dialoge, Verantwortung je Gesprächsteil, Status und Verlauf.
- **Stammdaten:** Import, Änderungsprüfung und Datenhistorie.
- **Auswertung & Abschluss:** Berichte, SAP-Ausgabe und Kampagnenabschluss.
- **Einrichtung & Hilfe:** Vorlagen, technische Konfiguration, Bedienhilfe; Administration entsprechend Berechtigung.

Erstellung und Versand sind direkt aus Vorgängen erreichbar. Ein zusätzlicher Versandzugang ist nur sinnvoll, wenn er Übersicht über offene Entwürfe und Sammelaktionen bietet; er darf keinen getrennten Status erzeugen.

Feedbacksammlungen bleiben als fachlich eigene Sammlung auffindbar; ihr sinnvoller Navigationsort wird beim Feedbackentwurf geprüft. Jahreskampagnen bündeln Auswahl und Planung und sind keine Schranke vor der Bearbeitung einzelner Dialoge.

## 6. Ergebnis und offene Entscheidungen

**Konzeptionelles Ergebnis:** Regulärer Rücklauf und SAP-Abgleich passen in dasselbe Bedienmuster. Eine gemeinsame Arbeitsübersicht lässt sich mit unterschiedlichen Detailprüfungen verbinden.

**Vor Umsetzung offen:** Ob eine gesonderte Scan-Datei in bestimmten Fällen unabhängig von der Unterschriftenkontrolle erforderlich ist, technische Validierungskriterien für automatische Übernahme/Bereitstellung, Korrektur nach externer Verarbeitung, Teilimportstrategie und verbindliche Fachregeln für Dialogbedarf/Zeiträume.

**Prüfung:** Dokumentarischer Abgleich mit den bisherigen Anforderungen und S01/S03/S04/S05; kein Browser- oder Integrationstest. Die produktive App ist unverändert.

**Abnahmekriterium zur Unterschriftenverantwortung:** Nur ausdrücklich prüfpflichtige Fälle benötigen vor der Bereitstellung die HR-Bestätigung für die konkrete PDF-Version. Aufgabenliste und Fall zeigen offene Prüfung, fehlende Unterschrift oder tatsächlich erfolgte Nachforderung. Nicht prüfpflichtige Fälle benötigen keine solche Bestätigung. Neue Fassungen werden erneut geprüft; Dubletten und reine Übergabewiederholungen derselben Version nicht. Der Verlauf unterscheidet automatische Verarbeitung von tatsächlicher HR-Prüfung.

**Abnahmekriterien zur Automatik:** Ein eindeutig zugeordnetes und erfolgreich validiertes reguläres PDF wird ohne HR-Aktion übernommen und einmalig bereitgestellt. Ein unklarer Zeitraum, nicht lesbarer Inhalt oder abweichende bereits vorhandene Version erzeugt eine konkrete Ausnahmeaufgabe. Eine Dublette bewirkt keine erneute Übergabe. Bei Ablagefehler bleibt die erfolgreiche Datenübernahme nachvollziehbar. Erledigte automatische Eingänge sind weiterhin auffindbar.
