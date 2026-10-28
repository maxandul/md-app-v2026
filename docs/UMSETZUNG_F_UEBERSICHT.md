# Etappe F: zusammenhängende HR-Übersichten

**Fortschreibung:** Das vollständige Testpaket mit E2, aktueller Gesamtprüfung und
Startanleitung steht in [E2](UMSETZUNG_E2_RELEASE.md) und
[Neue HR-Version starten](START_NEUE_HR_VERSION.md). Die folgenden Nachweise
beschreiben den F-Zwischenstand.

Branch: `feat/hr-uebersicht-f`; Basis: getestete Etappe E1.
Stand: 28. Oktober 2026. Automatisierter Prüfstand siehe unten; visuelle Bedienabnahme offen.

Die HR-Startseite führt zur Arbeitsübersicht über alle Jahre. Arbeit, Mitarbeitende,
Führungskräfte, Stammdaten und Auswertungen bilden die Hauptnavigation. Eingänge,
Versand, Ziele, Feedback, Übergaben und Durchläufe bleiben direkt erreichbar.
Bestehende Fachseiten und gespeicherte Originale bleiben erhalten. Die bisherige
Durchlaufplanung ist unter «Durchläufe planen und Einrichtung» bzw. `/?view=cycles`
weiter erreichbar.

Die neuen Listen suchen, zählen, sortieren und paginieren in SQLite mit 25/50/100
Zeilen. Aufgaben sind abgeleitete Ansichten bestehender Quellen, Gesprächsteile,
Prüfstände und Sammlungen. Sie haben keinen zusätzlichen Erledigt-Schalter.
Offene Altjahre sind ohne Jahresfilter sichtbar. Warten auf Rückmeldung beruht
auf dem dokumentierten Zustand; ein fehlendes Dokument allein ist keine erfolgte
Nachforderung.

Personen zeigen Anstellungen und Gesprächsteile über die Jahre. Führungskräfte
sehen die tatsächliche Zuständigkeit je Teil. Feedback bleibt eigenständig seiner
Führungskraft und seinem Durchlauf/Rückblickjahr zugeordnet. Gleiche Jahre aus
unterschiedlichen Durchläufen werden sichtbar unterschieden. Die Bündelung ist
weiterhin manuell; bestehende Bündel und Nachträge sind paginiert herunterladbar.
Es entstehen keine Feedback-Pflichtdokumente und keine automatische Mahnung.

Die Übergabenansicht trennt Nachweis-/Bereitstellungsbedarf von lokal abgelegten
Dateien und verweist getrennt auf SAP-Export und Durchlaufabschluss. Sie behauptet
keine bestätigte externe Dossier- oder SAP-Verarbeitung. Die Auswertung ergänzt
den operativen Arbeitsstand je Gesprächsteil und hinterlegter Formular-OE;
bestehende fachliche Auswertungen und Anonymisierungsschwellen bleiben erhalten.

## Geführte lokale Prüfung

`HR_TEST_AB.bat` bzw. `python review_hr_ab.py` startet nach Synchronisierung dieses
Branches eine neue, isolierte Testumgebung. Einstieg ist `/arbeit`. Die fünf
Zielnachreichungen bleiben erhalten. Für Alex Huber sind zusätzlich ein Rückblick D
und ein Ausblick samt getrennten, ausdrücklich fiktiven Testnachweisen vorbereitet.
Die offenen Kopien lassen sich auf der Rücklaufseite zuordnen, prüfen und in den
neuen Testordner bereitstellen. Das ist keine Prüfung echter Unterschriften.

Der Starter verwendet ausschliesslich ein neu angelegtes Verzeichnis. Outlook,
Postfachzugriff und produktive Übergaben bleiben gesperrt. Ein neuer HTTP-Test
belegt für beide Teile, dass die Kopie innerhalb dieses Testverzeichnisses bleibt;
eine vorgegebene externe Ablage wird nicht angelegt. Bestehende Verzeichnisse
werden beim Start weiterhin abgelehnt. Die bisherige lokale Sitzung wurde nicht
aktualisiert, weil die Arbeitsumgebung während der Umsetzung getrennt wurde.

## Validierung

[Erfolgreicher isolierter CI-Lauf](https://github.com/maxandul/md-app-v2026/actions/runs/40663467318)
auf `8476baa8331dc25058ca70e2fe6f3b4bfc10aff1`: **329 Python-Tests, 44 Unterprüfungen und
8 JavaScript-Tests bestanden**. Der Python-Lauf dauerte 61,63 Sekunden. Nach
diesem Nachweis wurde ausschliesslich Dokumentation ergänzt.

Der Umfang umfasst `tests`, die 22 bestehenden Python-Prüfungen unter
`prototype/html_dialog` sowie die Browser-Skriptprüfungen für Aktionsposition,
Versanddownload und Zielimport. Der frühere E1-CI-Nachweis war auf den Ordner
`tests` begrenzt. Die Browser-Skriptprüfungen ersetzen keine visuelle Bedienabnahme.

Die Prüfungen laufen auf einem frischen Ubuntu-Runner ohne lokale HR-Dateien.
Python und JavaScript werden in einem eigenen Linux-Netzwerk-Namensraum mit
leerer Umgebung ausgeführt; der Python-Prozess blockiert zusätzlich Netzwerk-
und Kindprozesse per Audit-Hook.

Im Mengenfall dauerten die beiden paginierten Listenabfragen zusammen **1,012 s**
auf diesem CI-Rechner. Gemessen wurden Personen- und Arbeitsliste mit dem
angegebenen synthetischen Bestand, nicht alle möglichen Aufgabenmischungen.


16 neue F-Prüfungen sowie ein zusätzlicher vollständiger E-Test im geführten
Teststart: Navigation/HTTP, bestehende Daten, getrennte
Verantwortung, Altjahre, Verlauf, Rücklauf-/Zielstatus, Feedback-Nachtrag,
Originalbündel, CSRF, Rückkehr zur Liste, Suchparameter, Auswertung und Zugriff.
Mengenfall: 1000 synthetische Mitarbeitende, fünf Jahre und 10000 Gesprächsteile.
Messungen im CI-Lauf sind kein Leistungsnachweis auf dem vorgesehenen HR-Rechner.

Visuelle Bedienabnahme und Windows-Lastmessung stehen aus. E2 (repräsentative
Formular-/Scanvalidierung und automatische Annahme geeigneter Varianten) bleibt
offen. Kein Merge nach main und keine produktive Migration oder externe Aktion.
