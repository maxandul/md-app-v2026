# Ablaufprüfung Word/PDF – 9. Oktober 2026

Geprüfter Ausgangsstand: `ef41734`, Branch `plan-b-word-pdf`.
Ziel: Fehler und unklare Übergänge vor dem nächsten Windows-Test finden.
Die nachstehend als behoben markierten Punkte sind Bestandteil dieses Commits.

## Methode und Reichweite

- Vollständige bestehende Python-Testsuite: 103 Tests erfolgreich zum Zeitpunkt des Gesamtlaufs, einschliesslich zweier neuer Ablauf-/Einrichtungstests. Anschliessend alle drei neuen Tests erfolgreich, inklusive zusätzlich ergänztem Scan-Ablauf (damit 104 unterschiedliche Python-Tests im aktuellen Bestand).
- Zwei JavaScript-Tests erfolgreich: Download wartet auf vollständige Datei; zurückgeleitete Fehler erscheinen als Fehler und werden nicht als ZIP heruntergeladen.
- Neuer durchgehender HTTP-Test mit isolierter Datenbank und synthetischen Personen: SAP-Import und Durchlauf über Testaufbau; Seiten aufrufen; Word-ZIP erzeugen; Wiederdownload finden; Rückblick und Ausblick hochladen; Prüfmaske absenden; Unterschriften bestätigen; lokale Dossierübergabe; Fall vollständig; SAP-XLSX erzeugen; doppelten Export verhindern.
- Zusätzlicher HTTP-Test für Bewertung D und Scanpflicht: Scan-Aktion erst nach Unterschriftenprüfung, nach Scan-Übergabe keine offene Upload-Aktion mehr.
- Die freigegebenen regulären Rückblick-/Ausblickvorlagen wurden zusätzlich mit synthetischen Stammdaten und Vorjahresziel erzeugt; ZIP und beide DOCX vorhanden. Keine erneute visuelle Word-Layoutabnahme in diesem Durchgang.
- Beide gelieferten Microsoft-PDFs erneut verglichen: jeweils sechs Leistungsziele, vier Entwicklungsziele, keine aktuellen Einschätzungen. Zielinhalte ohne geometrische Herkunftsangaben identisch.
- Gerenderte HTML-Seiten, Formulare, Dienste und Hilfetexte geprüft. Ein echter visueller Browser-Klicktest war nicht möglich: kein Browser installiert, Browserdownload fehlgeschlagen. JavaScript-Tests verwenden ein simuliertes DOM.
- Keine echten E-Mails, Outlook-Entwürfe, produktiven Datenbankänderungen, Netzlaufwerkablagen oder SAP-Importe ausgeführt. Outlook ist durch Testadapter abgedeckt. Die Dossierübergabe wurde ausschliesslich in einem temporären lokalen Ordner geprüft.

## Gefunden und behoben

| Stelle | Feststellung | Korrektur |
|---|---|---|
| Einrichtung | Fehlende Vorlagen wurden genannt, aber Standarddatei und relative Pfade waren direkt im Cockpit nicht erklärt. | Gemeinsame Einrichtungshilfe auf Versand und Führungslinie, inklusive `instance/word_config.json`, Schlüsselübersetzung und Pfadbeispiel. |
| Führungslinie nach Download | Kein dauerhafter Wiedereinstieg zum zuletzt erzeugten Word-Paket; Verlauf zeigte nur HTML-Dateien. | Letzte fünf Führungslinienpakete mit Wiederdownload; direkte Links zu Versand und Rückläufen. Einzelpersonenausgaben bleiben ausdrücklich von Versandpaketen getrennt. |
| Dokumentstatus | Neu importierte Word-PDFs hiessen «Vor Umstellung eingegangen». | «Unterschriften- und Ablageprüfung offen» mit passender Handlungsanweisung. |
| Fallprüfung | Nach PDF-Übernahme führte die Anweisung in die Fallprüfung, dort fehlte die Freigabeaktion. | Unterschriftenbestätigung direkt beim Fall; danach Dossierübergabe oder Scanpflicht. |
| Scanpflicht | In der Fallprüfung fehlte der anschliessende Scan-Upload. | Upload direkt beim betroffenen Dokument nach Unterschriftenprüfung. |
| Korrigiertes Word-PDF | Die Fallmaske bot nur einen Ersatzimport an, der einen Arbeitsmappen-Datenblock verlangt. | Word-Korrekturen werden in die Word-PDF-Prüfung geführt; Datenblock-Ersatz separat als Alternative bezeichnet. |
| Gesperrte Korrekturen | Hinweis empfahl neue PDF-Versionen auch nach Dossierfreigabe, obwohl Ersatz dann gesperrt bleibt. | Grenze und notwendige Abstimmung mit Dossier-/SAP-Verarbeitung erklärt. |
| Erfolg nach Übernahme | Standardmeldung verwies auch bei Nichtdurchführung, Nachreichung und Dublette auf die Ablagefreigabe. | Unterschiedliche Meldungen mit dem jeweils passenden Ergebnis und nächsten Schritt. |
| Prozesshilfe | «PDF übernehmen» wurde als direkte Ablage beschrieben; Anrede teilweise «Sie». | Word-Fachdatenübernahme und anschliessende Ablageprüfung getrennt erklärt; Du-Form. |
| Rückläufe | Postfachhinweis suggerierte unmittelbare Verarbeitung; leere Fallaufgabenliste konnte trotz offener Word-PDFs Entwarnung geben. | Prüfwarteschlange und Fallaufgaben sprachlich getrennt; Hinweis auf konfigurierten Mailordner. |
| Warteschlange | Trotz Durchlaufauswahl ist die Word-PDF-Liste global und auf 100 Einträge begrenzt. | Diese Grenze sichtbar erklärt; funktionale Erweiterung bleibt offen. |
| Erste Schritte | README führte neue Testende noch zur START-HTML-Datei. | Einstieg auf Word, PDF-Prüfung, Fallfreigabe und Export aktualisiert. |
| Backup | Oberfläche versprach «Vollständiges Backup», lokale Vorlagen und Konfiguration fehlen aber darin. | Als Prozessdatensicherung benannt; zusätzliche Sicherung der Vorlagen und Konfiguration ausdrücklich genannt. |

## Noch offen – priorisiert

| Priorität | Punkt | Konsequenz / nächster Schritt |
|---|---|---|
| Vor breitem Versand | Nach einem Prozessabbruch kann «Outlook-Übernahme läuft» dauerhaft stehen bleiben. Die App blockiert Wiederholung und Neuerzeugung, bietet für diesen Status aber keinen eigenen Klärungsdialog. | Kontrollierten Wiederanlauf mit expliziter Outlook-Prüfung entwerfen. Keinen laufenden Versand automatisch entsperren; eine Doppelzustellung muss vermieden werden. |
| Vor breitem Rücklauf | Word-PDF-Warteschlange hat keine Pagination/Filter und zeigt höchstens 100 Einträge. Bei über 100 offenen Prüfungen fehlen ältere offene Einträge in dieser Liste. | Pagination sowie Filter für offen/erledigt, Person und zugeordneten Durchlauf ergänzen. |
| Vor fachlicher Abnahme | SAP-Auswahl setzt derzeit einen vollständig abgeschlossenen Fall voraus. Ein fertiger Rückblick kann bei noch offenem Ausblick deshalb noch nicht exportiert werden. | Fachlich entscheiden, ob Rückblicke unabhängig vom Ausblick exportiert werden sollen. Diesen bestehenden Grundsatz nicht stillschweigend ändern. |
| Nutzerführung | PDF-Prüfmaske zeigt auch Felder anderer Formulararten; viele manuelle Prüfschritte. | Felder nach Rückblick/Ausblick/Probezeit/Nichtdurchführung kontextabhängig gruppieren; Reihenfolge im echten Browser beurteilen. |
| Nutzerführung | Sammelerzeugung/Outlook-Übergabe verwenden normale Seitenwechsel und haben keine sichtbare Fortschrittsanzeige wie der einzelne Download. | Wartezustand und Schutz gegen wiederholtes Absenden ergänzen; reale Laufzeit mit grösserer Führungslinie prüfen. |
| Nutzerführung | Erfolg eines einzelnen Personendownloads ist im aktuellen Tab sichtbar, aber nicht in einer separaten Personenausgaben-Historie. | Bei Bedarf dauerhaften Wiederdownload auch für Einzelpersonenausgaben ergänzen. |
| Betrieb | Lokale Konfiguration und Word-Vorlagen sind separat zu sichern. | Einrichtung und Wiederherstellung auf dem Windows-Gerät prüfen; ggf. kontrolliert ins Backup aufnehmen. |
| Visuelle Abnahme | Kein echter Browser-Klicktest in dieser Umgebung möglich. | Navigation, lange Tabellen, Auswahlfelder, Download und Scrollposition in Edge/Chrome prüfen. |
| Integration | Klassisches Outlook/S/MIME, produktiver Ablagepfad, RPA und SAP-Zielsystem nicht erreichbar. | Ein isolierter Windows-Testlauf bis zum SAP-Import bleibt notwendig. |
| PDF-Erkennung | Ausgefüllte echte Ausblick-/Probezeitformulare und historische Layouts fehlen weiterhin. | Je Exportweg echte anonymisierte Beispiele prüfen; unbekannte Layouts nicht automatisch freigeben. |

## Ergebnis

Der reguläre Word-PDF-Ablauf lässt sich nach den Korrekturen über die angebotenen HTTP-Aktionen bis zur lokalen Dossierübergabe und SAP-Datei durchlaufen. Das ist eine technische Ablaufprüfung, keine vollständige visuelle oder produktive Abnahme. Für einen kleinen Testlauf sind die gefundenen direkten Navigationsabbrüche korrigiert; vor breitem Einsatz bleiben insbesondere Warteschlange, Outlook-Wiederanlauf und fachliche SAP-Auswahl zu klären.
