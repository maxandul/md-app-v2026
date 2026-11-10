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
