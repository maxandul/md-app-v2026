# Entwurf D: SAP-Abgleich und fortlaufende Dialoge

Stand: 28. Oktober 2026. Branch: `feat/hr-sap-abgleich-d`.
Basis: geprüfte Etappe C bei `b94616781afabd572d6e113dc3c128a73d4242f5`.

**Status: implementierter Review-Entwurf, noch kein bestandener D-Abschlusslauf.**
Der erneute D-Testlauf am 28. Oktober wurde nach der Zustimmung zu allen
Etappen gestartet. Beim Abruf des weiteren Ergebnisses lehnte die automatische
Freigabeprüfung die Fortsetzung wegen einer gemeldeten externen
Visual-Studio-Telemetrieverbindung mit unbekanntem Inhalt erneut ab. Sie verlangt
ausdrückliche Zustimmung zu dieser externen Datenübertragung. Danach wurde
kein weiterer Testlauf gestartet. Ein vollständiges Ergebnis liegt nicht vor;
die 269 erfolgreichen C-Tests sind kein Nachweis für diese Änderungen.

## Ausgangsproblem und neue Arbeitsweise

Der bisherige Import überschrieb Stammdaten unmittelbar und deaktivierte im
Export fehlende Personen. Die anschliessende Durchlaufsynchronisierung konnte
Fälle aufheben oder neu erzeugen. Ein weiterer Dialog mit derselben Person,
Anstellung und Führungskraft im selben Jahr war durch einen Datenbankindex
ausgeschlossen. Bestimmte Rückläufe und Nachträge verlangten ein Wiederöffnen
der Kampagne.

Der Einstieg **Stammdaten** führt im aktivierten HR-Ablauf zur Vorschau. Ein
Upload speichert den Export und seinen Vergleichsstand, ohne vorhandene
Stammdaten oder MDs zu ändern. Die bekannte SAP-Klassifizierung wird dazu nur
in einer isolierten Datenbank im Arbeitsspeicher ausgeführt. Zusätzliche
Prüfungen halten widersprüchliche Führungskräfte, OE/Funktionen, fehlende
Anstellungsnummern und ungültige Datumsangaben zurück. Unformatierte Zahlen in
Datumsfeldern gelten als unklar; sie werden nicht als Kalenderdatum interpretiert.

| Schritt | Wirkung |
|---|---|
| Vorschau erstellen | Original, bisherige und neue Angaben sowie Struktur-/Vollständigkeitshinweise speichern |
| Person öffnen | Änderungen und betroffene Dialoge als mitarbeitende Person oder verantwortliche Führungskraft sehen |
| Personen auswählen | Konkrete Auswahl vor Ausführung zeigen; nur angekreuzte Zeilen, keine versteckte Auswahl aller Treffer |
| Stammdaten übernehmen | Ausgewählte Personen übernehmen; fehlende Personen/Anstellungen erhalten; keine MD-Pflichtentscheidung |
| Dialog-/Formularfolgen prüfen | Direkt zu Zuständigkeit, vorhandenen Rückläufen, Word-Ausgabe oder neuer Dialoganlage wechseln |
| Entscheidung dokumentieren | Beibehaltung, erneuten Vergleich oder abgeschlossene Folgeprüfung mit Grund, Benutzer und Zeitpunkt festhalten |

Die Übernahmeeinheit ist bewusst **eine Person mit allen im Export enthaltenen
Anstellungen**: Name, E-Mail und Anrede werden gemeinsam geführt. Widersprüche
innerhalb dieser Einheit werden zuerst im Export geklärt. Andere zulässige
Personen können separat übernommen werden. Fehlende Anstellungen werden nicht
entfernt. Die Bestätigung nennt den Umfang vor der Übernahme.

Die Änderungsliste wird serverseitig nach Person/Personalnummer und Art/Stand
gefiltert und mit 25 Zeilen je Seite dargestellt. Suche, Seite und Auswahlkontext
bleiben beim Öffnen einer Person und bei der Rückkehr erhalten. Vorschauen,
übernommene Daten und noch offene MD-Folgen sind getrennt erkennbar. Die
Arbeitsübersicht verweist auf dieselben Einträge; sie führt keinen zusätzlichen
Erledigt-Status.

## Daten- und Entscheidungserhalt

- Die Übernahme schreibt Stammdaten in einer Transaktion. Veraltete
  Vergleichsstände, veränderte Originaldateien und Konflikte verhindern die
  Übernahme der betreffenden Auswahl. Ein Fehler rollt diese Auswahl zurück.
- Identische Dateien und inhaltlich identische Exporte werden wiedererkannt.
  Ein bereits übernommener Eintrag erzeugt keinen zweiten Import. Ein neuer
  unveränderter Vergleich schliesst keine noch offene MD-Folgearbeit.
- Bereits vorhandene Teilzeiträume, Zuständigkeiten und Formular-OE werden vor
  einer Stammdatenänderung gesichert. Diese Sicherung ist als `preserved`
  gekennzeichnet und wird nicht als neue manuelle Fachentscheidung ausgegeben.
  Ausdrückliche Teilzuordnungen bleiben unverändert.
- Neue SAP-Führungszuordnungen sind Beobachtungen ohne behaupteten
  Wirksamkeitszeitraum. Importdatum und Eintrittsdatum werden nicht als Beginn
  einer Führungskraftzuordnung ausgegeben. Historische unbekannte Angaben
  werden nicht nachträglich erfunden.
- Übernommene Auswahlstände tragen einen Hinweis auf die Teilauswahl. Die
  dazugehörige Führungslinienübersicht enthält den weiterbestehenden Bestand
  und die geprüften Änderungen; sie behauptet keinen vollständigen neuen
  SAP-Gesamtabgleich. Bestehende Jahresfälle werden damit nicht synchronisiert.
- Fehlender Datensatz, tatsächliches Austrittsdatum, MD-Pflicht und gewünschte
  Folgeaktion bleiben verschiedene Sachverhalte. Es wird niemand aufgrund
  seines Fehlens im Export deaktiviert.

Die Stammdatenübernahme nutzt dieselbe Sperre wie der Outlook-Versand. Sie
versendet keine Nachricht und ersetzt keine externe Dossierdatei. Die alten
Import- und Synchronisierungswege können die Vorschau bei migrierten Daten
nicht umgehen. Die bisherige Importhistorie bleibt erreichbar.

## Unterjährige Dialoge

Manuell bestätigte Ereignisse erhalten auch ohne bereits eröffneten
Jahresdurchlauf einen verarbeitbaren Fall. Die App ordnet sie dem passenden
Jahr zu und legt bei Bedarf nur den notwendigen Jahresrahmen an, ohne weitere
Personen automatisch zu verpflichten. Ein abgeschlossener Kampagnenstatus
bleibt dabei erhalten und sperrt weder neue Ereignisse noch vorhandene
Rückläufe und Feedbacknachträge.

Mehrere fachlich unterschiedliche Gespräche derselben Person im selben Jahr
sind möglich. Eine identische wiederholte Anlage verweist auf das bestehende
Ereignis. Word-Dateien enthalten einen eindeutigen Fallbezug; die SAP-Auswahl
eines bestehenden Rückblicks wird durch ein zusätzliches manuelles Ereignis
nicht still zurückgesetzt. Neue manuelle Rückblicke werden nicht automatisch
zur SAP-massgeblichen Beurteilung erklärt.

Die Dialogübersicht zeigt im HR-Modus standardmässig alle Jahre. Offene Teile
anderer Jahre bleiben zusätzlich aus der Arbeitsübersicht erreichbar.

## Migration und technische Grenzen

Migration `004_sap_staging.sql` ergänzt Vorschauen, Entscheidungen und
Stammdatensnapshots. Sie erweitert Teilzuordnungen um ihre Herkunft. Um mehrere
Gespräche zu ermöglichen, muss die Falltabelle innerhalb einer Transaktion
ohne den bisherigen zusammengesetzten Eindeutigkeitszwang neu aufgebaut
werden. Alle bestehenden IDs, Spalten und Referenzen sowie der Zähler für
künftige IDs werden übernommen. Die Migration prüft die Fremdschlüssel vor
dem Commit und stellt deren Erzwingung anschliessend wieder her. Die bereits
veröffentlichten Migrationen 001–003 bleiben unverändert.

Dieser Tabellenumbau benötigt vor Produktivbetrieb einen erfolgreichen
Migrationstest und den bereits geforderten Sicherungs-/Wiederherstellungsnachweis.
Eine produktive Migration wurde nicht ausgeführt. Das Abschalten der
HR-Oberfläche ist weiterhin kein Datenbank-Rollback.

## Prüfstand und Wiederaufnahme

Für D wurden in `tests/test_sap_staging.py` 22 Ablaufprüfungen ergänzt:
Vorschau ohne Nebenwirkungen, Dubletten, Auswahl, Konflikte, fehlende Personen
und Anstellungen, alte MD-Zuordnungen, veraltete Vergleiche, Rollback,
Folgeentscheidungen, Quellenänderung, geschlossene Kampagnen, zusätzliche
Ereignisse, eindeutige Dateien, geschützte Routen und Erhalt bestehender
Dokumentverknüpfungen bei der Migration sowie unformatierte numerische Datumswerte.

Die ersten Testversuche fanden Anpassungsbedarf am bisherigen
Migrationsvergleich (die neue Herkunftsspalte) und an einem Testdatensatz mit
fehlender Anstellungsnummer. Beides wurde korrigiert. Der anschliessende Lauf
wurde durch die automatische Freigabeprüfung abgelehnt. Auch der erneute
Versuch am 28. Oktober lieferte vor der erneuten Ablehnung nur Fortschrittsausgabe,
kein vollständiges Testergebnis. Spätere Ergänzungen wurden nur statisch geprüft.
Python- und Jinja-Syntax sowie `git diff --check` sind fehlerfrei; das ersetzt keine
Ablauf- oder Migrationsprüfung.

Nach Freigabe zunächst D und betroffene A/B/C-Abläufe ausführen, Fehler beheben
und anschliessend die vollständige Testsammlung laufen lassen. Der bestehende
lokale Prüfstarter begrenzt Python-Netzwerkzugriffe und Unterprozesse und
deaktiviert zusätzliche pytest-Plugins. Die gemeldete Verbindung trat dennoch
auf; ihre Herkunft ist ungeklärt. Die statische Suche in App- und Testquellen
fand keine Visual-Studio-/Telemetrieanbindung. Die nachträgliche Abfrage aktiver
HTTPS-Verbindungen und entsprechender DNS-Einträge lieferte keine Zuordnung.
Beides ist kein Nachweis, dass die gemeldete Verbindung harmlos oder unterbunden ist.

## Isolierte Bedienfolge nach erfolgreichem Nachtest

`HR_TEST_AB.bat` erzeugt weiterhin ausschliesslich neue synthetische Daten.
Der Starter enthält zusätzlich eine D-Vorschau mit Lenas Wechsel, einer neu
eingetretenen Person und einem fehlenden Datensatz. Bestehende Testbestände
werden nicht ersetzt. Ein bereits laufender Server muss für neuen Code neu
gestartet werden; das wurde nicht automatisch getan.

1. **Stammdaten** öffnen und die D-Übung auswählen.
2. Lena öffnen und alte/neue SAP-Angaben mit den unveränderten MD-Teilen
   vergleichen. Den fehlenden Datensatz separat ansehen.
3. Nur Lena auswählen, Umfang prüfen und mit Testbegründung übernehmen.
   Der alte Rückblick bleibt bestehen; eine Ausblickzuordnung erfolgt erst
   durch die ausdrückliche Entscheidung bei diesem Teil.
4. Über **Dialogbedarf prüfen / Ereignis erfassen** einen weiteren Dialog mit
   explizitem Anlass und Zeitraum anlegen und dessen Word-Ausgabe prüfen.
5. Zur SAP-Folgeprüfung zurückkehren und das tatsächliche Ergebnis dokumentieren.

Dies ist eine Prüfanleitung, keine bereits bestandene Bedienprüfung. Reale
Outlook-Aufrufe, Postfachzugriff und externe Übergaben bleiben im Starter gesperrt.

## Weitere Etappen

Die Codeprüfung für E am 28. Oktober zeigt folgende zusammenhängende Änderungen:

| Befund im aktuellen Code | Erforderliche Änderung in E |
|---|---|
| `word_pdf_imports.confirm_import` setzt Scanpflicht nur am Rückblick D/E | Pflicht aus dem Rückblick auf beide zugehörigen Teile ableiten, auch bei späterem Eingang |
| `documents.import_handwritten_scan` erlaubt nur Rückblicke und verlangt zuerst ein digitales PDF | Datenquelle und Unterschriftennachweis getrennt verknüpfen; validierten Scan als alleinige Quelle zulassen |
| Scanimport speichert sofort `signature_checked=True` und stellt bereit | Upload, konkrete Sichtprüfung beider Unterschriften und technische Übergabe trennen |
| `db.init_db` entfernt offene Scanpflicht bei Nicht-Rückblicken | Alte Startkorrektur für das neue Modell ablösen, bestehende Nachweise und wiederholten Start prüfen |
| `confirm_digital_signature` vermischt Freigabe und Dateikopie | Fachliche Übernahme erhalten, technische Übergabe wiederholbar ausführen, keine erneute Sichtprüfung allein wegen Kopierfehler |
| Outlook-Eingangsmodell enthält keinen Nachrichtentext | Zusätzliche Mailanliegen nicht aus erfolgreichen Anhängen als ausgeschlossen behandeln |

Das ist eine Codeprüfung und noch keine Umsetzung oder Abnahme von E. In den
Repository-Verzeichnissen `tests` und `templates` liegen keine repräsentativen
Rücklauf-PDFs oder Scans; synthetische Parserprüfungen allein belegen keine
Formatfreigabe für produktive Rücklaufautomatik. Die Vorbereitung des
Versions-/Prüfmodells kann unabhängig davon erfolgen. Die Aktivierung der
Automatik bleibt an nachgewiesene Formatvalidierung gebunden.

E (validierte Rücklaufautomatik und selektive Scan-/Unterschriftenprüfung) und
F (Konsolidierung, Feedback, Auswertung und Übergaben) bleiben offen. Auch die
exakte Pflicht-/Zeitraumsmatrix und externe Korrekturabschlüsse sind durch D
nicht entschieden. Unterjährige Pflicht und Zeitraum werden ausdrücklich
bestätigt; dafür wird keine neue Automatik erfunden.

Kein Merge nach `main`, keine produktive Migration und keine echten Nachrichten.
