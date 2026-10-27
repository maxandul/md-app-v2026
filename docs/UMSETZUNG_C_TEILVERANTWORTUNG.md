# Lieferung C: Verantwortung je Gesprächsteil

Stand: 27. Oktober 2026. Branch: `feat/hr-teilverantwortung-c`.
Basis: A/B bei `28759a54fc11fd476efc121a7f79cb9a222eefa6`.
Diese Lieferung wird separat gegen `feat/hr-zielnachreichung-ab` geprüft.

Die Bedienprüfung A/B wurde vom Anwender mit «bedienprüfung i.o.» bestätigt.
Das ersetzt weder eine Prüfung echter Outlook-Zustellung noch die noch
ausstehende Bedienprüfung der neuen C-Oberfläche.

## Umgesetzt

Rückblick und Ausblick desselben Falls können jeweils eine andere Führungskraft,
einen anderen Zeitraum und eine eigene Formular-OE erhalten. Beispielsweise
bleibt der Rückblick bei der bisherigen Führungskraft, während die neue
Führungskraft den Ausblick erhält. Eine automatische Stichtags- oder
Pflichtentscheidung wird daraus nicht abgeleitet; HR bestätigt die Zuordnung.

Der neue Einstieg **Gesprächsteile** zeigt standardmässig offene Teile über alle
Jahre. Person/Personalnummer, Führungskraft, Teil, Endjahr des Zeitraums und
gespeicherte Formular-OE sind serverseitig filterbar. 25, 50 oder 100 Zeilen je
Seite und eine Rückkehr zur vorherigen Auswahl halten den Bestand übersichtlich.
Fall- und Führungsansichten zeigen die tatsächliche Verantwortung je Teil.

| Verbraucher | Verhalten in dieser Lieferung |
|---|---|
| Zuordnung | Führungskraft suchen und auswählen; Zeitraum, OE-Quelle und Grund je Teil speichern; Versionsprüfung schützt vor veralteten Browserständen |
| Formular-OE | OE der Anstellung oder der gewählten Führungskraft beim Speichern festhalten; spätere SAP-Änderungen überschreiben diesen Wert nicht |
| Word-Ausgabe | Formularfelder, Ziele, Zeitraum und Empfänger nach der Verantwortung des jeweiligen Teils auflösen |
| Regulärer Word-Versand | Auch Führungskräfte ohne ursprünglichen Gesamtfall erhalten ihre zugewiesenen Teile; Datenänderungen machen vorbereitete Ausgaben erneut prüfpflichtig |
| Personenbezogene Ausgabe | Ausgewählte Teile nach tatsächlichem Empfänger gruppieren; ein Erstellungsfehler lässt erfolgreiche andere Gruppen erhalten |
| Rücklauf | Zuordnung nach Person, Anstellung, Teil und tatsächlichem Zeitraum; abweichende Angaben begründen; Import eines Teils ändert nicht still den Umfang des anderen |
| Fristen und Erinnerungen | Je zuständiger Führungskraft und Teil; offene Erinnerungsentwürfe bleiben auch nach einem Wechsel über die ursprünglichen Teile verknüpft |
| Historie | Alte Dateien, Dokumentverantwortung, Versandstände und Zuordnungsgründe bleiben erhalten |
| Feedback | Temporäre MD-Vertretung ändert die reguläre Feedback-Zuordnung nicht; reine Vertretung erhält keine automatisch umgehängte Feedbackvorlage |

Ein offener Outlook-Vorgang verhindert einen zweiten Vorgang für denselben
Gesprächsteil auch über die verschiedenen Versandwege hinweg. Ein anderer Teil
kann separat vorbereitet und versandt werden. Bereits angelegte Entwürfe werden
durch eine neue Zuständigkeit weder gelöscht noch als versandt ausgewiesen.

Bei offenen Erinnerungen muss HR den tatsächlichen Outlook-Stand prüfen und
begründet dokumentieren: unversandten Entwurf gelöscht oder tatsächlich
verschlüsselt versandt. Der gespeicherte Vorgang bleibt erhalten. Ein Klick
ersetzt keine externe Handlung. Die bestehende globale Erinnerungssperre bei
ungeprüften PDF-Rückläufen bleibt erhalten; ungeklärte neue PDF-Eingänge werden
ebenfalls berücksichtigt.

## Erhalt bestehender Funktionen und Daten

Die additive Migration `003_part_consumers.sql` ergänzt eine Abfragesicht über
bestehende Verpflichtungen, einen Index und den Nachweis zur Klärung offener
Erinnerungen. Fall-, Dokument- und Versand-IDs werden nicht neu erzeugt. Die
Migrationen 001 und 002 bleiben unverändert. Der Migrationstest vergleicht
bestehende Fälle, Verpflichtungen, Zuordnungen und Erinnerungen vor und nach dem
Update und einem erneuten App-Start.

Die ältere HTML-Arbeitsmappe bleibt für Fälle ohne Teilzuordnung nutzbar.
Sie kann getrennte Zuständigkeiten nicht darstellen: Sobald solche Zuordnungen
vorliegen, werden betroffene neue HTML-Ausgaben, Aktualisierungen und Sendungen
mit einem konkreten Hinweis auf Word gestoppt. Vorhandene Dateien und ihre
Historie bleiben erhalten. Frühere PDF-Rückläufe dürfen keine getrennten Teile
durch eine pauschale Umfangsänderung aufheben.

Die Erweiterung verwendet weiterhin `MD_HR_GOAL_WORKFLOW=1`; bei einer bisher
nicht migrierten Installation ist die Funktion standardmässig ausgeschaltet.
Ein späteres Ausschalten des Menüs entfernt keine bereits migrierten Daten und
setzt keine gespeicherte Verantwortung zurück.

## Prüfungen

- Vollständiger Regressionstest vor den letzten Ergänzungen: **269 bestanden**.
- Ergänzende Ablauf-, Start- und Mengenprüfung: **18 bestanden**. Darin enthalten
  sind getrennte Empfänger, Teilfehler, alte offene Entwürfe, Fristen,
  Rücklaufzuordnung, SAP-Synchronisierung, Migration und gesperrte reale Aktionen.
- Anschliessend ergänzt, noch nicht vollständig nachgetestet: Jahresfilter für
  bestehende manuelle Fallzeiträume, Vorrang gespeicherter Teilzeiträume bei
  später abweichenden Anstellungsdaten, Seitenumfang/Verlaufshinweise und
  verständliche Beschriftungen der Versandänderungen. Entsprechende fachliche
  Assertions sind in `tests/test_part_consumers.py` ergänzt.
- Mengenbestand: 1000 Personen, fünf Jahre, 10’500 Teile und 10’000
  Zielquellenversionen. Gemessen vor der letzten Ergänzung: Gesprächsteilliste
  0,039 s, gezielte Suche 0,034 s. Das ist eine lokale Messung, kein
  Leistungsversprechen für das produktive Gerät.

**Offener Abschlusscheck:** Die automatische Freigabeprüfung stoppte den
abschliessenden Lauf wegen einer gemeldeten externen Visual-Studio-
Telemetrieverbindung mit unbekanntem Inhalt. Auch ein erneuter Versuch mit
gesperrten Python-Netzwerkzugriffen und Unterprozessen sowie deaktiviertem
pytest-Plugin-Autoload wurde wegen derselben Verbindung abgelehnt. Beide Läufe
werden nicht als bestanden gezählt; die Herkunft der Verbindung ist nicht
geklärt. Es wurden keine weiteren Testversuche gestartet. Der Entwurf bleibt
bis zum vollständigen Nachtest ausdrücklich in Prüfung.

Echte Word-Vorlagen, S/MIME/Outlook und die Darstellung im HR-Browser wurden für
C noch nicht manuell geprüft. Tests verwenden synthetische Vorlagen, isolierte
Datenbanken und Testadapter; sie bestätigen keine reale Zustellung.

## C im isolierten Übungsbestand ansehen

`HR_TEST_AB.bat` kann weiterhin verwendet werden. Ein Neustart erzeugt einen
frischen synthetischen Bestand; alte Übungsdateien bleiben liegen. Ein bereits
laufender Server übernimmt die neue Version nicht automatisch.

1. **Gesprächsteile** öffnen und nach Lena Meier suchen. Beide Teile vergleichen.
2. Beim Ausblick **Zuständigkeit / Verlauf** öffnen, Luca Winter suchen, Zeitraum
   und OE-Quelle auswählen und mit einer Testbegründung speichern.
3. Zur Auswahl zurückkehren: Rückblick und Ausblick zeigen unterschiedliche
   Zuständigkeiten. Bei Bedarf mit dem Jahr des gewählten Zeitraums suchen.
4. **Formulare nach Empfänger vorbereiten** öffnen und beide Teile auswählen.
   Zwei getrennte Ausgaben und die Empfänger prüfen.
5. Die erzeugten Dateien vergleichen. Der Rückblick darf durch die Änderung des
   Ausblicks weder seinen Empfänger noch seinen Zeitraum verlieren.

Echte Outlook-Aufrufe, Postfachzugriff und externe Übergaben bleiben im Starter
gesperrt. Diese Bedienfolge ist eine Anleitung, kein bereits bestätigtes Ergebnis.

## Danach

Als nächste Lieferung folgt **D: SAP-Vorschau und fortlaufende unterjährige MDs**.
Die bisherige automatische Deaktivierung/Synchronisierung und Kampagnenbarrieren
sind damit noch nicht ersetzt. E (Rücklaufautomatik und Scan-/Unterschriftenregeln)
und F (gesamte Oberfläche, Feedback, Auswertung und Übergaben) bleiben offen.

Die offene externe Dossierkorrektur bedeutet konkret: Wurde ein altes PDF schon
ausserhalb der App abgelegt, belegt die neue Datei in der App noch nicht, dass
das externe Dossier berichtigt wurde. Wer dies bestätigt und welcher Nachweis
genügt, ist erst vor Freigabe genau dieses Abschlusses festzulegen. Dieser
Sonderabschluss bleibt gesperrt; er blockiert C nicht.

Kein Merge nach `main`, keine produktive Migration, keine echte Nachricht und
keine externe Dossieränderung durch diese Lieferung.
