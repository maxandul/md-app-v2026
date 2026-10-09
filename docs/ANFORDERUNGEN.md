# Anforderungen – Word/PDF-Ablauf

Stand: 9. Oktober 2026. Dieser Stand ersetzt für den Standardbetrieb die frühere
[Arbeitsmappen-Spezifikation](historisch/ANFORDERUNGEN.md). Dortige Detailanforderungen
zur Offline-HTML-Datei sind keine Zusagen für den Word-Ablauf.

## Prozess und Zuständigkeiten

HR importiert SAP-Stammdaten, prüft Zuordnungen und legt Durchlauf und Pflichtumfang
fest. Führungskräfte erhalten pro Person passende Word-Formulare und senden die
fertig ausgefüllten PDFs zurück. HR prüft die Extraktion am Original, bestätigt die
Fallzuordnung und gibt geeignete Dokumente separat für die Dossierübergabe frei.
Die Phasen Vorbereitung, Versand, Rücklauf und Abschluss geben Orientierung;
ein Phasenwechsel versendet keine Dateien.

## Anforderungen

| Bereich | Aktueller Umfang |
|---|---|
| Stammdaten | Personen, Anstellungen und Führungslinien versioniert aus SAP übernehmen; blockierende Zuordnungskonflikte vor der Erzeugung klären. |
| Umfang | Rückblick, Ausblick und Probezeit anhand des Falls erzeugen; bestätigter Umfang hat Vorrang. Unterjährige Ereignisse bleiben getrennt nachvollziehbar. |
| Word-Erzeugung | Freigegebene lokale Vorlagen mit Stammdaten, Zeiträumen, Nebenbeschäftigungen und vorhandenen Vorjahreszielen befüllen. Zielzeilen dynamisch ergänzen; leere Entwicklungszielfelder beibehalten. |
| Versionierung | Neue Ausgabe aus aktuellen Quelldaten; frühere Ausgaben und lokal bearbeitete Dokumente nicht überschreiben. Konkurrierende Zielquellen zur Klärung anhalten. |
| Versand | Eigener ZIP-Anhang je Führungskraft. Erzeugung, Outlook-Entwurf und bestätigter Versand getrennt dokumentieren. Veraltete Pakete nicht versenden. |
| Rücklauf | Beide Microsoft-PDF-Exportwege unterstützen. Grundangaben, Ziele und aktuelle Einschätzungen vor Übernahme prüfen; unklare Werte offen lassen. |
| Nachreichung | Frühere Ausblicke als versionierte Zielquelle übernehmen; bei nächster Word-Erzeugung berücksichtigen. |
| Nichtdurchführung | Nur den betroffenen Gesprächsteil mit Begründung schliessen; administrativen Nachweis speichern. Keine Beurteilung oder Unterschrift erfinden. |
| Freigabe | Unterschriftenprüfung beim Fall; bei erforderlichem Scan dessen Eingang abwarten. Erst dann Dossierübergabe. Bereits übergebene Dokumente nicht automatisch ersetzen. |
| SAP | Führende, abgeschlossene und noch nicht exportierte Fälle als protokollierten Batch ausgeben. Aktuell wartet der Export auf den vollständigen Fall, gegebenenfalls inklusive Ausblick. |
| Auswertung | Geprüfte Angaben, Ziele, besprochene Kompetenzen und Zeichenanzahlen verwenden. Vorjahresziele zählen nicht als aktuelle Kompetenzbesprechung. Fehlend ist nicht «Nein» oder 0. |
| Bedienung | Standardoberfläche erklärt ausschliesslich Word/PDF. Historische Funktionen standardmässig ausblenden. |
| Administration | Server-Rechnername, Bindung und konfigurierten Zugriffslink zeigen; Linkkonfiguration ändert nicht DNS oder Netzwerkfreigaben. |
| Sicherung | Prozessdaten sichern; lokale Vorlagen und Konfiguration zusätzlich sichern. |

## Grenzen und Abnahme

Echte ausgefüllte Probezeit-/Ausblick-PDFs und Altlayouts benötigen weitere
Layoutprüfung. Keine OCR-Zusage. Browser-Bedienbarkeit sowie Outlook/S/MIME,
Netzwerkzugriff, Dossier-RPA und SAP-Import werden auf der Zielumgebung geprüft.
Die Word-PDF-Warteschlange ist derzeit auf 100 sichtbare Einträge begrenzt; ein
abgebrochener Outlook-Vorgang kann manuelle technische Klärung verlangen.
Details: [Implementierungsstand](PLAN_B_WORD_PDF.md), [Prüfbefunde](ABLAUFPRUEFUNG_WORD_PDF.md).


## Eigenständige HR-Betreuung

Im Cockpit stehen **Hilfe → Einrichtung**, die **vollständige Arbeitsliste** und
konkrete Hinweise zur Fehlerbehebung zur Verfügung. PDF-Prüfungen lassen sich als
Entwurf speichern, begründet zurückstellen und wieder öffnen. Die Warteschlange
ist durchsuchbar und in Seiten unterteilt; parallele Änderungen werden erkannt.
Eingegangene Dokumente lösen keine Nachforderung wegen offener HR-Prüfung aus.
Ungeprüfte PDF-Eingänge pausieren die Erstellung von Erinnerungen.

Unter **Stammdaten** können frühere DOCX-Ausblicke mit Vorschau importiert und
konkurrierende Zielquellen begründet ausgewählt werden. Ereignisse ohne Durchlauf
können zugeordnet, Fehlanlagen ohne Belege aufgehoben und verspätete Rückläufe
inaktiven Fällen begründet zugeordnet werden. Vor Bearbeitung geschlossener
Durchläufe diese wieder öffnen. Unterbrochene Outlook-Vorgänge dürfen erst nach
Prüfung in Outlook und Beendigung alter Serverprozesse geklärt werden.

Der Jahresabschluss verlangt eine Prüfung der externen Verarbeitung; offene
Aufgaben benötigen eine Restfallbegründung und eine verantwortliche Person.
Der Folgejahreslink bereitet das nächste Rückblickjahr vor. Die neuen Tabellen
werden beim App-Start ergänzt; bestehende Fachdaten bleiben erhalten.

Bedienung, Grenzen und Zuständigkeiten: [HR_BETREUUNG.md](HR_BETREUUNG.md).
Die Anwendung bestätigt weder SAP-Import noch Dossier-RPA-Verarbeitung automatisch.
