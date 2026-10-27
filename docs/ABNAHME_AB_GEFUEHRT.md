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
ausgeführt; eine erfolgreiche Live-Browserprüfung wird noch nicht behauptet.

## Abnahmeprotokoll

Noch keine fachliche oder visuelle Abnahme behauptet. Zu jedem gemeinsam
durchgeführten Schritt festhalten: Datum, getesteter Commit, Ergebnis,
Unklarheiten, notwendige Änderung und erneute Prüfung.

Kein Merge nach `main` und keine produktive Migration durch diesen Probelauf.
