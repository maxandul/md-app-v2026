# MD-App: Aufgaben, Navigation und Bedienung

Stand: 10. November 2026. Status: Konzeptentwurf zur fachlichen und gestalterischen Prüfung, keine neue Oberfläche implementiert.

Codeabgleich: `main` auf `ca48857160921a25a9669c56a19cf715a1be8d26` und die bisher erarbeiteten Änderungen in [PR #14](https://github.com/maxandul/md-app-v2026/pull/14), Stand `3a682c2bb4fed50b1c425fe5c8eac184d65648a3`. PR #14 war beim Abgleich offen. Seine Verbesserungen sind keine Voraussetzung, um dieses Konzept zu beurteilen.

Dieser Entwurf entwickelt die Nutzerführung aus den Arbeitsaufträgen von HR. Er ersetzt für den neuen UI-Entwurf die bisherige Gliederung nach technischen Arbeitsbereichen. Bestehende Fachregeln, Prüfungen und Historien werden dadurch nicht aufgehoben. Insbesondere die [bestätigten Fachregeln](UEBERGABE_UMSETZUNG_HR_NUTZERFUEHRUNG.md) bleiben Grundlage. Neue Vorschläge sind nachfolgend als Soll beschrieben; sie sind kein Nachweis vorhandener Funktionen.

## 1. Ziel und Leitentscheidungen

HR soll mit einem konkreten Anliegen einsteigen können: «Ich habe alte Ausblicke erhalten», «Petra braucht die Unterlagen nochmals» oder «Ich möchte offene Gespräche mahnen». Die App stellt den Zusammenhang zwischen den nötigen Schritten her. HR muss keine internen Datentypen oder Menüwege lernen.

1. Neue Aufgabe beginnen und bestehende Arbeit fortsetzen sind zwei gleichwertige Einstiege.
2. Gespräche lassen sich aus Mitarbeitenden- oder Führungskräftesicht finden. Beide Perspektiven beziehen sich auf dieselben Gesprächsteile.
3. Name, OE und direkte Führungskraft identifizieren eine Anstellung im Arbeitsalltag. Nummern ergänzen die fachlich eindeutige Zuordnung.
4. Stammdatenänderung, Änderung eines Gesprächsauftrags, Dateierstellung und Versand sind getrennte Wirkungen innerhalb eines zusammenhängenden Arbeitsauftrags.
5. Zulässige Teile eines Auftrags bleiben bearbeitbar, während andere Teile geklärt werden. Technisch notwendige Transaktionsgrenzen werden ausdrücklich angezeigt.
6. Bestätigungen benennen eine konkrete Entscheidung oder Wirkung. Routinemässiges Weiterklicken verlangt keine zusätzliche Freigabe.
7. Corporate Design gibt den gestalterischen Rahmen vor. Innerhalb dieses Rahmens werden Informationshierarchie, Arbeitsflächen und Interaktionsmuster verbessert.

## 2. Personen verständlich und eindeutig anzeigen

Alle Beispiele in diesem Dokument sind erfunden.

| Situation | Primäre Anzeige | Ergänzende Angaben |
|---|---|---|
| Person auswählen | Anna Muster | OE, direkte Führungskraft; Funktion bei Bedarf |
| Zwischen Anstellungen wählen | Anna Muster · Amt für Wirtschaft · direkte Führungskraft: Petra Beispiel | Funktion; Beschäftigungsgrad oder Zeitraum, soweit vorhanden und zur Unterscheidung hilfreich |
| Konkreten Rückblick öffnen | Anna Muster · Rückblick 2026 | OE, Zeitraum, verantwortliche Führungskraft |
| Aktuelle Führung und Gesprächsverantwortung unterscheiden sich | Direkte Führungskraft: Petra Beispiel; verantwortlich für diesen Rückblick: Martin Muster | Anlass und bestätigter Zeitraum der Abweichung |
| Technische Rückfrage oder Exportprüfung | Personenbezug wie oben | Personalnummer und Anstellungsnummer unter «Zuordnungsdetails» |
| Name fehlt im Bestand | Name nicht verfügbar · OE und Führungskraft, soweit bekannt | Nummer zur eindeutigen Klärung sichtbar; fehlenden Namen nicht durch eine erfundene Zuordnung ersetzen |

**Verbindliche Anzeigereihenfolge:** Name → OE und direkte Führungskraft → benötigter Gesprächskontext → technische Zuordnungsdetails. In einer Führungskräftegruppe muss derselbe Führungsname nicht in jeder Zeile wiederholt werden.

Die aktuelle direkte Führungskraft stammt aus dem aktuell übernommenen Stammdatenstand. Die Verantwortung für Rückblick und Ausblick stammt aus der konkreten Gesprächszuordnung. Historisch unbekannte Führungszuordnungen bleiben als unbekannt bezeichnet. Aus dem Importdatum wird kein Wechseltermin abgeleitet.

Wenn Name, OE und Führungskraft mehrere Anstellungen nicht unterscheiden, ergänzt die App vorhandene Funktion, Pensum oder Zeitraum. Bleibt die Auswahl mehrdeutig, wird die Anstellungsnummer als letzte notwendige Unterscheidung eingeblendet. HR muss sie nicht kennen oder eintippen. Namen sind keine Datenbankschlüssel; die Auswahl bleibt intern an die eindeutige Anstellung gebunden.

Suche nach Vorname, Nachname oder Namenskombination; Nummernsuche bleibt zusätzlich möglich. Mitarbeitende und Führungskräfte haben eigene Suchfelder mit klarer Rollenbezeichnung. Namensänderungen, gleiche Namen und Mehrfachanstellungen führen nicht zu einer automatischen Zusammenlegung.

## 3. Aufgabenlandkarte

Die Tabelle beschreibt Arbeitsaufträge, keine Liste von sechzehn Hauptmenüpunkten. Einträge können im Aufgabenstart sowie kontextbezogen bei einer Person, Führungskraft oder einem Durchlauf angeboten werden.

| ID | Arbeitsauftrag | Einstieg aus dem Arbeitskontext | Fertig, wenn … |
|---|---|---|---|
| U01 | Ordentlichen Durchlauf starten | Start → Jahresdurchlauf | vorgesehene Gespräche geprüft und Unterlagen zugestellt oder konkrete Ausnahmen offen sind |
| U02 | Rückläufe verarbeiten | Start oder Eingänge | Dokumente übernommen, fachfremde Eingänge ausgeschlossen und Rückfragen konkret ausgewiesen sind |
| U03 | Unterlagen nochmals zustellen | Person/Führungskraft → vorhandener Versand | dieselbe geeignete Fassung nochmals zugestellt wurde |
| U04 | Gesprächsauftrag ändern oder ersetzen | ausgewähltes Gespräch | Zuständigkeit, Zeitraum und benötigte Teile geregelt, nötige Unterlagen zugestellt und bisherige Aufträge geklärt sind |
| U05 | Fristen anpassen | Gesprächsauswahl, Führungskraft oder Durchlauf | die ausgewählten Fristen geändert und ihre Auswirkungen sichtbar sind |
| U06 | Vorjahresziele nachtragen | Start, Eingang oder Gespräch | Ziele geprüft und nötige Rückblicke erstellt/zugestellt bzw. bestehende Rückläufe zur Korrektur bearbeitet sind |
| U07 | Stand der Gespräche überblicken | Gespräche | offene und erledigte Teile nach Mitarbeitenden oder Führungskraft nachvollziehbar sind |
| U08 | An ausstehende Gespräche erinnern | gefilterte Gesprächsauswahl | passende Erinnerungen zugestellt oder als konkrete Entwürfe offen sind |
| U09 | Stammdaten im Durchlauf aktualisieren | Start → Jahresdurchlauf | Stammdaten und Folgen für betroffene Gespräche getrennt bearbeitet sind |
| U10 | Unterjähriges Gespräch veranlassen | Start → Unterjährige Gespräche | erforderliche Gespräche zu Eintritt/Wechsel/Probezeit usw. geregelt und Unterlagen zugestellt sind |
| U11 | Rücklauf korrigieren oder vervollständigen | Eingang oder Gespräch | gültige Daten, erforderliche Nachweise und Auswirkungen früherer Fassungen geklärt sind |
| U12 | Daten für SAP exportieren | Start oder Daten & Auswertung | der geeignete Bestand als nachvollziehbarer Export bereitliegt |
| U13 | Feedbacks zusammenstellen | Eingang oder Führungskraft | geprüfte Feedbacks gebündelt bzw. als Nachtrag bereitgestellt sind |
| U14 | Dossierbereitstellung klären | offener Bereitstellungsauftrag | erforderliche Kopien lokal bereitliegen bzw. ein externer Korrekturbedarf dokumentiert ist |
| U15 | Jahresdurchlauf abschliessen | ausgewählter Durchlauf | Restarbeiten geregelt und der Abschluss dokumentiert ist |
| U16 | Ergebnisse auswerten | Daten & Auswertung | ausgewählte Kennzahlen mit verständlicher Bezugsmenge vorliegen |

### U01 – Ordentlichen Durchlauf starten

**Story:** Als HR-Verantwortliche möchte ich den Jahresdurchlauf mit aktuellen Grundlagen eröffnen und die benötigten Unterlagen an die zuständigen Führungskräfte zustellen.

**Ablauf:** Rückblick- und Ausblickjahr festlegen; letzten Stammdatenstand anzeigen und bei Bedarf aktualisieren; vorgeschlagene Gesprächsaufträge mit Anlass, Teilen, Zeitraum und Verantwortung prüfen; Fristen setzen; geeignete Vorlagen erstellen; Dateien und Empfänger prüfen; Versand vorbereiten und tatsächlichen Versand festhalten.

**Entscheidungen und Ausnahmen:** Ein bereits bestehender Durchlauf wird zuerst zur Fortsetzung angeboten. Konflikte, fehlende Führungskräfte oder Vorlagen erscheinen bei den betroffenen Einträgen. Dieselbe Aktion darf keinen zweiten identischen Durchlauf oder doppelten Versand erzeugen. Rückblick und Ausblick können unterschiedlich zugeordnet sein.

**Wirkung und Wiederaufnahme:** Jede Teilwirkung wird getrennt angezeigt. «Durchlauf eröffnet» bedeutet noch nicht «Unterlagen versendet». Wiederaufnahme führt beispielsweise zu «12 Versandentwürfe offen», nicht zurück zur Stammdateneingabe.

### U02 – Rückläufe verarbeiten

**Story:** Als HR-Verantwortliche möchte ich eingetroffene Nachrichten und Dateien verarbeiten, ohne fachfremde Anhänge als MD erfassen zu müssen.

**Ablauf:** Postfachscan bei Bedarf aktivieren oder manuell scannen; Mail/Upload öffnen; Dokumentart und Bezug prüfen; eindeutige zulässige Dokumente übernehmen; unsichere Inhalte gezielt klären; erforderliche Nachweise bzw. Bereitstellung weiterbearbeiten. Fachfremde Dateien erhalten «Kein MD-Dokument – ausschliessen» ohne MD-Pflichtfelder.

**Entscheidungen und Ausnahmen:** Mehrere Anhänge einer Mail dürfen verschiedene Bearbeitungsstände haben. Ein unzugeordneter Eingang wird als ungeklärt bezeichnet, nicht als belegter Rückblick einer bestimmten Person. Ausschluss bleibt rücknehmbar. Bereits übernommene Dokumente benötigen den Korrekturweg U11.

**Wirkung und Wiederaufnahme:** Original und Herkunft bleiben nachvollziehbar. Nur reine, vollständig verarbeitete MD-Mails ohne weitere offene Anliegen dürfen automatisch verschoben werden. Fremdanlagen oder zusätzliche Anliegen verhindern dies. «Mailprüfung erledigt» verschiebt keine Mail, auch nicht beim nächsten Scan. Offene Folgearbeit bleibt bestehen.

### U03 – Unterlagen nochmals zustellen

**Story:** Als HR-Verantwortliche möchte ich einer Führungskraft bereits gültige Unterlagen nochmals zustellen.

**Ablauf:** Person oder Führungskraft suchen; Gespräch und vorhandene Ausgabe wählen; Aktualität der Ausgabe sowie Empfänger prüfen; dieselbe Fassung zur erneuten Zustellung vorbereiten; tatsächlichen Versand dokumentieren.

**Entscheidungen und Ausnahmen:** Haben sich Ziele, Zuständigkeit oder Inhalte geändert, bietet die App U04 oder U06 an. Ein offener Outlook-Vorgang wird fortgesetzt oder geklärt. Bereits bearbeitete Word-Dateien werden nicht still ersetzt.

**Wirkung und Wiederaufnahme:** Neuer Zustellnachweis, kein neues Gespräch und keine zusätzliche Pflicht. Die bisherige Versandhistorie bleibt bestehen. Vorschlag für die neue UI; ein gemeinsamer unveränderter Wiederzustellungsweg ist im Code noch gesondert zu prüfen.

### U04 – Gesprächsauftrag ändern oder ersetzen

**Story:** Als HR-Verantwortliche möchte ich die richtige Person mit der richtigen Führungskraft für Rückblick und/oder Ausblick verknüpfen und nötige Unterlagen zustellen.

**Ablauf:** Bestehendes Gespräch öffnen; betroffene Teile wählen; verantwortliche Führungskraft namentlich auswählen; Zeitraum und Formular-OE bestimmen; Auswirkungen auf bisherigen Auftrag, erstellte Dateien, offene Entwürfe und Rückläufe prüfen; Änderungen anwenden; erforderliche neue Unterlagen erstellen und zustellen.

**Entscheidungen und Ausnahmen:** Die App unterscheidet «Zuständigkeit ändern», «zusätzliches Gespräch veranlassen» und «bisherigen Auftrag als erübrigt markieren». Ein Wechsel begründet nicht automatisch den Wegfall des alten Rückblicks. Bereits eingegangene oder bereitgestellte Dokumente werden nicht gelöscht oder pauschal erledigt. Bei Übertritt kann die alte Führungskraft den Rückblick und die neue den Ausblick übernehmen. Zeitraum und OE sind je Teil festzulegen.

**Wirkung und Wiederaufnahme:** Vorschau zeigt Alt → Neu mit Namen und Teilzeiträumen. Erübrigung ist eine begründete fachliche Entscheidung am bisherigen Auftrag. Die appweite Ersetzung einschliesslich bereits versendeter Unterlagen ist vor Umsetzung als eigener Übergang zu spezifizieren; ein allgemeines «erledigt» reicht nicht.

### U05 – Fristen anpassen

**Story:** Als HR-Verantwortliche möchte ich die Rückblick- oder Ausblickfrist für bestimmte Gespräche ändern.

**Ablauf:** Auswahl aus Gesprächen, Führungskraft oder Durchlauf übernehmen; Teil und neue Frist angeben; betroffene offene Teile und bisherige Fristen prüfen; Änderung speichern.

**Entscheidungen und Ausnahmen:** Abgeschlossene/erübrigte Teile sind nicht automatisch enthalten. Unterschiedliche bisherige Fristen werden gezeigt. Eine Information an die Führungskraft ist als eigene optionale Zustellung kenntlich; Speichern allein sendet nichts.

**Wirkung und Wiederaufnahme:** Neue Frist wirkt auf dieselben Gesprächspflichten und die Erinnerungsauswahl. Bereits vorhandene Entwürfe werden auf veraltete Fristangaben geprüft, bevor sie wiederverwendet werden. Beliebige Teilauswahl und Entwurfsfolgen sind noch auf vorhandene technische Unterstützung abzugleichen.

### U06 – Vorjahresziele nachtragen

**Story:** Als HR-Verantwortliche möchte ich aus erhaltenen alten Ausblicken Ziele übernehmen und erforderliche Rückblicke gemeinsam zustellen.

**Ablauf:** Eingang verwenden oder Dateien einlesen; Person/Anstellung und Zieljahr prüfen; erkannte Ziele am Original prüfen bzw. korrigieren; massgebende Zielversion bestätigen; passende Rückblicke bestimmen; zulässige neue Vorlagen gemeinsam erstellen; Dateien prüfen; nach tatsächlicher Rückblickverantwortung bündeln und zustellen.

**Entscheidungen und Ausnahmen:** Zieljahr ist das Jahr der vereinbarten Ziele, nicht automatisch das Folgejahr. Mehrere Quellen werden verglichen, nicht vermischt. Kein passendes Gespräch führt zur Gesprächszuordnung oder begründetem Verzicht. Ein vorhandener Rücklauf führt zu U11. Ein lediglich ungeprüfter Eingang führt zu U02, ohne allgemeine Rückblickentscheidung. Bereits begonnene Word-Bearbeitung benötigt einen Inhaltsabgleich vor Ersatz.

**Wirkung und Wiederaufnahme:** Auslesen, fachliche Bestätigung, Erstellen und Versenden sind unterscheidbar. Ein Stapel bleibt zusammen auffindbar; offene Quellen halten andere zulässige Einträge nicht auf. Versand erfolgt als gemeinsames ZIP je tatsächlich zuständiger Führungskraft; frühere Ausgaben bleiben erhalten.

### U07 – Stand der Gespräche überblicken

**Story:** Als HR-Verantwortliche möchte ich erkennen, welche Rückblicke und Ausblicke fehlen und wo HR selbst handeln muss.

**Ablauf:** Zeitraum/Durchlauf wählen oder alle offenen Jahre betrachten; nach Mitarbeitenden oder verantwortlicher Führungskraft gruppieren; nach Frist, OE, Anlass, Teil und Stand filtern; Person oder Gespräch öffnen und zur erhaltenen Auswahl zurückkehren.

**Entscheidungen und Ausnahmen:** «Rücklauf fehlt», «Eingang ungeprüft», «Nachweis fehlt», «HR-Prüfung offen» und «Bereitstellung offen» sind unterschiedliche Gründe. Ein abgeschlossener Rückblick bedeutet nicht automatisch einen abgeschlossenen Ausblick. Offene Altjahre bleiben auffindbar und werden nicht unbemerkt ausgeblendet.

**Wirkung und Wiederaufnahme:** Reine Übersicht ändert keine Daten. Zählungen unterscheiden Personen, Gespräche, Gesprächsteile und Aufgaben. Die Perspektive nach aktueller direkter Führungskraft ist ausdrücklich von derjenigen nach tatsächlicher Gesprächsverantwortung zu unterscheiden.

### U08 – An ausstehende Gespräche erinnern

**Story:** Als HR-Verantwortliche möchte ich zuständige Führungskräfte gezielt an fehlende Gesprächsteile erinnern.

**Ablauf:** U07-Auswahl übernehmen; zulässige Erinnerungskandidaten prüfen; pro Führungskraft die betreffenden Namen, Teile und Fristen sehen; Nachricht prüfen; Entwürfe erstellen und tatsächlichen Versand dokumentieren.

**Entscheidungen und Ausnahmen:** Ein ungeprüfter Eingang wird zuerst geklärt. Fehlende Unterschriften benötigen eine konkrete Nachforderung, keine allgemeine Erinnerung an ein vermeintlich fehlendes Gespräch. Ein offener Entwurf wird wiedergefunden. Feedbacks erhalten keine automatische Vollständigkeitsmahnung.

**Wirkung und Wiederaufnahme:** Erinnerung ändert nicht den Erledigungsstand des Gesprächs. Die App nennt ausgeschlossene Teile und Gründe. Neue Stammdaten oder Fristen werden vor Versand erneut geprüft.

### U09 – Stammdaten im laufenden Durchlauf aktualisieren

**Story:** Als HR-Verantwortliche möchte ich einen neuen SAP-Stand übernehmen und seine Auswirkungen auf laufende Gespräche gezielt bearbeiten.

**Ablauf:** Durchlaufkontext setzen; Export einlesen und Unterschiede ansehen; zulässige Personen auswählen; Stammdaten übernehmen; betroffene Gespräche mit Alt-/Neuverantwortung, Zeitraum, Vorlagen und Rückläufen prüfen; beibehalten, ändern oder ergänzen; bei Bedarf Unterlagen erneuern und zustellen.

**Entscheidungen und Ausnahmen:** Übernahmeeinheit der vorhandenen SAP-Verarbeitung ist eine Person mit den im Export enthaltenen Anstellungen. Die UI verspricht keine getrennte Feldübernahme, die der Dienst nicht unterstützt. Fehlender Datensatz beweist keinen Austritt. Manuell geregelte Gesprächszuständigkeiten bleiben bestehen. Der Importzeitpunkt beweist keinen Führungswechseltermin.

**Wirkung und Wiederaufnahme:** Stammdatenübernahme schliesst offene Gesprächsfolgen nicht ab. Änderungen führen direkt zu passenden Folgeaufgaben. Teilauswahl wird nicht als vollständiger SAP-Gesamtabgleich bezeichnet.

### U10 – Unterjähriges Gespräch veranlassen

**Story:** Als HR-Verantwortliche möchte ich ausserhalb der Jahresvorbereitung die benötigten Gespräche für Eintritt, Probezeitende, Wechsel oder Austritt auslösen.

**Ablauf:** Stammdaten bei Bedarf wie in U09 abgleichen; Person und richtige Anstellung namentlich auswählen; vorhandene Gespräche prüfen; Anlass und bestätigtes Ereignisdatum festlegen; erforderliche Teile, Verantwortung, Zeitraum und Formular-OE prüfen; nötige Vorlagen erstellen und zustellen.

**Entscheidungen und Ausnahmen:** Bestehendes Jahresgespräch fortführen, ändern oder einen zusätzlichen Auftrag anlegen sind verschiedene Optionen. Die App wendet bestätigte Probezeit-/Austrittsregeln an und zeigt deren Begründung. Fehlende Daten werden nicht geraten. Unterjährige Arbeit bleibt auch nach Abschluss einer Kampagne erreichbar.

**Wirkung und Wiederaufnahme:** Ein neuer Auftrag ist vom alten unterscheidbar; zurückgesandte Dokumente bleiben ihrem Gespräch zugeordnet. Technische Bindungen an einen Durchlauf dürfen keinen unverständlichen Zwang zum Wiederöffnen des Jahres erzeugen; vorhandene Entkopplung im Code prüfen.

### U11 – Rücklauf korrigieren oder vervollständigen

**Story:** Als HR-Verantwortliche möchte ich Daten, Scans oder Ersatzfassungen eines konkreten Rücklaufs zuverlässig bearbeiten.

**Ablauf:** Dokument/Person öffnen; Datenquelle und vorhandene Nachweise vergleichen; fehlende Angaben konkret ergänzen oder nachfordern; gegebenenfalls Ersatzfassung zuordnen; Unterschriften am betreffenden Scan prüfen; Bereitstellung fortsetzen.

**Entscheidungen und Ausnahmen:** Bei Rückblickbeurteilung genügend/ungenügend gelten die bestätigten Nachweispflichten für Rückblick und Ausblick. Ein ausreichend auslesbarer, vollständig geprüfter Scan kann zugleich Datenquelle und Unterschriftennachweis sein. Fehlendes digitales PDF allein ist keine automatische Blockade. Uneinigkeit hat ohne eindeutigen Formularmarker keine pauschale automatische Prüfaufgabe zur Folge.

**Wirkung und Wiederaufnahme:** Version, Sichtprüfung und Nachforderung bleiben nachvollziehbar. Daten kommen nur einmal in den Fachbestand. Bei bereits extern bereitgestellter Fassung wird eine Korrekturwirkung sichtbar; lokales Ersetzen bestätigt keine externe Berichtigung.

### U12 – Daten für SAP exportieren

**Story:** Als HR-Verantwortliche möchte ich bereits geeignete Rückblicke auch während des laufenden Jahresdurchlaufs exportieren.

**Ablauf:** Durchlauf/Zeitraum wählen; geeignete, bereits exportierte und noch nicht geeignete Rückblicke getrennt sehen; führendes Ereignis bei mehreren Rückblicken prüfen; Exportzusammenstellung prüfen; Datei erzeugen und herunterladen.

**Entscheidungen und Ausnahmen:** Auswahl und Wiederholung dürfen keine unbemerkten Doppelübernahmen verursachen. Eine fachlich korrigierte frühere Exportfassung braucht einen erkennbaren Korrekturweg. Der Abschluss des gesamten Durchlaufs ist keine Voraussetzung für einen geeigneten Teilbestand.

**Wirkung und Wiederaufnahme:** «Exportdatei erstellt» ist keine Bestätigung des tatsächlichen Imports in SAP. UI-Listen zeigen Namen; technische Nummern bleiben im vorgegebenen Exportformat enthalten. Ein Nachweis einer tatsächlichen SAP-Übernahme darf nur bei vorhandener Funktion und belastbarer Rückmeldung angeboten werden.

### U13 – Feedbacks zusammenstellen

**Story:** Als HR-Verantwortliche möchte ich geprüfte Feedbacks je Führungskraft und Jahr zusammenstellen und Nachträge bearbeiten.

**Ablauf:** Führungskraft/Jahr wählen; geprüfte Eingänge und vorhandene Bündel ansehen; gewählte Feedbacks bündeln; für vorgesehenen Ablageweg bereitstellen; späteren Eingang als Nachtrag behandeln.

**Entscheidungen und Ausnahmen:** Keine automatische Vollständigkeitsmahnung. Temporäre Gesprächsvertretung verändert die Feedback-Zuordnung nicht automatisch. Unbekannte personenbezogene Zuordnung wird nicht erfunden.

**Wirkung und Wiederaufnahme:** Bündel, enthaltene Dateien und Nachträge sind nachvollziehbar. Bereitstellung bleibt von einer bestätigten nachgelagerten Ablage unterscheidbar.

### U14 – Dossierbereitstellung klären

**Story:** Als HR-Verantwortliche möchte ich offene technische Bereitstellungen oder externe Korrekturen erledigen.

**Ablauf:** Betroffene Person und konkrete Dokumentfassung öffnen; fehlende fachliche Voraussetzung von technischem Dateifehler unterscheiden; Voraussetzung klären oder unveränderte technische Bereitstellung erneut versuchen; Ergebnis dokumentieren.

**Entscheidungen und Ausnahmen:** Eine unveränderte Datei benötigt beim blossen technischen Wiederholungsversuch keine neue Sichtprüfung. Inhaltsänderung verlangt Prüfung der neuen Version. Die App bestätigt keine externe Verarbeitung, die sie nicht beobachtet hat.

**Wirkung und Wiederaufnahme:** Dossierbereitstellung und SAP-Export sind getrennte Wege. Ein externer Korrekturfall bleibt mit Zuständigkeit und benötigtem Nachweis offen, bis der tatsächliche Abschlussweg fachlich geklärt ist.

### U15 – Jahresdurchlauf abschliessen

**Story:** Als HR-Verantwortliche möchte ich den Jahresdurchlauf nach Prüfung der verbleibenden Arbeit nachvollziehbar schliessen.

**Ablauf:** Restarbeiten nach fehlenden Gesprächen, HR-Prüfung, Versand, Bereitstellung und Export ansehen; nötige Arbeit erledigen oder fachlich zulässig begründen; Abschluss mit Zeitpunkt und Verantwortung dokumentieren.

**Entscheidungen und Ausnahmen:** Keine pauschale Erledigung aller offenen Aufgaben. Unterjährige Gespräche und offene Altjahresfälle bleiben erreichbar. Fachliche Korrektur und technische Wiederaufnahme bleiben unterscheidbar.

**Wirkung und Wiederaufnahme:** Kampagnenabschluss organisiert den Jahresprozess; er löscht keine Historie und bestätigt weder Mailversand noch externe Verarbeitung.

### U16 – Ergebnisse auswerten

**Story:** Als HR-Verantwortliche möchte ich Arbeitsstände und verfügbare fachliche Kennzahlen für einen definierten Bestand auswerten.

**Ablauf:** Fragestellung, Zeitraum und OE wählen; Datenstand/Bezugsmenge sehen; verfügbare Kennzahlen anzeigen und bei Bedarf exportieren.

**Entscheidungen und Ausnahmen:** Operative Rücklaufzahlen werden nicht mit fachlichen Ergebnissen vermischt. Mehrere Anstellungen und Gespräche werden nach klar benannter Einheit gezählt. Gewünschte, aber nicht vorhandene historische Daten werden als Lücke ausgewiesen.

**Wirkung und Wiederaufnahme:** Reine Auswertung verändert keine Gesprächsaufträge. Statistik ist ein ergänzender Einstieg, keine Voraussetzung für tägliche Fallarbeit.

## 4. Vorgeschlagene Navigation

### Hauptnavigation und ihre Rollen

| Einstieg | Zweck | Inhalt |
|---|---|---|
| Start | Neue Arbeit beginnen und laufende Arbeit fortsetzen | Aufgabenstart nach Anliegen; konkrete offene Aufgaben; zuletzt bearbeitete Vorgänge |
| Gespräche | Personen, Führungskräfte und Gesprächsstände finden | Umschalter «Nach Mitarbeitenden» / «Nach verantwortlicher Führungskraft»; Suche, Filter, Listen- und Detailansichten |
| Eingänge | Dokumente und Nachrichten verarbeiten | Mail/Upload, Scansteuerung, Originalvergleich, Zuordnung und Ausschluss |
| Versand | Unterlagen und Erinnerungen zustellen bzw. fortsetzen | Erstellte Ausgaben, Empfängergruppen, offene Entwürfe, Versandhistorie |
| Daten & Auswertung | Datenstand pflegen und Ergebnisse ausgeben | Stammdatenabgleich, SAP-Export, Kennzahlen; getrennte Unteransichten |

Hilfe und Administration bleiben als Hilfsnavigation erreichbar. Administration ist rollenabhängig. Keine zweite ständig sichtbare Menüzeile mit allen internen Arbeitsbereichen. Innerhalb eines Bereichs sind wenige kontextbezogene Reiter möglich. «Stammdaten aktualisieren» bleibt zusätzlich als direkter Arbeitsauftrag von Start und Durchlauf aus erreichbar.

Feedback und Dossierbereitstellung sind weiterhin fachlich auffindbar: bei der betroffenen Führungskraft/Person, als offene Aufgabe auf Start und über die passenden Unteransichten. Sie benötigen keinen eigenen dauerhaften Hauptmenüpunkt.

### Startseite als Arbeitsfläche

Die Startseite kombiniert drei klar getrennte Zonen:

| Zone | Inhalt | Interaktion |
|---|---|---|
| Neue Aufgabe beginnen | Drei kompakte Aufgabengruppen: Jahresdurchlauf, laufende Betreuung, unterjährige Gespräche | Konkrete Textaktionen statt sechzehn gleichgewichteter Kacheln; häufige Aufgaben direkt, weitere gesammelt erreichbar |
| Offene Arbeit | Was HR jetzt tun kann; separat Warten auf Rückmeldung; Quelle und betroffene Namen | Direkter Einstieg zur nächsten tatsächlichen Handlung; Filtern und Fortsetzen |
| Arbeitskontext | Aktuelle Durchläufe und zuletzt bearbeitete Vorgänge | Gewählten Kontext übernehmen, ohne andere offene Jahre unbemerkt zu verbergen |

Beispiele für direkte Aktionen: «Jahresdurchlauf starten», «Stammdaten aktualisieren», «Alte Ausblicke übernehmen», «Rückläufe verarbeiten», «Gespräch veranlassen», «Offene Gespräche und Erinnerungen».

Ein Durchlauf ist Kontext, keine globale Zugangssperre. Die Aufgabenliste zeigt offene Altjahre standardmässig mit Jahr. Ein ausdrücklich gesetzter Filter zeigt seinen Umfang und die Möglichkeit «Alle offenen Jahre». Unterjährige Aufträge sind auch ohne aktive Jahresvorbereitung erreichbar.

### Kontext innerhalb einer Aufgabe

Jede Arbeitsansicht besitzt eine klare Hierarchie: Pfad und Rückweg; Aufgabentitel; kompakte Kontextzeile mit Jahr/Durchlauf, Umfang und betroffenen Personen; bei Bedarf Schrittnavigation; aktuelle Arbeitsfläche und nächste Hauptaktion. Die vollständige Prozessbeschreibung ist optional aufrufbar und steht nicht dauerhaft über der Bearbeitung.

Ein Auftrag kann mehrere Bearbeitungsstände enthalten. «18 bereit, 2 offen» ist aussagekräftiger als ein einziger globaler Fortschrittsbalken. Schritte werden aus tatsächlichen Teilständen abgeleitet. Verlauf und technische Details stehen nachrangig.

## 5. Einheitliche Bedienmuster

### Formulare und Entscheidungen

- Eine fachlich zusammenhängende Eingabe pro Abschnitt. Gängige Fälle zuerst, seltene Varianten nach Auswahl einblenden. Kritische Pflichtangaben und Blockaden bleiben sichtbar.
- Vorhandene Angaben vorbelegen und ihre Quelle kenntlich machen. Direkte Führungskraft wird nicht still zur Gesprächsverantwortung umgedeutet.
- Namen und Anstellungen über Suche auswählen; ausgewählte Person bleibt mit OE und Führungskraft sichtbar. Keine reguläre Eingabe von Personal- oder Anstellungsnummern.
- Feldfehler direkt am Feld mit konkreter Korrektur; bei mehreren Fehlern zusätzlich verlinkte Zusammenfassung. Gültige Eingaben bleiben erhalten. Datum und Pflichtumfang werden im gewählten Gesprächskontext erklärt.
- «Entwurf speichern», «Änderungen übernehmen», «Dateien erstellen» und «Outlook-Entwurf erstellen» haben unterschiedliche Beschriftungen. «Bestätigen» allein ist zu ungenau.
- Eine kurze Friständerung kann als kompakter Dialog erscheinen. Originalvergleich oder komplexe Zuordnungsänderung erhält eine eigene Arbeitsansicht statt eines kleinen Modals.
- Ein Klick auf «Kein MD-Dokument – ausschliessen» verlangt keine MD-Daten oder zusätzliche Standardbestätigung. Rücknahme ist direkt möglich. Fachliche Prüfung vor Verwendung einer Zielquelle bleibt ausdrücklich erforderlich.

### Tabellen, Filter und Auswahl

- Namen bilden den festen visuellen Einstieg. Bei Gesprächsteilen stehen Art, Jahr/Zeitraum und tatsächliche Verantwortung in der Nähe. Nummern stehen in Details oder optionalen Spalten.
- Kompakte Zeilen mit ausreichend lesbarer Schrift; keine grossen Karten je Person bei Hunderten Einträgen. Breite Tabellen nutzen eine geeignete Arbeitsbreite. Unvermeidbare Tabellenüberbreite wird innerhalb der Tabelle behandelt.
- Serverseitige Suche, Filter, Sortierung und Seiteneinteilung. Kein scheinbar vollständiger Bestand aus nur den ersten 100 Treffern.
- Filterleiste bleibt an einer stabilen Position. Aktive Filter als lesbare Auswahl mit «Zurücksetzen». Frist und Überfälligkeit sind getrennt vom fachlichen Bearbeitungsstand filterbar.
- Checkbox in der Kopfzeile bedeutet zunächst «Diese Seite auswählen». Erst eine weitere ausdrückliche Aktion wählt alle gefilterten Treffer. Beispiel: «25 dieser Seite ausgewählt. Alle 146 gefilterten Gesprächsteile auswählen».
- Auswahlumfang, gewählte Einheit und mögliche Aktionen stehen in einer gemeinsamen Aktionsleiste. Filterwechsel leert die Auswahl mit sichtbarem Hinweis; die App führt nie eine Aktion auf einer unsichtbar weiterbestehenden Auswahl aus.
- Nicht zulässige Einträge werden mit Grund ausgewiesen. Einträge werden weder still übersprungen noch durch pauschales «Fehler» zugeordnet. Vor einer Sammelaktion zeigt die App geeignete und ausgeschlossene Teile.
- Rückkehr aus einer Detailansicht stellt Filter, Sortierung, Seite und Scrollposition wieder her. Auswahl eines laufenden Arbeitsauftrags wird anhand stabiler IDs wiederhergestellt und vor Ausführung neu validiert.
- Beim Neuladen mit geändertem Bestand wird die Änderung angezeigt; ein veralteter Auswahlstand löst keine stillen Wirkungen aus. Wiederholungen finden bereits erzeugte Dateien oder offene Versandvorgänge wieder.

### Mengen und Status

| Begriff | Bedeutung im UI |
|---|---|
| Person | Natürliche Person; kann mehrere Anstellungen besitzen |
| Gespräch / Gesprächsanlass | Beispielsweise Jahresgespräch oder Probezeit; intern mit stabilem Ereignis verknüpft |
| Gesprächsteil | Rückblick oder Ausblick mit eigener Verantwortung, Frist und Bearbeitung |
| Datei / Ausgabe | Konkrete Fassung, nicht gleichbedeutend mit einem abgeschlossenen Gespräch |
| Versandgruppe | Nachricht an eine tatsächliche verantwortliche Führungskraft mit konkreten Ausgaben |
| Aufgabe | Aus einem Fachstand abgeleitete nächste Handlung; kein unabhängig schliessbarer zweiter Erledigt-Status |

Fachstand, Versandstand und technische Bereitstellung sind getrennte Dimensionen. Ein kompakter Überblick zeigt den wichtigsten offenen Grund und die nächste Handlung; Details können weitere Gründe enthalten. «PDF eingegangen», «inhaltlich übernommen», «Unterschriftenprüfung offen» und «bereitgestellt» werden nicht zu einem unspezifischen «erledigt» zusammengefasst.

Farben unterstützen den Text. Farbe allein trägt keine Statusinformation. Blau kennzeichnet die nächste Hauptaktion, neutrale Darstellung Nebenaktionen, ein Warn-/Gefahrenstil fachlich einschneidende Aktionen. Eine Seite erhält pro aktuellem Arbeitsschritt eine klar erkennbare Hauptaktion.

### Ergebnis, Unterbruch und technische Probleme

Nach einer Sammelaktion bleiben Umfang und Einzelresultate sichtbar: «18 Rückblicke erstellt; 2 benötigen Klärung». Namen verlinken zu offenen Einträgen. Die App nennt getrennt, was gespeichert, erstellt, als Entwurf an Outlook übergeben oder tatsächlich versendet wurde. Ein Export-/Ablagefehler darf einen erfolgreichen vorherigen Schritt nicht fälschlich als ungeschehen darstellen.

Rückfragen erhalten einen konkreten Grund, Empfänger/Zuständigkeit soweit bekannt und eine passende Wiederaufnahme. Ein technischer Fehler erhält Wiederholung oder Klärung am betroffenen Vorgang. Bei unklarem Outlook-Ausgang wird der bestehende Vorgang geprüft, bevor ein neuer erzeugt werden kann. Ein Rückweg wird nicht als Abbruch mit Datenverlust behandelt.

### Corporate Design und Zugänglichkeit

Vorhandene CD-Bausteine, Farbvariablen, Schriftregeln und Komponenten sind Ausgangspunkt. Eine formale Übereinstimmung mit den offiziellen digitalen CD-Vorgaben kann erst anhand der freigegebenen Referenz geprüft werden; die vorhandene CSS-Datei allein ist kein Nachweis.

UI-Ziel: Desktop-Arbeitsplatz mit vielen Datensätzen; sinnvolle Nutzung bei schmaleren Fenstern und Vergrösserung. Tastaturbedienung, sichtbarer Fokus, echte Feldbeschriftungen, verständliche Überschriften und angemessene Kontraste werden an den konkreten Entwürfen geprüft. Formulare passen sich der Breite an; Original und Bearbeitung können nebeneinander oder untereinander stehen. Fixierte Kontext-/Aktionsleisten verdecken keine Felder oder Meldungen. Dialoge, Tabellen und Filter behalten ihre Position statt beim Öffnen unerwartet in andere Bereiche zu springen.

## 6. Seitenentwurf A: Vorjahresziele übernehmen und zustellen

Dies ist ein inhaltlicher Seitenentwurf, kein bereits gestalteter oder implementierter Bildschirm. Die Zahlen sind ein erfundenes Prüfszenario: 20 Zielquellen betreffen hier 20 Personen und jeweils einen Rückblick. Diese Gleichheit darf die App nicht allgemein voraussetzen.

| Bildschirm | Oben sichtbar | Arbeitsfläche | Hauptaktion und Ergebnis |
|---|---|---|---|
| 1. Eingang wählen | «Vorjahresziele übernehmen»; Eingang der Führungskraft Petra Beispiel; erkannte Zieljahre | Gesicherte Anhänge der Mail oder Dateiauswahl. Originale bleiben direkt erreichbar | «20 Dokumente prüfen»; noch keine Zielfreigabe |
| 2. Ziele prüfen | Stapelübersicht: 18 bestätigt, 2 offen; Namen/OE/Führungskraft; aktuelles Zieljahr | Personenliste und Originalvergleich mit Zielbearbeitung. Unklare Zuordnung/Quelle konkret nennen | Pro Quelle «Geprüfte Ziele übernehmen und weiter»; jederzeit die 18 bestätigten Quellen fortsetzen |
| 3. Rückblicke vorbereiten | Nach aktuellem Prüfstand: 18 neue Rückblicke bereit, 2 Quellen offen | Tabelle: Name, OE, verantwortliche Führungskraft, Rückblickzeitraum, nächste Aktion | «18 Rückblicke erstellen» nach klarer Auswahl; Ausnahmezeilen bleiben erreichbar |
| 4. Dateien prüfen | Erstellte Fassungen und erforderliche Dateiprüfung | Dateilinks je Person; verwendete Zielversion; vorhandene/ersetzte Fassung erkennbar | «Geprüfte Dateien für den Versand vorbereiten»; keine neue Zielbestätigung |
| 5. Zustellen | Empfängergruppe Petra Beispiel; Namen der enthaltenen Personen; ZIP-Anhang | Empfänger, Betreff, Nachricht, Dateiinhalt; vorhandener Outlook-Stand | «Outlook-Entwurf erstellen»; später «Tatsächlichen Versand bestätigen» |
| Ergebnis | «18 Rückblicke versendet; 2 Quellen noch zu prüfen» | Erledigte Teilresultate und direkte Links zu den zwei offenen Quellen | Aufgabe für offene Quellen fortsetzen; Versandte Fassungen bleiben Verlauf |

**Wichtige Abzweigungen:** Vorhandener Rückblick → konkrete Korrektur U11; unzugeordneter Eingang → U02 mit Rückweg zu genau diesem Stapel; kein MD-Dokument → Ausschluss am Eingang und aktualisierte Rückblickauswahl; kein passender Gesprächsauftrag → Zuordnung oder begründeter Verzicht. Keine allgemeine Entscheidungsauswahl vor der Klärung, was überhaupt vorliegt.

Die tatsächliche Rückblickverantwortung kann von der absendenden oder aktuellen direkten Führungskraft abweichen. Die App gruppiert erst nach der geprüften Verantwortung. Zusätzliche Empfängergruppen sind deshalb ein mögliches reguläres Ergebnis.

## 7. Seitenentwurf B: Offene Gespräche überblicken und erinnern

| Bereich | Inhalt und Bedienung |
|---|---|
| Kopf | «Gespräche»; gewählter Durchlauf oder «Alle offenen Jahre»; Zeitpunkt des Datenstands |
| Perspektive | «Nach Mitarbeitenden» / «Nach verantwortlicher Führungskraft»; derselbe Bestand, keine getrennten Aufgabenlisten |
| Filter | Name, OE, Jahr/Durchlauf, Anlass, Rückblick/Ausblick, Frist, konkreter Bearbeitungsgrund; aktive Auswahl sichtbar |
| Tabelle nach Mitarbeitenden | Name; OE und direkte Führungskraft; Gesprächsteil/Zeitraum; verantwortliche Person, falls abweichend; Frist; Stand und nächste Handlung |
| Tabelle nach Führungskraft | Gruppenüberschrift mit verantwortlicher Führungskraft; darunter Personen und Teile. Zählung benennt ausdrücklich Gesprächsteile und Personen |
| Sammelaktionen | Auswahl → «Erinnern», «Frist ändern», «Zuständigkeit ändern» oder «Unterlagen nochmals zustellen», jeweils nach Zulässigkeit |
| Detail/Rückkehr | Ausgewählter Gesprächsteil mit nächster Handlung; Rückkehr zum unveränderten Filter- und Seitenkontext |

Beispiel für Erinnerungsauswahl: «146 offene Gesprächsteile gefunden; 37 ausgewählt; davon 32 erinnerbar, 5 zuerst klären». Die Vorschau zeigt die fünf Namen mit Ausschlussgründen und gruppiert die 32 geeigneten Teile nach tatsächlicher Verantwortung. Mehrere Teile derselben Person erscheinen in der Empfängernachricht verständlich zusammen. Eine einzelne blockierte Person hält die anderen Gruppen nicht auf. Die Verarbeitung prüft vor Erstellung und Versand erneut den aktuellen Stand.

## 8. Abgleich mit der vorhandenen Umsetzung

Dieser Abgleich beschreibt wiederverwendbare Bausteine, keine abgeschlossene technische Detailprüfung aller Use Cases.

| Aufgaben / Muster | Vorhandene Grundlage | Konsequenz für die Umsetzung |
|---|---|---|
| Start und fortsetzbare Aufgaben | `hr_routes.py`, `services/hr_views.py`, `templates/hr/work.html` | Aufgabenstart und abgeleitete offene Arbeit zusammenführen; Fachobjekte wiederverwenden |
| Person-/Führungskräftesicht | `hr_views.people/managers/parts`, `services/part_queries.py` | Gemeinsame Gesprächsübersicht; Namen und Führungsrollen verständlich anzeigen; Suche und Zählungen prüfen |
| U01, U04, U10 | `services/cycles.py`, `dialog_events.py`, `part_responsibilities.py` | Vorhandene Anlage und Teilverantwortung nutzen; Änderungs-/Ersetzungsübergänge und Entkopplung ausdrücklich prüfen |
| U02, U11, U14 | `routes.py`, `return_routes.py`, `services/hr_workflow.py`, `return_review.py`, `return_automation.py` | Eingang, Originalprüfung, Nachweis und Bereitstellung als zusammenhängende Aufgabe präsentieren |
| U03 und Versand | `services/word_dispatch.py`, `dispatch_changes.py`, `person_corrections.py`, `goal_delivery.py` | Unveränderte Wiederzustellung von Neuerstellung unterscheiden; bestehende Entwürfe/Wirkungen wiederfinden |
| U05 | `services/deadlines.py` | Vorhandene Änderung auf Durchlauf-/Führungskraft-/Fallumfang nutzen; beliebige Teilmengen noch nicht als vorhanden versprechen |
| U06 | `goal_routes.py`, `services/goal_review.py`, `goal_followups.py`, `goal_queries.py` | Stapelkontext durchgängig erhalten; PR #14 als Zwischenverbesserung berücksichtigen |
| U08 | `services/reminders.py`, `part_queries.py` | Voraussetzungen und tatsächlichen Empfänger prüfen; Entwurf und Versand getrennt darstellen |
| U09 | `sap_routes.py`, `services/sap_staging.py` | Übernahme und Gesprächsfolgen verbinden, ohne die fachlichen Entscheidungen zu vermischen |
| U12, U13, U15, U16 | `sap_export.py`, `feedback.py`, `hr_workflow.closure_summary`, `analytics.py` | Spezifische Ergebnisse und externe Wirkungsgrenzen im jeweiligen Arbeitsauftrag erklären |

Die Navigation benötigt weder ein zweites Pflichtenregister noch unabhängig schliessbare Kopien bestehender Aufgaben. Ein gespeicherter Arbeitskontext darf Auswahl, fachliche Entscheidung und Wiederaufnahme verknüpfen; Fachstatus bleiben bei ihren bestehenden Objekten. Für Aktualität, parallele Bearbeitung und Wiederholungen werden vorhandene Revisions- und Wirkungsprüfungen weiterverwendet.

## 9. Abnahmeszenarien für das neue Bedienkonzept

1. Eine Person ohne Projektwissen findet «Vorjahresziele übernehmen», ohne «Zielquelle» als internes Konzept kennen zu müssen.
2. Zwei Anstellungen derselben Person sind über OE und direkte Führungskraft verständlich unterscheidbar; Nummern müssen nicht eingegeben werden.
3. Zwei weiterhin gleich beschriftete Anstellungen werden mit zusätzlichen vorhandenen Angaben eindeutig auswählbar; keine geratene Auswahl.
4. Beim Führungswechsel sind direkte Führungskraft, Rückblickverantwortung und Ausblickverantwortung erkennbar. Änderung oder Erübrigung des alten Auftrags ist ausdrücklich nachvollziehbar.
5. 18 bereite und 2 ungeklärte Quellen lassen sich ohne Verlust der offenen Arbeit weiterbearbeiten.
6. Ein fremdes PDF lässt sich ohne MD-Felder ausschliessen; danach führt der Rückweg zur ursprünglichen Rückblickauswahl. Kein fremder Rücklauf wird einer Person als Tatsache zugeschrieben.
7. Eine Erinnerungsauswahl über mehrere Seiten nennt exakt Umfang, Einheit und ausgeschlossene Teile. Ein Filterwechsel führt nicht zu einer versteckten Massenaktion.
8. Eine Friständerung ändert den offenen Pflichtteil; eine Nachricht wird nur bei tatsächlich ausgelöster Zustellung behauptet.
9. Unveränderte Wiederzustellung erzeugt kein neues Gespräch. Neue Ziele oder veränderte Zuständigkeit führen erkennbar zur Erneuerung statt zur Wiederzustellung alter Dateien.
10. Stammdatenübernahme lässt bisherige manuelle Gesprächszuordnungen bestehen und nennt offene Folgen. Fehlende Personen gelten nicht automatisch als ausgetreten.
11. Unterjährige Arbeit und offene Altjahre bleiben nach Kampagnenabschluss auffindbar.
12. Dateierstellung, Outlook-Entwurf, tatsächlicher Versand, lokale Dossierbereitstellung und SAP-Dateiexport sind verständlich unterscheidbar.
13. Eine Detailprüfung erhält gültige Eingaben und führt zu Filtern, Seite und Arbeitskontext zurück. Gleichzeitige Änderung wird mit verständlicher Wiederaufnahme gemeldet.
14. Die beiden Seitenentwürfe sind mit Tastatur, schmalerem Fenster, Vergrösserung und einem synthetischen Bestand mit mehr als 100 Treffern nutzbar.

## 10. Umsetzung in überprüfbaren Schritten

| Etappe | Ergebnis | Prüfumfang |
|---|---|---|
| A – Fachliches Aufgabenmodell | Dieser Katalog mit klaren Übergängen, Rollen und Wirkungen | Besonders U03/U04, Fristfolgen und Abschlussweg externer Korrekturen gezielt prüfen |
| B – Konkrete Seitenentwürfe | Start und die beiden Arbeitsansichten aus Abschnitt 6/7 mit repräsentativen Beispieldaten und CD-Bausteinen | Aufgaben finden, Auswahl verstehen, Original prüfen, Rückkehr und Teilresultate nachvollziehen |
| C – Gemeinsame Grundlagen | Einheitliche Personenanzeige, Kontext, Tabellen-/Formularmuster und Statusbegriffe | Namen/Mehrfachanstellung/Führungswechsel, grosse Listen, parallele Bearbeitung |
| D – Zwei vollständige Aufgabenwege | U06 sowie U07/U08 einschliesslich Ausnahmen auf denselben Fachobjekten | Durchgehender Bediencheck mit Testdaten bis zum jeweiligen Ergebnis |
| E – Weitere Aufgaben übertragen | U01/U09/U10, Korrekturen, Wiederzustellung und übrige Aufgaben nach Dringlichkeit | Bestehende Geschäftsregeln und Historien behalten; vorhandene Tests passend weiterverwenden |

Vor der UI-Implementierung sind drei Punkte zu konkretisieren: Wie wird ein ersetzter Gesprächsauftrag inklusive offener Entwürfe eindeutig abgeschlossen? Welche beliebigen Teilmengen können Fristenänderung und unveränderte Wiederzustellung bereits unterstützen? Welcher belastbare Nachweis schliesst eine externe Dossierkorrektur ab? Diese Punkte sind Code-/Fachabgleich, keine pauschale Aufforderung zur erneuten Freigabe des gesamten Konzepts.

Der nächste sinnvolle Arbeitsschritt sind die konkreten Seitenentwürfe mit Beispieldaten aus Etappe B. Änderungen aus PR #14 bleiben ein eigenständig überprüfbarer Zwischenstand; ihre Veröffentlichung wird nicht mit der Abnahme dieses umfassenderen Entwurfs gleichgesetzt.
