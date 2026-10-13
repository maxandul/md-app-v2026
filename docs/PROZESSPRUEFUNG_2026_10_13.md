# Erweiterte Prozessprüfung Plan B – 13. Oktober 2026

Geprüft auf `fix/plan-b-goals-outlook-scan`, aufbauend auf dem Ordnerimport
für Vorjahresziele. Tests mit temporären Datenbanken und synthetischen
Stammdaten; das gelieferte alte Ausblick-PDF zusätzlich nur lesend geprüft.
Keine produktiven Mails versendet, verschoben oder SAP-Daten verändert.

## Ergebnis und Grenzen

Der technische Kernprozess funktioniert in den automatisierten Tests.
Eine vollständige Betriebsabnahme ist das nicht: Der Word-Feedback-Rücklauf
ist noch unvollständig; Windows/Outlook/S/MIME, VPN, echte Word-PDF-Ausgabe,
Netzlaufwerke, Dossier-RPA und SAP-Import sind hier nicht verfügbar.

| Prozess | Prüfergebnis |
|---|---|
| SAP-Stammdaten, Zuordnungen, Anstellungen, Konflikte | Bestehende Import-, Synchronisierungs- und Konflikttests erfolgreich |
| Vorjahresziele, alte/neue Word-/PDF-Quellen | Import-, Quellenwahl-, Dubletten- und Jahreszuordnungstests erfolgreich |
| Word-Dossier und ZIP-Download | HTTP-Ablauf, Dateiinhalte, Vorlagenbefüllung und Managertrennung erfolgreich |
| Versand und Wiederanlauf | Mit simuliertem Outlook: Entwurf, Versandstatus, Fehler, Wiederholung und Schutz vor veralteten Paketen erfolgreich |
| Postfach und PDF-Prüfwarteschlange | Mit simulierten Mails: Zuordnung, Dubletten, Einzelmailfehler und Sperre vor verfrühtem Abschluss erfolgreich |
| HR-Prüfung, Korrektur und Versionierung | HTTP- und Servicetests erfolgreich; Originale bleiben erhalten |
| Nichtdurchführung, Probezeit, D/E, Scanpflicht | Bestehende Sonderfalltests erfolgreich |
| Unterschriftenfreigabe und Dossierbereitstellung | HTTP-Ablauf bis lokale Ablagedatei erfolgreich; externe Übernahme nicht geprüft |
| SAP-Ausgabe | XLSX-Erstellung und Wiederholung ohne doppelte Exportzeilen erfolgreich |
| Fristen, Erinnerungen, Auswertungen | Bestehende Tests erfolgreich; kein echter Mailversand |
| Jahresabschluss/Wiederöffnung | Kontrollierte Statuswechsel und begründete Restfälle erfolgreich |
| Folgejahr | Neu bis zur Word-Datei geprüft: bestätigte Ausblickziele werden zu Vorjahreszielen im nächsten Rückblick |
| Backup/Wiederherstellung | Neu mit vollständigem Testablauf: Word-ZIPs, PDFs, Ablagedateien und SAP-Exportdaten an denselben Pfaden wiederhergestellt; Datei-Prüfsummen stimmen |
| Feedback aus Word | **Offene Funktionslücke**, siehe unten |

## Gefundene Fehler und Änderungen

### Ziele mit Seitenumbruch: behoben

Im normalen PDF-Rücklauf wurde ein Zielteil auf der Folgeseite als eigenes Ziel
ohne Zieltext gelesen. Am gelieferten alten Ausblick ergaben sich dadurch vier
statt drei Entwicklungsziele. Die Fortsetzungslogik des Ordnerimports wird nun
zentral auch für den normalen Rücklauf verwendet. Nach der Korrektur erkennen
beide Wege ein Leistungsziel und drei Entwicklungsziele mit identischem Inhalt.

Zusammengeführt wird nur ein Teil ohne Titel am oberen Rand der unmittelbar
folgenden Seite und mit derselben Kompetenz. Neue Ziele und unklare Fragmente
bleiben getrennt. Regression mit einem echten synthetischen mehrseitigen PDF
sowie Gegenproben für Seitenabstand, Position und Kompetenzwechsel ergänzt.

### Freitext mit Seitenumbruch: Prüfhinweis ergänzt

Im alten Beispiel lässt sich ein Freitext auf Seite 2 nicht eindeutig seinem
Feld zuordnen. Der Text ist im Original und in den extrahierten Feldern vorhanden,
fehlte aber im zugeordneten Freitext. Jetzt erscheint für solche breiten,
ausgefüllten Felder ein seitenbezogener Hinweis in der HR-Prüfung. Die Übernahme
verlangt dadurch auch eine Prüfnotiz. HR muss den Text anhand des Originals im
richtigen Feld ergänzen. Die automatische Freitextzuordnung über Seiten hinweg
ist damit ausdrücklich noch nicht vollständig gelöst.

### Word-Feedback-Rücklauf: offen

Die Word-Feedbackvorlage wird erzeugt und mitgegeben. Der Feedbackimport erwartet
jedoch weiterhin einen strukturierten Datenblock mit Fall, Person, Führungskraft,
Jahr und Versandpaket aus dem früheren HTML-Verfahren. Das neue Word-Formular
liefert diesen Datenblock nicht.

Reproduktion mit synthetischem Feedback-PDF ohne Datenblock: Direktimport lehnt
es als nicht erkanntes Feedback ab; Postfachverarbeitung legt es in die allgemeine
Word-PDF-Prüfwarteschlange (`pending`). Ergebnis: keine Feedbackübernahme und kein
Feedbackbündel. Dort gibt es nur Rückblick/Ausblick als Dokumentarten. Das PDF
darf nicht ersatzweise als Rückblick oder Ausblick bestätigt werden.

Erforderliche nächste Erweiterung: eigener Word-Feedback-Rücklauf mit verlässlicher
Zuordnung zu Führungskraft und Jahr, HR-Prüfung, Dublettenschutz und Bündelung.
Die erfolgreichen Feedbacktests decken bisher nur das alte Datenblockverfahren ab.

## Ausgeführte Tests

- 139 Python-App-Tests erfolgreich: `python -m unittest discover -s tests -v`.
- 22 Tests der früheren HTML-Arbeitsmappe erfolgreich:
  `python -m unittest discover -s prototype/html_dialog -p 'test_*.py' -q`.
- 5 JavaScript-Tests erfolgreich:
  `node --test tests/test_dispatch_download.cjs tests/test_goal_import.cjs`.
- JavaScript mit simuliertem DOM; kein realer Edge-/Chrome-Durchlauf.
- Kein visueller Layouttest in Microsoft Word; Dateiinhalte und XML geprüft.
- Backup-Restore an geänderten Serverpfaden und produktive Migration nicht geprüft.
- Für einen neuen Jahresprozess aktuelle SAP-Stammdaten verwenden: Ein alter
  Datenbestand mit bereits ausgeschiedenen Personen kann unzulässige Zeiträume
  enthalten und die gemeinsame Paketerzeugung blockieren. Der Folgejahrestest
  prüft gezielt den weiterhin beschäftigten Testfall.

## Noch am Arbeitsplatz abzunehmen

1. Echte Word-Dossiers öffnen, bearbeiten und mit dem eingesetzten Word als PDF
   speichern; mehrseitige Ziele und Freitexte in der HR-Prüfung vergleichen.
2. S/MIME-Entwurf/Versand und Scan im tatsächlichen Windows-/Outlook-Profil prüfen,
   einschliesslich einer unlesbaren und einer lesbaren Nachricht.
3. Freigegebenes Dossier auf dem Netzlaufwerk und seine tatsächliche externe
   Übernahme kontrollieren; SAP-Datei im vorgesehenen Testverfahren einlesen.
4. Neue Word-Feedbacks bis zur Ergänzung des Rücklaufwegs separat bearbeiten.
