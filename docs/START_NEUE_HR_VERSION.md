# MD-App einrichten und verwenden

Stand: 29. Oktober 2026. Die neue HR-Oberfläche ist der Standard. Für den Alltag
gibt es **MD-Web.bat**, für die einmalige Installation **INSTALL_MD.bat**.

**Node.js und npm werden nicht benötigt.** Alle fertigen Oberflächen-Dateien
(CSS und JavaScript) sind unter `webapp/static` auf GitHub und im ZIP enthalten.
Für die Oberfläche ist kein Build-Schritt oder zusätzlicher Download nötig.
Die Node-Befehle im Entwicklungsabschnitt der README betreffen ausschliesslich
Tests, die auch automatisch auf GitHub laufen.

## Neuinstallation

1. Das ZIP von `main` vollständig in einen festen App-Ordner entpacken.
2. Python 3.11 oder neuer bereitstellen und `INSTALL_MD.bat` ausführen.
3. `MD-Web.bat` starten; <http://127.0.0.1:5050/arbeit> öffnen.
4. Ein Administrationskonto anlegen. Die App erstellt Datenbank und lokale Ablage unter `instance`.
5. Die Beispiele aus `config` als `instance/organisation.json` und `instance/word_config.json` einrichten.
6. In der Word-Konfiguration die eigenen Vorlagen für Rückblick, Ausblick und Probezeit hinterlegen. Reflexion und Feedback werden mitgeliefert und können ebenfalls konfiguriert werden.
7. Unter **Stammdaten** den SAP-Export hochladen, Vorschau und Konflikte prüfen, die ausgewählten Daten übernehmen und den Durchlauf eröffnen.

Konfiguration der HR-Absenderadresse, Outlook-Postfach und Dossierpfad mit der
bestehenden Umgebung abstimmen. Relative Vorlagenpfade beziehen sich auf die
Word-Konfigurationsdatei. Unter **Hilfe → Einrichtung** zeigt die App fehlende
Voraussetzungen. Fehlermeldungen bei der Installation im Konsolenfenster lesen;
bei Bedarf den vorgesehenen Proxy über `MD_PIP_PROXY` setzen.

Für Vorlagen im Unterordner `templates` lautet `instance/word_config.json` zum Beispiel:

```json
{
  "templates": {
    "review": "../templates/MD_Rückblick_2026.docx",
    "outlook": "../templates/MD_Ausblick_2026.docx",
    "probation": "../templates/MD_Rückblick_Probezeit_2026.docx"
  }
}
```

Die drei genannten DOCX-Dateien müssen dort tatsächlich liegen. Sie werden nicht
mitgeliefert. Beide schliessenden Klammern gehören zur JSON-Datei. Windows darf
keine zusätzliche Endung `.txt` angehängt haben. Nach einer Änderung den Server
mit Strg+C beenden und `MD-Web.bat` erneut starten. **Hilfe → Einrichtung** zeigt
den tatsächlichen Konfigurationspfad, Lesefehler und die aufgelösten Vorlagenpfade.
Ein gesetztes `MD_WORD_CONFIG` hat Vorrang vor der Standarddatei in `instance`.

Eine vorhandene `.venv` wird sowohl für Installation als auch Start verwendet.
Ohne `.venv` werden die Pakete für das ausgewählte installierte Python eingerichtet.
Die neue Oberfläche wird auch bei `python run_web.py` automatisch verwendet.

## Tägliche Arbeit

`MD-Web.bat` starten und das Konsolenfenster offen lassen. Der Browser darf
zwischenzeitlich geschlossen werden. Strg+C beendet die App. Bei belegtem Port
keinen zweiten Prozess starten; der Starter öffnet die laufende Instanz.

Installation und Start zeigen die Python-Suche, Paketprüfung und den App-Start
als einzelne Schritte. Während der Paketprüfung wird jedes geladene Paket
genannt; Fehlermeldungen bleiben sichtbar. «Requirement already satisfied»
bestätigt nur die Installation, noch nicht, dass sich ein Paket laden lässt.
Der Browser öffnet sich nach erfolgreichem Serverstart. Falls das Öffnen des
Browsers blockiert ist, die angezeigte Adresse manuell öffnen.

Bleibt der Start stehen, die letzte angezeigte Prüfung und eine allfällige
Fehlermeldung weitergeben. Zum direkten Start PowerShell im App-Ordner öffnen:

```powershell
py -3.11 -u run_web.py --host 127.0.0.1 --port 5050
```

Bei Verwendung von `.venv` stattdessen `.\.venv\Scripts\python.exe` verwenden.
Das Fenster offen lassen und nach «MD-Verwaltung läuft auf …» die angezeigte
Adresse öffnen. Ein pip-Update ist für diese Diagnose nicht erforderlich.

PDFs werden verbessert ausgelesen und vor der Übernahme von HR geprüft.
Die begrenzte Rücklaufautomatik ist standardmässig ausgeschaltet. Sie kann später
über `MD_HR_RETURN_AUTOMATION=1` vor dem Start aktiviert werden. Das ist kein
Oberflächenwechsel und aktiviert keinen Postfachscan.

Den ersten Word-Versand samt Empfängern sowie die erste Dossier-/SAP-Übergabe bis
zum Ziel prüfen. Diese Anbindungen sind nicht durch einen Linux-Test bestätigt.
Bedienmängel können laufend korrigiert werden; falsche Zuordnung und unklare
externe Übergaben beim betroffenen Vorgang zuerst klären.

In Formularen verwenden Eingabefelder Arial in normaler Schriftstärke; Titel
verwenden Arial Black. Hauptaktionen sind blau, weitere Aktionen haben einen
sichtbaren blaugrauen Hintergrund. Verwerfen, Zurücknehmen und Entfernen sind rot.

Begründungen und Prüfnotizen sind optional und haben keine Mindestlänge. Im
regulären Rückblick sind nur die beiden Datumsfelder des Rückblickzeitraums und
die Gesamtbeurteilung Pflichtinhalte. Der gesamte Zeitraum muss im Rückblickjahr
und zwischen Eintritt und Austritt der zugeordneten Anstellung liegen. Fehlende
Gesprächsdaten werden beim Übernehmen mit dem aktuellen Tagesdatum ergänzt und
als Ergänzung vermerkt. Das Original-PDF bleibt unverändert.

Leere Zusatzangaben, Ziele und Einschätzungen sind zulässig; unbekannte Antworten
werden nicht als Ja oder Nein ausgelegt. Ausblick und Probezeitformular können
leere Zeiträume aus dem ausdrücklich gewählten Fall übernehmen. Ein leerer
Probezeit-Anstellungsentscheid bleibt leer. Bei ausdrücklich bestätigter
Nichtdurchführung bleiben Beurteilung und Gesprächsdatum leer. Person, Anstellung
und Fall müssen weiterhin eindeutig zugeordnet sein; die Bestätigung der Prüfung
am Original sowie erforderliche Unterschriftennachweise bleiben bestehen.

Bei neu erstellten Rückblicken aus nachgereichten Ausblicken erhält jede
Führungskraft eine Mail mit **einem ZIP für alle ausgewählten Rückblicke**.
Das ZIP enthält die geprüften Word-Dateien direkt. Einzelne Ausgaben bleiben
in der App zur Prüfung verfügbar. Bereits erstellte Outlook-Entwürfe werden
nicht nachträglich verändert. Einen noch offenen alten Entwurf bei Bedarf in
Outlook löschen, in der App «Abbruch bestätigen» und den Versand erneut vorbereiten.

Bei D/E sind Rückblick und Ausblick jeweils zu unterschreiben. Der entsprechende
Hinweis in der eigenen Ausblick-Wordvorlage muss diese Regel enthalten. Scans und
zusätzliche E-Mail-Anliegen weiterhin manuell prüfen.

## Sicherung und spätere Updates

Die App erstellt unter Administration eine Sicherung von Datenbank, Dokumentablage
und Dossierordner. Lokale Konfiguration, `instance/secret_key`, eigene Word-Vorlagen
und der bisherige Programmstand sind zusätzlich zu sichern. Vor einem Update
Postfachverarbeitung pausieren und laufende Vorgänge beenden; nach der Sicherung
die App stoppen. Nur den Programmstand aktualisieren; `instance` und eigene
Dateien behalten. Danach wieder `MD-Web.bat` verwenden.

Die fünf versionierten Migrationen werden beim Start angewendet und nicht
nachträglich verändert. Bei Rückkehr zu einer früheren Version passenden Code
und Datenstand gemeinsam wiederherstellen. Bereits extern verarbeitete Mails,
Dateien und SAP-Importe werden durch eine lokale Wiederherstellung nicht zurückgenommen.

## Bereinigung

Die zusätzlichen HR-, Übungs- und Entwicklungsstarter, alte HTML-Arbeitsmappen,
Demo, Generator und HTML-Versand-/Rücklaufaktionen sind entfernt. Ein früheres
`MD_HR_GOAL_WORKFLOW` oder `MD_LEGACY_WORKBOOKS` schaltet die App nicht mehr um.
Ein alter `LEGACY_WORKBOOKS`-Eintrag in einer Konfigurationsdatei wird mit Hinweis
ignoriert. Historische Formate, Datenbankstände und Nachweise bleiben lesbar.
