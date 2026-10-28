# Etappe F: zusammenhängende HR-Übersichten

Branch: `feat/hr-uebersicht-f`; Basis: getestete Etappe E1.
Stand: 28. Oktober 2026. Automatischer Nachtest dieses Branches läuft noch.

Die HR-Startseite führt zur Arbeitsübersicht über alle Jahre. Arbeit, Mitarbeitende,
Führungskräfte, Stammdaten und Auswertungen bilden die Hauptnavigation. Eingänge,
Versand, Ziele, Feedback, Übergaben und Durchläufe bleiben direkt erreichbar.
Bestehende Fachseiten und gespeicherte Originale bleiben erhalten.

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

## Validierung

16 neue Prüfungen vorbereitet: Navigation/HTTP, bestehende Daten, getrennte
Verantwortung, Altjahre, Verlauf, Rücklauf-/Zielstatus, Feedback-Nachtrag,
Originalbündel, CSRF, Rückkehr zur Liste, Suchparameter, Auswertung und Zugriff.
Mengenfall: 1000 synthetische Mitarbeitende, fünf Jahre und 10000 Gesprächsteile.
Messungen im CI-Lauf sind kein Leistungsnachweis auf dem vorgesehenen HR-Rechner.

Visuelle Bedienabnahme und Windows-Lastmessung stehen aus. E2 (repräsentative
Formular-/Scanvalidierung und automatische Annahme geeigneter Varianten) bleibt
offen. Kein Merge nach main und keine produktive Migration oder externe Aktion.
