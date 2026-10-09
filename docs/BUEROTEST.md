# Bürotest – Word/PDF

Stand: 9. Oktober 2026. Testbranch: `plan-b-word-pdf`.
Die [früheren Arbeitsmappen-Tests](historisch/BUEROTEST.md) sind keine Anleitung
für diesen Ablauf. Mit isolierten Testdaten und einem Testempfänger arbeiten.

## 1. Einrichtung und Zugriff

1. Branch als ZIP herunterladen und entpacken. Bestehende Datenbank, lokale Konfiguration und Vorlagen bei Updates erhalten; vorher sichern.
2. Abhängigkeiten gemäss Projektinstallation einrichten. Word-Konfiguration unter `instance/word_config.json` und Organisationskonfiguration unter `instance/organisation.json` prüfen.
3. App starten und persönliches Konto verwenden. Unter Administration Rechnername, Bindung und Port kontrollieren.
4. Für bereits eingerichteten Netzwerkbetrieb den vollständigen Rechner-/DNS-Namen von einem zweiten HR-PC testen, z. B. mit `Resolve-DnsName RECHNERNAME` und anschliessend im Browser mit dem richtigen Port. DNS-Aktualisierung mit der IT klären.
5. Den geprüften Link als `PUBLIC_BASE_URL` hinterlegen, neu starten und unter Administration prüfen. Die Einstellung ändert keine Bindung und keine Firewall.
6. Prozessbackup sowie Vorlagen und Konfiguration separat sichern. Wiederherstellung nur in isolierter Testumgebung prüfen.

## 2. Stammdaten und Durchlauf

SAP-Testexport unter Stammdaten importieren. Personen, Anstellungen, direkte
Führungslinien und Konflikte stichprobenartig prüfen. Durchlauf eröffnen, Jahre und
Fristen prüfen. Pflichtumfang und unterjährige Ereignisse kontrollieren.

## 3. Word-Erzeugung

Einzelperson, Führungslinie und Sammelauswahl testen. ZIP herunterladen und in Word
öffnen. Namen, Personalnummern, Anstellungen, Zeiträume und Nebenbeschäftigungen
prüfen. Vorjahresziele mit mehreren Zeilen und mehreren Zielen pro Kompetenz
prüfen. Probezeitfall mit eigener Vorlage prüfen. Leere Felder müssen bearbeitbar
bleiben. Nach nachgereichten Zielen neu erzeugen: neue Ausgabe enthält sie, alte
Ausgabe bleibt unverändert. Fehler einer fehlenden Vorlage muss verständlich sein.

## 4. Versand

Unter Versand eigenen Anhang je Test-Führungskraft prüfen. Zunächst Outlook-Entwurf
erstellen. Empfänger, Absender, Inhalt, richtigen Anhang und S/MIME in klassischem
Outlook prüfen. Ein Entwurf zählt noch nicht als Versand. Erst nach manuellem
Versand bestätigen. Veraltete Pakete müssen gesperrt werden. Fehlgeschlagene oder
abgebrochene Vorgänge zuerst in Outlook klären; nicht unkontrolliert wiederholen.

## 5. PDF-Rücklauf

1. Rückblick und Ausblick ausfüllen und jeweils über «Speichern als PDF» und «Drucken als PDF» ausgeben.
2. Unter Rückläufe einlesen. Original öffnen und alle erkannten Angaben vergleichen; Person, Anstellung, Zeitraum, Fall und Umfang ausdrücklich prüfen.
3. Fehlende Angaben ergänzen; leere Antworten nicht als «Nein» behandeln. Vorjahresziele nicht als aktuelle Kompetenzbesprechung zählen.
4. Übernehmen und Fallprüfung öffnen. Unterschriften bestätigen; lokale Dossierübergabe und Original-Zugriff prüfen.
5. Scanpflicht-Fall testen: vor Scan keine endgültige Ablage; nach geprüftem Scan korrekte Übergabedatei.
6. Dublette, korrigierte Version vor Freigabe und Ersatzversuch nach Freigabe testen. Bereits bereitgestellte Belege dürfen nicht automatisch ersetzt werden.
7. Nur Rückblick nicht durchgeführt, nur Ausblick nicht durchgeführt und beide nicht durchgeführt testen. Anderer Pflichtteil bleibt gegebenenfalls offen.
8. Nachgereichten Ausblick als Zielquelle übernehmen; erneute Word-Ausgabe prüfen.
9. Testmail mit nur MD-Anlagen sowie gemischten Anlagen einlesen. Word-PDFs müssen zunächst in die Prüfwarteschlange gelangen; Mailprüfung ist von Ablagefreigabe getrennt.

## 6. Abschluss und Export

Auswertungen einschliesslich offener Antworten und Zeichenanzahlen prüfen.
Vollständigen Fall als SAP-Batch exportieren; erneuter Export darf ihn nicht erneut
aufnehmen. Bestehenden Batch erneut herunterladen. SAP-Import und Dossier-RPA mit
den zuständigen Stellen kontrollieren. Der Export wartet derzeit auf den gesamten
Fall, gegebenenfalls inklusive Ausblick. Durchlauf schliessen und begründete
Nachbearbeitung testen.

## Abnahmeprotokoll

Je Schritt Erwartung, Ergebnis, Dokumentbeispiel und Fehler festhalten. Browser,
Word-Version, Exportweg und Outlook-Version notieren. Offene Grenzen und bekannte
Befunde stehen in [ABLAUFPRUEFUNG_WORD_PDF.md](ABLAUFPRUEFUNG_WORD_PDF.md).


## Ergänzende Ausnahmefälle und Stellvertretung

1. Als neue HR-Person Hilfe und Einrichtung öffnen; fehlende Voraussetzungen und Zuständigkeiten müssen verständlich sein.
2. PDF hochladen: Arbeitsliste zeigt den Eingang. Entwurf speichern, Seite verlassen und wieder öffnen; Werte und Zuordnung vergleichen.
3. Dieselbe Prüfung in zwei Fenstern öffnen, eines speichern und danach das andere: veralteter Stand darf den neueren nicht überschreiben.
4. Falschen Eingang begründet zurückstellen, über den Filter finden und begründet wieder öffnen. Keine Fachdatenübernahme durch Entwurf oder Zurückstellung.
5. Mehr als 100 Eingänge mit synthetischen Dateien prüfen: alle über Suche/Seitennavigation erreichbar.
6. Eingegangenes PDF übernehmen: Unterschriftenaufgabe erscheint. Eine reine HR-Prüfung darf keine Erinnerung auslösen. Offener PDF-Eingang pausiert Erinnerungen.
7. Manuelles Ereignis ohne Durchlauf zuordnen; bei bestehendem Fall derselben Führungslinie verständliche Konfliktmeldung. Fehlanlage ohne Belege aufheben.
8. Nachzügler auf inaktiven Fall begründet übernehmen; Fall bleibt inaktiv. Geschlossenen Durchlauf vorher wieder öffnen.
9. Alten DOCX-Ausblick mit Vorschau importieren; mehrere Zielquellen vergleichen und auswählen. Ändert sich eine Quelle, muss die Auswahl erneut geprüft werden.
10. Nur in isolierter Testumgebung: abgebrochenen Outlook-Vorgang nach tatsächlicher Outlook-Prüfung klären. Kein zusätzlicher Versand; laufender Vorgang bleibt gesperrt.
11. Unerreichbare Testablage: verständliche Hilfe und gespeicherten Status prüfen, nach Fehlerbehebung ohne doppelte Ablage weiterarbeiten.
12. Abschluss ohne externe Prüfung ablehnen; bei Restfällen Grund und zuständige Person verlangen. Folgejahr eröffnen und Zielübernahme prüfen.

Aktuelle Anleitung und verbleibende Grenzen: [HR_BETREUUNG.md](HR_BETREUUNG.md).
