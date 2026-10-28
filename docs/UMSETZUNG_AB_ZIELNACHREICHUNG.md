# Lieferung A/B: Zielnachreichung

> Entwicklungsnachweis: Startangaben und Zwischenstände in diesem Dokument sind historisch.
> Aktuell: [MD-Web.bat und Einrichtung](START_NEUE_HR_VERSION.md).

Stand: 27. Oktober 2026. Implementierungsbranch: `feat/hr-zielnachreichung-ab`.

Fortsetzung nach bestätigter Bedienprüfung: [Lieferung C – Verantwortung je
Gesprächsteil](UMSETZUNG_C_TEILVERANTWORTUNG.md) auf einem separaten Branch. Die
folgenden Angaben beschreiben weiterhin den Lieferstand A/B.

## Ausgangspunkt und Umfang

Grundlage ist `docs/prozessuebersicht-nutzerfuehrung` bei
`67f57772899ce2168fd6aff2c6ab39fe0826ee33`. Die Übergabe und alle fünf dort
verlinkten Konzepte wurden gelesen. `main` stand beim Abgleich weiterhin auf
`9d7ca779afc18e9bd9c6607a5b3dbe8465537a18`; der Konzeptbranch ergänzt sechs
Dokumente, keine neuere Implementierung. Es gibt keine repositoryeigenen
`AGENTS.md`-Anweisungen.

Der aktuelle Code bestätigt die wesentlichen Risiken der Übergabe: alte
Word-Mailimporte übernehmen Ziele teilweise direkt, Zuständigkeiten liegen am
Gesamtfall, und die bisherige Startinitialisierung wiederholt fachliche
Backfills. Wiederverwendet werden deshalb Parser, Word-Renderer, Originalablage,
PDF-Prüfung, S/MIME-Adapter und Backupdienst. Die neue Bearbeitung erhält eigene,
versionierte Zustände und verweist auf die bestehenden Fälle/Dokumente.

Diese Lieferung enthält A/B hinter `MD_HR_GOAL_WORKFLOW=1`. Standard ist **aus**.
Es wurden ausschliesslich isolierte synthetische Daten verwendet. Keine
produktive Datenbank wurde geöffnet oder migriert, kein echter Outlook-Entwurf
erstellt und keine Nachricht versandt. Kein Merge nach `main`.

## Gesamtstruktur und Einordnung

Die folgende Zielstruktur konkretisiert die Einstiege; sie ist ein
Implementierungsentwurf und keine bereits erfolgte UX-Abnahme. Bestehende
Einstiege bleiben während der schrittweisen Umstellung erreichbar.

| Bereich | Gemeinsame Objekte / nächste Aktionen | Lieferstand |
|---|---|---|
| Arbeit / Arbeitsübersicht | Offene Aufgaben, wartende Vorgänge, Verlauf, Fristen | Bestehend; direkter Einstieg Zielnachreichungen ergänzt |
| Arbeit / Eingänge | Mail als Herkunftsklammer; Original, Verwendung und Bearbeitungsstand je Anhang | Word-Mail und Upload führen in dieselbe Zielprüfung; PDF-Ausblick direkt übernehmbar |
| Arbeit / Zielnachreichungen | Quellen prüfen → Folgeentscheidung → Rückblicke auswählen → Ausgaben prüfen | In A/B umgesetzt, unabhängig von gewähltem Durchlauf, alle offenen Jahre |
| Arbeit / Versand | Erzeugte Fassung, Empfänger, Outlook-Vorgang, bestätigter Versand | A/B-Versand mit stabilen Direktlinks; bisheriger Erstversand bleibt erreichbar |
| Mitarbeitende | Person, Anstellungen, Ereignisse, Rückblick-/Ausblick-Verantwortung, Historie | Bestehende Fallseiten verlinkt; vollständige gemeinsame Sicht folgt C/F |
| Führungskräfte | Tatsächliche Teilverantwortung, offene Teile, selektive Ausgabe, Feedback | A/B gruppiert nach Rückblick-Verantwortung; Gesamtansicht folgt C/F |
| Stammdaten / Aktualisieren | Importvorschau, übernommene Stammdaten, getrennte MD-Folgeentscheidungen | D; A/B schützt explizite Teilzuordnungen vor dem alten SAP-Abgleich |
| Feedback | Führungskraft/Jahr, Sammlungen und Nachträge | Bestehend; Konsolidierung in F |
| Arbeit / Übergaben | Dossierbereitstellung und SAP-Export, externe Wirkung und Wiederaufnahme | Bestehend; bei Zielkorrekturen externe Dossierwirkung sichtbar |
| Auswertungen | Zeitraum, OE, Personen, Gesprächsteile und Arbeitsstände | Bestehend; Konsolidierung in F |
| Administration / Hilfe | Betrieb, Vorlagen, Sicherungen, Erklärungen | Bestehend, ausserhalb der eigentlichen Zielbearbeitung |

Zielquelle, Quellenrevision, Gesprächsteil, Ausgabe und Versandgruppe besitzen
stabile IDs. Aufgabenstände werden aus diesen Objekten abgeleitet: Mailablage
oder eine zweite Liste können keine Kopie der fachlichen Aufgabe schliessen.
Listen nennen ihre Zähleinheit, suchen/filtern/paginieren serverseitig und
kennzeichnen die Auswahl als Auswahl dieser Seite. Rücklinks tragen die
Filter-/Seitenparameter mit. Die Einzelprüfung zeigt die Quellen desselben
Eingangs und bietet gemeinsames Weiterbearbeiten bestätigter Quellen.

## Implementierung und Invarianten

- `webapp/migrations.py` und `migrations/001_hr_goals.sql`: additive Migration
  mit Prüfsumme, transaktionalem Ledger und Indizes. Bestehende IDs, Originale,
  Versanddaten und Dokumentversionen werden nicht umgeschrieben. Sobald das
  neue Schema existiert, unterbleiben die alten fachlichen Startup-Backfills.
- `migrations/002_goal_withdrawals.sql`: zusätzliche Rücknahmehistorie und
  getrennte Folgeentscheidungen je Rücknahme. Migration 001 bleibt unverändert.
  Der Übergang von 001 auf 002 und wiederholter Neustart sind isoliert geprüft.
- `goal_review`: gleiche Originalbytes führen unabhängig von Mail/Upload zum
  gleichen Vorgang. Original/Extraktion bleiben erhalten; jede Speicherung
  erstellt eine Revision. Bestätigung verlangt Originalprüfung, eindeutige
  Zuordnung, Zieljahr und bei Unsicherheiten/konkurrierenden Quellen eine
  dokumentierte Klärung. Ein Versionskonflikt überschreibt keine fremde Arbeit.
- `word_packages.prior_goals`: bestätigte, bearbeitete Zielversionen werden als
  reproduzierbare Quellen mit Fingerprint in den bestehenden Resolver
  aufgenommen. Ein neu bestätigter Konkurrent macht alte Auswahlgrundlagen
  ungültig. Bereits ausgegebene Dateien bleiben unverändert.
- `goal_withdrawals`: Eine falsch freigegebene Person, Anstellung oder ein
  falsches Zieljahr kann nach Prüfung der Auswirkungen begründet zurückgenommen
  werden. Ein neuer Prüfentwurf erlaubt die richtige Zuordnung; alte Revisionen,
  Originale, Dateien und Versandnachweise bleiben erhalten. Alte Rohimporte
  derselben Datei werden nicht wieder als Ersatzquelle verwendet, auch nicht im
  bisherigen HTML-Ausgabeweg. Andere Quellen werden nicht automatisch ausgewählt.
- Noch ausschliesslich lokal vorbereitete Ziel-Versandgruppen werden bei einer
  Rücknahme abgebrochen. Gültige Ausgaben anderer Gruppenmitglieder bleiben
  erneut auswählbar. Bestehende Outlook-Vorgänge bleiben als tatsächliche
  Historie erhalten und müssen vor Abschluss der Folgen geklärt sein.
  Die bisherigen Fälle bleiben als eigene Folgeaufgaben auffindbar, auch nach
  neuer Person/Jahr-Zuordnung oder geändertem Rückblickzeitraum. Ein Abschluss
  verlangt zusätzlich die Prüfung manueller Downloads und Weitergaben.
- `part_responsibilities`: zentraler Resolver für Teile; in A/B werden
  Rückblick-Verantwortung, Zeitraum und Formular-OE für diese Nachreichung
  gepflegt. Die OE wird als historischer Wert gespeichert. SAP-Reimporte
  deaktivieren solche explizit zugeordneten Fälle nicht und erzeugen keinen
  neuen Ersatzfall nur wegen einer geänderten Führungslinie. Andere
  SAP-Wirkungen sind noch nicht auf Staging umgestellt.
- `goal_followups`: vorhandene aktuelle Rückblicke, ungeprüfte passende PDFs
  und unzugeordnete mögliche Rückläufe sperren eine neue leere Vorlage.
  Begründeter Verzicht, Rückfrage, tatsächliche Anforderung, bearbeiteter
  korrigierter Rücklauf und Wiederaufnahme sind unterschiedliche Entscheidungen.
  Ein Korrekturabschluss braucht einen neuen, geprüften, verknüpften Rücklauf;
  eine unveränderte Dublette genügt nicht. Die Prüfung externer Dossierwirkungen
  folgt auch der Kette ersetzter Dokumente; eine erneute Anforderung umgeht sie
  nicht.
- Erstellung erfolgt pro ausgewähltem Rückblick, nur mit bestätigten Quellen.
  Ein Fehler lässt andere Ergebnisse bestehen. Wiederholung verwendet die
  vorhandene Ausgabe derselben Grundlagen. Dateinamen unterscheiden Anstellung
  und Fall. Original, Daten- und Vorlagenfingerprint, Manager, OE und Zeitraum
  sind im Ausgabestand nachvollziehbar.
- `goal_delivery`: ausdrücklich geprüfte Ausgaben werden nach tatsächlicher
  Rückblick-Verantwortung gruppiert. Vor Erstellung des S/MIME-Entwurfs werden
  Grundlagen, Dateihash, Rücklaufstand, Empfänger und andere offene
  Outlook-Vorgänge erneut geprüft. Die alten Word-/Einzelversandwege prüfen die
  neuen Vorgänge ebenfalls. Eine gemeinsame Betriebssystem-Sperre schützt den
  Übergang zwischen diesen Versandwegen.
- Erzeugt, vorbereitet, Outlook-Übernahme läuft, Entwurf erstellt, Ausgang
  unklar, Versand bestätigt und abgebrochen bleiben getrennt. Bei unklarem
  Outlook-Ergebnis gibt es keinen blinden Wiederholungsversuch. HR bestätigt
  den tatsächlichen historischen Zustand mit Begründung; auch dann, wenn die
  fachlichen Daten inzwischen geändert wurden.
- Neue POST-Aktionen sind angemeldet, featuregebunden und gegen CSRF geschützt.
  Der Original-PDF-Viewer erlaubt nur die Einbettung derselben Herkunft.

## Review und isolierter Probelauf

1. Eine **separate** vollständige Testkopie von Datenbank, Storage und
   Dossierbereich bereitstellen. `instance`-Konfiguration, Secrets,
   Vorlagenkonfiguration und alle extern referenzierten Vorlagen separat
   sichern; der vorhandene ZIP-Backupdienst umfasst nicht automatisch alle
   Dateien ausserhalb seiner konfigurierten Verzeichnisse.
2. Kopie zuerst mit dem aktuellen Basisstand prüfen. Diese Lieferung ist gegen
   das Schema des oben genannten Basiscommits getestet, nicht gegen beliebige
   ältere, bisher uninitialisierte Datenbanken.
3. In der isolierten Umgebung `MD_HR_GOAL_WORKFLOW=1` setzen und auf die Kopie
   konfigurieren. Der App-Start führt die additive Migration dort einmalig aus.
   Nach Anwendung die SQL-Datei nicht verändern; weitere Änderungen erhalten
   eine neue Migrationsnummer.
4. Unter **Zielnachreichungen** mehrere alte Ausblicke einlesen oder gespeicherte
   Word-Mailanhänge direkt öffnen. Ein PDF-Ausblick kann aus seiner bestehenden
   Eingangsprüfung direkt als Zielquelle bearbeitet werden. Ein erneuter Upload
   ist nicht nötig. Das Original bleibt am bisherigen gesicherten Ort.
5. Am Original vergleichen, Zuordnung/Zieljahr gegebenenfalls zunächst als
   Entwurf speichern, Quellen vergleichen, Ziele bestätigen. Anschliessend
   ausgewählte Fälle erstellen, die Dateien prüfen und Versandgruppen öffnen.
   Der Entwurf ist ausdrücklich noch kein Versandnachweis.
6. Unterbrechung, erneuten Upload, einen bereits eingegangenen Rückblick und
   eine geänderte Rückblick-Verantwortung ausprobieren. Für Outlook nur einen
   freigegebenen Testpostfach-/Windows-Aufbau verwenden.
7. Eine absichtlich falsche Freigabe über **Falsche Freigabe zurücknehmen**
   zurücknehmen. Bisherige Unterlagen und Versandfolgen prüfen, im neuen Entwurf
   Person/Anstellung/Jahr korrigieren und erneut bestätigen. Folgen der alten
   Freigabe separat entscheiden; die neue Freigabe schliesst sie nicht.

Ein Ausschalten des Flags ist **kein Datenrollback**: bestätigte Quellen und
Schutzregeln bleiben erhalten; die neue Oberfläche ist dann nicht erreichbar.
Für einen Rollback Anwendung anhalten und eine zusammengehörige vollständige
Sicherung samt passendem Code und Konfiguration zurückspielen. Externe
Outlook-/Dossierwirkungen werden durch einen lokalen Restore nicht rückgängig.
Produktive Aktivierung ist nicht Teil dieser Lieferung.

## Prüfstand

Automatisierte Prüfung auf Windows/Python 3.12 mit synthetischen Word/PDFs,
isolierter SQLite-Datenbank und Fake-Outlook. Der letzte vollständige Testlauf
wird vor Bereitstellung unten eingetragen. Die Test-Temp-Verzeichnisse wurden
innerhalb des beschreibbaren Arbeitsbereichs angelegt; das Standard-Temp war
für den bestehenden atomaren Backup-Dateitausch im Sandbox-Kontext ungeeignet.

```powershell
$env:TEMP = 'PFAD_ZUM_BESCHREIBBAREN_TEST_TEMP'
$env:TMP = $env:TEMP
python -m pytest -q --disable-warnings
python -m pytest tests/test_goal_workflow_volume.py -q -s --disable-warnings
git diff --check
```

| Abnahmebereich | Automatisierter Nachweis | Noch separat zu prüfen |
|---|---|---|
| A02: fünf Quellen, eine unklar | Vier Ausgaben, zwei tatsächliche Rückblick-Empfänger; einzelner Rendererfehler, Wiederaufnahme ohne Dubletten | HR-Bedienbarkeit und echte Vorlagen |
| A03: Ziele nach Rücklauf | Passender/unklarer ungeprüfter Eingang sperrt Erstellung und Entwurf; Verzicht, neue Korrekturfassung, externe Wirkung | Fachlicher Abschlussweg nach externer Verarbeitung |
| A04, A/B-Anteil | Abweichender Rückblick-Manager/OE im Word und Versand; OE-Snapshot; veränderte/fehlende SAP-Führungslinie erhält Entscheidung | Alle anderen Verbraucher und übergreifende FK-/Personenansichten in C |
| A12: Wiederaufnahme | Gleiche Mail/Upload-Bytes, alte Browserrevision, zweiter DB-Zugriff, Teilfehler, Outlook-Fehler, gemeinsame Sperre | Tatsächlicher Windows-/Outlook-Abbruch während COM-Aufruf |
| Eingangsverknüpfung | PDF wechselt ohne Kopieren in Zielprüfung; bisherige Queue zeigt keine zweite Prüfung; Mail/Upload teilen Revision | Repräsentative produktive Dateiformate |
| Versandgrundlagen | Geänderte Ziele, Zuordnung, Empfänger, Dateimanipulation, neuer Rücklauf und spätere Folgeentscheidung sperren Ausgabe/Entwurf | S/MIME-Konfiguration und reale Zustellwirkung |
| Falsche Freigabe | Rücknahme, neue Person/Jahr-Zuordnung, alte Rohimporte, gemischte Gruppen, offene/versandte Outlook-Vorgänge, manuelle Weitergaben, spätere Rückläufe und geänderte Zeiträume | HR-Bedienprüfung des neuen Rücknahmeablaufs |
| Daten und Neustart | Wiederholte Initialisierung erhält Datensätze; Migrationsprüfsumme; DDL-Fehler rollt vollständig zurück | Sicherungswiederherstellung des vollständigen Zielsystems vor Produktivmigration |
| Sicherung | Originale, neue Tabellen, Revisionen, Ausgaben und Versandhistorie über bestehenden Backup-/Restoredienst wiederhergestellt und verglichen | Externe Konfiguration/Secrets/Vorlagen mit Betriebsverantwortlichen prüfen |
| Listen | 1'000 Personen × fünf Jahre, 10'500 Teile inklusive Probezeit, 10'000 Quellrevisionen; stabile Seiten und PN-Filter | Messung auf vorgesehenem HR-System |

Mengenmessung in dieser Testumgebung nach gezielter Indexierung und vorgezogener
Filterung und mit den Rücknahmeabfragen: offene Liste **0,690 s**, PN-Suche
**0,027 s**. Vor der Optimierung
waren es 17,227 s bzw. 13,049 s. Das ist eine Messung, kein Leistungsversprechen
für das Zielsystem. Die funktionale Mengenprüfung enthält bewusst keine
zeitabhängige Bestehensschwelle.

Browserprüfung: Der integrierte Browser konnte den lokalen Testserver nicht
erreichen (`ERR_CONNECTION_TIMED_OUT`). Der Anwender hat anschliessend im eigenen
Browser die synthetische Grundstrecke bis zur Gruppenvorbereitung und den
erneuten Upload positiv rückgemeldet. Einzelheiten und Grenzen stehen im
[geführten Abnahmeprotokoll](ABNAHME_AB_GEFUEHRT.md). Flask-Routen,
HTML-Rendering, Originalabruf, CSRF, Suche und fachliche Aktionen sind
automatisiert geprüft. Eine vollständige HR-Abnahme, Responsive-Darstellung,
Tastaturführung und die Bedienprüfung der neuen Rücknahme bleiben offen.

## Bewusste Grenzen / offene Fachregeln

- C–F sind nicht abgeschlossen: allgemeiner Erstversand, Rücklaufzuordnung,
  Erinnerungen, vollständige FK-/Personenansichten, SAP-Vorschau, neue
  Ereignismatrix, Scan-/Unterschriftenautomatik, Feedback und Übergaben bleiben
  im bisherigen Ablauf. Abweichende A/B-Rückblick-Zuordnungen werden in alten
  Word-Versandwegen vorsorglich gesperrt statt an falsche Empfänger versandt.
- Nach bereits erfolgter externer Dossierbereitstellung ist der fachliche
  Korrekturabschluss gesperrt und sichtbar. Der tatsächliche externe
  Korrektur-/Bestätigungsweg muss für diesen Fall mit HR geklärt werden:
  Wer bestätigt die Übernahme im Dossier, und welcher Nachweis wird erfasst?
  Die angebotene Entscheidung zwischen Rückmeldung der zuständigen Stelle,
  eigener Dossierprüfung durch HR und weiterhin offenem Ablauf wurde noch nicht
  beantwortet. Es wurde deshalb keine Abschlussregel erfunden. Ein begründeter
  Entscheid, dass keine Korrektur nötig ist, bleibt vom Korrekturabschluss getrennt.
- Eine tatsächliche Korrekturanforderung wird mit Empfänger, Datum und Inhalt
  dokumentiert. Diese Erfassung verschickt keine Mail und bestätigt keinen
  Eingang. Die Nachricht wird ausserhalb dieses Schritts tatsächlich versandt.
- Bereits bestätigte Personen-/Jahreszuordnung wird nicht überschrieben.
  Die Rücknahme öffnet einen neuen Prüfentwurf und eigene Folgeaufgaben für die
  alte Zuordnung. Nicht erfasste manuelle Weitergaben kann die App nicht erkennen;
  HR muss deren Prüfung ausdrücklich bestätigen. Die Rücknahme ruft keine
  bereits versandte Nachricht zurück und ändert keine externen Dossierdateien.
- Word wird als Original zum Öffnen angeboten; die daneben verfügbare
  Extraktion ist ausdrücklich keine originalgetreue Vorschau. Kein neuer
  OCR-/Scan-Qualitätsnachweis wird behauptet.
- Unzugeordnete mögliche Rückläufe sperren vorsichtig die Neuerstellung bis zur
  Zuordnung. Keine neue fachliche Regel für die allgemeine Erinnerungssperre.
- Der vorhandene Mailadapter liefert keinen Nachrichtentext. Neue
  Zielnachreichungs-Mails werden deshalb nicht allein nach Anhangserfolg
  automatisch verschoben. Manuell erledigte Mailprüfung bleibt unabhängig
  von offener Folgearbeit; sie löst auch beim nächsten Scan keine Verschiebung
  aus. Die sichere Erkennung zusätzlicher Mailanliegen bleibt offen.

### Letzter vollständiger Prüflauf

`python -m pytest -q --disable-warnings --maxfail=1`: **253 bestanden**,
6 Warnungen, **126,25 Sekunden**. Darin enthalten: 25 A/B-Ablauftests,
16 zusätzliche Rücknahmeprüfungen, eine Mengenprüfung und ein Test des
isolierten Übungsstarters. Die Warnungen betreffen bestehende Bibliotheken
(insbesondere PyMuPDF/SWIG). Beim Beenden meldete zusätzlich `pyreadline3` ein
ungültiges Windows-Konsolenhandle; der Testprozess endete mit Code 0.

Nach Ergänzung direkter Links zum bisherigen Versand: Rücknahme- und Mengenprüfung
erneut ausgeführt, **17 bestanden**, 1 Warnung, **13,99 Sekunden**.

Zusätzlich: JavaScript-Syntaxprüfung für `goal_workflow.js` und
`table_controls.js` erfolgreich; `git diff --check` ohne Befund.

Review-Nachtrag: Ein späterer ungeprüfter Rücklauf öffnet eine zuvor
abgeschlossene Korrektur erneut. Der isolierte Starter `HR_TEST_AB.bat`
bereitet fünf synthetische Quellen vor; Outlook und externe Übergaben bleiben
gesperrt. Siehe [geführte Abnahme](ABNAHME_AB_GEFUEHRT.md) für die bereits
positiv rückgemeldeten Bedienprüfungen und die noch offenen Prüfschritte.
