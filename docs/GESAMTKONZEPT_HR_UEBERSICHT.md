# Gesamtübersicht und Nutzerführung im dauerhaften HR-Betrieb

Stand: 27. Oktober 2026  
Status: Konzept und Prüfkriterien, keine implementierte oder im Betrieb getestete Oberfläche.  
Grundlage: [Prozessübersicht](PROZESSUEBERSICHT_NUTZERFUEHRUNG.md), [Umsetzungsplan](UMSETZUNGSPLAN_NUTZERFUEHRUNG.md). Codebefunde beziehen sich auf main `9d7ca779afc18e9bd9c6607a5b3dbe8465537a18`.

## 1. Beurteilung und Entscheidung

Die beschriebenen Einzelprozesse reichen noch nicht als Nachweis einer übersichtlichen Gesamtanwendung. Die Gesamtgestaltung wird vor dem Umbau entworfen und mit HR-Szenarien geprüft. Die Umsetzung kann danach schrittweise erfolgen.

| Frage | Befund | Erforderliches Ziel |
|---|---|---|
| Alltag übersichtlich? | Arbeitsliste verwendet einzelne Aufgabenkarten; Funktionen verteilen sich auf mehrere fachliche und technische Einstiege | Kompakter Arbeitsvorrat mit konkreter nächster Aktion und Direktlink |
| Führungskraft nachvollziehbar? | Bestehende Ansicht ist durchlaufbezogen; Formularerstellung und Friständerung stehen vor dem Fallbestand | Offene Verantwortung zuerst, getrennt nach Gesprächsteil; Historie erreichbar |
| Mitarbeiterin nachvollziehbar? | Falldetail bietet Status, Dokumente und Verlauf, aber keinen umfassenden Personen-Einstieg über mehrere Ereignisse/Jahre | Personenübersicht mit laufenden und vergangenen MDs, Anstellungen und Zuständigkeiten |
| Grosse Listen? | Tabellensteuerung paginiert manche Tabellen clientseitig ab 50 Zeilen; einzelne Bereiche besitzen eigene Paginierung | Einheitliche serverseitige Suche, Filter und Paginierung; keine vollständige Historie im Browser laden |
| Orientierung? | Breadcrumbs bestehen bereits; Navigation ist umfangreich und aktive Kennzeichnung nicht überall gleich | Verlässlicher Seitenkopf, aktive Navigation, Rückkehr mit erhaltenen Filtern |
| Kurze verständliche Texte? | Führungskräfte- und Fallseiten mischen Erklärungen, Formulare und Verlauf | Status, Grund und nächste Aktion zuerst; Details bei Bedarf |
| 1000 Mitarbeitende? | Kein Lasttest oder Nutzbarkeitstest durchgeführt | Mehrjährigen Bestand und reale Arbeitsmengen prüfen; Mitarbeiterzahl allein ist kein Skalierungsnachweis |

Codebelege: [Arbeitsliste](../webapp/templates/worklist.html), [Führungskraft](../webapp/templates/manager.html), [Fall](../webapp/templates/case_detail.html), [Navigation](../webapp/templates/base.html), [Tabellensteuerung](../webapp/static/table_controls.js), [Feedback](../webapp/templates/feedback_collection.html).

## 2. Drei Perspektiven auf dieselben Vorgänge

### Arbeitsvorrat: Was muss HR jetzt tun?

Standardansicht zeigt offene Arbeit über Jahresgrenzen hinweg. Filter: „Jetzt bearbeiten“, „Warten auf Führungskraft“, „Frist überschritten“ und „Erledigt“. Fachlich blockierte Arbeit nennt den konkreten Grund. Eingang, fachliche Bearbeitung und externe Übergabe bleiben unterscheidbar.

Eine Zeile nennt Person oder Gruppe, Anlass/Zeitraum, Gesprächsteil, Aufgabe, zuständige Führungskraft, Frist und nächste Aktion. Wiederkehrende Einzelaufgaben einer Nachreichung können gruppiert werden; offene Einzelfälle bleiben zugänglich. Erfolgreich automatisch verarbeitete Dokumente stehen im Verlauf und erzeugen keine künstliche Prüfaufgabe.

### Führungskraft: Was ist bei dieser Führungskraft offen?

Der Seitenkopf nennt die Führungskraft und den betrachteten Umfang. Zähler unterscheiden Personen, Gesprächsteile und Aufgaben ausdrücklich. Eine Person mit zwei offenen Teilen darf nicht unbeschriftet als zwei Mitarbeitende gezählt werden.

Die Hauptliste zeigt Person/Anstellung, Anlass/Zeitraum, Rückblick, Ausblick beziehungsweise Probezeit, Frist und nächste Aktion. Nur fachlich anwendbare Teile erscheinen. Filter erlauben offene Arbeit, alle aktuellen Vorgänge und Historie. Mehrere Ereignisse derselben Person bleiben unterscheidbar.

Die Ansicht folgt der tatsächlichen Verantwortung je Gesprächsteil: Bei Übertritt kann der Rückblick bei der bisherigen und der Ausblick bei der neuen Führungskraft erscheinen. Aktuelle SAP-Linie und historische MD-Verantwortung sind sichtbar unterscheidbar. Historische Ansichten dürfen nicht nach jedem Stammdatenimport umgeschrieben werden.

Sammelaktionen werden nach Auswahl angeboten, beispielsweise „Rückblicke für 5 Personen erstellen“. Unzulässige Einträge und Gründe sind vor Ausführung sichtbar; erfolgreiche Einzelergebnisse bleiben bei Teilfehlern erhalten.

Feedback hat einen eigenen Bereich mit Sammlung je Führungskraft/Jahr, offenen Eingängen und Bündel-/Nachtragsstatus. Die Feedback-Zuordnung folgt nicht automatisch einer vorübergehenden MD-Vertretung. Es gibt keine automatische Vollständigkeitsmahnung für Feedback.

### Mitarbeitende: Welche MDs gibt es für diese Person?

Personensuche nach Name und Personalnummer. Bei Mehrfachanstellung ist die Anstellung ausdrücklich auswählbar. Der Kopf zeigt aktuelle Stammdaten; darunter zuerst laufende Ereignisse, danach die aufklappbare Historie.

Jedes Ereignis zeigt Anlass, Zeitraum, Teile, Verantwortlichkeit je Teil, Formular-OE, Frist, Dokumentstand und nächste Aktion. Jahres-MD, unterjähriger MD und Probezeit-Rückblick bleiben eigenständige Vorgänge. Ein neuer MD überschreibt keinen vorherigen.

Die Detailseite zeigt die Zusammenfassung vor Korrekturformularen. Originale, Versionen, Entscheidungen, Versand und Übergaben sind im Verlauf auffindbar. Feedback darf nur dort personenbezogen erscheinen, wo seine fachliche Zuordnung dies tatsächlich erlaubt; keine erfundene Autoren- oder Mitarbeiterzuordnung.

## 3. Navigation und Orientierung

Vorschlag für die Hauptnavigation: Arbeit, Mitarbeitende, Führungskräfte, Stammdaten, Auswertungen. Administration und Hilfe bleiben separat erreichbar.

„Arbeit“ enthält Arbeitsvorrat, Dokumenteneingang und Versand als klar benannte Ansichten. Feedback-Sammlungen sind sowohl global filterbar als auch bei der Führungskraft erreichbar. Dossierbereitstellung und SAP-Export behalten klar benannte Einstiege; ein reduziertes Menü darf keine Fachfunktion verstecken. Die endgültige Gruppierung wird am Prototyp geprüft.

Jede Bearbeitungsseite enthält:
- aktiven Navigationspunkt und eindeutigen Titel;
- Person oder Führungskraft, Anlass und Zeitraum als Kontext;
- kurze Statusaussage mit nächster Aktion;
- nachvollziehbaren Rückweg zur Ausgangsliste mit Filtern, Sortierung und Seite;
- stabile Direktlinks auf den konkreten Vorgang.

Jahr/Durchlauf ist ein Filter und organisatorischer Bezug, keine Grenze für offene Arbeit. Ein Standardfilter auf das aktuelle Jahr darf überfällige Altjahresfälle nicht unsichtbar machen.

## 4. Listen bei 1000 Mitarbeitenden und wiederkehrenden MDs

Ein plausibler synthetischer Prüfumfang sind 1000 Mitarbeitende über fünf Jahre mit je zwei regulären Gesprächsteilen: rund 10 000 Teile, zusätzlich Probezeit, unterjährige Ereignisse, Versionen und Aufgaben. Das ist ein Testszenario, keine gemessene Datenmenge oder Leistungszusage.

- Serverseitige Suche, Filter, stabile Sortierung und Seiten mit 25/50/100 Einträgen.
- Trefferzahl bezieht sich auf alle passenden Datensätze, nicht nur die geladene Seite.
- Filter nach Status, Dokumentart/Anlass, Zeitraum, Führungskraft und OE; historischer Bezug der OE klar benennen.
- Standardmässig relevante offene Arbeit; erledigte Historie gezielt zuschaltbar.
- Kompakte Zeilen ohne dauerhaft geöffnete Upload- und Korrekturformulare.
- Auswahl „diese Seite“ und „alle passenden Treffer“ ausdrücklich unterscheiden; bei Filterwechsel keine unsichtbare Auswahl beibehalten.
- Vor Sammelaktionen Anzahl, Umfang, ausgeschlossene Einträge und Empfänger prüfen; vor Ausführung aktuellen Stand erneut validieren.
- Lade-, Leer- und Fehlerzustände verständlich anzeigen; „keine Treffer“ von „keine offenen Aufgaben“ unterscheiden.

Abfragen, Indizes, Dokumentzugriffe und Antwortzeiten sind mit realistischem Bestand zu messen. Ein mögliches Abnahmeziel ist unter zwei Sekunden für typische Such- und Listenaktionen auf dem vorgesehenen HR-System; dieses Ziel ist vor dem Test zu vereinbaren, nicht als bereits erreicht darzustellen. Lange Datei- oder Sammelarbeiten benötigen Fortschritt und sichere Wiederaufnahme.

## 5. Einheitliche Prozessanzeige und kurze Texte

Nicht jeden technischen Zustand zu einem neuen Fallstatus machen. Sichtbar sind drei zusammenhängende Angaben:
1. Fachlicher Stand, etwa „Rückblick eingegangen“.
2. Offener Grund, etwa „Unterschrift fehlt“.
3. Nächste Aktion, etwa „Nachforderung dokumentieren“.

Zusätzlich bleibt sichtbar, wer handeln muss. „Warten auf Führungskraft“ unterscheidet sich von einer offenen HR-Prüfung. Ein bereits eingegangenes Dokument darf wegen interner Prüfung nicht als fehlend angemahnt werden. Eine tatsächlich fehlende Unterschrift kann gezielt nachgefordert werden.

| Unklare Bezeichnung | Konkreter Vorschlag |
|---|---|
| E-Mail-Anhänge prüfen | 2 Ausblicke zuordnen |
| Prüfung erforderlich | Zeitraum des Rückblicks klären |
| Import abgeschlossen | Ziele übernommen · 4 Rückblicke können erstellt werden |
| Erledigt | Für Dossier bereitgestellt |
| Nachgefordert nach blossem Entwurf | Entwurf erstellt · Versand noch offen |

Standardtexte beschränken sich auf Status, Grund und Handlung. Hintergrundwissen liegt unter „Details“ oder Hilfe. Entscheidungsrelevante Warnungen und Folgen bleiben direkt sichtbar. Dokumentbegriffe werden einheitlich verwendet; insbesondere „Ausblick als Zielquelle“ und „neuer Ausblick“ sind unterscheidbar.

## 6. Unterschriften: gezielte Sichtprüfung

**Aktuelle Fachregel (27. Oktober 2026; ersetzt den generellen Verzicht auf HR-Unterschriftenkontrolle vom 26. Oktober):** Bei den durch „genügend“ oder „ungenügend“ ausgelösten Prüffällen öffnet HR den konkreten Scan und bestätigt, dass die erforderlichen Unterschriften vorhanden sind. Mögliche Zustände: „Prüfung offen“, „Unterschrift fehlt“, „Nachgefordert“ und „Unterschriften vorhanden“. Nur diese Fälle warten vor der Dossierbereitstellung auf die Bestätigung. Andere eindeutig zugeordnete und erfolgreich validierte Rückläufe werden weiterhin automatisch verarbeitet.

Die Prüfung ist an die konkrete Dokumentversion gebunden, mit Bearbeiter und Zeitpunkt. Eine neue Version ist erneut zu prüfen. „Unterschrift fehlt“ bezeichnet den Befund; „Nachgefordert“ dokumentiert eine tatsächlich erfolgte Anforderung mit Datum und Adressat, nicht bloss einen erzeugten Entwurf. Die Aufgabe wechselt dann zu „Warten auf Führungskraft“. Eine nachgereichte Datei öffnet die Prüfung erneut. Identische Dubletten erzeugen keine neue Prüfung. Eine unlesbare oder nicht eindeutig zugeordnete Gesamtbeurteilung wird als fachliche Ausnahme geklärt. Der fehlende Uneinigkeitsmarker erzeugt dagegen keine Prüfpflicht. Die Einholung der Unterschriften bleibt Aufgabe der Führungskräfte.

**Konkretisierte Fachregel (27. Oktober 2026):** Bei Gesamtbeurteilung des Rückblicks „genügend“ oder „ungenügend“ sind sowohl Rückblick als auch zugehöriger Ausblick auszudrucken, von Führungskraft und mitarbeitender Person zu unterzeichnen und einzuscannen. Je Gesprächsteil sind das digitale, maschinenlesbare PDF und der unterschriebene Scan zurückzusenden. HR prüft am jeweiligen Scan das Vorhandensein beider Unterschriften. Ein Scan ersetzt das maschinenlesbare PDF nicht; beide Dateien werden demselben Gesprächsteil zugeordnet und bleiben erhalten.

Die Beurteilung des Rückblicks löst die Pflicht für **beide** Teile aus. Der Ausblick braucht dafür keine eigene negative Beurteilung. Getrennte Eingänge sind möglich; die App zeigt je Teil getrennt „Digitales PDF fehlt“, „Unterschriebener Scan fehlt“, „Unterschriftenprüfung offen“, „Unterschrift fehlt“, „Nachgefordert“ bzw. „Unterschriften vorhanden“. Ein vorhandener Scan ist erst nach HR-Sichtprüfung bestätigt. Bei getrennten Verantwortlichkeiten bleibt je Teil die dafür zuständige Führungskraft massgeblich. Bereits eingegangene oder bereitgestellte Ausblicke werden bei später erkannter Pflicht im selben MD erneut auf den erforderlichen Nachweis geprüft; externe Ablagen werden nicht stillschweigend ersetzt.

Auch bei Uneinigkeit zwischen Führungskraft und mitarbeitender Person gilt fachlich dieselbe Druck-, Unterschriften- und Rücksendepflicht. Dafür fehlt im Formular ein eindeutiger Marker: HR prüft diesen Auslöser nicht systematisch, und die App erzeugt daraus keine automatische Prüf- oder Nachforderungsaufgabe. Fehlender Marker darf weder als bestätigte Einigkeit noch als Anlass für eine pauschale Klärungsaufgabe bei allen Fällen interpretiert werden.

**Zweck laut HR:** Dokumentation, dass Leistung beziehungsweise Verhalten besprochen und Erwartungen geklärt wurden, sowie angestrebte Verbindlichkeit und Absicherung für mögliche personalrechtliche Folgeschritte. Dies beschreibt die organisatorische Zielsetzung, keine geprüfte Aussage zur rechtlichen Beweiswirkung. Unterschriftenprüfung bestätigt das Vorhandensein der Unterschriften, nicht Einigkeit mit der Beurteilung.

**Technische Umsetzung:** Zuordnung der vorhandenen Beurteilungscodes zu „genügend“/„ungenügend“ anhand der Formulare prüfen. Maschinenlesbares PDF und Scan sind unterschiedliche Dokumentrollen, keine konkurrierenden Versionen oder Dubletten. Die Prüfung bindet den konkreten Scan an den zugehörigen digitalen Dokumentstand; eine inhaltlich neue Fassung darf die alte Unterschriftenbestätigung nicht erben.

Die Prüfung öffnet das PDF direkt im Fall. „Unterschriften vorhanden“ bestätigt nur deren Vorhandensein, keine Echtheitsprüfung. Die Aktion darf keine anderen fachlichen Warnungen aufheben. Eine Nachforderung kann vorbereitet und danach als tatsächlich erfolgt dokumentiert werden; Statusänderung allein versendet keine Nachricht.

Die Fachübernahme eines Rücklaufs, diese Prüfung und die technische Dossierübergabe bleiben getrennt. Ein Übergabefehler verlangt keine erneute Unterschriftenprüfung derselben unveränderten Version. Bereits extern bereitgestellte Fassungen werden bei späteren Korrekturen nicht stillschweigend ersetzt.

## 7. Nächster Arbeitsschritt und Abnahme

Vor der Umsetzung einen zusammenhängenden Entwurf der Arbeitsübersicht, Führungskräfteübersicht, Personenübersicht, Fallbearbeitung und Feedback-Sammlung erstellen. Die bereits ausgearbeiteten Nachreichungs- und SAP-Abläufe werden darin verortet.

Mit HR insbesondere diese Aufgaben durchspielen:
- Nachgereichte Ausblicke mehrerer Personen bearbeiten und zulässige Rückblicke gesammelt erstellen.
- Bei einer Führungskraft alle offenen Teile finden, einschliesslich alter Jahre und Vertretungen.
- Bei einer Mitarbeiterin aktuellen MD, früheren Rückblick und unterjährigen Anlass unterscheiden.
- Übertritt mit alter Rückblick- und neuer Ausblick-Verantwortung nachvollziehen.
- Neue Person während des laufenden Jahres aufnehmen und Probezeit/MD-Bedarf bearbeiten.
- Prüfpflichtiges PDF öffnen, fehlende Unterschrift dokumentieren, tatsächliche Nachforderung und neue Fassung bearbeiten.
- Feedback-Sammlung und Nachtrag bearbeiten, ohne künstliche Einzelpflichten zu erzeugen.
- Nach Unterbrechung vom Arbeitsvorrat direkt an der richtigen Stelle fortsetzen.

Abnahmefragen: Findet HR ohne Erklärung den richtigen Fall, erkennt den Stand und die zuständige Person, führt die nächste Aktion aus und sieht deren Ergebnis? Bleibt das bei einem grossen mehrjährigen Bestand verständlich? Erst danach die erste Umsetzungsetappe beginnen. Spätere Praxistests ergänzen diesen Entwurfstest; die frühe Gesamtgestaltung ersetzt keine Erprobung der implementierten App.
