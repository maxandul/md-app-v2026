# Entwurf E1: Rücklaufprüfung, Unterschriften und Bereitstellung

Stand: 28. Oktober 2026. Branch: `feat/hr-ruecklauf-e`.
Basis: Etappe D bei `1eb56ce3b2652adff3ee90d1583bf88bb845c950`.

**E1 automatisiert geprüft, Bedienabnahme noch offen.** Der isolierte CI-Lauf auf
`68be0629533901166bee10d33a4cf4140155f734` bestand am 28. Oktober 2026 mit
290 Tests und 36 Unterprüfungen (48,97 Sekunden). Der E1-CI-Lauf umfasst den Ordner `tests`. Der spätere Gesamtnachweis in
[Etappe F](UMSETZUNG_F_UEBERSICHT.md) ergänzt die 22 Prüfungen der älteren
Arbeitsmappe und die JavaScript-Tests.
Automatische Übernahme neuer PDF-/Scanvarianten ist noch offen. Die anschliessende
Konsolidierung steht in [Etappe F](UMSETZUNG_F_UEBERSICHT.md).

## Problem und Arbeitsweise

Der bisherige Weg vermischte die Übernahme von Fachdaten, ein allgemeines
Unterschriftenkennzeichen und die Dateikopie für das Dossier. Er erlaubte
Unterschriftennachweise nur für Rückblicke und verlangte immer zuerst ein
digitales PDF. Eine nachträglich erkannte Prüfpflicht für den Ausblick liess
sich damit nicht korrekt abbilden.

Nach bestätigter PDF-Prüfung führt die App auf eine Rücklaufseite für die
konkrete Dokumentversion. Dort stehen Person, Anstellung, Teilzeitraum,
Verantwortlichkeit, Datenquelle, Unterschriftennachweis und Bereitstellung
nebeneinander. Arbeitsübersicht, Fall und PDF-Prüfung verweisen darauf.

| Aktion / Stand | Wirkung im Entwurf |
|---|---|
| Angaben am Original prüfen und übernehmen | Fachdaten speichern; noch keine Unterschriftenbestätigung oder Bereitstellung |
| Scan als Datenquelle wählen | Vollständig geprüfter Scan kann zugleich Datenquelle und Unterschriftennachweis sein |
| Zusätzlichen Scan hochladen oder gesicherten Eingang zuordnen | Datei erhalten, Sichtprüfung öffnen; keine zweite fachliche Übernahme |
| Unterschrift fehlt | Konkreten Befund speichern; nicht als Nachforderung ausgeben |
| Nachforderung dokumentieren | Tatsächliches Kontaktdatum, Adressat und Inhalt speichern; keine Nachricht erzeugen oder versenden |
| Unterschriften vorhanden | Beide Unterschriften und vollständige inhaltliche Übereinstimmung für diese Daten-/Scanversion bestätigen |
| Für Dossier bereitstellen | Geprüfte Fassung lokal kopieren; keine externe Verarbeitung behaupten |
| Unklaren Übergabeausgang klären | Erst nach Prüfung, dass keine Übergabe erfolgte und kein alter Prozess mehr läuft, Wiederholung ermöglichen |

Die Rückblickcodes D/E (bestehende Zuordnung zu genügend/ungenügend) lösen die
Prüfpflicht für Rückblick und Ausblick desselben Falls aus. Fehlender
Uneinigkeitsmarker löst keine zusätzliche Aufgabe aus. Die Bestätigung der
Unterschriften behauptet keine Einigkeit mit der Beurteilung.

## Daten- und Versionserhalt

Migration 005 ergänzt die Prüfnachweise, Scanreferenzen, Entscheidungen und
Übergabeversuche. Veröffentlichte Migrationen 001–004 bleiben unverändert.
Bestehende Dokumentzeilen, IDs, Pfade und Unterschriftenkennzeichen werden bei
der Migration nicht überschrieben. Frühere Scanprüfungen bleiben ausdrücklich
Altbestand; Bearbeiter oder Prüfzeitpunkt werden nicht erfunden. Der vorhandene
HR-Startpfad überspringt die alte Scanregel-Korrektur bereits. Ein vorbereiteter
Wiederanlauftest prüft den Erhalt der Ausblickpflicht.

Neue Bestätigungen speichern Benutzer, Zeitpunkt, Datenprüfsumme und konkrete
Scanprüfsumme im Entscheidungsverlauf. Der alte allgemeine Wert
`signature_checked` wird dafür nicht pauschal gesetzt. Eine neue Fachdatenversion
erhält einen eigenen Prüfnachweis. Eine andere Scanversion öffnet die Sichtprüfung
erneut; eine identische Datei behält ihren bisherigen Prüfstand. Alle Originale
bleiben erhalten. Detailseite, Führungszähler und Abschlusskontrolle verwenden
denselben abgeleiteten Prüf-/Bereitstellungsstand aus `hr_return_status`. Quellenänderungen und veraltete Zuordnungs-/Revisionsstände
blockieren die jeweilige Aktion.

Ein zusätzlicher Scan kann direkt aus der offenen PDF-Prüfung einem bestehenden
Rücklauf zugeordnet werden. Download und erneuter Upload sind dafür nicht nötig.
Auch danach öffnet der Original-Link dieses Eingangs dessen tatsächliche Datei,
nicht versehentlich das zugehörige digitale PDF. Die fachlichen Daten werden
nicht doppelt übernommen. Unterschiedliche Inhalte sind kein automatischer
Ersetzungsfall: Die Übereinstimmung muss ausdrücklich geprüft werden; andernfalls
ist eine korrigierte Fassung bzw. fachliche Klärung nötig.

## Technische Bereitstellung und externe Wirkung

Vor der Dateikopie wird ein Übergabeversuch gespeichert. Ein unterbrochener
oder unklarer Versuch wird nicht automatisch wiederholt. Nach geklärtem
technischem Fehler bleibt die Unterschriftenprüfung erhalten. Ein schon als
bereitgestellt dokumentierter Rücklauf wird auch dann nicht nochmals kopiert,
wenn ein nachgelagerter Prozess die Datei inzwischen abgeholt hat.

Bestehende externe Dateinamen werden beibehalten. Würde ein anderer Rücklauf
denselben Ablagenamen verwenden, bleibt die neue Bereitstellung zur Klärung
gesperrt, auch wenn die frühere Datei bereits abgeholt wurde. Die Unterstützung
mehrerer solcher Rückläufe im externen RPA-Namensvertrag ist noch abzustimmen;
es wird kein neuer Dateinamensvertrag behauptet.

Trifft eine negative Rückblickbeurteilung erst nach bereitgestelltem Ausblick
ein, bleibt die bisherige Bereitstellung sichtbar. Die neue Nachweisprüfung
wird möglich; ein zusätzlicher externer Korrekturbedarf bleibt offen. Dieser
Entwurf erfindet keinen Bestätigungsweg für eine tatsächlich erfolgte externe
Korrektur und ersetzt keine externe Datei stillschweigend.

## Importwege und Mail

Der reguläre Word-/Scan-Prüfweg bleibt manuell. Frühere Arbeitsmappen-PDFs mit
Rückblick-/Ausblick-Datenblock werden im HR-Modus in dieselbe Prüfung geführt;
der Datenblock allein bewirkt keine automatische neue Freigabe. Der bestehende
administrative Kein-MD-Weg bleibt erhalten. Bereits gespeicherte Fachdaten und
historische Dokumente bleiben zugänglich. Alte Freigabe-/Scanrouten verweisen
auf die konkrete Rücklaufprüfung und umgehen deren Versionsbindung nicht.

Der Outlook-Eingangsadapter liefert weiterhin keinen Nachrichtentext. Deshalb
wird im neuen Modell aus erfolgreichen Anhängen nicht auf fehlende zusätzliche
Anliegen geschlossen. Diese Mails bleiben zur manuellen Klärung in Outlook;
«Prüfung erledigt» erzeugt weiterhin keinen späteren Verschiebeauftrag. Eine
automatische Erkennung zusätzlicher Mailanliegen ist nicht implementiert.

## Validierung und noch offene Automatik

Die statische Syntaxprüfung ist erfolgreich: 80 Python-Dateien in `webapp`
und `tests`, 49 Jinja-Vorlagen; `git diff --check` ohne Beanstandung.
Dies prüft keine SQL-Ausführung, Migration, Dateikopie oder Bedienabläufe.

Die 21 neuen E-Ablaufprüfungen sind im erfolgreichen Gesamtlauf enthalten: beide Gesprächsteile, Scan allein,
zwei Unterschriften, identische/neue Scanversion, neue Fachdatenversion,
Nachforderung, späte Prüfpflicht, Originalintegrität, Zuständigkeitswechsel,
technischer Wiederanlauf, verbrauchter Übergabeordner, CSRF, alte Routen,
Mailablage, abgeleitete Aufgaben, bestehende Führungs-/Abschlussübersichten sowie
Migration und erneuter Start.

Der frühere lokale Ergebnisabruf blieb ohne Nachweis; der Prozess ist nicht
mehr verfügbar. Der neue Testlauf verwendet einen frischen Ubuntu-Runner,
synthetische Testdaten und keine lokalen HR-Dateien. Der Python-Testprozess
läuft in einem eigenen Linux-Netzwerk-Namensraum, mit leerer Umgebung und
zusätzlichem Python-Audit-Hook gegen Netzwerk- und Kindprozesse. Outlook und
produktive Ablagen sind nicht angeschlossen.

Der erste CI-Lauf zeigte eine fehlende Testabhängigkeit (PyMuPDF); diese ist
nun in requirements-dev.txt deklariert. Der anschliessende Gesamtlauf bestand:
[CI-Nachweis](https://github.com/maxandul/md-app-v2026/actions/runs/40657897837).
Er umfasst auch Migration, Wiederanlauf und bestehende Regressionstests.
Ein visueller E-Bediennachweis auf dem vorgesehenen Windows-System steht aus.

Für eine Formatfreigabe fehlen noch repräsentative ausgefüllte Rückblicke,
Ausblicke, Probezeitformulare und Scans mit geprüften Sollwerten für sämtliche
benötigten Angaben. Vorhandene Word-Vorlagen und ein älterer Ausblick konnten
inhaltlich gesichtet werden. Deren lokale Materialisierung für Parserprüfungen
scheiterte an der Verbindung des Dateizugriffs. Ein einzelnes älteres PDF und
synthetische Parserbeispiele belegen keine zuverlässige automatische Verarbeitung
aller Varianten. Insbesondere bietet der bestehende Parser weder eine
vollständige automatische Gesamtbeurteilungs-Auslesung noch eine nachgewiesene
OCR-Verarbeitung.

Die Automatik bleibt deshalb aus. E1 bereitet den nachvollziehbaren
Ausnahme-/Nachweisweg vor; E2 benötigt Formatvalidierung und den anschliessenden
vollständigen Automatikpfad. Die anschliessende Konsolidierung ist in [Etappe F](UMSETZUNG_F_UEBERSICHT.md)
separat dokumentiert.

Kein Merge nach `main`, keine produktive Migration, keine echten Nachrichten
und keine produktive Dossierübergabe. Den Entwurf erst nach bestandenem Nachtest
und separat geprüfter Einführung aktivieren.
