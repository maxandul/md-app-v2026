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

Fristanpassungen und Erinnerungen werden über die vorhandene Durchlaufansicht
bearbeitet. Die Gesprächsübersicht verlinkt diese Ansicht; ihre Suchfilter werden
nicht als Aktionseinschränkung übernommen. Es gibt dort noch keine neue gemeinsame
Auswahl von Gesprächsteilen über alle gefilterten Seiten. Diese Funktion braucht
eine eigene Vorschau und erneute fachliche Prüfung unmittelbar vor der Ausführung.

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
