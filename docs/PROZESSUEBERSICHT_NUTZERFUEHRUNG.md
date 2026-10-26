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
| P10 | MD-Zuständigkeit festlegen oder ändern | Verantwortliche Führungskraft und Geltungsbereich sind nachvollziehbar festgelegt | P02/P03; bestehende Rückläufe und Historie berücksichtigen |

Einrichtung, Benutzerverwaltung, Backup und technische Störungen sind unterstützende Betriebsprozesse. Sie sollen fachliche Aufgaben bei Bedarf konkret blockieren und einen Lösungsweg anbieten, aber nicht die normale Arbeitsübersicht dominieren.

## 3. Welche Einheiten zusammengehören

| Einheit | Bedeutung für die Nutzerführung |
|---|---|
| Durchlauf / Jahreskampagne | Ist: technischer Jahreskontext. Soll: organisatorische Bündelung und Filter; keine Zugangshürde für unterjährige Dialoge oder globale Eingänge |
| Dialogfall | Person, Anstellung, Anlass, Zeitraum und MD-Zuständigkeit; mehrere fachlich unterschiedliche Dialoge pro Jahr möglich; Zuständigkeitswechsel allein erzeugt nicht automatisch einen neuen Dialog |
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

**Sollvorschlag:** Vom Anlass aus direkt zu betroffenen Formularen und deren Versand führen. Gültige Quelle, verwendete Ausgabe und Versand bleiben verknüpft. Mehrere nachgereichte Ausblicke gemeinsam prüfen und alle ausgewählten freigegebenen Rückblicke in einem Arbeitsschritt erstellen. Bündelung und Versand nach tatsächlicher MD-Zuständigkeit; Einzelstatus und Wiederaufnahme bleiben möglich (Abschnitt 5.5).

**Abschluss:** Alle betroffenen Ausgaben wurden bearbeitet; eine unterlassene Neuerstellung/Übermittlung ist begründet.

### P04 – MD-Rückläufe prüfen und bereitstellen

**Ist:** Postfachscan oder PDF-Upload; Word-PDF-Prüfwarteschlange; Originalvergleich, Fallzuordnung und fachliche Übernahme; anschliessende Fall-/Unterschriften- bzw. Scanprüfung und Dossierbereitstellung.

**HR-Arbeit:** Dokumentart, Person/Anstellung, Jahr/Zeitraum und Angaben prüfen; benötigte Unterschriften/Scans kontrollieren; fehlende oder falsche Unterlagen klären.

**Varianten:** Rückblick, Ausblick, Probezeit; historischer Ausblick als Zielquelle; alter Formularstand; Dublette/neue Version; unlesbares PDF/Scan; unklare Zuordnung; inaktiver Fall; geschlossener Durchlauf; Nichtdurchführung; gemischte E-Mail.

**Sollvorschlag:** Ein Eingang bietet unmittelbar die passende Bearbeitung. Nach fachlicher Übernahme direkt zur noch nötigen Prüfung führen. Fehlende Unterschrift, unlesbare Angaben und technische Ablagefehler erhalten unterschiedliche Aufgaben.

**Abschluss:** Dokument ist geprüft und erforderliche Übergabe ist erfolgt, oder es ist nachvollziehbar zurückgewiesen/zurückgestellt. Ein benötigter, ungeklärter Rücklauf bleibt offen.

**Offen:** Die fachliche Unterschriften-/Scanregel je Dokumenttyp wird im Detail separat gegen den aktuellen Word-Standard geprüft; ältere HTML-Regeln nicht ungeprüft übernehmen.

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

**Offen:** Welche Änderungen dürfen nach der Vorschau gemeinsam übernommen werden, welche brauchen eine Einzelentscheidung? Die Prüfung soll nach fachlichen Auswirkungen priorisieren, nicht jede unveränderte Person erneut vorlegen.

### P10 – MD-Zuständigkeit festlegen oder ändern

**Anforderung:** Eine andere Führungskraft kann den MD verantworten, beispielsweise bei Vakanz. Das kann bei Neuanlage oder einem bereits laufenden Dialog vorkommen.

**Ist:** Für manuelle Ereignisse sind Führungskraft und Formular-OE auswählbar. Eine umfassende Änderung der Zuständigkeit bestehender Dialoge einschliesslich Folgeaktionen wird hier noch nicht als vorhanden vorausgesetzt.

**Sollablauf:** Dialog bzw. betroffene Personen auswählen → SAP-Führungskraft und bisherige MD-Zuständigkeit anzeigen → verantwortliche Führungskraft auswählen → Grund, Geltungsbereich und Formular-OE bestätigen → Auswirkungen auf Formulare, offene Versandvorgänge, Rückläufe und Erinnerungen prüfen.

**Sollvorschlag:** Standardmässig gilt die Abweichung für den ausgewählten Dialog. Eine gemeinsame Zuweisung für mehrere ausgewählte Dialoge ist möglich. SAP-Zuordnung und manuelle MD-Zuständigkeit bleiben getrennt gespeichert. Ein neuer SAP-Import hebt die bewusste Abweichung nicht stillschweigend auf.

**Varianten:** Vakanz, Stellvertretung, Übertritt mit Rückblick durch alte Führungskraft, Zuständigkeitswechsel vor/nach Versand, bereits eingegangener Rücklauf, unterschiedliche Zuständigkeiten für verschiedene Gesprächsanlässe.

**Abschluss:** MD-Zuständigkeit ist gespeichert und nötige Korrekturen/Benachrichtigungen sind als Folgearbeit sichtbar. Ein Wechsel allein bestätigt keinen Versand. Feedback an eine bestimmte Führungskraft darf nicht pauschal auf die neue MD-verantwortliche Person umgebucht werden.

**Offen:** Brauchen wir zusätzlich zeitlich befristete Vertretungen für eine ganze Organisationseinheit oder genügt zunächst die gemeinsame Auswahl konkreter Dialoge? Können Rückblick und Ausblick desselben Anlasses unterschiedliche Verantwortliche benötigen?

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
11. SAP-Führungslinie und MD-Zuständigkeit werden getrennt geführt und bei Änderungen miteinander abgeglichen.
12. Sammelaktionen bündeln passende Aufgaben, ohne Einzelstatus, Fehler oder abweichende Empfänger zu verdecken.
13. Auch der alternative Abschluss „nicht erforderlich“, „Dublette“ oder „begründet verworfen“ ist nachvollziehbar.

## 7. Gemeinsame Ausarbeitung und Prüfung

Nächste Reihenfolge:
1. Prozessumfang und fehlende Varianten gemeinsam ergänzen; P09/P10 sowie parallele Jahres- und unterjährige Dialoge sind aufgenommen.
2. Entscheidungen aus P03 fachlich festlegen.
3. P03 als Seitenfolge entwerfen.
4. Muster auf P04 und danach weitere Prozesse übertragen.
5. Erst dann Menüstruktur und technische Umsetzung ableiten.

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

## 8. Quellen des Iststands

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
