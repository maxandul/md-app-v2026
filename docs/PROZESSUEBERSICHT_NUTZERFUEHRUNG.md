# Prozessübersicht und Nutzerführung – Arbeitsstand

Stand: 26. Oktober 2026  
Codebasis: main, Commit 9d7ca779afc18e9bd9c6607a5b3dbe8465537a18  
Status: Diskussionsgrundlage; Sollabläufe und offene Entscheidungen sind noch keine implementierten Funktionen.

## 1. Ziel und Umfang

HR soll einen fachlichen Vorgang vom Anlass bis zum Ergebnis bearbeiten können, ohne die Verbindung zwischen Postfach, Import, Fall, Formularerstellung und Versand selbst herstellen zu müssen.

Diese Übersicht beschreibt den Word-/PDF-Standardablauf aus HR-Sicht. Handlungen von Mitarbeitenden, Führungskräften sowie Outlook, Dossier-Roboter und SAP werden an den Übergängen sichtbar gemacht. Die frühere HTML-Arbeitsmappe ist ein gesonderter Übergangsweg.

Grundlage sind Quellcode, Seitenvorlagen und Projektdokumentation. Produktive Daten, konkrete problematische Eingänge und die Bedienung im Windows-/Outlook-Betrieb wurden nicht geprüft. Fachliche Spezialfallregeln werden hier nicht neu festgelegt.

**Kennzeichnung:**
- **Ist:** im untersuchten Stand erkennbares Verhalten.
- **Sollvorschlag:** Grundlage für die gemeinsame Ausarbeitung.
- **Offen:** fachlich oder technisch noch zu entscheiden bzw. genauer zu prüfen.

## 2. Gesamtübersicht

Die Prozesse laufen ganzjährig und parallel. Während Jahresdialoge bearbeitet werden, können Neueintritte einen unterjährigen Dialog auslösen, Stammdatenänderungen bestehende Fälle betreffen und Zielnachreichungen Korrekturausgaben erfordern.

**Anforderungen aus der Abstimmung vom 26. Oktober 2026:** Regelmässiger SAP-Stammdatenabgleich ist ein eigenständiger häufiger Prozess. Die MD-verantwortliche Führungskraft kann von SAP abweichen. Mehrere nachgereichte Ausblicke sollen gemeinsam zu neuen Rückblicken verarbeitet werden können. Die strikte Trennung nach Durchläufen soll die tägliche Bearbeitung nicht bestimmen.

**Sollvorschlag zum Grundmodell:** Der einzelne Dialog mit Anlass, Anstellung, Zeitraum und MD-Zuständigkeit ist die fachliche Arbeitseinheit. Die gemeinsame Arbeitsübersicht zeigt alle offenen Aufgaben; Dialogart, Jahr, Führungskraft und OE dienen als Filter. Eine Jahreskampagne bündelt Planung, Sammelversand und Auswertung. Sie ist keine Voraussetzung dafür, einen unterjährigen Dialog zu starten. Die bestehende technische Durchlaufbindung muss dafür gesondert geprüft und gegebenenfalls angepasst werden.

| ID | Teilprozess und Auslöser | Ergebnis / Abschluss | Anschluss |
|---|---|---|---|
| P01 | Jahreskampagne vorbereiten | Umfang, Fristen und Auswahl der Jahresdialoge sind geprüft | P02; Datenabgleich über P09; weitere Dialoge über P07 |
| P02 | Formulare erstellen und erstmals versenden | Vorgesehene Unterlagen wurden an die richtige Führungskraft übermittelt; Versand ist dokumentiert | P04, P05, P06 |
| P03 | Ziele nachreichen oder ausgegebene Formulare korrigieren | Aktualisierung wurde übermittelt oder begründet als nicht nötig entschieden | P04; bei neuer Änderung erneut P03 |
| P04 | MD-Dokumente empfangen, prüfen und bereitstellen | Gültiger Rücklauf ist zugeordnet und erforderliche Prüfungen/Übergaben sind erledigt | P08; fehlende Unterlagen an P06 |
| P05 | Feedbacks empfangen und zusammenführen | Geprüfte Sammlung bzw. Nachtrag wurde bereitgestellt | Externe Dossierverarbeitung |
| P06 | Fehlende Unterlagen nachverfolgen | Unterlage eingegangen, Pflicht begründet aufgehoben oder weiterer Klärungsbedarf dokumentiert | P04 bzw. P07 |
| P07 | Unterjähriges Ereignis oder Ausnahme bearbeiten | Richtiger Dialog mit Person, Anstellung, Führungskraft, Umfang, Zeitraum und Formular-OE ist festgelegt | P02/P03, danach P04 |
| P08 | Auswerten, SAP bereitstellen und Jahreskampagne abschliessen | Exporte und Restfälle sind nachvollziehbar; Kampagnenabschluss ist dokumentiert | Folgejahr P01; offene und neue Dialoge bleiben bearbeitbar (Soll) |
| P09 | SAP-Stammdaten regelmässig aktualisieren | Änderungen sind geprüft; nötige Folgeaufgaben sind verknüpft | P07 bei neuen Dialogen; P03 bei Korrekturen; P10 bei Zuständigkeitsfragen |
| P10 | Zuständigkeit und Formular-OE je Gesprächsteil festlegen oder ändern | Verantwortung für Rückblick und Ausblick ist getrennt nachvollziehbar festgelegt | P02/P03; bestehende Rückläufe und Historie berücksichtigen |

Einrichtung, Benutzerverwaltung, Backup und technische Störungen sind unterstützende Betriebsprozesse. Sie sollen fachliche Aufgaben bei Bedarf konkret blockieren und einen Lösungsweg anbieten, aber nicht die normale Arbeitsübersicht dominieren.

## 3. Welche Einheiten zusammengehören

| Einheit | Bedeutung für die Nutzerführung |
|---|---|
| Durchlauf / Jahreskampagne | Ist: technischer Jahreskontext. Soll: organisatorische Bündelung und Filter; keine Zugangshürde für unterjährige Dialoge oder globale Eingänge |
| Dialogfall / Gesprächsteile | Person und Anstellung mit Anlass; Rückblick und Ausblick besitzen jeweils Zeitraum, MD-Zuständigkeit und Formular-OE. Mehrere fachlich unterschiedliche Dialoge pro Jahr bleiben möglich; ein Zuständigkeitswechsel allein erzeugt keine doppelten Pflichten |
| SAP-Führungslinie / MD-Zuständigkeit | Aktuelle organisatorische Zuordnung und für diesen Dialog verantwortliche Führungskraft getrennt halten; begründete Abweichungen bei neuen SAP-Importen sichtbar erhalten |
| Eingang | E-Mail oder manuell hochgeladene Datei; eine Mail kann mehrere unabhängige Anliegen enthalten |
| Dokument / Zielquelle | Inhalt, Zuordnung, Jahr, Prüfung und gültige Version |
| Formularausgabe | Konkrete erzeugte Fassung mit den dafür verwendeten Grundlagen |
| Versand / Übergabe | Nachweis, was an wen bzw. an welches externe System übergeben wurde |
| Vorgang (Sollvorschlag) | Verbindet Anlass, Dokumente, betroffene Fälle, Entscheidungen und Folgearbeiten bis zum fachlichen Ergebnis |

**Leitregel:** Eine erledigte Mail ist kein Nachweis für einen versendeten Rückblick. Eine übernommene Zielquelle ist noch keine aktualisierte Formularausgabe. Eine bereitgestellte PDF-Datei ist kein Nachweis der tatsächlichen Roboterverarbeitung.

## 4. Teilprozesse: Ist und benötigte Führung

### P01 – Jahreskampagne vorbereiten

**Ist:** SAP-Import und Konflikte unter Stammdaten; Durchlauf und Dialogpflichten unter Dialoge. Historische Zielquellen haben ebenfalls einen Einstieg unter Stammdaten. Änderungen können bestehende Ausgaben veralten lassen.

**HR-Arbeit:** Auf dem geprüften Datenstand aus P09 aufbauen; Jahr, Auswahl der Jahresdialoge, MD-Zuständigkeiten, Umfang, Fristen und Sonderfälle klären; verfügbare Ziele kontrollieren. Neue Stammdaten werden laufend über P09 bearbeitet, unabhängig von der Kampagnenphase.

**Varianten:** Mehrfachanstellung, widersprüchliche Zuordnung, fehlende Führungskraft, Ein-/Austritt, Übertritt, fehlende Vorjahresziele, erneuter SAP-Import.

**Sollvorschlag:** Vorbereitung zeigt prüfbare Punkte und deren Auswirkungen. Fehlende optionale Ziele werden von blockierenden Zuordnungsfehlern unterschieden. Änderungen nach Versand führen gezielt zu P03.

**Offen:** Welche Punkte müssen zwingend geklärt sein, bevor einzelne Personen bzw. eine ganze Führungslinie versendet werden dürfen?

### P02 – Formulare erstellen und erstmals versenden

**Ist:** Personalisierte Word-Ausgaben und Führungskräftepakete; Reflexion und Feedbackvorlage als Beilagen. Erzeugung, Outlook-Übergabe und Versand sind getrennte Schritte.

**HR-Arbeit:** Personen/Formulare auswählen, Ausgabe prüfen, Versand vorbereiten und tatsächlichen Versand nachvollziehen.

**Varianten:** Einzelperson, Führungslinie, Sammelauswahl; fehlende E-Mail; geänderte Grundlagen; erneute Erzeugung; Outlook-Unterbrechung; Abbruch.

**Sollvorschlag:** Sichtbare Schritte „Unterlagen prüfen“, „Versand vorbereiten“, „Versand bestätigen“. Bei Wiederholung erkennen, welche Fassung bereits übermittelt wurde. Offene Outlook-Vorgänge zuerst klären.

**Abschluss:** Versand der vorgesehenen gültigen Ausgabe ist dokumentiert oder die Ausgabe wurde begründet verworfen.

### P03 – Ziele nachreichen und Formulare korrigieren

**Ist:** Word-Zielimport über Postfach oder manuellen Import; PDF-Ausblick auch als historische Zielquelle. Quellenvergleich, Änderungsprüfung und personenspezifische Korrekturausgabe sind vorhanden, aber über mehrere Seiten verteilt.

**Varianten:** Siehe ausführlichen Ablauf in Abschnitt 5. Weitere Auslöser sind korrigierte Stammdaten, Gesprächsumfang, Zeitraum, Formular-OE oder Vorlagen.

**Sollvorschlag:** Vom Anlass aus direkt zu betroffenen Formularen und deren Versand führen. Gültige Quelle, verwendete Ausgabe und Versand bleiben verknüpft. Mehrere nachgereichte Ausblicke gemeinsam prüfen und alle ausgewählten freigegebenen Rückblicke in einem Arbeitsschritt erstellen. Bündelung und Versand nach tatsächlicher MD-Zuständigkeit des jeweiligen Gesprächsteils; Einzelstatus und Wiederaufnahme bleiben möglich (Abschnitt 5.5).

**Abschluss:** Alle betroffenen Ausgaben wurden bearbeitet; eine unterlassene Neuerstellung/Übermittlung ist begründet.

### P04 – MD-Rückläufe prüfen und bereitstellen

**Ist:** Postfachscan oder PDF-Upload; Word-PDF-Prüfwarteschlange; Originalvergleich, Fallzuordnung und fachliche Übernahme; anschliessende Fall-/Unterschriften- bzw. Scanprüfung und Dossierbereitstellung.

**HR-Arbeit:** Dokumentart, Person/Anstellung, Jahr/Zeitraum und Angaben prüfen; benötigte Unterschriften/Scans kontrollieren; fehlende oder falsche Unterlagen klären.

**Varianten:** Rückblick, Ausblick, Probezeit; historischer Ausblick als Zielquelle; alter Formularstand; Dublette/neue Version; unlesbares PDF/Scan; unklare Zuordnung; inaktiver Fall; geschlossener Durchlauf; Nichtdurchführung; gemischte E-Mail.

**Sollvorschlag:** Ein Eingang bietet unmittelbar die passende Bearbeitung. Nach fachlicher Übernahme direkt zur noch nötigen Prüfung führen. Fehlende Unterschrift, unlesbare Angaben und technische Ablagefehler erhalten unterschiedliche Aufgaben.

**Abschluss:** Dokument ist geprüft und erforderliche Übergabe ist erfolgt, oder es ist nachvollziehbar zurückgewiesen/zurückgestellt. Ein benötigter, ungeklärter Rücklauf bleibt offen.

**Offen:** Die fachliche Unterschriften-/Scanregel je Dokumenttyp wird im Detail separat gegen den aktuellen Word-Standard geprüft; ältere HTML-Regeln nicht ungeprüft übernehmen.

#### P04.1 Gemeinsamer Dokumenteneingang

**Bestätigte Richtung (26. Oktober 2026):** Alle MD-bezogenen Dokumente aus Postfachscan und manuellem Upload erscheinen in einer gemeinsamen Eingangsliste. Die fachliche Aufgabe hängt am Dokument und führt direkt zur passenden Bearbeitung. Die E-Mail bleibt als Herkunft und gemeinsame Klammer ihrer Anhänge sichtbar.

Dies betrifft auch die Eingänge für P03 und P05. Ein gemeinsamer Eingang bedeutet nicht, dass alle Dokumentarten dieselben fachlichen Prüfungen oder dieselbe Ablage benötigen.

| Verwendungszweck | Bearbeitung | Anschluss |
|---|---|---|
| Nachgereichter Ausblick als Zielquelle | Ziele und Zuordnung prüfen, gegebenenfalls korrigieren | P03: betroffene Rückblicke aktualisieren |
| Regulärer Rückblick oder Ausblick | Angaben, Gesprächsteil, Person/Anstellung, Zeitraum und Zuständigkeit prüfen | Erforderliche Folgeprüfung und Dossierbereitstellung |
| Feedback | Führungskraft, Jahr und Inhalt prüfen | P05: passende Sammlung |
| Unklarer Eingang | Dokumentart, Verwendung, Person/Anstellung oder Jahr klären | Passenden Ablauf im selben Vorgang fortsetzen |
| Bereits verarbeitetes Dokument | Vorhandene Verarbeitung anzeigen; bei abweichendem Inhalt Versionen vergleichen | Dublette abschliessen oder Korrektur prüfen |

**Dokumentart und Verwendungszweck trennen:** „Ausblick“ beschreibt die Art des Dokuments. Ob er als regulärer Rücklauf oder als nachgereichte Zielquelle bearbeitet wird, ergibt sich aus Jahr, Fallkontext und bestätigter Verwendung. Ein regulär übernommener Ausblick kann später auch Ziele für einen Rückblick liefern. Diese spätere Nutzung erzeugt weder einen zweiten Eingang noch eine zweite Dossierübergabe. Die Herkunft der Ziele bleibt mit dem übernommenen Dokument verbunden.

#### P04.2 Anzeige und direkte Bearbeitung – Sollentwurf

Jeder Eintrag zeigt:
- Person und Anstellung/OE, soweit bekannt; andernfalls konkret fehlende Zuordnung;
- Dokumentart, Jahr/Zeitraum und vorgesehene Verwendung;
- Quelle: Mail mit Absender/Betreff oder manueller Upload;
- was bereits gesichert, übernommen oder bereitgestellt wurde;
- den konkreten offenen Punkt und eine direkt passende Aktion.

Beispiele für Aufgaben:
- „Ausblick von Person X: Anstellung zuordnen“;
- „Rückblick von Person Y: Angaben am Original prüfen“;
- „Ziele von Person Z: unvollständig erkannte Stelle ergänzen“;
- „Feedback: Führungskraft zuordnen“;
- „Geprüftes PDF: Bereitstellung nach Ablagefehler erneut versuchen“.

Die Aktion öffnet das betreffende Dokument mit erhaltenem Kontext, nicht den Anfang einer allgemeinen Übersichtsseite. Bereits gespeicherte Anhänge müssen nicht heruntergeladen und erneut hochgeladen werden, um in einen anderen fachlichen Bearbeitungsweg zu wechseln.

#### P04.3 Sammelaktionen und Teilergebnisse – Sollentwurf

Mehrere geklärte Dokumente können gemeinsam weiterverarbeitet werden, soweit die jeweilige Aktion fachlich passt. Die Auswahl zeigt pro Dokument, welche Voraussetzungen erfüllt sind und welche noch fehlen.

- Zielquellen: freigegebene Rückblicke gemeinsam erstellen, wie in P03 beschrieben.
- Reguläre Rückläufe: nur Dokumente mit erfüllten Voraussetzungen gemeinsam zum passenden nächsten Schritt weiterführen.
- Feedbacks: nach Führungskraft und Jahr in die passende Sammlung führen.
- Ungeklärte Dokumente: mit konkretem Grund offen lassen; nicht durch die Sammelaktion als geprüft behandeln.
- Technische Teilerfolge: erfolgreiche Ergebnisse erhalten und fehlerhafte Dokumente gezielt wiederholen können.

Ein gemischter Eingang wird nicht pauschal als eine einzige fachliche Aufgabe behandelt. Ein Sammelbutton muss seine Wirkung auf die ausgewählten Dokumente vor der Ausführung benennen; die Herkunft aus derselben Mail allein ist keine fachliche Freigabe.

#### P04.4 Dokumentstatus, Folgearbeit und Mailablage – Sollentwurf

Drei Ebenen sind zu unterscheiden:

| Ebene | Beispiel | Aussage |
|---|---|---|
| Dokumentbearbeitung | „Als Zielquelle übernommen“ | Inhalt und Verwendung dieses Dokuments sind bestätigt |
| Fachliche Folgearbeit | „Aktualisierter Rückblick noch zu versenden“ | Das Anliegen ist noch nicht vollständig erledigt |
| Mailablage | „Mail in Outlook verschoben“ | Nur der Ablageort der Nachricht hat sich geändert |

Die Mailansicht fasst die Bearbeitungsstände ihrer MD-Dokumente zusammen und zeigt noch offene Anliegen ohne verarbeitbares Dokument, beispielsweise eine Rückfrage im Nachrichtentext. Fremdanlagen bleiben gemäss bestehender Abgrenzung ausserhalb der MD-Dateiablage.

**Regeln:**
- „Mailprüfung erledigt“ darf offene Dokumentaufgaben oder Folgearbeiten nicht verdecken oder automatisch schliessen.
- Erledigte Dokumentprüfungen sollen nicht zusätzlich unabhängig als dieselbe Prüfaufgabe an der Mail offen bleiben. Separate Anliegen der Mail benötigen dagegen einen eigenen Klärungsgrund.
- Ein Verschieben in Outlook ist weder fachliche Übernahme noch Bestätigung eines Korrekturversands.
- Nach einem Teilerfolg bleiben ungeklärte Anhänge und Folgearbeiten sichtbar, auch wenn andere Dokumente bereits übernommen wurden.
- Erneuter Scan oder manueller Upload derselben Datei verweist auf die vorhandene Verarbeitung; abweichende Inhalte werden als mögliche neue Version geprüft.
- Wiederaufnahme setzt beim letzten bestätigten Schritt an.

**Noch offen:** Der genaue Zeitpunkt des automatischen Verschiebens einer Mail wird separat festgelegt. Dabei dürfen „Dokument bearbeitet“, „Anliegen samt Folgearbeiten erledigt“ und „Mail abgelegt“ nicht gleichgesetzt werden. Diese Konzeption ändert die bestehende Verschieberegel noch nicht.

#### P04.5 Prüfkriterien

- Dasselbe Dokument gelangt über Mail und Upload in denselben fachlichen Prüfablauf.
- Eine unklare Zuordnung lässt sich direkt am Eingang klären.
- Ein Ausblick kann passend zum Kontext als regulärer Rücklauf oder Zielquelle verwendet werden; spätere Zielnutzung bleibt nachvollziehbar.
- Eine Mail mit Zielquelle, Rücklauf und Feedback führt zu den jeweils passenden Bearbeitungen.
- Gemeinsame Weiterverarbeitung erledigt keine ungeklärten Anhänge.
- Eine erledigte Dokumentprüfung verschwindet als Prüfaufgabe; nötige Folgearbeit bleibt sichtbar.
- Ein technischer Fehler kann ohne erneute fachliche Übernahme erfolgreicher Dokumente wiederholt werden.
- Eine bereits verschobene Mail blockiert nicht die weitere Bearbeitung gesicherter Dokumente.

### P05 – Feedbacks bearbeiten

**Ist:** Feedbacks werden geprüft, Führungskraft und Jahr zugeordnet und gesammelt. HR löst die Zusammenführung und Bereitstellung aus; spätere Eingänge können Nachträge bilden. Erwartete Anzahl dient der Orientierung, nicht automatischem Mahnen.

**Varianten:** Einzel-/Sammeleingang, unbekannte Führungskraft, falsches Jahr, Dublette, Nachtrag nach Bündelung.

**Sollvorschlag:** Sammlung zeigt „ungeprüft“, „bereit zum Zusammenführen“ und „bereits bereitgestellt“. Der konkrete Eingang führt direkt zur passenden Sammlung.

**Abschluss:** Ausgewählte geprüfte Feedbacks wurden gebündelt und bereitgestellt. Eine fehlende rechnerische Sollzahl erzeugt keine automatische Mahnpflicht.

### P06 – Fehlende Unterlagen nachverfolgen

**Ist:** Fristen und Erinnerungsentwürfe beziehen sich auf offene, zurückgewiesene oder scanpflichtige Unterlagen. Offene PDF-Eingänge blockieren aktuell Erinnerungsentwürfe durchlaufübergreifend.

**HR-Arbeit:** Prüfen, ob etwas wirklich fehlt; Eingangsklärung, Rückfrage, Friständerung oder Erinnerung wählen; Versand dokumentieren.

**Varianten:** Bereits eingegangen, aber ungeprüft; Korrektur angefordert; Scan fehlt; Frist verlängert; Pflicht entfällt; Erinnerung bereits als Entwurf vorhanden.

**Sollvorschlag:** „Warten auf HR“ und „Warten auf Führungskraft“ klar unterscheiden. Jede Erinnerung nennt das konkrete fehlende Dokument.

**Offen:** Globale Erinnerungssperre beibehalten oder bei belastbarer Zuordnung auf tatsächlich betroffene Fälle beschränken?

### P07 – Unterjährige Ereignisse und Ausnahmen

**Ist:** Manuelle Ereignisse mit Auswahl von Person/Anstellung und Führungskraft; Formular-OE wählbar; Zeitraum, Umfang, Fristen und Durchlaufzuordnung. Ereignisse ohne Durchlauf und begründete Aufhebung von Fehlanlagen sind vorgesehen.

**Varianten:** Probezeit, Austritt, Übertritt, Führungswechsel, Vakanz/Stellvertretung, mehrere Gespräche im selben Jahr, kein MD bzw. entfallender Gesprächsteil.

**Sollvorschlag:** Unterjährige Dialoge jederzeit aus der gemeinsamen Arbeitsübersicht oder aus einer Stammdatenänderung starten, auch während einer laufenden Jahreskampagne. Vom Anlass zur passenden Konstellation führen; zeigen, ob ein bestehender Fall geändert oder ein zusätzlicher Dialog benötigt wird. Änderungen an Stammdaten von der historischen Formularzuordnung unterscheiden. Verantwortlichkeit über P10 festlegen. Bereits vorhandene Probezeit-, Jahres- oder Übertrittsdialoge anzeigen, damit kein unbeabsichtigter Doppelauftrag entsteht.

**Abschluss:** Fallkonstellation ist geklärt und nötige Ausgabe/Rücklaufaufgabe verknüpft.

**Offen:** Fachliche Spezialfallmatrix gemeinsam bestätigen, insbesondere Austritt. Technische Begrenzung bei mehreren Fällen derselben Person/Anstellung/Führungslinie im selben Durchlauf berücksichtigen.

### P08 – Auswertung, SAP und Abschluss

**Ist:** Auswertungen, Auswahl des SAP-massgeblichen Rückblicks, SAP-Batches, Abschlussprüfung, begründete Restfälle und Wiederöffnung. Externe SAP-/Roboterverarbeitung ist nicht mit lokaler Bereitstellung gleichzusetzen.

**Varianten:** Mehrere Rückblicke pro Jahr; noch ausstehender Ausblick; Korrektur nach Export/Ablage; verspäteter Eingang; Restfälle; Folgejahr.

**Sollvorschlag:** Auswertungen sind jederzeit nach Jahr, Zeitraum, Dialogart, OE und Zuständigkeit nutzbar und zeigen ihren Datenstand. Der Abschluss einer Jahreskampagne unterscheidet fachlich offene Arbeiten, Übergaben und extern zu kontrollierende Ergebnisse. Er blockiert keine neuen unterjährigen Dialoge. Offene Restfälle bleiben in der gemeinsamen Arbeitsübersicht sichtbar; abgeschlossene Einzelfälle benötigen für nachträgliche Änderungen einen nachvollziehbaren Korrekturweg.

**Offen:** Wie werden externe Verarbeitung und Korrekturen bestätigt? Aktuelle SAP-Exportvoraussetzungen einschliesslich gegebenenfalls erforderlichem Ausblick fachlich bestätigen.

### P09 – SAP-Stammdaten laufend aktualisieren

**Anforderung:** Häufige neue Exporte mit Eintritten, Austritten, Übertritten und weiteren Änderungen einlesen – auch bei bereits versendeten Formularen und laufenden Rückläufen.

**Ist:** SAP-Import und Synchronisierung sind vorhanden. Die genaue Wirkung jeder Änderung auf offene und historische Dialoge muss vor der Umsetzung geprüft werden; die nachfolgende Vorschau ist ein Sollvorschlag.

| Schritt | Sollablauf / HR-Entscheidung | Ergebnis |
|---|---|---|
| Neuen Export laden | Datenstand und Vollständigkeit prüfen; alten Stand zum Vergleich verwenden | Auswertbare Änderungsliste |
| Änderungen prüfen | Neue Personen, Austritte, Wechsel von OE/Führungskraft sowie Konflikte getrennt zeigen | Bedeutung und Zuordnung geklärt |
| Auswirkungen klären | Betroffene offene Dialoge und ausgegebene Formulare zeigen; bei Eintritt Dialogbedarf prüfen | Bestehenden Fall beibehalten/ändern oder zusätzlichen Dialog anlegen |
| Änderungen übernehmen | Bestätigte Aktualisierungen nachvollziehbar speichern; manuelle MD-Zuständigkeiten erhalten bzw. zur Entscheidung vorlegen | Aktueller Stammdatenstand mit dokumentierten Ausnahmen |
| Folgearbeit bearbeiten | Direkt zu Dialogstart, Zuständigkeitsklärung oder Korrekturausgabe führen | Verknüpfte Aufgaben statt erneuter Personensuche |

**Varianten:** Vollständiger Export, unbeabsichtigte Teilliste, unveränderter erneuter Import, Mehrfachanstellung, rückwirkende Änderung, fehlende Person, Führungskraft vakant, bestehende manuelle Zuständigkeit.

**Leitregeln für den Sollablauf:**
- Eine im Export fehlende Person nicht ohne Klärung als Austritt behandeln.
- Neue SAP-Führungskraft nicht automatisch zur verantwortlichen Person für einen bereits begonnenen historischen Dialog machen.
- Frühere Formulare, Zeiträume und abgeschlossene Dialoge bleiben nachvollziehbar.
- Ein Eintritt kann P07 auslösen; die passende Dialogpflicht folgt den fachlichen Regeln und bereits vorhandenen Fällen.
- Die Übernahme neuer Stammdaten ist abgeschlossen, wenn ihre Auswirkungen entschieden und Folgeaufgaben verknüpft sind; der Versand dieser Folgeaufgaben hat einen eigenen Status.

**Bestätigte Richtung (26. Oktober 2026):** Der Import führt zu einer konkreten Änderungsliste mit Auswirkungen und direkt erreichbaren Folgearbeiten. Unveränderte Personen werden nicht erneut zur Prüfung vorgelegt. Eindeutige Änderungen können gemeinsam übernommen werden. Manuelle MD-Zuständigkeiten bleiben erhalten; fehlende Personen gelten nicht automatisch als ausgetreten.

#### P09.1 Änderungsliste nach dem Upload

Die Vorschau zeigt bisherigen und neuen Datenstand sowie pro betroffenem Eintrag Person, Anstellung/OE, geänderte Angaben mit Alt-/Neuwert, betroffene Dialoge und Ausgaben sowie die vorgeschlagene Folgeaktion. Stammdatenübernahme und fachliche Entscheidung zu einem bestehenden Dialog sind getrennte Schritte.

| Erkannte Änderung | Vorgeschlagene Folgearbeit | Behandlung im Sollentwurf |
|---|---|---|
| Neue Person oder zusätzliche Anstellung | Dialogbedarf nach Anlass und Zeitraum prüfen; vorhandene Dialoge anzeigen | Eindeutigen Stammdatensatz gemeinsam übernehmen; Dialogvorschläge prüfen und passende gemeinsam anlegen |
| Explizites Austrittsdatum | Offene Dialoge und Pflichten prüfen | Stammdatum übernehmen; bestehende Pflichten nicht pauschal aufheben |
| Andere OE oder SAP-Führungskraft | Zuständigkeit, Zeitraum und ausgegebene Formulare prüfen | Neue organisatorische Zuordnung speichern; Auswirkungen auf betroffene laufende Dialoge gezielt entscheiden |
| Bestehende manuelle MD-Zuständigkeit | Abweichung und möglichen Konflikt anzeigen | Bewusste Zuordnung erhalten; Änderung nur nach ausdrücklicher Entscheidung |
| Geänderte Angaben, die im Formular verwendet werden | Betroffene Ausgaben zur Aktualisierung anbieten | Eindeutige Stammdaten gemeinsam übernehmen; Korrekturbedarf über P03 bearbeiten |
| Person/Anstellung fehlt im Export | Exportumfang, Identifikation oder Austritt klären | Keine automatische Aufhebung von Dialogen oder Versandaufträgen |
| Widersprüchliche oder mehrdeutige Zuordnung | Konflikt anhand der Quelldaten klären | Betroffene Zuordnung nicht ungeprüft überschreiben |
| Keine inhaltliche Änderung | Keine | Keine neue Aufgabe oder Korrekturausgabe |

Die Einordnung „eindeutig“ setzt eine belastbare Zuordnung zur Person und Anstellung sowie gültige Daten voraus. Ein geänderter Anzeigename allein darf nicht zu einer neuen Person führen.

#### P09.2 Aktionen und Wiederaufnahme – Sollentwurf

1. **Export prüfen:** Struktur, erforderliche Angaben und auffällige Abweichungen im Umfang prüfen. Ein möglicherweise unvollständiger Export wird vor der Übernahme als solcher kenntlich gemacht.
2. **Änderungen ansehen:** Nach neuen Personen, Austritten, Zuständigkeits-/OE-Wechseln, Formularänderungen und Konflikten filtern. Unveränderte Datensätze erscheinen nur bei Bedarf.
3. **Eindeutige Änderungen übernehmen:** Eine gemeinsame Aktion übernimmt die zulässigen Änderungen und legt verknüpfte Folgeaufgaben an. Sie erzeugt oder versendet noch keine Formulare und ändert nicht stillschweigend die historische Verantwortung für einen Dialog.
4. **Klärungsfälle bearbeiten:** Einzelentscheidung direkt am betroffenen Dialog treffen. Gleichartige Fälle dürfen gemeinsam entschieden werden, wenn Auswirkungen und Auswahl vorher sichtbar sind.
5. **Ergebnis bearbeiten:** Direkt aus der Ergebnisliste neue Dialoge starten, Verantwortlichkeit klären oder Formulare gesammelt aktualisieren.

**Beispiel einer Ergebnisliste (fiktive Zahlen):**
- 3 neue Personen: Dialogbedarf prüfen;
- 2 laufende Dialoge: MD-Zuständigkeit klären;
- 4 ausgegebene Formulare: Aktualisierung prüfen;
- 1 fehlende Anstellung: Ursache klären.

Die Zahlen bezeichnen Aufgaben bzw. betroffene Ausgaben; eine Person kann mehrere Folgearbeiten auslösen. Der UI-Entwurf muss die Zähleinheit jeweils nennen.

**Status unterscheiden:** „Daten übernommen“ beschreibt die Stammdatenaktualisierung. „Folgearbeiten offen“ zeigt noch ausstehende Dialogentscheidungen oder Korrekturen. „Abgleich geklärt“ bedeutet, dass die Auswirkungen entschieden und Folgearbeiten verknüpft sind; ein noch ausstehender Korrekturversand bleibt als eigene Aufgabe sichtbar.

**Wiederaufnahme:** Ein erneuter Import derselben Daten erzeugt keine doppelten Dialoge oder Aufgaben. Ändern sich Daten während einer offenen Klärung erneut, werden Alt-/Neustand und Vorschlag aktualisiert und eine veraltete Entscheidung nicht ungeprüft angewendet.

**Noch technisch zu entscheiden:** Ob ein Import mit ungelösten Datenkonflikten teilweise übernommen werden kann oder als vollständiger Datenstand warten muss. Vor Umsetzung sind Konsistenz und bisherige Synchronisierungslogik zu prüfen. Die gemeinsame Übernahme eindeutiger Änderungen ist das Bedienziel; sie darf nicht unbemerkt einen unvollständigen Export zum vollständigen SAP-Stand erklären.

#### P09.3 Prüfkriterien

- Ein Eintritt während der Jahreskampagne führt zu einem passenden Dialogvorschlag in derselben Arbeitsübersicht.
- Ein Führungswechsel überschreibt keine manuelle MD-Zuständigkeit und keine historische Zuordnung.
- Ein Austritt oder fehlender Datensatz löscht keine laufenden Rücklaufarbeiten.
- Unveränderte Daten erzeugen keine neue Prüfpflicht.
- Gemeinsame Übernahme zeigt nachvollziehbar, was übernommen und was zurückgehalten wurde.
- Jede Folgeaufgabe öffnet den betroffenen Fall mit dem Grund der Änderung.
- Alte Ausgaben bleiben erhalten; neue Stammdaten allein bestätigen weder Neuerstellung noch Versand.


### P10 – Zuständigkeit und Formular-OE je Gesprächsteil

**Bestätigte Anforderungen (26. Oktober 2026):**
- Rückblick und Ausblick einer Person können unterschiedliche verantwortliche Führungskräfte haben.
- Beispiel Übertritt im zweiten Halbjahr: Die bisherige Führungskraft übernimmt den Rückblick, die neue den Ausblick.
- Auch aus anderen Gründen, etwa Langzeitabwesenheit oder Vakanz, kann eine andere Führungskraft einen oder beide Gesprächsteile übernehmen.
- Die Formular-OE muss zur konkreten Gesprächskonstellation passen. Die aktuelle OE der mitarbeitenden Person ist für einen historischen Rückblick nicht immer richtig. Die bereits vorhandene Auswahl der OE der zugewiesenen Führungskraft bleibt fachlich erforderlich.
- Für die Zeit vor Einführung fehlen SAP-Vergleichsstände; historische Konstellationen müssen manuell erfasst werden. Mit laufenden Importen sollen Änderungen künftig aus den verfügbaren Stammdatenständen erkannt und als Zuordnungsvorschlag genutzt werden.

**Ist:** Für manuelle Ereignisse sind Führungskraft und Formular-OE auswählbar. Die vorhandene Auswahl zwischen Mitarbeiter-OE und Führungskraft-OE ist bestätigt. Eine durchgängige Zuständigkeit je Gesprächsteil, historische Ableitung und entsprechende Folgeaktionen werden hier noch nicht als implementiert vorausgesetzt.

#### P10.1 Fachliches Modell

| Angabe | Bedeutung / Geltungsbereich |
|---|---|
| Aktuelle SAP-Führungskraft und OE | Aktueller organisatorischer Stand der Anstellung |
| Frühere organisatorische Zuordnung | Aus früheren Importständen bekannte Führungskraft/OE; Herkunft und zeitliche Aussagekraft bleiben sichtbar |
| Verantwortliche Führungskraft Rückblick | Konkrete Verantwortung für diesen Rückblick |
| Verantwortliche Führungskraft Ausblick | Konkrete Verantwortung für diesen Ausblick |
| Formular-OE je Gesprächsteil | Auswahl Mitarbeiter-OE oder OE der zugewiesenen Führungskraft; verwendete OE wird für den Gesprächsteil nachvollziehbar festgehalten |
| Zeitraum je Gesprächsteil | Fachlicher Zeitraum des Rückblicks bzw. Ausblicks, unabhängig vom Datum des Stammdatenimports |
| Herkunft der Zuständigkeit | Aus SAP vorgeschlagen, aus Historie vorgeschlagen oder manuell festgelegt; Entscheidung mit Grund nachvollziehbar |

Die Oberfläche kann beide Teile gemeinsam zeigen. Sie muss nicht für eine abweichende Führungskraft einen zweiten vollständigen MD mit doppelten Pflichten erzeugen. Wie dies auf bestehende Fälle und Ereignisse abgebildet wird, ist eine technische Entwurfsfrage.

#### P10.2 Beispiele

| Anlass | Rückblick | Ausblick | Formular-OE |
|---|---|---|---|
| Regulärer MD ohne Wechsel | Regulär zuständige Führungskraft | Regulär zuständige Führungskraft | Üblicherweise OE der mitarbeitenden Person |
| Übertritt im zweiten Halbjahr | Bisherige Führungskraft | Neue Führungskraft | Für Rückblick bisherige Konstellation, z. B. OE der zugewiesenen bisherigen Führungskraft; für Ausblick neue Konstellation |
| Langzeitabwesenheit der Führungskraft | Ersatzperson, falls dieser Teil übernommen wird | Ersatzperson oder reguläre Führungskraft entsprechend Entscheidung | Eigenständig prüfen; Ersatzperson aus anderer OE bedeutet nicht automatisch andere Mitarbeiter-OE |
| Vakanz | Festgelegte Vertretung | Festgelegte Vertretung oder neue Führungskraft | Mitarbeiter-OE kann trotz anderer Führungskraft bestehen bleiben |
| Übertritt vor erstem verfügbaren Import | Bisherige Führungskraft manuell auswählen | Neue Führungskraft auswählen/bestätigen | Je Teil explizit festlegen |

Das Übertrittsbeispiel beschreibt die vom Nutzer bestätigte Aufteilung der Verantwortung. Daraus werden keine zusätzlichen Regeln zu Beurteilungszeiträumen, weiteren Gesprächen oder zur SAP-massgeblichen Beurteilung abgeleitet; diese bleiben gesondert festzulegen.

#### P10.3 Ableitung aus Stammdatenhistorie

**Sollvorschlag:** P09 vergleicht die Zuordnung derselben Person und Anstellung über die Importstände. Ein Wechsel von Führungskraft oder OE erzeugt einen prüfbaren Änderungsvorschlag für die betroffenen Gesprächsteile. HR bestätigt, ob ein Übertritt, eine organisatorische Änderung oder eine andere Konstellation vorliegt.

- Frühere und aktuelle Zuordnung mit Herkunft und Datum des Datenstands anzeigen.
- Ein Importdatum ist kein sicherer Übertrittstermin. Wenn SAP kein verlässliches Wirksamkeitsdatum liefert, zeigt die App nur den erkannten Wechsel zwischen den Datenständen und verlangt bei fachlicher Relevanz die Ergänzung des Ereignisdatums.
- Ohne hinreichende Historie keine bisherige Führungskraft oder historische OE erfinden; manuelle Erfassung anbieten.
- Eine bereits bewusst festgelegte MD-Zuständigkeit bleibt erhalten. Eine neu erkannte Abweichung führt zur Prüfung, nicht zu einer stillen Ersetzung.
- Historische Formularwerte dürfen nicht bei jeder Neuerzeugung aus den aktuellen Stammdaten neu berechnet werden. Auch wenn sich die OE der früheren Führungskraft später ändert, muss die bestätigte Konstellation nachvollziehbar bleiben.
- Bereits ausgeschiedene oder inzwischen nicht mehr als Führungskraft geführte Personen müssen für historische Zuordnungen berücksichtigt werden können; Versandfähigkeit separat prüfen.

#### P10.4 Bearbeitungsablauf – Sollvorschlag

1. Person/Anstellung und Anlass öffnen; bestehende Dialoge und beide Gesprächsteile anzeigen.
2. Für Rückblick und Ausblick jeweils verantwortliche Führungskraft, Zeitraum und Formular-OE prüfen.
3. Bei manueller Abweichung „Rückblick“, „Ausblick“ oder „beide Teile“ auswählen; Ersatzperson und Grund erfassen. Dieselbe Entscheidung kann für mehrere ausgewählte Personen angewendet werden, wenn die betroffenen Teile und Auswirkungen sichtbar sind.
4. Vorschlag aus SAP/Historie bestätigen oder manuell korrigieren. Bewusste Entscheidungen je Gesprächsteil speichern.
5. Auswirkungen anzeigen: Welche Formulare müssen erstellt/korrigiert werden, welche offenen Versandvorgänge sind überholt und wer erhält künftige Erinnerungen?
6. Folgearbeiten direkt öffnen; unveränderte Gesprächsteile bleiben unverändert.

**Abschluss:** Zuständigkeit und Formular-OE sind je betroffenem Teil festgelegt und Folgearbeiten verknüpft. Ein Wechsel allein bestätigt keinen Versand.

**Folgen für andere Prozesse:**
- P02/P03 bündeln Formulare nach der für den jeweiligen Gesprächsteil zuständigen Person. Bei getrennter Verantwortung erhält nicht automatisch jede Führungskraft beide Teile.
- P04 ordnet Rückläufe dem richtigen Gesprächsteil und historischen Kontext zu; aktuelle SAP-Zuordnung allein reicht nicht.
- P06 richtet Erinnerungen für fehlende Rückblicke/Ausblicke an die jeweils verantwortliche Führungskraft.
- Feedback an eine bestimmte Führungskraft wird nicht pauschal der Ersatzperson oder neuen MD-Verantwortlichen zugeordnet.
- Bereits übermittelte oder zurückgegebene Dokumente behalten ihren Verlauf; notwendige Korrekturen werden ausdrücklich entschieden.

**Noch offen:** Brauchen wir zusätzlich zeitlich befristete Vertretungen für eine ganze OE oder genügt zunächst die gemeinsame Auswahl konkreter Gesprächsteile? Welche Wirksamkeitsdaten und historischen Angaben liefert der tatsächliche SAP-Export? Fachliche Regeln für andere Übertrittszeitpunkte und die SAP-massgebliche Beurteilung sind separat zu bestätigen.

**Prüfkriterien:**
- Übertritt im zweiten Halbjahr führt zu Rückblick bei alter und Ausblick bei neuer Führungskraft, ohne doppelte Pflichten.
- Die Konstellation lässt sich auch ohne Importhistorie manuell erfassen.
- Langzeitabwesenheit erlaubt Ersatz für nur einen oder beide Teile.
- Formular-OE ist je Teil unabhängig von aktueller Mitarbeiter-OE festgelegt.
- Ein neuer SAP-Import erhält bestätigte manuelle Zuständigkeiten.
- Ein aus Vergleichsständen erkannter Wechsel erhält kein erfundenes Wirksamkeitsdatum.
- Sammelerstellung, Versand und Erinnerungen respektieren die Zuständigkeit je Teil.

## 5. Detailablauf P03: Alter Ausblick geht nachträglich ein

### 5.1 Heutiger Weg und Bruchstellen

1. Postfachscan sichert den Word-Anhang und versucht den Zielimport.
2. Eindeutige Ziele werden übernommen. Bei Teilübernahme bleibt eine Prüfung offen; bei unklarem Jahr, Zuordnung oder abweichender Quelle ist manuelle Klärung nötig.
3. Für manche Fehler verweist die App auf Stammdaten/Vorjahresimport. Bereits gespeicherte Dokumente können dadurch einen Download und erneuten Upload erfordern.
4. Der manuelle Import zeigt eine Vorschau; nach Übernahme folgt die Meldung „Bitte die Word-Dossiers neu erzeugen.“ Die Seite bleibt die Importvorschau.
5. Betroffene Ausgaben müssen über Führungslinie bzw. Versand/Änderungsprüfung gefunden werden. Personenspezifische Korrekturen besitzen einen eigenen Versandablauf.
6. Mailprüfung und Korrekturversand sind keine durchgängige Aufgabenfolge.

Besonderheit: Der Postfachimport erlaubt partielle Word-Übernahme. Die manuelle Vorschau behandelt unklare Erkennung restriktiver. Diese Unterschiede müssen beim Zusammenführen der Wege ausdrücklich aufgelöst werden.

### 5.2 Sollvorschlag: Durchgehender Vorgang

| Schritt | Automatik / Anzeige | Aktion HR | Ergebnis und nächster Schritt |
|---|---|---|---|
| 1 Eingang erkennen | Original sichern; Herkunft, Dokumentart und mögliche Zuordnung anzeigen | Nur unklare Zuordnung klären | Zugeordnet zu Person, Anstellung, Zieljahr |
| 2 Ziele prüfen | Erkannte Ziele, bestehende Quellen und genaue offene Stellen zeigen | Original vergleichen; unklare Inhalte ergänzen/bestätigen oder Rückfrage vermerken | Freigegebene Quelle oder begründeter Wartezustand |
| 3 Auswirkungen bestimmen | Passende Rückblicke und bereits erzeugte/versendete Fassungen ermitteln | Aktualisierung je betroffenem Fall bestätigen oder begründet verneinen | Konkrete Liste nötiger Ausgaben |
| 4 Rückblick erstellen | Nur gewählte Formulare mit der freigegebenen Quelle erzeugen | Ergebnis prüfen | Geprüfte Korrekturausgabe |
| 5 Übermittlung | Richtige Führungskraft und konkrete Ausgabe vorauswählen | Versand vorbereiten und tatsächlichen Versand bestätigen | Übermittlung dokumentiert |
| 6 Vorgang abschliessen | Prüfen, ob offene Klärungen und Folgearbeiten verbleiben | Nur nötige Restentscheidung treffen | Vorgang erledigt; Mailablage separat erkennbar |

Die direkte Bearbeitung erkannter Word-Ziele ist ein Sollvorschlag, keine vorhandene Funktion. Bereits gespeicherte Anhänge werden innerhalb des Vorgangs weiterverwendet.

### 5.3 Verzweigungen und Abschlussbedingungen

| Variante | Vorgeschlagener Weg | Wann erledigt? |
|---|---|---|
| Alles eindeutig, noch keine Ausgabe vorhanden | Quelle speichern und für Erstausgabe bereitstellen | Zielquelle freigegeben; verbundene Erstausgabe bleibt in P02 sichtbar |
| Alles eindeutig, Rückblick bereits versendet | Korrekturbedarf zeigen; gezielte Neuerstellung und Versand | Korrektur übermittelt oder begründeter Verzicht |
| Ziele nur teilweise erkannt | Offene Stellen am Original prüfen; Rückfrage oder Ergänzung | Keine ungeklärten Stellen mehr bzw. ausdrückliche Entscheidung zum Umgang damit |
| Person, Anstellung oder Jahr unklar | Im selben Vorgang auswählen/bestätigen | Eindeutige bestätigte Zuordnung |
| Mehrere abweichende Quellen | Inhalt und Herkunft vergleichen; gültige Quelle wählen | Quelle gewählt und Folgen für Ausgaben geklärt |
| Identische Datei / identische Ziele | Bestehende Verarbeitung verlinken | Keine zusätzliche Arbeit; vorhandene offene Folgearbeit bleibt bestehen |
| Kein passender aktiver Rückblick | Historischen Bezug, Gesprächsumfang und Zeitraum prüfen | Quelle gespeichert und „keine aktuelle Ausgabe nötig“ begründet oder richtiger Fall verknüpft |
| Rückblick schon bearbeitet oder zurückgegeben | Abstimmung zur nötigen Korrektur statt blindem Ersatz | Vereinbarter Korrekturweg erledigt; bestehender Inhalt bleibt nachvollziehbar |
| Rückfrage an Führungskraft nötig | Grund, Adressat und nächsten Prüftermin festhalten | Antwort verarbeitet; nicht schon mit Erstellen der Rückfrage |
| Mehrere Anhänge / gemischte Mail | Anhänge einzeln bearbeiten; Mail als gemeinsame Herkunft | Alle relevanten Anliegen geklärt; Mailablage getrennt dokumentiert |
| Unterbrechung bei Erzeugung/Outlook | Letzten bestätigten Schritt anzeigen und dort fortsetzen | Tatsächlicher Ausgang geklärt; keine doppelte Ausgabe/Übermittlung |

### 5.4 Fachliche Entscheidungen für diesen Ablauf

**Empfehlungen zur Bestätigung:**
1. Mail und manueller Upload führen in denselben fachlichen Prüfablauf.
2. Unsichere Stellen bleiben sichtbar, auch wenn lesbare Ziele schon gespeichert wurden.
3. Für automatisch als unklar erkannte Teilübernahmen erfolgt die Freigabe zur Korrekturausgabe erst nach einer ausdrücklichen Entscheidung zu den offenen Stellen.
4. HR kann eine Neuerstellung begründet als nicht nötig entscheiden; die Aufgabe verschwindet nicht allein durch Übernahme der Quelle.
5. Änderungen nach bereits bearbeitetem/retourniertem Rückblick benötigen einen gesonderten Korrekturentscheid.

**Bestätigte Entscheidung (26. Oktober 2026):** HR soll unvollständig erkannte Ziele direkt in der App ergänzen und korrigieren können. Original und erkannte Ziele werden nebeneinander zugänglich gemacht. Änderungen werden nachvollziehbar gespeichert; die bestätigte Fassung bildet die Grundlage für Rückblicke und spätere Neuerstellungen. Dies ist eine beschlossene Anforderung, noch keine implementierte Funktion.

### 5.5 Mehrere nachgereichte Ausblicke gemeinsam bearbeiten

**Anforderung:** Reicht eine Führungskraft mehrere Ausblicke nach, soll HR die neuen Rückblicke für alle betroffenen Mitarbeitenden in einem Zug erstellen können.

**Sollablauf:**
1. Gemeinsamen Eingang oder ausgewählte Nachreichungen öffnen; pro Person Anstellung, Zieljahr, Quelle und Prüfstatus anzeigen.
2. Freigegebene Fälle gemeinsam auswählen; unklare Fälle mit konkretem Grund zurückhalten.
3. „Ausgewählte Rückblicke erstellen“ erzeugt nur die benötigten Rückblicke; ein vollständiges neues Führungskräftepaket ist dafür nicht nötig.
4. Ergebnisse pro Person anzeigen. Erfolgreiche Ausgaben bleiben erhalten; fehlgeschlagene können gezielt wiederholt werden.
5. Geprüfte Rückblicke pro tatsächlicher MD-verantwortlicher Führungskraft für einen gemeinsamen Versand bündeln. Der Absender der Nachreichung ist nicht automatisch der richtige Empfänger.
6. Versandstatus sowohl für das Bündel als auch die enthaltenen Ausgaben nachvollziehen. Offene Personen bleiben sichtbar und können später als Nachtrag folgen.

**Beispiel:** Fünf Ausblicke kommen gemeinsam an. Vier Quellen sind freigegeben, eine braucht Klärung. HR kann vier Rückblicke gemeinsam erstellen und übermitteln; die fünfte Aufgabe bleibt mit Grund offen. Ein Teilerfolg darf nicht den gesamten Eingang als fachlich abgeschlossen darstellen.

**Abgrenzung:** Die Sammelaktion spart wiederholte Bedienung; Prüfung, Zuordnung und Verlauf bleiben pro Person/Anstellung und Dokument erhalten. Die bestehende Unterstützung für personenspezifische Korrekturen ist noch kein Nachweis, dass dieser Sammelablauf bereits implementiert ist.

### 5.6 Prüfmaske und Übergang zur Sammelerstellung – Sollentwurf

Dieser Entwurf konkretisiert die bestätigte direkte Zielkorrektur. Die genaue Gestaltung und technische Umsetzung stehen noch aus.

**Einstieg:** Eine Nachreichung oder Sammelauswahl öffnet eine Personenliste mit Name, Anstellung/OE, Zieljahr, MD-Verantwortlichkeit und Prüfstatus. Bei mehreren Personen zeigt sie, wie viele Quellen noch ungeklärt und wie viele bereits freigegeben sind.

**Bearbeitung einer Quelle:**
- Kopfbereich: Person, Anstellung, Zieljahr und Herkunft; unklare Zuordnungen direkt bearbeiten.
- Originalbereich: unveränderte eingegangene Datei zugänglich machen; erkannte Fundstellen soweit verfügbar anzeigen.
- Zielbereich: Leistungs- und Entwicklungsziele mit Zieltext, Kompetenz, Messkriterien, Weg zum Ziel und Termin bearbeiten.
- Fehlende Ziele ergänzen, irrtümlich erkannte Zeilen entfernen und falsch aufgeteilte Inhalte korrigieren können.
- Unsichere Stellen konkret markieren. Ein vom Import leer gelassenes Feld ist nicht automatisch eine fachliche Lücke; HR gleicht es mit dem Original ab.
- Original, automatische Erkennung und von HR bestätigte Fassung getrennt nachvollziehbar halten. Bearbeiter und Änderungszeitpunkt dokumentieren.

**Aktionen und ihre Wirkung:**

| Aktion | Wirkung | Folge |
|---|---|---|
| Entwurf speichern | Zuordnung und bearbeitete Ziele sichern; noch keine Freigabe | Später an derselben Stelle weiterarbeiten |
| Rückfrage vermerken | Offenen Punkt und benötigte Klärung festhalten; kein automatischer Mailversand | Quelle bleibt ungeklärt |
| Ziele bestätigen | Aktuelle Zuordnung und korrigierte Fassung fachlich freigeben | Betroffene Rückblicke für die Erstellung anbieten |
| Nächste Person prüfen | Zur nächsten Quelle derselben Auswahl wechseln | Kontext und bisherige Ergebnisse bleiben erhalten |

**Nach Bestätigung:** Die Übersicht zeigt beispielsweise „4 Quellen freigegeben, 1 Rückfrage offen“. HR wählt die passenden Rückblicke aus und startet „Ausgewählte Rückblicke erstellen“. Anschliessend folgen Ergebnisprüfung und gebündelte Versandvorbereitung nach MD-Verantwortlichkeit. Die Freigabe einer Quelle erstellt oder versendet für sich allein noch kein Formular.

**Änderung nach Freigabe:** Wird eine bestätigte Quelle erneut korrigiert, muss die neue Fassung wieder bestätigt werden. Bereits erstellte oder versendete Rückblicke bleiben als historische Fassungen erhalten; die App zeigt den daraus entstandenen Korrekturbedarf.

**Technisch zu klären:** Word-Dateien lassen sich nicht ohne Weiteres im Browser originalgetreu anzeigen. Für die Gegenüberstellung ist eine geeignete Vorschau bzw. lokale Konvertierung zu prüfen; die Originaldatei bleibt zusätzlich zugänglich. Eine reine Textextraktion darf nicht als originalgetreue Darstellung bezeichnet werden.

**Prüfkriterien für die spätere Umsetzung:**
- Korrigierte Ziele werden beim Erstellen und erneuten Erstellen tatsächlich verwendet.
- Ein gespeicherter Entwurf ist von einer bestätigten Quelle unterscheidbar.
- Abbruch und Wiederaufnahme erhalten Änderungen und Gruppenkontext.
- Erneuter Eingang desselben Originals überschreibt keine bestätigte HR-Korrektur.
- Eine Änderung nach Freigabe macht betroffene Ausgaben erkennbar.
- Ungeklärte Quellen bleiben bei einer erfolgreichen Sammelerstellung offen.

## 6. Übergreifende Regeln für die spätere Nutzerführung

1. Jede Aufgabe zeigt Anlass, betroffene Person/Anstellung, Jahr, offenen Punkt und nächste Aktion.
2. Aufgaben verlinken direkt zur konkreten Bearbeitung; Jahres- und Personenkontext bleiben erhalten.
3. „Warten auf HR“, „Warten auf Rückmeldung“ und „Technisch blockiert“ sind unterscheidbar.
4. Ein Ergebnis löst die passende Folgeaufgabe aus oder schliesst den Vorgang nachvollziehbar ab.
5. Verschiedene Ansichten zeigen denselben Bearbeitungsstand; keine unabhängigen Erledigt-Markierungen für dieselbe Facharbeit.
6. Mail, Anhang und Fall dürfen unterschiedliche Status haben; ihre Bedeutung wird sichtbar erklärt.
7. Wiederaufnahme und erneute Eingänge erzeugen keine unbemerkten Doppelarbeiten.
8. Alte Ausgaben bleiben nachvollziehbar; Änderungen zeigen die tatsächlich betroffenen Personen und Formulare.
9. Erfolgsmeldungen benennen Wirkung und nächsten Schritt konkret.
10. Offene Arbeiten sind unabhängig von Kampagne und Dialogart gemeinsam auffindbar; Filter schränken die Anzeige bewusst ein.
11. SAP-Führungslinie und MD-Zuständigkeit je Gesprächsteil werden getrennt geführt und bei Änderungen miteinander abgeglichen. Rückblick und Ausblick können unterschiedliche Führungskräfte und Formular-OE haben.
12. Sammelaktionen bündeln passende Aufgaben, ohne Einzelstatus, Fehler oder abweichende Empfänger zu verdecken.
13. Auch der alternative Abschluss „nicht erforderlich“, „Dublette“ oder „begründet verworfen“ ist nachvollziehbar.

## 7. Gemeinsame Ausarbeitung und Prüfung

Stand der gemeinsamen Ausarbeitung:
1. Prozessumfang mit laufendem Stammdatenabgleich, Zuständigkeit je Gesprächsteil und parallelen Dialogarten ergänzt.
2. Direkte HR-Korrektur erkannter Ziele und gemeinsamer Dokumenteneingang festgehalten.
3. Fünf vollständige Beispieldurchläufe konzeptionell geprüft (Abschnitt 8); verbleibende Fachfragen markiert.
4. Nächster Schritt: Arbeitsübersicht und konkrete Bearbeitung am Beispiel der Zielnachreichung als Seitenentwurf ausarbeiten.
5. Danach weitere Abläufe einordnen und Menüstruktur sowie technische Umsetzung ableiten.

Prüfszenarien für P03:
- eindeutiger Word-Ausblick nach bereits erfolgtem Erstversand;
- teilweise auslesbare Ziele;
- Mehrfachanstellung und fehlendes Zieljahr;
- konkurrierende Quelle und identischer erneuter Eingang;
- bereits bearbeiteter Rückblick;
- gemischte Mail;
- unterbrochener Korrekturversand;
- mehrere Nachreichungen mit teils unklaren Quellen und unterschiedlichen MD-Verantwortlichen.

Zusätzliche Prüfszenarien für das Grundmodell:
- SAP-Neuimport während der Jahreskampagne mit gleichzeitigem Eintritt, Austritt und Übertritt;
- Eintritt führt zu einem unterjährigen Dialog, während für andere Personen Jahresrückläufe offen sind;
- manuelle Zuständigkeit wegen Vakanz bleibt beim nächsten Import sichtbar erhalten;
- Übertritt nach Versand verändert den historischen Rückblick nicht unbemerkt;
- Kampagnenabschluss lässt offene Restfälle und neue unterjährige Aufgaben zugänglich.

Erfolgskriterium: Eine HR-Person ohne Projektwissen kann jeweils erkennen, was bereits geschehen ist, was konkret fehlt und wie sie bis zum fachlichen Abschluss gelangt.

## 8. Fünf vollständige Beispieldurchläufe

**Art der Prüfung:** Konzeptioneller Durchgang durch die vereinbarten Sollabläufe, keine Ausführung oder Abnahme der App. Personenbezeichnungen, Mengen und Situationen sind fiktive Beispiele. Noch offene Fachregeln sind als solche markiert.

### S01 – Regulärer Jahresdialog mit getrennten Rückläufen

**Ausgangslage:** Person A hat eine eindeutige Anstellung; Rückblick und Ausblick sind erforderlich und derselben Führungskraft zugeordnet. Stammdaten und verwendete Zielquellen sind geprüft.

| Schritt / Was HR sieht | Entscheidung oder Aktion HR | Systemaktion im Soll | Danach offen |
|---|---|---|---|
| Person A: Rückblick und Ausblick zur Ausgabe bereit | Gewählte Formulare erstellen und prüfen | Ausgabe mit verwendeten Grundlagen speichern | Versand vorbereiten |
| Geprüfte Ausgabe und Empfänger | Versand vorbereiten, tatsächlichen Versand bestätigen | Ausgabe und Versandnachweis verknüpfen | Rückblick und Ausblick ausstehend, jeweils mit Frist |
| Rückblick trifft vor dem Ausblick ein | Dokument direkt aus Eingang öffnen | Original sichern, Gesprächsteil und Fall vorschlagen | HR-Prüfung Rückblick; Ausblick weiterhin ausstehend |
| Angaben und Original nebeneinander | Angaben/Zuordnung bestätigen oder korrigieren | Fachliche Übernahme; erforderliche Folgeprüfung bestimmen | Gegebenenfalls Unterschriften-/Scanprüfung bzw. Bereitstellung |
| Rückblick fachlich geprüft | Nötige Folgeprüfung abschliessen | Bereitstellung des freigegebenen Dokuments protokollieren | Ausblick ausstehend; externe Verarbeitung separat |
| Ausblick trifft später ein | Prüfen und übernehmen | Dem Ausblickteil zuordnen; erforderliche Bereitstellung und spätere Zielnutzung verknüpfen | Gegebenenfalls Übergabe-/Exportaufgaben |
| Beide Teile erledigt | Gesamtstand prüfen | Keine unerledigte Dokumentpflicht anzeigen; Export-/Übergabestatus separat halten | Nur tatsächlich verbleibende externe oder administrative Arbeiten |

**Unterbrechung:** Benötigt der Rückblick eine Rückfrage, bleibt diese am Rückblick offen. Der separat eintreffende Ausblick kann trotzdem bearbeitet werden.

**Erkenntnis:** Ein einzelner Gesamtstatus „MD offen“ ist zu grob. Rückblick und Ausblick benötigen getrennte Fristen, Eingangs-, Prüf- und Erledigungsstände. „Noch nicht eingegangen“ darf nicht mit „bereits eingegangen, HR-Prüfung offen“ verwechselt werden.

**Offen:** Unterschriften-/Scanregeln je Dokumenttyp, Auslöser der Dossierbereitstellung sowie SAP-Exportvoraussetzungen abschliessend festlegen. Das Beispiel bestätigt keine neue Fachregel dazu.

### S02 – Fünf Ausblicke nachgereicht, vier zunächst verwendbar

**Ausgangslage:** Eine Führungskraft reicht fünf alte Ausblicke nach. Vier sind nach Prüfung verwendbar; beim fünften fehlt eine eindeutig lesbare Zielpassage. Rückblicke wurden bereits erstmals versendet.

| Schritt / Was HR sieht | Entscheidung oder Aktion HR | Systemaktion im Soll | Danach offen |
|---|---|---|---|
| Gemeinsamer Eingang mit fünf Dokumenten | Nachreichung öffnen | Pro Dokument Person, Anstellung, Zieljahr, Verwendung und Prüfbedarf anzeigen | Fünf Quellen prüfen |
| Vier Quellen vollständig, fünfte mit markierter Lücke | Vier bestätigen; fünfte anhand Original korrigieren oder Rückfrage vermerken | Bestätigte Fassungen speichern; unbestätigte getrennt halten | Vier Korrekturausgaben möglich; eine Klärung offen |
| Betroffene Rückblicke mit bisherigem Versandstand | Vier Rückblicke gemeinsam auswählen | Verantwortlichkeit und verwendbare Zielversion pro Ausgabe prüfen | Erstellung |
| Ergebnisse der Sammelerstellung | Vier Ausgaben prüfen | Pro Person konkrete Fassung und Erfolg/Fehler speichern | Versand der geprüften Ausgaben |
| Versandgruppe nach Rückblick-Verantwortlichkeit | Gemeinsamen Versand vorbereiten und bestätigen | Versand mit den enthaltenen vier Ausgaben verknüpfen | Fünfte Person weiterhin offen |
| Antwort zur fünften Quelle trifft ein | Gesicherten Vorgang fortsetzen, ergänzen und bestätigen | Neue bestätigte Fassung; einzelnen Rückblick anbieten | Nachtrag erstellen und versenden |
| Nachtrag übermittelt | Ergebnis kontrollieren | Alle fünf Folgearbeiten erledigt; Verlauf bleibt erhalten | Mailablage gegebenenfalls separat |

**Unterbrechung:** Schlägt eine von vier Erstellungen fehl, bleiben die drei erfolgreichen Ausgaben erhalten. Nur die fehlgeschlagene Erstellung wird wiederholt. Bereits versendete Fassungen werden nicht ungeprüft nochmals verschickt.

**Erkenntnis:** Die Sammelansicht braucht Einzelstatus. Die Eingangsgruppe und die Versandgruppe sind nicht zwingend identisch: Bei abweichender Verantwortung muss nach tatsächlichem Empfänger aufgeteilt werden.

**Offen:** Umgang mit inzwischen bearbeiteten oder retournierten Rückblicken; Zeitpunkt der Mailverschiebung. Word-Vorschau technisch prüfen.

### S03 – Übertritt im zweiten Halbjahr

**Ausgangslage:** Person B ist per bekanntem Ereignisdatum im zweiten Halbjahr von OE Alt zu OE Neu übergetreten. Die bisherige Führungskraft übernimmt den Rückblick, die neue den Ausblick. Der aktuelle SAP-Stand enthält OE Neu.

| Schritt / Was HR sieht | Entscheidung oder Aktion HR | Systemaktion im Soll | Danach offen |
|---|---|---|---|
| SAP-Vergleich zeigt Wechsel; alternativ manuell erfasster Übertritt | Anlass und verlässliches Ereignisdatum bestätigen | Herkunft der Angaben speichern; bestehende Dialoge anzeigen | Zuständigkeiten und Zeiträume prüfen |
| Zwei Gesprächsteile derselben Person | Rückblick alte, Ausblick neue Führungskraft zuordnen | Je Teil Verantwortung speichern; keine doppelten Pflichten erzeugen | Formular-OE und Zeitraum je Teil |
| Aktuelle Mitarbeiter-OE sowie gewählte Führungskräfte | Für Rückblick passende bisherige OE wählen, für Ausblick neue Konstellation bestätigen | Formular-OE je Teil festhalten | Ausgaben erstellen bzw. korrigieren |
| Betroffene Ausgaben und bisherige Versandstände | Nur nötige Formulare auswählen | Rückblick und Ausblick nach jeweiligem Empfänger bündeln | Versand an alte bzw. neue Führungskraft |
| Rückläufe treffen getrennt ein | Jeweils richtigen Teil prüfen | Historische Zuständigkeit berücksichtigen; nicht allein nach aktueller SAP-Linie zuordnen | Folgeprüfungen pro Teil |
| Fehlende Unterlage wird fällig | Konkreten Ausstand prüfen | Erinnerung an für diesen Teil verantwortliche Person anbieten | Fehlender Teil bleibt offen |

**Alternative ohne Historie:** Die frühere Zuordnung wird manuell erfasst. Dafür muss die bisherige Führungskraft auch auswählbar sein, wenn sie nicht mehr in der aktuellen Führungskräfteauswahl enthalten ist; Identität und Versandadresse werden gesondert geprüft.

**Erkenntnis:** Aktuelle Stammdaten, Verantwortung für den Gesprächsteil und verwendete Formular-OE sind drei getrennte Angaben. Die bestätigte historische Konstellation muss auch spätere Importe überstehen.

**Offen:** Der Übertrittstermin legt nicht automatisch den Beurteilungszeitraum fest. Die fachlichen Regeln für Zeiträume, zusätzliche Gespräche und die SAP-massgebliche Beurteilung bleiben zu bestätigen.

### S04 – Eintritt während laufender Jahresdialoge

**Ausgangslage:** Für bestehende Mitarbeitende laufen Rücklaufarbeiten. Ein neuer vollständiger SAP-Export enthält Person C, deren Eintritt einen unterjährigen Dialogbedarf auslöst.

| Schritt / Was HR sieht | Entscheidung oder Aktion HR | Systemaktion im Soll | Danach offen |
|---|---|---|---|
| Importvorschau: neue Person/Anstellung | Daten prüfen und übernehmen | Neue Anstellung speichern; vorhandene Dialoge auf mögliche Doppelanlage prüfen | Dialogbedarf klären |
| Aufgabe „Neue Person: Dialogbedarf prüfen“ | Passenden Anlass, erforderliche Teile, Zeitraum, Zuständigkeit und Fristen bestätigen | Vorschlag anhand verfügbarer Daten und bestätigter Fachregeln bilden | Dialog zur Ausgabe bereit |
| Unterjähriger Dialog in derselben Arbeitsübersicht wie Jahresdialoge | Unterlagen erstellen und prüfen | Eigene Pflichten und Ausgabe für diesen Anlass speichern | Versand |
| Geprüfte Unterlagen | Versand vorbereiten und bestätigen | Versand dokumentieren | Rücklauf zum unterjährigen Dialog |
| Dokument im gemeinsamen Eingang | Anlass/Zeitraum und Gesprächsteil prüfen | Richtigen Dialog zuordnen; Jahresdialoge anderer Personen unberührt lassen | Erforderliche Folgeprüfungen |
| Jahreskampagne wird abgeschlossen | Restfälle prüfen | Unterjährigen Dialog und seine offenen Aufgaben weiterhin zugänglich halten | Noch offene Aufgaben dieses Dialogs |

**Unterbrechung:** Fehlende Probezeit- oder Ereignisangaben führen zu einer konkreten Klärungsaufgabe. Sie rechtfertigen weder eine geratene Frist noch eine automatische Anlage aller denkbaren Dialogarten.

**Erkenntnis:** Neue Dialoge müssen aus dem Stammdatenabgleich direkt gestartet werden können. Eine vorherige Wahl oder Wiederöffnung eines Jahresdurchlaufs darf im Soll kein notwendiger Umweg sein.

**Offen:** Präzise Regeln für Eintritt/Probezeit und Verhältnis zum anschliessenden Jahresdialog sowie Anpassung der bestehenden technischen Durchlaufbindung.

### S05 – Vertretung für einen Teil und späterer SAP-Import

**Ausgangslage:** Die reguläre Führungskraft von Person D ist länger abwesend. Eine Ersatzperson übernimmt nur den Rückblick. Der Ausblick bleibt bei der regulären Führungskraft. Die Ersatzperson gehört einer anderen OE an.

| Schritt / Was HR sieht | Entscheidung oder Aktion HR | Systemaktion im Soll | Danach offen |
|---|---|---|---|
| Rückblick und Ausblick mit bisheriger Verantwortung | „Rückblick“ auswählen, Ersatzperson und Grund erfassen | Manuelle Entscheidung nur für diesen Teil speichern | Auswirkungen prüfen |
| Formular-OE und vorhandene Ausgaben | Mitarbeiter-OE beibehalten; nötige Korrektur bestimmen | OE-Auswahl unabhängig von Ersatzperson speichern | Gegebenenfalls Rückblick neu erstellen/versenden |
| Neuer SAP-Export nennt weiterhin reguläre Führungskraft | Daten übernehmen; nur neue relevante Konflikte prüfen | Bestätigte Abweichung erhalten; unveränderte Abweichung nicht als neuen Konflikt erzeugen | Vorher offene Aufgaben bleiben bestehen |
| Späterer Export enthält tatsächlich neue organisatorische Zuordnung | Auswirkungen auf die Vertretung prüfen | Alten, neuen und manuell festgelegten Stand nebeneinander zeigen | Nur betroffene Entscheidung offen |
| Rückblick fehlt, Ausblick hat anderen Stand | Nötige Erinnerung prüfen | Rückblick-Erinnerung an Ersatzperson richten | Rückblick ausstehend |
| Vertretung endet | Falls erforderlich betroffene Teile ausdrücklich neu zuordnen | Wirkung auf offene Ausgaben/Versand prüfen; abgeschlossene Rückblicke unverändert lassen | Nötige Folgearbeiten |

**Erkenntnis:** Eine bekannte begründete Abweichung darf nicht bei jedem Import erneut eine Aufgabe erzeugen. Erst eine inhaltlich neue relevante Änderung verlangt eine neue Prüfung. Ebenso darf das Ende einer Vertretung nicht rückwirkend die Verantwortung für erledigte Teile umschreiben.

**Offen:** Zeitlich befristete Vertretungsregeln auf OE-Ebene gegenüber gemeinsamer manueller Auswahl konkreter Teile. Feedbackzuordnung bleibt unabhängig vom Vertretungswechsel.

### 8.6 Ergebnis des konzeptionellen Durchgangs

Die Szenarien passen grundsätzlich zum vorgeschlagenen Modell. Sie sind kein Nachweis, dass der aktuelle Code sie bereits unterstützt. Der Durchgang schärft insbesondere folgende Anforderungen:

| Befund | Konsequenz für Konzept und spätere Oberfläche |
|---|---|
| Ein Gesamtstatus pro Person reicht nicht | Rückblick/Ausblick und ihre konkreten Pflichten getrennt zeigen |
| Fachlich erledigt und extern verarbeitet sind verschieden | Prüfung, Bereitstellung, Versand und externe Bestätigung unterscheiden |
| Eingang, Personengruppe und Versandgruppe können auseinanderfallen | Herkunft gemeinsam anzeigen; fachlich nach Teil und Empfänger gruppieren |
| Importe treffen auf manuelle Entscheidungen | Bekannte Abweichungen erhalten; nur neue relevante Änderungen zur Prüfung vorlegen |
| Zuständigkeit hat zeitlichen und fachlichen Kontext | Historische Zuordnung und Formularwerte nicht aus aktuellen Stammdaten überschreiben |
| Ein Vorgang kann teilweise erledigt sein | Einzelstatus, Wiederaufnahme und Nachträge in Sammelansichten erhalten |
| Unterjährige Dialoge laufen ganzjährig | Gemeinsame Arbeitsübersicht; Kampagne/Jahr als Filter und organisatorische Bündelung |
| Ableitung aus Daten hat Grenzen | Unbekannte Ereignis- und Wirksamkeitsdaten sichtbar klären statt erraten |

**Noch vor verbindlicher Umsetzung zu klären:**
- Unterschriften-/Scan- und Bereitstellungsregeln je Dokumentart;
- Eintritts-/Probezeit- und Übertrittsregeln einschliesslich Zeiträumen und zusätzlichen Dialogen;
- SAP-Exportvoraussetzungen und Auswahl der massgeblichen Beurteilung;
- Korrektur bereits bearbeiteter/retournierter oder extern verarbeiteter Unterlagen;
- automatische Mailverschiebung und Umfang zeitlicher Vertretungen.

Diese Punkte verhindern einen ersten Seitenentwurf nicht; der Entwurf muss sie als offene Regeln berücksichtigen.

### 8.7 Aus den Szenarien abgeleitete Arbeitsansichten – Vorschlag

| Arbeitsansicht | Leitfrage und Inhalt |
|---|---|
| Arbeitsübersicht | Was ist jetzt zu tun, was wartet auf Rückmeldung und was ist technisch blockiert? Alle Dialogarten, mit Filtern |
| Konkrete Bearbeitung | Welche Angaben fehlen für diese Aufgabe? Original, Zuordnung, Prüfung, Entscheidung und nächste Aktion im Kontext |
| Person und Dialoge | Welche Anlässe und Gesprächsteile gibt es für diese Anstellung? Verantwortung, Zeitraum, Formular-OE, Pflichten und Verlauf |
| Gemeinsame Erstellung / Versand | Welche freigegebenen Ausgaben kann ich zusammen erstellen und an wen übermitteln? Einzelstatus trotz Sammelaktion |
| Stammdatenabgleich | Was hat sich geändert und welche offenen Dialoge oder Ausgaben betrifft das? |

Dies sind benötigte Arbeitsansichten, noch keine beschlossene Menüstruktur. Eingangsliste, Quellenprüfung und Fallprüfung sollen sich in diese Wege einfügen, ohne neue konkurrierende Aufgabenlisten aufzubauen.

## 9. Quellen des Iststands

- [HR-Betreuung](HR_BETREUUNG.md) – Orientierung; ältere Datumsstände gegen Code abgleichen.
- [Postfach und Fortschrittsanzeige](../webapp/services/mail_intake.py)
- [Word-Zielimport aus Mails](../webapp/services/mail_goals.py)
- [Importansicht](../webapp/templates/legacy_goal_preview.html) und [Routen](../webapp/routes.py)
- [Arbeitsliste](../webapp/templates/worklist.html) und [Cockpit](../webapp/services/cockpit.py)
- [Änderungsprüfung](../webapp/services/dispatch_changes.py)
- [Personenspezifische Korrekturausgaben](../webapp/services/person_corrections.py)
- [Rücklaufansicht](../webapp/templates/returns.html) und [Fallprüfung](../webapp/services/case_review.py)
- [Dialoge und Ereignisse](../webapp/templates/dialogs.html)
- [Erinnerungen](../webapp/services/reminders.py)
- [Abschluss und Prüfwarteschlange](../webapp/services/hr_workflow.py)
