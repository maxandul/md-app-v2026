# E2 und Vorbereitung der neuen HR-Version

**Historischer E2-Nachweis vor der Bereinigung.** Der aktuelle Einstieg ist
[MD-Web.bat](../MD-Web.bat); die aktuelle Anleitung steht in
[Einrichtung und Betrieb](START_NEUE_HR_VERSION.md). Frühere Starter und der
Oberflächenschalter wurden anschliessend entfernt.

Stand: 28. Oktober 2026. Arbeitsbranch: `feat/hr-e2-release-preparation`.
Basis: `d171e96` auf `feat/hr-uebersicht-f`; enthält die bisherigen Etappen A–F.
Produktives `main`: `9d7ca77`. Kein Merge und keine produktive Migration durchgeführt.
GitHub-Schreibzugriff ist inzwischen verfügbar. Der Nutzer wünscht den direkten
Einstieg mit laufender Mängelbehebung. `MD-HR.bat` aktiviert dafür die neue
Oberfläche mit manueller Rücklaufprüfung. Der tatsächliche Windows-Start und die
externen Integrationsnachweise werden dadurch nicht als erledigt ausgegeben.

## Ergebnis

E2 ergänzt die automatische Übernahme eindeutig zugeordneter, vollständig erkannter
digitaler Formulare. Die sechs gelieferten Originale sind als reproduzierbarer
Prüfsatz ausgewertet. Es wurden keine Originale, Unterschriftenbilder oder
PDF-Autorenmetadaten ins Repository aufgenommen.

Die Freigabe ist auf das geprüfte Strukturprofil `word-md-2026-v1` begrenzt.
Je Formularart liegt ein digitales Beispiel vor, dazu der zugehörige Scan.
Das belegt die unten genannten Felder dieser Beispiele, keine allgemeine
OCR-Zuverlässigkeit oder beliebige Word-/PDF-Versionen. Die Beispiele enthalten
bewusst Platzhalter und Widersprüche. Keines der sechs Originale wird automatisch
übernommen; gültige Varianten durchlaufen zusätzlich synthetische Ablaufprüfungen.
Sollwerte wurden aus den sichtbaren Originalen abgeleitet, nicht von HR separat
bestätigt.

## Befunde der Originalprüfung

| Beispiel | Korrigierte oder bestätigte Auslesung | Erwartete Behandlung |
|---|---|---|
| Digitaler Rückblick | PN 231654, VG 654; Zeitraum/Gespräch 28.10.2026; Gut → C; nächsthöheres Gespräch Ja; Bewilligungen Ja; ein Leistungsziel, ein Entwicklungsziel, drei Einschätzungen; alle acht relevanten Freitextfelder | Prüfung: Durchführung Ja bei ausgefüllter Nichtdurchführungsbegründung; Präzisierung trotz aktueller Bewilligungen |
| Digitaler Ausblick | PN 1345, VG 696731; Zeitraum/Gespräch 28.10.2026; KNF I bleibt als Originalwert erhalten und ergibt Laufbahnwunsch Ja; ein Leistungsziel, drei Entwicklungsziele; alle vier Textfelder | Prüfung: Durchführung Ja bei ausgefüllter Nichtdurchführungsbegründung |
| Digitale Probezeit | PN 1234, VG 3214; Zeitraum 05.–28.09.2025, Gespräch 13.09.2024; Weiterführung Ja; nächsthöheres Gespräch Nein; alle 13 Einschätzungen und sechs Textfelder | Prüfung: Gespräch vor Rückblickzeitraum; Gesprächsbemerkungen trotz Nein |
| Alle drei Scans | Enthalten OCR-Text, aber unvollständige Felder/Tabellen. Sichtbare Signaturzüge in beiden abschliessenden Unterschriftsfeldern. Keine Aussage zur Echtheit oder rechtlichen Wirksamkeit | Originalprüfung; keine automatische Daten- oder Unterschriftenbestätigung |

Vorher fehlten die Gesamtbeurteilung, KNF-Auswahl, Bewilligungsantwort, einzelne
mehrzeilige Textfelder und die über den Seitenwechsel laufende
Selbstmanagement-Einschätzung. Beim Ausblick-Scan erschien die PN der
mitarbeitenden Person fälschlich als VG-PN. Bei erkannten Scans werden deshalb
OCR-Werte nicht als vorausgewählte Person-/Datumsfelder angeboten. Der Originaltext
bleibt sichtbar. Ein allein gelieferter Scan bleibt manuell erfassbar und kann
nach vollständiger Prüfung gleichzeitig Datenquelle und Unterschriftennachweis sein.

Die Ausblickvorlage nennt im Unterschriftenhinweis nur «ungenügend», während die
bestätigte App-Regel D/E beide Teile betrifft. Vor dem nächsten Versand den Hinweis
in der tatsächlich eingesetzten Word-Vorlage angleichen. Die gelieferten PDFs
wurden nicht verändert. Die Probezeit-Testdatei hat 2026 im Dateinamen, aber 2025
im Zeitraum; der Dateiname wird nicht zur Jahreszuordnung verwendet.

## Automatischer Ablauf

Die vorhandene HR-Funktion muss aktiviert sein. Zusätzlich steuert
`MD_HR_RETURN_AUTOMATION=1` die Automatik; Standard bleibt aus. Beide Schalter
werden vor dem Start gesetzt. Die isolierte Übung aktiviert sie ausschliesslich
für ihre neu erzeugten Testdaten.

1. Original sichern und anhand SHA-256 auf Dubletten prüfen.
2. Aktuelles Original erneut auslesen: vollständige Seitennummerierung,
   bekannte Abschnitts-/Kompetenzstruktur, Tabellen, benötigte Einzel- und
   Textfelder. Scan, unbekanntes Format, fehlende Antwort oder Widerspruch
   führen in die konkrete Klärung.
3. Genau eine Anstellung und ein aktiver benötigter Gesprächsteil müssen zu
   PN, Führungskraft, exaktem Zeitraum und Probezeit-/Jahresform passen.
   Mehrfachanstellung, unklare Zuordnung, konkurrierender Eingang, begonnener
   Prüfentwurf und bestehende Fassung verhindern eine automatische Übernahme.
4. Fachdaten und versionsgebundener Nachweis werden gemeinsam gespeichert.
   Herkunft ist `automatic`, nicht eine erfundene HR-Sichtprüfung.
5. Ohne besondere Unterschriftenpflicht folgt einmalig die lokale Bereitstellung.
   Bei D/E bleibt der erforderliche Nachweis für jeden Gesprächsteil offen.
   Ein späterer D/E-Rückblick aktiviert weiterhin auch beim Ausblick Prüfbedarf.
6. Scheitert die Dateikopie, bleiben Fachdaten erhalten. Ein unklarer
   Übergabeausgang muss geklärt werden; erneuter Upload importiert und kopiert
   nicht nochmals. Bereits bereitgestellte Fassungen werden nicht ersetzt.

Mail und Upload verwenden denselben Ablauf. Der Outlook-Adapter liefert weiterhin
keinen Nachrichtentext. Automatisches Verschieben reiner MD-Mails ist daher
**weiterhin nicht freigegeben**; erfolgreiche Anhänge ersetzen keine Prüfung
zusätzlicher Mailanliegen. Dieser Teil des ursprünglichen Sollprozesses bleibt
bewusst offen. Die Anwendung versendet durch E2 keine Nachricht.

## Nachweise

- Gesamtlauf: 340 Python-Tests und 50 Unterprüfungen erfolgreich, 111,35 s.
- Browser-Skriptprüfungen: 8 erfolgreich.
- Direkter Einstieg: 11 bestehende Prüfungen zu Migration, Wiederanlauf, Backup
  und abgeschalteter Automatik nochmals erfolgreich. Der normale HR-Start wurde
  zusätzlich mit einer bestehenden synthetischen Datenbank geprüft: gleicher
  Datenbankpfad, fünf Migrationen, Anmeldung aktiv und Rücklaufautomatik aus.
- Originalprüfung: alle sechs Dateien gegen Prüfsumme und feldgenaue Sollwerte
  erfolgreich; siehe `E2_PRUEFERGEBNIS_2026_10_28.json` und
  `tests/fixtures/e2_expected.json`.
- Die elf neuen E2-Tests prüfen gültigen Rückblick/Ausblick/Probezeit,
  Beurteilungen A–E, fehlende Seiten, unbekannte Beurteilung, uneindeutige
  Anstellung, Zuständigkeit/Zeitraum, konkurrierende Fassungen, Entwurfserhalt,
  HTTP-Upload, Mail, Kopierfehler, Wiederholung nach Abholung durch RPA und
  die Unterdrückung unzuverlässiger vorausgefüllter OCR-Werte bei Scans.
- Bestehende Tests prüfen Migration, Wiederanlauf, Backup/Restore,
  getrennte Verantwortung, Scan allein, Nachforderung und beide Unterschriften.
- Mengenfall mit 1000 Personen und fünf Jahren: zwei paginierte Abfragen
  zusammen 1,309 s auf diesem Linux-Testrechner; kein Windows-Leistungsnachweis.
- Keine erfolgreiche visuelle Browserabnahme in dieser Umgebung: die lokale
  Test-App konnte gestartet werden, der getrennte Browser erreichte ihren lokalen Port nicht.
  Der lokale Browserdownload lieferte kein verwendbares Archiv.

Reproduzieren:

```powershell
python -m pip install -r requirements-dev.txt
python scripts/run_tests_offline.py tests prototype/html_dialog -q --tb=short
node --test tests/test_action_position.cjs tests/test_dispatch_download.cjs tests/test_goal_import.cjs
python scripts/validate_e2_samples.py --input-dir "C:\Pfad\zu\den\sechs\Testdateien"
```

Die Originalprüfung läuft ausserhalb der CI mit den unveränderten Dateien. Die
CI enthält ausschliesslich synthetische PDFs. Alle Testdatenbanken, Dateikopien
und Übergaben wurden isoliert erzeugt; produktive Daten waren nicht angeschlossen.

## Übergang in den Einsatz

Der direkte Einstieg, Sicherung und Aktivierung stehen in
[START_NEUE_HR_VERSION.md](START_NEUE_HR_VERSION.md). Die Programmierung und
automatisierte Prüfung sind vorbereitet. Auf Wunsch des Nutzers kann der Einsatz
vor der vollständigen separaten Abnahme beginnen; die erste Nutzung externer
Funktionen wird begleitet. Dies ist kein Nachweis bereits erfolgter Installation
oder externer Integrationsprüfung.
