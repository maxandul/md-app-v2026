# Geführte HR-Abnahme A/B

Die technische Prüfung und die fachliche Bedienprüfung werden getrennt
festgehalten. Ein bestandener Test ist keine Bestätigung einer echten Zustellung.

## Start der isolierten Übung

Im Repository `HR_TEST_AB.bat` per Doppelklick oder `python review_hr_ab.py` im Terminal starten und im Browser dieses Geräts
<http://127.0.0.1:5056/arbeit/ziele> öffnen. Der Starter verwendet ausschliesslich
neu erzeugte Testdaten unter `instance/hr-ab-review-…`, liest keine produktive
Organisationskonfiguration und startet keine automatische Postfachprüfung.
Jeder Start legt einen neuen Übungsbestand an; frühere Daten werden nicht
überschrieben. `Ctrl+C` beendet den Server, die Testdateien bleiben erhalten.

Erkennbar ist die Übung am Banner **HR-TEST**. Outlook-Entwürfe, Postfachzugriff
und externe Übergaben sind in dieser Oberfläche gesperrt. Nur Testdateien
verwenden. Die synthetischen Word-Vorlagen demonstrieren den Ablauf; Layout und
Parserqualität der wirklichen HR-Vorlagen sind später separat zu prüfen.

## Schritt 1 – Finden und verstehen

1. Die Liste soll fünf Zielquellen zeigen: Lena Meier, Noah Keller, Mira Steiner,
   Jonas Weber und einen noch nicht zugeordneten Ausblick von Alex Huber.
2. Bei **Lena Meier** auf **Ziele prüfen** klicken.
3. Person, Anstellung, Zieljahr 2025, Herkunft und Originalzugang suchen.
4. Das Original öffnen und den Zieltext **Projekt abschliessen** sowie
   Messkriterien, Weg zum Ziel und Termin mit der Bearbeitungsansicht vergleichen.

Rückmeldung: Ist die nächste Aktion verständlich? Sind Person, Jahr und Original
ohne Erklärung auffindbar? Welche Beschriftung oder Anordnung ist unklar?
Noch keine Sammelausgabe oder Versandbestätigung für diesen ersten Schritt.

## Folgende gemeinsame Schritte

| Schritt | Handlung | Erwartung |
|---|---|---|
| 2 | Zieltext ändern, Entwurf speichern, Seite verlassen und wieder öffnen | Änderung erhalten; Original unverändert; noch keine Freigabe |
| 3 | Am Original prüfen und bestätigen; weitere Quellen prüfen | Vier bestätigte Quellen können unabhängig von der unklaren fünften weiterbearbeitet werden |
| 4 | Bestätigte Quellen auswählen, Rückblicke erstellen und Dateien prüfen | Nur ausgewählte Rückblicke; zwei Empfängergruppen; eindeutige Personen und Anstellungen |
| 5 | Eine Rückblick-Verantwortung ändern | Neue Empfänger-/Formular-OE-Grundlage sichtbar; alte Ausgabe bleibt erhalten und ist für neuen Versand ungültig |
| 6 | Bereits eingegangenen Rückblick und nachgereichte Ziele prüfen | Korrekturklärung statt neuer leerer Vorlage; Entscheidung und späterer neuer Eingang nachvollziehbar |
| 7 | Dieselbe Datei erneut einlesen und Bearbeitung unterbrechen | Derselbe Vorgang mit bisherigen Änderungen, keine doppelte Ausgabe |
| 8 | Separates freigegebenes Windows-/Outlook-Testumfeld | Tatsächliche S/MIME-Entwürfe, Abbruch und Wiederaufnahme prüfen; keine produktiven Empfänger |

Die Schritte 6 und 8 benötigen einen gesondert vorbereiteten Eingangs- bzw.
Outlook-Testfall. Die einfache Startübung behauptet diese Voraussetzungen nicht.

## Review-Fund vom 27. Oktober 2026

Ein als korrigiert abgeschlossener Fall blieb bisher abgeschlossen, wenn später
ein weiterer ungeprüfter Rücklauf hinzukam, solange das zuvor bestätigte Dokument
noch aktuell war. Die Entscheidung ist jetzt nur bei unverändertem vollständigem
Rücklaufstand wirksam. Ein späterer Eingang öffnet die Folgeklärung erneut.
Der automatisierte Korrekturtest prüft diesen Übergang ausdrücklich.

Der isolierte Starter ist zusätzlich automatisiert geprüft: fünf Quellen, eine
offene Zuordnung, gültige Word-ZIP-Struktur, Erstellung und Gruppierung,
gesperrter Outlook-Aufruf, gesperrte alte POST-Aktionen, Loopback-Beschränkung,
keine Postfach-Hintergrundprüfung und kein Öffnen bestehender Datenverzeichnisse.

Die Agentenumgebung verweigert lokale Socket-Verbindungen (Windows-Fehler
10013). Deshalb wird der Browserstart durch den Anwender auf dem eigenen Gerät
ausgeführt. Die unten festgehaltenen Ergebnisse beruhen auf seinen Rückmeldungen,
nicht auf einer visuellen Prüfung durch den Agenten.

## Abnahmeprotokoll

Am 27. Oktober 2026 wurde der synthetische Ablauf gemeinsam durchgegangen.
Bereitgestellter Stand war `08df2c48df4a3700455fc7806ad732c09540248f`;
die Commit-ID des tatsächlich laufenden Browser-Servers wurde nicht unabhängig
ausgelesen. Der Anwender meldete die folgenden Schritte positiv zurück und
schloss mit «ja ich glaub ist alles gut». Das ist eine informelle Bedienprüfung,
keine vollständige fachliche Freigabe oder Bestätigung realer Zustellung.

| Prüfung | Rückgemeldetes Ergebnis |
|---|---|
| Einstieg und Original | Fünf Quellen sichtbar; Angaben und Original bei Lena Meier auffindbar |
| Entwurf und Wiederaufnahme | Zieltext «Projekt abschliessen und Ergebnisse dokumentieren» nach erneutem Öffnen erhalten; Original unverändert |
| Quellenfreigabe | Lena, Noah, Mira und Jonas bestätigt; Alex blieb unzugeordnet |
| Selektive Erstellung | Vier ZIP-Ausgaben erstellt und geprüft, einschliesslich Lenas geändertem Text |
| Vorbereitung | Vier Ausgaben freigegeben und zwei Gruppen vorbereitet: Eva Sommer mit Lena/Noah, Luca Winter mit Mira/Jonas; kein Outlook-Entwurf |
| Erneuter Upload | Dieselbe Lena-Datei führte weiterhin zu fünf Quellen; Bearbeitung und Freigabe blieben erhalten |
| Verantwortung | Änderung bei Lena von Eva auf Luca mit Begründung durchgegangen; positiv, zuletzt vorsichtig bestätigt. Erneute Dateierstellung mit neuer Verantwortung nicht separat bestätigt |

Offen bleiben der vorbereitete Rücklauffall (Schritt 6), reale Vorlagen,
Windows/S/MIME/Outlook (Schritt 8), Darstellung bei anderen Bildschirmgrössen,
Tastaturführung und die neue Rücknahmefunktion.

## Ergänzende Rückmeldung vom 27. Oktober 2026

Der Anwender bestätigt anschliessend ausdrücklich «bedienprüfung i.o.» und
beauftragt die Fortsetzung mit den weiteren Etappen. Die Bedienprüfung A/B wird
damit als akzeptiert geführt. Eine weitergehende Einzelbestätigung realer
Outlook-Zustellung oder aller nachstehenden Sonderfälle wird daraus nicht
abgeleitet. Es ist keine erneute allgemeine Bedienfreigabe für A/B erforderlich.

Die folgende Prüfanleitung bleibt für spätere Wiederholungen erhalten.
Die neue [Lieferung C](UMSETZUNG_C_TEILVERANTWORTUNG.md) dokumentiert ihren eigenen
Umfang, die technischen Nachweise und die noch ausstehende C-Bedienprüfung.

## Prüfanleitung: falsche Freigabe zurücknehmen

Den neuen Code bereitstellen und den isolierten Starter neu starten. Er erzeugt
einen frischen Übungsbestand; bisherige Übungsdateien bleiben erhalten.
Ein bereits laufender Server übernimmt die Änderungen nicht automatisch.

1. Lena bestätigen, eine Ausgabe erstellen, prüfen und eine Versandgruppe
   vorbereiten. Noch keinen Outlook-Vorgang erzeugen.
2. Bei der Zielquelle **Falsche Freigabe zurücknehmen** öffnen. Bisherige Fälle,
   Ausgaben und Versandgruppe vergleichen. Begründung, beispielsweise
   «Test: falsche Person bei der Freigabe ausgewählt», erfassen und bestätigen.
3. Die vorbereitete Gruppe muss als abgebrochen erhalten bleiben; ihre Dateien
   und die ursprüngliche Freigabe bleiben im Verlauf sichtbar.
4. **Quelle neu zuordnen und Ziele prüfen** öffnen. Für diese reine Übung eine
   andere Person oder ein anderes Jahr wählen und wieder bestätigen. Die
   Folgen der alten Zuordnung müssen weiterhin offen sichtbar bleiben.
5. **Folgen der Rücknahme klären** öffnen und für die alte Person entscheiden.
   Nur wenn im Test tatsächlich nichts weitergegeben wurde: «Keine Korrektur
   bisheriger Unterlagen nötig», Begründung erfassen und Prüfung manueller
   Weitergaben bestätigen. Danach muss die alte Folgeaufgabe geschlossen sein.
6. Dieselbe Originaldatei erneut hochladen. Es darf keine zweite Quelle und
   keine Wiederbelebung der zurückgenommenen Freigabe entstehen.

Automatisierte Prüfungen ergänzen diese Bedienprüfung um bereits erstellte
Outlook-Entwürfe, bestätigten Versand, gemischte Gruppen, konkurrierende Quellen,
veraltete Browserstände, Korrekturrückläufe und spätere neue Eingänge.
Nach externer Dossierbereitstellung bleibt der Korrekturabschluss gesperrt,
bis Verantwortlichkeit und Nachweis der externen Übernahme fachlich geklärt sind.

Kein Merge nach `main` und keine produktive Migration durch diesen Probelauf.
