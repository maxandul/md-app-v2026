# Zielnachreichung: nächste Aufgabe sichtbar machen

Der Ablauf führt von eingelesenen Dokumenten über die Prüfung der Ziele zu den
aktualisierten Rückblicken, der Dateiprüfung und dem bestätigten Versand.

## Sichtbares Verhalten

- Die Übersicht zählt Zielquellen über alle Seiten im gewählten Eingang und mit
  den gewählten Such-, Jahr- und OE-Filtern. Der Arbeitsstandfilter beeinflusst
  die Liste, nicht diese Gesamtzählung. Eine Quelle kann mehrere Rückblicke betreffen.
- Entwürfe nennen die fehlenden Angaben und die noch erforderliche Originalprüfung.
  «Bestätigen und Rückblicke vorbereiten» führt nach erfolgreicher Prüfung direkt weiter.
- Übersicht, Arbeitsliste und Ausgabeauswahl verwenden dieselbe Ableitung der
  nächsten Aufgabe. Erstellbare Rückblicke, offene Klärungen, Dateiprüfung und
  Versand sind getrennt erkennbar. Bereite Teile bleiben einzeln erstellbar.
- Die Vorprüfung verwendet die Erstellungsprüfungen für Zielquellen, Rücklauf,
  SAP-Zuordnungskonflikte, Zeitraum und Word-Vorlage. Erstellen und Versenden
  prüfen den aktuellen Stand weiterhin erneut; Dateifehler können auch danach auftreten.
- Ungeklärte Eingänge erscheinen mit Dateiname und Bearbeitungslink. Bei
  unzugeordneten Mailanhängen sind die passende Postfachsuche und das Original
  erreichbar. Bereits übernommene Rückblicke führen in die Rücklaufprüfung.
- Bestehende aktuelle Ausgaben werden zur Prüfung oder zum Versand angeboten;
  sie erscheinen nicht nochmals als neu zu erstellender Rückblick.

## Ungeklärte Eingänge

Eine vollständig fehlende Zuordnung kann weiterhin mehrere Personen betreffen.
Das wird erklärt und zum auslösenden Eingang verlinkt. Ein eindeutig einer
anderen Person zugeordneter PDF-Eingang blockiert deren Rückblick nicht.
Fachfremde PDFs können direkt oben in der Eingangsprüfung mit «Kein MD-Dokument –
ausschliessen» gekennzeichnet werden, ohne MD-Felder auszufüllen. Der Ausschluss
verwendet den vorhandenen rücknehmbaren Prüfstatus und wird in den Prüfmetadaten
und im Audit protokolliert. Er gilt für diesen Eingang über alle Zielquellen.
Die Eingangsübersicht bietet dafür den Filter «Kein MD-Dokument». Der Ausschluss
lässt sich wieder aufheben, ohne die zuvor ausgelesenen oder gespeicherten Angaben
zu verlieren. Bereits übernommene PDFs lassen sich so nicht ausschliessen.

Solange nur ein ungeprüfter Eingang vorliegt, erscheint keine Entscheidung zum
Rückblick. Die App führt zuerst zum Eingang und von dort zurück zur Auswahl.
Entscheidungen bleiben für vorhandene Rückblicke oder bereits dokumentierte
Rückfragen sichtbar. Die vorhandenen Originalprüfungen bleiben erforderlich.
Darstellungsdaten werden nicht in die gespeicherten Rücklauf-Nachweise oder
deren Prüfsummen aufgenommen. Keine Datenbankmigration ist erforderlich.

## Prüfung

- Python-Regression offline: 351 Tests und 65 Subtests erfolgreich. Elf gezielte
  Ablaufprüfungen decken auch den rücknehmbaren Ausschluss fachfremder Eingänge ab.
- JavaScript: elf vorhandene Prüfungen erfolgreich.
- Volumentest: 1000 Personen, fünf Jahre, 10500 Gesprächsteile.
- Visuelle Browserprüfung ausstehend: Der verfügbare externe Browser erreicht
  den lokalen Testserver nicht; lokales Chromium startet in dieser Umgebung nicht.

## Bediencheck

1. Mehrere alte Dokumente einlesen: Die Übersicht zeigt den gesamten Eingang
   und unterscheidet bestätigte Quellen von noch zu prüfenden Entwürfen.
2. Eine Quelle prüfen und bestätigen: Der nächste Bildschirm bietet den
   passenden Rückblick an oder nennt den konkreten Grund samt Bearbeitungslink.
3. Einen gemischten Stapel öffnen: Nur zulässige neue Rückblicke sind auswählbar;
   ein bekannter Rücklauf einer anderen Person hält diese nicht auf.
4. Rückblick erstellen: Die nächste Aufgabe wechselt zur Dateiprüfung. Nach
   deren Bestätigung folgt die Versandvorbereitung; ein Outlook-Entwurf gilt
   weiterhin erst nach Bestätigung des tatsächlichen Versands als versendet.
5. Einen ungeklärten PDF-Eingang öffnen und zuordnen: Anschliessend ist er
   ausschliesslich bei den fachlich passenden Rückblicken zu berücksichtigen.
6. Einen fachfremden Eingang ohne MD-Feldeingaben ausschliessen: Die Auswahl
   wird wieder erstellbar, das Original bleibt erhalten und der Ausschluss lässt
   sich unter «Kein MD-Dokument» wieder öffnen. Bei Wiederöffnung erscheint der
   Eingang erneut in der Prüfung.
