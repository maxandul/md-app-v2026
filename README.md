# MD-App v2026

Lokale Flask-/SQLite-Anwendung zur administrativen Verarbeitung des jährlichen
Mitarbeitenden-Dialogs (MD). Der aktuelle Stand ist ein lauffähiger MVP für
gemeinsame Tests und die schrittweise Weiterentwicklung.

Die Umstellung auf Word-Vorlagen mit PDF-Rücklauf ist begonnen. In der
**Führungslinie → Word-Vorlagen** lassen sich personalisierte Formulare einzeln
oder für die Führungslinie als ZIP erzeugen. Unter **Versand** werden Word-Pakete
für ausgewählte Führungskräfte, eine Organisationseinheit oder den ganzen Durchlauf
vorbereitet. Die Outlook-Zustellung und der tatsächliche Versand sind separat
protokolliert. Unter **Rückläufe → Word-PDFs
einlesen** werden Grundangaben, Zieltabellen und aktuelle Einschätzungen zur
Prüfung vorgelegt. HR bestätigt Fall und Anstellung oder übernimmt einen
nachgereichten Ausblick als versionierte Zielquelle. Word-PDFs aus dem Postfach
landen ebenfalls in dieser Prüfung. Der bisherige Arbeitsmappen-Ablauf bleibt technisch erhalten, ist aber standardmässig ausgeblendet.
Nichtdurchführungen lassen sich je Gesprächsteil mit Begründung bestätigen.
Die Auswertung ergänzt Ja/Nein/offen-Angaben und Zeichenanzahlen geprüfter Textfelder.
Einrichtung, Umsetzungsstand und nächste Schritte:
[`docs/PLAN_B_WORD_PDF.md`](docs/PLAN_B_WORD_PDF.md).

Im Cockpit führen **Hilfe → Einrichtung** durch den Erststart und **Arbeitsliste** durch die offenen Aufgaben. Die [HR-Betreuungsanleitung](docs/HR_BETREUUNG.md) beschreibt Unterbrechungen, Ausnahmen und Jahreswechsel.

## Aktueller Standardablauf

- SAP-Stammdaten importieren, Zuordnungskonflikte prüfen und Durchlauf eröffnen.
- Personalisierte Word-Vorlagen einzeln oder als Führungslinien-/Sammelpakete erzeugen.
- Pro Führungskraft eine Reflexionsvorlage und eine mit ihren Stammdaten befüllte Feedbackvorlage zur Weiterleitung beilegen.
- Eigene ZIP-Anhänge je Führungskraft über klassisches Outlook bereitstellen; Entwurf und Versand getrennt nachhalten.
- Word-PDFs einlesen, am Original prüfen und dem Fall zuordnen.
- Unterschriften und erforderliche Scans prüfen, danach Dossierübergabe bereitstellen.
- Nachgereichte Ausblicke als Zielquelle übernehmen; bestehende Word-Ausgaben unverändert lassen.
- Nichtdurchführung je Gesprächsteil dokumentieren; Auswertungen und SAP-Batches erzeugen.
- Benutzer, Audit, Prozessbackups und Wiederherstellung verwalten.

Die [Dokumentationsübersicht](docs/README.md) trennt aktuelle Anleitungen von
historischen Spezifikationen. Alte Offline-Funktionen sind standardmässig
unsichtbar und bleiben technisch verfügbar; zum ausdrücklichen Einblenden dient
`LEGACY_WORKBOOKS: "enabled"` in der Organisationskonfiguration.

## Lokal unter Windows starten

Voraussetzung: Python 3.11 oder neuer.

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Anschliessend `MD-Web.bat` doppelklicken oder im aktivierten Terminal starten:

```powershell
python run_web.py
```

Die Anwendung ist danach unter <http://127.0.0.1:5050> erreichbar. Beim ersten
Start wird die lokale SQLite-Datenbank automatisch unter `instance/` angelegt.
Systemadministrationen finden Benutzerkonten, Audit, Backup und Restore unter
`Administration`. Backups enthalten Personaldaten und müssen unmittelbar auf ein
genehmigtes, verschlüsseltes und getrenntes Medium übertragen werden.

## Erster Testlauf

1. Die App starten.
2. Den SAP-Export unter «Stammdaten» hochladen.
3. Für diesen Import einen Jahresprozess eröffnen.
4. In der Prozessübersicht eine vorgesetzte Person auswählen.
5. Die lokalen Word-Vorlagen gemäss `docs/PLAN_B_WORD_PDF.md` einrichten und ein Word-Paket erzeugen.
6. Unter «Versand» den Paketstatus prüfen. Testformulare in Word ausfüllen und als PDF zurückgeben.
7. Unter «Rückläufe» einlesen, am Original prüfen und übernehmen. Danach beim Fall die Unterschriften- und Ablageprüfung abschliessen.
8. Den SAP-Export erzeugen. Outlook, Dossier-RPA und SAP-Import werden auf dem Windows-Testgerät geprüft.

Das Repository enthält bewusst keine SAP-Exporte, Personendaten, ausgefüllten
Dialoge, PDFs oder lokale Datenbank. Solche Dateien bleiben auf dem geschützten
HR-Gerät und sind durch `.gitignore` vom Commit ausgeschlossen.

## Wichtige Sicherheitsgrenze des MVP

Der Server bindet standardmässig an `127.0.0.1` und ist für den Betrieb auf
einem einzelnen HR-Laptop gedacht. Vor einem Zugriff weiterer Arbeitsplätze
müssen mindestens Windows-Authentisierung, Rollen/Berechtigungen, TLS, Backup,
Protokollierung und die Betriebsverantwortung festgelegt werden. Den Server mit
Personaldaten nicht ungeschützt über `0.0.0.0` im Netzwerk freigeben.

Der Versand und Rückversand von Dateien mit Personaldaten erfolgt gemäss dem
vorgesehenen Prozess S/MIME-verschlüsselt. Die Anwendung prüft die gespeicherte
Verschlüsselungsmarkierung vor jedem Direktversand. Alternativ können weiterhin
Outlook-Entwürfe erzeugt und vor dem manuellen Versand kontrolliert werden. Der
vollständige Nachweis ist mit dem produktiven HR-Postfach, den Zertifikaten und
der konkreten Outlook-Version durchzuführen.

Für die Entwurfserstellung sind Windows, klassisches Outlook und `pywin32`
erforderlich. Die Organisationswerte werden lokal hinterlegt:

1. `config/organisation.example.json` nach `instance/organisation.json` kopieren.
2. `HR_MAILBOX_EMAIL` (Absenderadresse), `OUTLOOK_MAILBOX_NAME` (Postfachname),
   `OUTLOOK_TARGET_FOLDER`, `DOSSIER_HANDOFF_ROOT` und `SPECIAL_CASES_URL` setzen.
3. App neu starten. Ohne Absenderadresse bleibt der Outlook-Versand gesperrt.
   Ohne Spezialfälle-Link wird in der HTML-Alternative auf HR verwiesen.

`MD_ORG_CONFIG` kann auf eine andere JSON-Datei zeigen. Umgebungsvariablen
`MD_HR_MAILBOX_EMAIL`, `MD_OUTLOOK_MAILBOX`, `MD_OUTLOOK_TARGET_FOLDER`,
`MD_ROBOT_INPUT_ROOT` (alternativ `MD_DOSSIER_HANDOFF_ROOT`) und
`MD_SPECIAL_CASES_URL` überschreiben die jeweiligen Dateieinträge.
Relative Ablagepfade beziehen sich auf das Konfigurationsverzeichnis. Ohne
Ablagepfad verwendet die App lokal `STORAGE_ROOT/dossier_ready`; es gibt keinen
fest eingebauten Netzlaufwerkspfad. Organisationsdatei und Word-Vorlagen bleiben
in `instance/` und werden nicht in Git aufgenommen. Sie sind zusätzlich zum
Datenbank-/Dateibackup lokal zu sichern.

Das Einlesen ignoriert Mails ohne MD-Bezug. Erfolgreich verarbeitete reine
MD-Mails werden nach «12 Mitarbeitenden-Dialog» verschoben. Bei gemischten Mails
werden die MD-Dokumente verarbeitet, die Fremdanlagen aber nicht gespeichert;
die Mail bleibt bis zur manuellen Prüfung im Posteingang.

Mitarbeitende senden ihr separates Feedback-PDF standardmässig an ihre
vorgesetzte Person. Diese übermittelt die gesammelten Feedbacks in einer
S/MIME-verschlüsselten E-Mail an HR. Die Anwendung führt die eingegangenen
Feedbacks pro Führungskraft zusammen; HR verfolgt deren Vollständigkeit nicht.

## Zugriffsadresse für HR

Unter **Administration** stehen Rechnername, Bindung/Port und der konfigurierte
Zugriffslink. Trage in `instance/organisation.json` den vollständigen Link unter
`PUBLIC_BASE_URL` ein, z. B. `http://md-server.example.invalid:5050`; alternativ
`MD_PUBLIC_BASE_URL`. Vor dem Verteilen auf einem zweiten HR-PC testen.

Ein Rechner-/DNS-Name kann bei wechselnder IP gleich bleiben, sofern die interne
Namensauflösung aktualisiert wird. Die Linkeinstellung ändert weder Serverbindung
noch Firewall. Der BAT-Starter bleibt lokal; ein bereits eingerichteter
Netzwerkstart wird dadurch nicht umkonfiguriert. Details: [Technik](docs/FLASK_SQLITE_MVP.md).

## Tests

Die Tests erzeugen ausschliesslich synthetische SAP-Daten in temporären Ordnern.

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m unittest discover -s prototype/html_dialog -p "test_*.py" -v
```

Weitere Architektur- und Prozesshinweise stehen in
[`docs/FLASK_SQLITE_MVP.md`](docs/FLASK_SQLITE_MVP.md). Die betrieblichen
Schutzmassnahmen, Restore-Schritte und noch notwendigen Freigaben stehen im
[`docs/BETRIEBSKONZEPT.md`](docs/BETRIEBSKONZEPT.md).
Die kontrollierte Prüfung mit SAP, Word-Formularen, Outlook und Restore ist in
[`docs/BUEROTEST.md`](docs/BUEROTEST.md) beschrieben.
