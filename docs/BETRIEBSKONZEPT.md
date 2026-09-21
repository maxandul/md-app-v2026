# Betriebskonzept MD-App v2026

**Stand:** 21. September 2026  
**Status:** Technischer Entwurf; vor dem Produktivbetrieb durch Fachverantwortung,
Applikationsverantwortung und Informationssicherheit freizugeben.

## 1. Geltungsbereich und Betriebsmodell

Die MD-App ist eine lokale Übergangslösung für besonders schützenswerte
Personaldaten. Sie läuft auf einem verwalteten Windows-HR-Gerät und bindet nur an
`127.0.0.1`. Eine Freigabe im Netzwerk, gemeinsamer Mehrplatzbetrieb oder das
Ablegen in einem nicht genehmigten Cloud-Speicher ist nicht Bestandteil dieses
Betriebsmodells.

Die Anwendung umfasst die SQLite-Datenbank, alle Dateien unter `instance/data`,
den konfigurierten Dossier-Übergabeordner sowie lokale Backups. Outlook und die
nachgelagerte Dossier-RPA bleiben eigenständige Systeme.

## 2. Rollen und Verantwortungen

| Rolle | Verantwortung |
|---|---|
| HR-Administration | SAP-Import, Durchläufe, Versand, Rückläufe, Freigaben und fachliche Kontrollen |
| HR-Systemadministration | Konten, Backup/Restore, Auditkontrolle, technische Konfiguration und Störungsbehebung |
| Applikationsverantwortung | Releases, Tests, Wiederanlauf und Pflege dieser Dokumentation |
| Fachverantwortung | Freigabe von Prozess, Aufbewahrung, Löschung und Berechtigungen |
| Informationssicherheit/Datenschutz | Freigabe der Schutzmassnahmen und Behandlung von Vorfällen |

Konten sind personengebunden. Systemadministrationsrechte werden nur für die
oben genannten Aufgaben vergeben. Geteilte Konten sind nicht zulässig.

## 3. Technische Ablage und Schutz

Standardmässig liegen Datenbank, Prozessdateien und Backups unter `instance/`.
Abweichende Verzeichnisse werden über die vorgesehenen Umgebungsvariablen
konfiguriert. Das Windows-Gerät und jedes externe Backup-Medium müssen
vollverschlüsselt, verwaltet und durch restriktive NTFS-Berechtigungen geschützt
sein. Backups besitzen denselben Schutzbedarf wie die Originaldaten.

Folgende Inhalte dürfen nie in Git gelangen: produktive Datenbank, SAP-Exporte,
Arbeitsmappen, Rückläufe, PDFs, Dossier-Dateien, Backups und Schlüssel. Die
vorhandene `.gitignore` ist nur eine zusätzliche Schutzschicht und ersetzt keine
Zugriffskontrolle.

## 4. Backup

Die Systemadministration erstellt in der Administrationsansicht ein vollständiges
ZIP-Backup. Es enthält:

- eine konsistente SQLite-Kopie über die SQLite-Backup-API,
- sämtliche Prozessdateien im Storage-Verzeichnis,
- den Dossier-Übergabeordner, sofern er ausserhalb des Storage-Verzeichnisses liegt,
- ein Manifest mit Dateigrössen und SHA-256-Prüfsummen.

Empfohlener, noch freizugebender Rhythmus: an jedem Arbeitstag mit Änderungen
sowie unmittelbar vor Importen, Releases oder administrativen Eingriffen. Eine
Kopie soll auf einem getrennten, genehmigten und verschlüsselten Medium liegen.
Der Download im Browser gilt erst nach kontrollierter Ablage auf diesem Medium als
erfolgreiche Datensicherung.

## 5. Restore und Wiederanlauf

Ein Restore darf nur durch die HR-Systemadministration und möglichst im
Vier-Augen-Prinzip erfolgen.

1. Anwendung für weitere Bearbeitung sperren und Ursache dokumentieren.
2. Gewünschtes Backup anhand Datum und Herkunft identifizieren.
3. In der Administrationsansicht das ZIP wählen und `WIEDERHERSTELLEN` bestätigen.
4. Die Anwendung erzeugt zuerst ein Sicherheitsbackup des aktuellen Zustands.
5. Archivpfade, Vollständigkeit, Prüfsummen, SQLite-Integrität und erwartete
   Tabellen werden geprüft.
6. Datenbank und Dateien werden ersetzt; bei einem technischen Fehler wird auf
   den vorherigen Zustand zurückgerollt.
7. Nach dem Restore neu anmelden und Stichproben für SAP-Datenstand, offenen
   Durchlauf, Rückläufe und Dossier-Übergabe durchführen.
8. Ergebnis und verwendetes Backup im Audit und im Betriebsjournal festhalten.

Ein Restore-Test mit einer separaten Testkopie ist mindestens quartalsweise sowie
nach Änderungen der Ablagestruktur durchzuführen. Ein Backup gilt erst nach einem
erfolgreichen Restore-Test als nachgewiesen wiederherstellbar.

## 6. Audit und Überwachung

Die Administrationsansicht zeigt die letzten 200 Audit-Einträge mit Zeitpunkt,
Konto, Aktion, Objekt und strukturierten Details. Protokolliert werden insbesondere
Anmeldung, fehlgeschlagene beziehungsweise begrenzte Anmeldeversuche,
Benutzerverwaltung, SAP-Import, Durchlauferöffnung, Arbeitsmappen, Rückläufe,
Korrekturen, Dokumentersetzungen, Exporte, Backup und Restore.

Passwörter, eingegebene E-Mail-Adressen fehlgeschlagener Anmeldungen und
Dateiinhalte werden nicht im Audit gespeichert. Die Systemadministration prüft das
Audit nach Störungen, vor und nach Restores sowie regelmässig auf unerwartete
administrative Aktionen.

## 7. Aufbewahrung und Löschung

Für produktive Personaldaten ist noch eine verbindliche Aufbewahrungs- und
Löschregel durch die Fachverantwortung und den Datenschutz festzulegen. Bis zu
dieser Freigabe löscht die Anwendung weder Falldaten noch Backups automatisch.
Das verhindert unkontrollierten Datenverlust, ist aber keine zulässige dauerhafte
Aufbewahrungsregel.

Vor Produktivstart sind mindestens festzulegen:

- Frist je SAP-Import, Arbeitsmappe, Rücklauf, offiziellem Dokument und Audit,
- Backup-Rotation und Zahl der getrennten Generationen,
- Verantwortliche Person und Nachweis der periodischen Löschung,
- Vorgehen bei Austritt, Rechtsstreit, Sperrfrist oder Akteneinsicht.

## 8. Störung und Sicherheitsvorfall

Bei Verdacht auf Datenabfluss, Malware, Verlust des Geräts oder unberechtigten
Zugriff wird die Bearbeitung gestoppt, das Gerät gemäss interner Vorgabe isoliert
und die zuständige Informationssicherheits-/Datenschutzstelle beigezogen. Audit,
Backup und betroffene Dateien werden beweissicher erhalten; es erfolgen keine
eigenmächtigen Bereinigungen.

Vorgeschlagene, noch freizugebende Ziele sind ein maximaler Datenverlust von einem
Arbeitstag (RPO) und ein Wiederanlauf innerhalb von vier Arbeitsstunden (RTO).

## 9. Freigabecheckliste vor Produktivbetrieb

- [ ] Rollen und namentliche Verantwortungen genehmigt
- [ ] verwaltetes und vollverschlüsseltes Windows-Gerät bestätigt
- [ ] produktive Verzeichnisse und NTFS-Berechtigungen geprüft
- [ ] S/MIME-Ablauf mit produktivem Outlook und Zertifikat nachgewiesen
- [ ] getrenntes verschlüsseltes Backup-Medium festgelegt
- [ ] vollständiger Backup-/Restore-Test protokolliert
- [ ] RPO, RTO, Backup-Rotation, Aufbewahrung und Löschung freigegeben
- [ ] Incident- und Stellvertretungsweg bekannt
- [ ] keine echten Personaldaten im Git-Repository vorhanden

