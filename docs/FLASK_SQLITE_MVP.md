# Technischer Stand – Word/PDF

Stand: 9. Oktober 2026. Frühere Architekturdetails zur HTML-Arbeitsmappe stehen
unter [historisch](historisch/FLASK_SQLITE_MVP.md).

## Komponenten

Flask stellt das HR-Cockpit bereit, Waitress dient als Server. SQLite speichert
Stammdaten, Durchläufe, Dialogfälle, Dokumentpflichten, Versionen und Auditdaten.
`word_packages` befüllt DOCX-Vorlagen; `word_dispatch` verwaltet Versandpakete und
Outlook-Status; `word_pdf`/`pdf_cells` extrahieren PDF-Inhalte;
`word_pdf_imports` verwaltet die Prüfwarteschlange und bestätigte Übernahmen.
`documents` steuert Unterschriften, Scans und lokale Dossierübergabe;
`sap_export` erzeugt nachvollziehbare Excel-Batches.

## Einrichtung

- `instance/word_config.json`: lokale Pfade der drei Word-Vorlagen.
- `instance/organisation.json`: Organisationswerte, `PUBLIC_BASE_URL` und `LEGACY_WORKBOOKS`.
- `PUBLIC_BASE_URL` ist optional und enthält den vollständigen vereinbarten Zugriffslink, z. B. `http://md-server.example.invalid:5050`. `MD_PUBLIC_BASE_URL` überschreibt ihn.
- `LEGACY_WORKBOOKS` ist standardmässig `disabled`; `enabled` blendet die historischen Oberflächen ein. Die zugrunde liegenden Daten und Kompatibilitätsrouten werden nicht gelöscht. Dies ist kein Berechtigungsschalter.
- Start: `python run_web.py`, standardmässig `127.0.0.1:5050`. `--host` und `--port` wählen die Bindung. Der vorhandene BAT-Starter verwendet ebenfalls Loopback.

## Rechnername und Netzwerkzugriff

Unter Administration werden der tatsächliche Rechnername des Serverprozesses,
die vom Starter übergebene Bindung und der konfigurierte Link angezeigt.
Ein automatisch abgeleiteter Rechnernamen-Link ist lediglich ein ungeprüfter
Vorschlag. DNS, Firewall, Port und gegebenenfalls Reverse Proxy bestimmen die
Erreichbarkeit von anderen HR-PCs. Ein durch die IT gepflegter DNS-Name oder
Alias kann bei wechselnder IP einen gleichbleibenden Link ermöglichen.

Bindet der Server an eine konkrete alte IP, genügt ein DNS-Wechsel allein nicht.
Loopback erlaubt ausschliesslich lokalen Zugriff. `0.0.0.0` bezeichnet alle
IPv4-Schnittstellen und ist kein Link zum Verteilen. Die Anwendung ändert diese
Bindung nicht aufgrund des konfigurierten Links. Netzwerkbetrieb und TLS sind
Teil der lokalen Betriebsentscheidung, nicht automatisch durch den Link freigegeben.

## Daten und Wiederherstellung

Datenbank und Prozessdateien bleiben lokal. Word-/PDF-Dateien und Konfiguration
gehören nicht ins öffentliche Repository. App-Backups enthalten Prozessdaten und
Dossierübergabe, nicht die lokalen Vorlagen und Konfiguration. Diese sind separat
zu sichern. Externe Wirkungen bleiben getrennt: Datei erzeugt, Outlook übergeben,
Versand bestätigt, Dossier bereitgestellt und SAP-Datei erzeugt sind verschiedene
Schritte; RPA-Übernahme und SAP-Import erfolgen ausserhalb der Anwendung.

Details: [Word/PDF](PLAN_B_WORD_PDF.md), [Betrieb](BETRIEBSKONZEPT.md), [Test](BUEROTEST.md).


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
