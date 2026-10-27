# Umsetzungsplan: Durchgängige HR-Nutzerführung

Stand: 27. Oktober 2026  
Geprüfte Codebasis: main, Commit `9d7ca779afc18e9bd9c6607a5b3dbe8465537a18`.  
Status: Codeabgleich und Umsetzungsvorschlag; keine Implementierung oder Migration durchgeführt.

Grundlagen:
- [Prozessübersicht und bestätigte Fachentscheidungen](PROZESSUEBERSICHT_NUTZERFUEHRUNG.md)
- [Seitenentwurf Zielnachreichung](SEITENENTWURF_ZIELNACHREICHUNG.md)
- [Seitenentwurf Rücklauf und Stammdaten](SEITENENTWURF_RUECKLAUF_STAMMDATEN.md)

## 1. Ergebnis des Codeabgleichs

Die vorhandenen Fachfunktionen sind eine brauchbare Grundlage. Die wesentlichen Lücken liegen in gemeinsamen Vorgangsverknüpfungen, bearbeitbaren Zielversionen, Zuständigkeit je Gesprächsteil und der bisherigen Kopplung an Jahresdurchläufe. Ein reiner Menüumbau würde diese Lücken bestehen lassen.

### Vorhandenes und notwendige Änderungen

| Bereich | Befund im Code | Konsequenz |
|---|---|---|
| Zielauslesung | `goal_documents.py` und `legacy_forms.py` lesen Word/PDF-Ziele, melden Unsicherheiten und behandeln Dubletten | Wiederverwenden; Erkennung und fachliche Freigabe trennen |
| Zwei Zielimportwege | Postfach verwendet `allow_partial_word=True`; manueller Import standardmässig nicht | Beide Zugänge in dieselbe Prüfung überführen, ohne Teilimporte stillschweigend als bestätigt zu behandeln |
| Quellenwahl | `prior_goals()` verbindet Falldaten, PDF-Zielversionen und historische Ziele; Quellenwahl ist mit Fingerprint abgesichert | Zentralen Resolver erweitern, damit bestätigte HR-Korrekturen reproduzierbar verwendet werden |
| Zielkorrektur | Historische Ziele sind Zeilen je importierter Datei; PDF-Zielversion hat ein eindeutiges `import_id` | Mehrere editierte Fassungen desselben Originals brauchen ein ausdrückliches Versionsmodell |
| Word-Erzeugung | `create_word_package()` unterstützt ein ganzes Führungskräftepaket oder einen Fall mit ausgewählten Dokumentarten | Renderer erhalten; gezielte Mehrfachauswahl und Teilergebnisse ergänzen |
| Einzelkorrektur | `person_corrections.py` besitzt eigene Ausgabe, Manifest, Outlook-Entwurf, Versandbestätigung und Wiederanlaufschutz | Bausteine erhalten; Versandgruppen mit mehreren Ausgaben ergänzen |
| Arbeitsliste | `cockpit_overview()` bildet Aufgaben aus getrennten Tabellen; Mailaufgaben sind allgemein „E-Mail-Anhänge prüfen“ | Gemeinsames Aufgabenmodell mit stabilen Verweisen und konkreter nächster Aktion |
| Verantwortlichkeit | `dialog_cases.manager_pn` und `dialog_events.manager_assignment_id` gelten für den ganzen Fall/das Ereignis | Verantwortung, Zeitraum und Formular-OE je Rückblick/Ausblick ergänzen |
| Formular-OE | `dialog_form_org_units` speichert einen Wert pro Ereignis; Word-Erzeugung verwendet ihn für dessen Dokumente | Auswahlprinzip erhalten, Geltungsbereich auf Gesprächsteil erweitern |
| Durchläufe | Ereignis darf ohne Durchlauf existieren; produktive Ausgabe/Dokumente hängen weiterhin an Fall und `cycle_id` | Durchlaufentkopplung ist ein fachlicher und technischer Umbau, nicht nur ein ausgeblendeter Filter |
| SAP-Abgleich | Import verändert aktuelle Personen/Anstellungen; Route synchronisiert anschliessend offene Durchläufe | Vorschau und Fachentscheidungen vor wirksamen Änderungen einführen |
| PDF-Rücklauf | `stage_pdf()` legt Word-PDFs als `pending` ab; `confirm_import()` übernimmt nach manueller Prüfung | Automatische Zulässigkeitsentscheidung mit klar begrenzten Formaten und denselben fachlichen Validierungen ergänzen |
| Unterschriften | `signature_checked` wirkt auf Abschluss, Übergabe und Abschlussübersicht; Startmigration verändert offene Altstände | Nicht nur Button entfernen: Statuslogik, Migration und abhängige Auswertungen gemeinsam ändern |
| Mailtext | `InboundMessage` enthält im geprüften Stand keinen Nachrichtentext; Outlook-Adapter liest Betreff und Anhänge | Zusätzliche Mailanliegen können aktuell nicht zuverlässig erkannt werden; Adapter/Verarbeitung erweitern |

## 2. Besonders wichtige Abhängigkeiten

### 2.1 SAP-Import verändert heute unmittelbar den Arbeitsbestand

`import_sap_workbook()` schreibt aktuelle Stammdaten und setzt nicht im Import enthaltene Personen auf inaktiv. Die Route ruft danach `synchronize_open_cycles()` auf.

`synchronize_cycle_with_import()` deaktiviert zunächst nicht manuell angelegte Fälle, aktiviert passende Führungslinien erneut und legt fehlende Kombinationen neu an. Ereignisse inaktiver Fälle werden auf `cancelled` gesetzt. Manuelle Fälle sind bei der pauschalen Deaktivierung ausgenommen.

**Folgerung:** Ein Führungswechsel kann heute zur neuen Fallkombination führen. Für das Soll muss der Import zuerst Unterschiede darstellen und Entscheidungen über bestehende Gesprächsteile respektieren. Diese Synchronisierung darf beim neuen Ablauf nicht unbemerkt weiterlaufen.

### 2.2 Historie ist teilweise vorhanden, aber kein verlässlicher Wechselkalender

`reporting_lines` enthält Führungskraft/OE je Import. `manager_assignments` verweist ebenfalls auf Imports. Aktuelle Anstellungsangaben werden dagegen überschrieben. Die beim SAP-Import geschriebenen `valid_from/valid_to` stammen aus Eintritt/Austritt der Anstellung, nicht aus dem tatsächlichen Beginn/Ende einer Führungszuordnung.

**Folgerung:** Vorhandene Importstände sind als Beobachtungen nutzbar. Aus ihnen darf kein genaues Übertrittsdatum erfunden werden. Zusätzlich braucht es nachvollziehbare Stammdatensnapshots sowie ein ausdrücklich bestätigtes oder aus verlässlicher Quelle stammendes Ereignisdatum.

### 2.3 Gesprächsteile sind in Pflichten bereits angelegt

`document_obligations` unterscheidet Rückblick und Ausblick mit eigener Frist und eigenem Status. Das ist ein sinnvoller Ansatzpunkt. Verantwortung und Formular-OE liegen jedoch oberhalb der Pflicht.

**Vorschlag:** Ergänzende Gesprächsteil-Konfiguration mit stabiler Referenz auf Ereignis und Dokumentart. Sie enthält Verantwortung, Zeitraum, Formular-OE samt Herkunft, Entscheidungsgrund und Revision. Vor endgültigem Schema prüfen, ob diese Angaben direkt an bestehende Pflichten oder an eine eigene Teil-Tabelle gehören. Keine unabhängige zweite Pflichtenliste schaffen.

### 2.4 Selektive Unterschriftenprüfung und Automatik

`confirm_import()` erzeugt reguläre Dokumente derzeit mit `signature_checked=False` und `needs_signature_check`; `refresh_case_status()` berücksichtigt das Flag. Auch `closure_summary()` zählt offene Übergaben anhand dieses Flags. Die Initialisierung passt alte Zustände erneut an.

**Aktualisierte Fachregel vom 27. Oktober 2026:** Bei ausdrücklich unterschriftspflichtigen Fällen bestätigt HR die vorhandenen Unterschriften am konkreten PDF. Prüfpflicht und Prüfentscheid an die Dokumentversion binden; offene Prüfung, fehlende Unterschrift und tatsächlich erfolgte Nachforderung unterscheiden. Neue Version erneut prüfen, identische Dublette nicht. **Konkretisierte Fachregel (27. Oktober 2026):** Bei Gesamtbeurteilung des Rückblicks „genügend“ oder „ungenügend“ sind sowohl Rückblick als auch zugehöriger Ausblick auszudrucken, von Führungskraft und mitarbeitender Person zu unterzeichnen und einzuscannen. Je Gesprächsteil sind das digitale, maschinenlesbare PDF und der unterschriebene Scan zurückzusenden. HR prüft am jeweiligen Scan das Vorhandensein beider Unterschriften. **Annahmeregel:** Ein unterschriebener Scan allein genügt, wenn daraus alle benötigten Daten vollständig und zuverlässig gewonnen und validiert werden können und HR die erforderlichen Unterschriften bestätigt. Die Rücksendeanweisung bleibt aus Gründen der Verarbeitungssicherheit bei beiden Fassungen. Ein fehlendes digitales PDF allein erzeugt weder eine Blockade noch eine Nachforderung. Unsichere oder fehlende Angaben werden konkret zur Prüfung angezeigt; lassen sie sich nicht eindeutig klären, wird das digitale PDF nachgefordert. Sind beide Dateien vorhanden, werden sie demselben Gesprächsteil zugeordnet und erhalten. Eine erfolgreiche OCR-Ausführung oder fehlende Warnung allein belegt keine vollständige Auslesung. Die Zuverlässigkeit ist vor Automatisierung mit repräsentativen Scans und bekannten Sollwerten zu prüfen, insbesondere für Freitexte, Beurteilungen, Datumsangaben und Markierungen. Dies ist eine Sollregel, keine Aussage über bereits vorhandene OCR-Fähigkeiten.

Die Beurteilung des Rückblicks löst die Pflicht für **beide** Teile aus. Der Ausblick braucht dafür keine eigene negative Beurteilung. Getrennte Eingänge sind möglich; die App zeigt je Teil getrennt „Datenauslesung klären“, „Unterschriebener Scan fehlt“, „Unterschriftenprüfung offen“, „Unterschrift fehlt“, „Nachgefordert“ bzw. „Unterschriften vorhanden“. Ein vorhandener Scan ist erst nach HR-Sichtprüfung bestätigt. Bei getrennten Verantwortlichkeiten bleibt je Teil die dafür zuständige Führungskraft massgeblich. Bereits eingegangene oder bereitgestellte Ausblicke werden bei später erkannter Pflicht im selben MD erneut auf den erforderlichen Nachweis geprüft; externe Ablagen werden nicht stillschweigend ersetzt.

Auch bei Uneinigkeit zwischen Führungskraft und mitarbeitender Person gilt fachlich dieselbe Druck-, Unterschriften- und Rücksendepflicht. Dafür fehlt im Formular ein eindeutiger Marker: HR prüft diesen Auslöser nicht systematisch, und die App erzeugt daraus keine automatische Prüf- oder Nachforderungsaufgabe. Fehlender Marker darf weder als bestätigte Einigkeit noch als Anlass für eine pauschale Klärungsaufgabe bei allen Fällen interpretiert werden.

**Zweck laut HR:** Dokumentation, dass Leistung beziehungsweise Verhalten besprochen und Erwartungen geklärt wurden, sowie angestrebte Verbindlichkeit und Absicherung für mögliche personalrechtliche Folgeschritte. Dies beschreibt die organisatorische Zielsetzung, keine geprüfte Aussage zur rechtlichen Beweiswirkung. Unterschriftenprüfung bestätigt das Vorhandensein der Unterschriften, nicht Einigkeit mit der Beurteilung.

**Technische Umsetzung:** Zuordnung der vorhandenen Beurteilungscodes zu „genügend“/„ungenügend“ anhand der Formulare prüfen. Datenquelle und Unterschriftennachweis sind unterschiedliche Dokumentrollen; ein ausreichend auslesbarer Scan kann beide Rollen erfüllen. Zwei Fassungen dürfen keine doppelten Fachdaten erzeugen. Widersprüche zwischen den Fassungen werden geklärt. Die Prüfung bindet den konkreten Scan an die daraus gewonnenen beziehungsweise zugehörigen digitalen Inhalte; eine inhaltlich neue Fassung darf die alte Unterschriftenbestätigung nicht erben.

**Vorschlag:** Fachliche Validierung, Unterschriftenprüfung und technische Bereitstellung getrennt modellieren. Bestehende Unterschriftenhistorie erhalten, aber keine neuen Datensätze durch pauschales Setzen von `signature_checked=1` als geprüft ausweisen. Alte Prüfblockaden gezielt in nachvollziehbare neue Zustände überführen. Rücksendeanweisung für beide Fassungen und Annahme eines ausreichend auslesbaren, unterschriebenen Scans unterscheiden; Datenquelle und Unterschriftennachweis nachvollziehbar erhalten.

## 3. Gemeinsame technische Grundlage – Vorschlag

### Vorgänge und Aufgaben

Ein schlanker Vorgang verknüpft:
- Eingang und Originaldatei bzw. bestehende Import-ID;
- betroffene Gesprächsteile;
- geprüfte Zielversionen;
- Ausgaben und Versandgruppen;
- Entscheidungen, Rückfragen und Verlauf.

Fachstatus bleiben an den jeweiligen Fachobjekten. Die Aufgabenübersicht wird daraus abgeleitet; sie speichert nicht zusätzlich einen widersprüchlichen zweiten Erledigt-Status. Nur echte Entscheidungen, Wartegründe und Revisionen werden ausdrücklich gespeichert.

Ein Vorgang kann mehrere Teilaufgaben enthalten, etwa „Quelle klären“ und „drei Rückblicke versenden“. Gleiche Eingänge über Scan und Upload müssen dieselbe Verarbeitung wiederfinden.

### Zielversionen

Original, automatische Extraktion, bearbeiteter Entwurf und bestätigte Fassung unterscheiden. Bestätigte Fassungen nicht überschreiben; neue Änderung erzeugt eine neue Revision. Die Formularausgabe referenziert die tatsächlich verwendete Revision.

Bestehende historische Ziele und PDF-Zielversionen über Adapter einbeziehen. Alte Importe nicht nachträglich als „von HR bestätigt“ deklarieren; vorhandenen Prüfstand erhalten oder als unbekannt markieren. Für bisher teilweise importierte Word-Ziele vorhandene Warnungen soweit verfügbar übernehmen; fehlende Information nicht als Freigabe interpretieren.

### Erzeugung und Versandgruppen

Mehrere Ausgaben gruppieren, statt für jede Person einen unabhängigen Versand erzwingen:
- Einzelresultat mit eigener Version und Prüfsumme;
- Empfänger je Gesprächsteil;
- Versandgruppe mit Referenzen auf enthaltene Ausgaben;
- bestätigter Versand wirkt nur auf tatsächlich enthaltene Ausgaben.

Vor Erstellung und vor Outlook-Übergabe erneut prüfen: aktuelle Zielversion, Verantwortung, Formulargrundlagen und bereits eingegangener Rückblick. Ein zwischenzeitlicher Rücklauf muss die Person aus der Vorlagenerstellung in die Korrekturklärung führen.

### Wiederanlauf und externe Wirkung

Datenbankspeicherung, Dateierzeugung und Outlook sind nicht eine gemeinsame Transaktion. Bestehende Sperren und Status „processing/failed/draft_created“ weiterverwenden bzw. auf Gruppen erweitern. Ein unklarer Ausgang darf keinen zweiten Entwurf oder eine doppelte Ablage erzeugen. Bei Sammelfehlern erfolgreiche Einzelresultate erhalten.

## 4. Reihenfolge der Umsetzung

Die übergreifende Nutzerführung wird **vor** der Implementierung anhand des [Gesamtkonzepts](GESAMTKONZEPT_HR_UEBERSICHT.md) entworfen. Feedback, Probezeit, Personenhistorie, Führungskräfteübersicht und grosse Listen gehören bereits in diesen Entwurf; Etappe F ist keine Verschiebung dieser Grundsatzarbeit.

| Etappe | Lieferumfang | Abhängigkeit / Abnahme |
|---|---|---|
| 0 – Gesamte Oberfläche prüfen | Zusammenhängender Entwurf für Arbeitsvorrat, Führungskraft, Mitarbeitende, Fall und Feedback; Navigation, kurze Texte, Filter und Sammelaktionen | HR-Szenarien mit wiederkehrenden MDs, Altjahresresten, Probezeit und 1000 Mitarbeitenden durchspielen; keine bereits nachgewiesene Skalierbarkeit behaupten |
| A – Grundlage vorbereiten | Versionierte Migrationen; verknüpfte Vorgänge; zentrale Auflösung von Gesprächsteil-Verantwortung; Referenzen auf bestehende Daten | Alte Fälle, Dokumente und Versandnachweise bleiben unverändert auffindbar |
| B – Erster vollständiger Ablauf | Gemeinsamer Zieleingang, direkte HR-Korrektur, Quellenfreigabe, Korrekturklärung, ausgewählte Rückblicke gesammelt erstellen, gruppierter Outlook-Entwurf und Versandbestätigung | A; fünf Nachreichungen mit Teilfehlern und abweichender Rückblick-Verantwortung vollständig bearbeitbar |
| C – Getrennte Zuständigkeiten vollständig nutzen | Rückblick/Ausblick getrennt zuweisen; Formular-OE und Zeiträume; regulärer Versand, Rücklaufzuordnung und Erinnerungen umstellen | Zentrale Auflösung aus A; kein Verbraucher darf unbemerkt die alte gemeinsame Führungskraft verwenden |
| D – SAP-Abgleich und fortlaufende Dialoge | Staging/Vorschau, Snapshots, Änderungsvorgänge, Schutz manueller Entscheidungen; produktive Bearbeitung unterjähriger Dialoge unabhängig vom Kampagnenabschluss | C; bestehende automatische Deaktivierung gezielt ersetzen; bestehende Fälle vollständig berücksichtigen |
| E – Rücklaufautomatik | Gemeinsame Validierung, automatische Übernahme geeigneter PDFs, Ausnahmen; selektive Unterschriftenprüfung und getrennte Übergabestatus | Belastbare Zuordnung aus C/D; automatisierte Prüfungen mit repräsentativen Formularvarianten |
| F – Konsolidieren | Neue Arbeitsübersicht als Standard; redundante Einstiege entfernen; Feedback, Auswertung und Abschluss auf neue Verknüpfungen abstimmen | Vorhandene Spezialfälle und Verläufe weiterhin erreichbar |

**Warum A vor B?** Ohne stabile Zielversionen, Verknüpfungen und Verantwortungsauflösung würde der erste UI-Umbau später nochmals grundlegend geändert werden müssen.

**Umfang der ersten Lieferung B:** Der durchgängige Nachreichungsablauf ist das erste nutzbare Ergebnis. Die vollständige Durchlaufentkopplung und automatische Verarbeitung aller PDF-Rückläufe sind darin noch nicht enthalten. Eine abweichende Rückblick-Verantwortung muss B bereits korrekt berücksichtigen; getrennte Ausblick-Verantwortung in allen weiteren Abläufen wird in C vervollständigt. Bis dahin keine UI anbieten, die eine systemweit wirksame Trennung verspricht.

Die Etappen sind aufeinander abgestimmte Arbeitspakete, keine Aufwandsschätzung oder Termine.

## 5. Konkrete Arbeitspakete für die erste Lieferung

### B1 – Mail und Upload zum selben Vorgang führen
- Gesicherte Anhänge referenzieren statt herunterladen/erneut hochladen.
- Extraktion über vorhandene Parser.
- Person/Anstellung/Jahr und Warnungen in derselben Prüfung korrigieren.
- Dubletten mit vorhandenem Vorgang verknüpfen.

### B2 – Ziele editieren und bestätigen
- Versionierte Entwürfe; Original erhalten.
- Optimistische Revisionsprüfung nach Muster von `workflow_pdf_state`.
- Bestätigung prüft Zuordnung und offene Erkennungsprobleme.
- `prior_goals()` auf bestätigte Fassung erweitern; bestehende Mehrquellenprüfung erhalten.

### B3 – Folgeaktion bestimmen
- Noch kein Rückblick: Formularerstellung anbieten.
- Bereits eingegangen, auch ungeprüft: Korrekturbedarf klären.
- Schon bereitgestellt: Übergabe sichtbar machen, keine automatische Ersetzung.
- „Keine Korrektur nötig“ und „korrigierten Rücklauf anfordern“ dokumentieren.
- Relevante Eingangsinformationen aus offiziellen Dokumenten und noch offenen Importen berücksichtigen; ein unzugeordneter Eingang darf nicht als sicher fehlender Rücklauf gelten.

### B4 – Sammelerstellung und Versand
- Ausgewählte Gesprächsteile statt gesamter Führungslinie.
- Einzelresultate und eindeutige Dateinamen auch bei Mehrfachanstellungen.
- Vorhandene Word-Renderer, Manifeste und Outlook-Adapter nutzen.
- Geprüfte Ausgaben nach Rückblick-Verantwortlichkeit gruppieren.
- Unterbrochene Versandgruppen und schon übermittelte Mitglieder korrekt behandeln.

### B5 – Arbeitsübersicht und Verlauf
- Konkrete Aufgaben mit Direktlink.
- Gruppierter Fortschritt mit offenen Einzelpunkten.
- Bearbeitungsstand unabhängig von Mailablage.
- Erledigung aus Fachzuständen ableiten; keine zusätzliche pauschale Mailfreigabe als fachlicher Abschluss.

## 6. Datenübernahme und Einführung

1. Vor Schemaänderung Wiederherstellung einer vollständigen Kopie von Datenbank, Originalen, Ausgaben und Konfiguration nachweisen.
2. Migrationen ausdrücklich versionieren. Die aktuelle Initialisierung enthält wiederkehrende fachliche Datenänderungen; neue Zustände dürfen dadurch beim nächsten Start nicht zurückgesetzt werden.
3. Neue Verknüpfungen ergänzend aufbauen, bestehende IDs und Dateipfade erhalten. Historische Zuständigkeiten oder Zeitpunkte nicht nachträglich erraten.
4. Altbestand mit fehlender Herkunft kennzeichnen; nur tatsächlich entscheidungsbedürftige Fälle zur Klärung vorlegen.
5. Neue und alte Einstiege dürfen übergangsweise dieselben Dienste nutzen. Niemals zwei unabhängige Import-/Versandautomaten für denselben Eingang aktivieren.
6. Rückkehr zum alten UI nur zulassen, solange es die neuen Daten korrekt versteht. Nach neuen Schreibvorgängen ist ein einfaches Abschalten der Oberfläche kein Datenbank-Rollback.
7. Vor Aktivierung auf dem HR-Gerät repräsentative Kopien und synthetische Szenarien prüfen; Outlook-/Ablagewirkung in einer kontrollierten Testkonfiguration abnehmen.

## 7. Prüfplan

Vorhandene Tests dienen als Ausgangspunkt, nicht als Nachweis für die neue Logik. Im Codeabgleich wurden keine Tests ausgeführt.

| Prüfbereich | Wesentliche Fälle |
|---|---|
| Zielquellen | Word/PDF derselben Ziele, Teilübernahme, mehrere Quellen, neue HR-Version, erneuter Eingang überschreibt Korrektur nicht |
| Sammelerstellung | Vier erfolgreiche und eine ungeklärte Person, Fehler einer Ausgabe, Mehrfachanstellung, Empfängerwechsel |
| Zeitpunktkonflikte | Rückblick trifft nach Auswahl ein; Quelle oder Zuständigkeit ändert sich vor Erstellung/Versand |
| Zuständigkeiten | Alte Führungskraft Rückblick, neue Ausblick; Ersatz nur für einen Teil; Formular-OE bleibt historisch korrekt |
| SAP-Abgleich | Vollständiger/auffällig unvollständiger Export, fehlende Anstellung, neue Person, bekannter manueller Override, Wechsel ohne Ereignisdatum |
| PDF-Automatik | Bekannte gültige Formate, Erkennungswarnungen, unklare Zuordnung, abweichende Version, Dublette, Ablagefehler |
| Unterschriften | Genügend/ungenügend aktiviert Pflicht für Rückblick UND Ausblick; je Teil digitales PDF plus Scan oder allein ausreichend auslesbarer Scan mit beiden Unterschriften; keine Nachforderung allein wegen fehlender digitaler Fassung; unvollständige/unsichere Auslesung und widersprüchliche Fassungen; getrennte Eingänge; bereits bereitgestellter Ausblick; fehlender Scan/Unterschrift; Nachforderung; neue Version; Uneinigkeit ohne Marker erzeugt keine automatische Prüfung |
| Gesamtoberfläche und Menge | 1000 Mitarbeitende über mehrere Jahre, serverseitige Filter/Paginierung, offene Altjahresfälle, Führungskraft mit vielen Personen, Mehrfachanstellung, Feedback und Probezeit |
| Migration | Altbestand vollständig, teilweise importierte Ziele, offene Entwürfe, bereitgestellte Dokumente, wiederholter Start |
| Bedienung | S01–S05 aus Prozessübersicht; Direktlinks, Wiederaufnahme, Gruppenkontext und konkrete nächste Aktion |
| Externe Integration | Echter Windows-/Outlook-Entwurf, Versandbestätigung, Verschieben und tatsächliche Dossierbereitstellung |

Vorhandene Testdateien: `test_goal_import.py`, `test_mail_goals.py`, `test_person_corrections.py`, `test_word_packages.py`, `test_word_dispatch.py`, `test_word_pdf_imports.py`, `test_auth_and_sap_sync.py`, `test_hr_independence.py`. Neue Tests sollen die fachlichen Übergänge und Wiederholbarkeit prüfen, nicht nur einzelne UI-Texte.

## 8. Noch gezielt zu klären

- Welche tatsächlichen Exportfelder liefern ein verlässliches Übertritts-/Wirksamkeitsdatum?
- Exakte Regeln für Eintritt/Probezeit/Übertrittszeiträume und SAP-massgeblichen Rückblick.
- Wie bestätigt HR eine nötige Korrektur nach externer Dossier-/SAP-Verarbeitung?
- Wie werden zusätzliche Anliegen im Mailtext erkannt? Der aktuelle Adapter stellt den Text nicht bereit; Erkennung darf nicht allein aus erfolgreichen Anhängen gefolgert werden.
- Welche Word-/PDF-Varianten dürfen nach belegter Erkennungsqualität automatisch verarbeitet werden?

Diese Fragen blockieren nicht die vorbereitende Arbeit und den Zielnachreichungsablauf insgesamt. Sie blockieren jeweils die davon abhängige Automatik bzw. abschliessende Implementierung.

## 9. Codebelege

Alle Befunde beziehen sich auf die oben genannte unveränderte main-Codebasis.

- [Schema](../webapp/schema.sql): Fälle, Ereignisse, Pflichten, Zielquellen, Versand und Formular-OE.
- [Initialisierung/Migrationen](../webapp/db.py): Schemaergänzungen, Scanregel-Anpassung und Backfill.
- [SAP-Import](../webapp/services/sap_import.py): `import_sap_workbook`, `_sync_active_flags`.
- [Durchlaufsynchronisierung](../webapp/services/cycles.py): `synchronize_cycle_with_import`, `synchronize_open_cycles`.
- [Routen](../webapp/routes.py): SAP-Import mit nachfolgender Synchronisierung; getrennte Ziel- und Korrektureinstiege.
- [Ereignismodell](../webapp/services/dialog_events.py): manuelle Ereignisse und Spiegelung aus Jahresfällen.
- [Word-Erzeugung](../webapp/services/word_packages.py): `prior_goals`, `create_word_package`.
- [Zielauslesung](../webapp/services/goal_documents.py), [historische Quellen](../webapp/services/legacy_forms.py), [Upload-Batches](../webapp/services/goal_batches.py), [Mail-Ziele](../webapp/services/mail_goals.py).
- [Einzelkorrekturen](../webapp/services/person_corrections.py): `prepare`, `act`.
- [PDF-Import](../webapp/services/word_pdf_imports.py): `stage_pdf`, `matching_cases`, `_validate`, `confirm_import`.
- [Dokumentstatus und Übergabe](../webapp/services/documents.py): `refresh_case_status`, `confirm_digital_signature`.
- [Arbeitsübersicht](../webapp/services/cockpit.py), [Prüf-/Abschlusszustände](../webapp/services/hr_workflow.py).
- [Postfacheingang](../webapp/services/mail_intake.py), [Outlook-Adapter](../webapp/adapters/outlook.py).
