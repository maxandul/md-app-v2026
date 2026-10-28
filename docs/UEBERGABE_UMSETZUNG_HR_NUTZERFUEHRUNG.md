# Übergabe: Umsetzung der HR-Nutzerführung

**Fortschreibung vom 28. Oktober 2026:** A–F und die begrenzte E2-Automatik sind
im Branch `feat/hr-e2-release-preparation` implementiert und automatisiert
geprüft. Aktueller Stand: [E2-Ergebnisse](UMSETZUNG_E2_RELEASE.md) und
[Testpaket / Einführung](START_NEUE_HR_VERSION.md). Der Nutzer hat anschliessend
den direkten Einstieg mit laufender Mängelbehebung gewählt. `MD-HR.bat` aktiviert
die neue Oberfläche mit manueller Rücklaufprüfung; tatsächliche Installation und
Windows-/Integrationsnachweise bleiben offen. Der folgende Auftrag
hält die ursprünglichen Anforderungen fest; seine damaligen Ist-Aussagen sind
kein aktueller Implementierungsstand.

Stand: 27. Oktober 2026  
Repository: maxandul/md-app-v2026  
Konzeptbranch: `docs/prozessuebersicht-nutzerfuehrung`

## 1. Auftrag und aktueller Stand

Die bestehende Flask/Jinja/SQLite-App unterstützt HR bei Rückblicken, Ausblicken, Feedback und Probezeit-Rückblicken. Sie soll rund 1000 Mitarbeitende mit wiederkehrenden und unterjährigen MDs übersichtlich verwalten. Bestehende Funktionen erhalten und zu verständlichen, zusammenhängenden Abläufen verbinden.

In diesem Konzeptauftrag wurden nur Dokumente geändert. Keine Fachlogik implementiert, keine Migration durchgeführt, kein Merge nach main und keine produktiven Nachrichten versandt. Der frühere Codeabgleich bezog sich auf main `9d7ca779afc18e9bd9c6607a5b3dbe8465537a18`; vor Umsetzung aktuellen Stand und inzwischen erfolgte Änderungen prüfen. Keine aktuellen Codeeigenschaften allein aus diesem alten Abgleich ableiten.

Der Nutzer will die Umsetzung einem frischen Agenten übergeben. Dieser Auftrag ersetzt die Rekonstruktion des langen Gesprächs. Er ist keine Anweisung, sofort produktiv zu migrieren oder main zu überschreiben. Auf separatem Implementierungsbranch arbeiten und nachvollziehbare, getestete Etappen liefern.

Es gab eine interaktive Vorschau mit fiktiven Daten im Gespräch. Sie zeigt nur erste Navigations- und Bearbeitungsbeispiele, keine vollständige Anwendung und keinen erfolgreich getesteten Produktablauf. Sie ist keine Voraussetzung für die Umsetzung; alle relevanten Anforderungen stehen hier und in den verlinkten Dokumenten. Kein unverbindliches Vorschauverhalten als Fachregel übernehmen.

## 2. Dokumente und Verbindlichkeit

Zuerst diesen Auftrag, dann:
1. [Gesamtkonzept](GESAMTKONZEPT_HR_UEBERSICHT.md): Perspektiven, Navigation, Listen, Sprache.
2. [Umsetzungsplan](UMSETZUNGSPLAN_NUTZERFUEHRUNG.md): Codeabgleich, Abhängigkeiten, Etappen A–F und Prüfplan.
3. [Zielnachreichung](SEITENENTWURF_ZIELNACHREICHUNG.md): erste vollständige Lieferung.
4. [Rücklauf und Stammdaten](SEITENENTWURF_RUECKLAUF_STAMMDATEN.md): weitere Bearbeitungsseiten.
5. [Prozessübersicht](PROZESSUEBERSICHT_NUTZERFUEHRUNG.md): vollständiger fachlicher Kontext und Varianten.

Bestätigte Regeln sind verbindliche Anforderungen. Datenbankschema, genaue Menügestaltung und technische Lösung bleiben begründete Implementierungsentscheidungen. Als offen markierte Fachfragen nicht selbst erfinden. Bei Widersprüchen gilt die jüngste bestätigte Regel, insbesondere die selektive Unterschriftenprüfung samt Scan-Ausnahme in Abschnitt 4. Historische Ist-Beschreibungen sind keine Sollanforderungen.

## 3. Bestätigte Gesamtstruktur

| Einstieg | Inhalt und Zweck |
|---|---|
| Arbeit → Arbeitsübersicht | Zu bearbeiten, Warten auf Rückmeldung, Verlauf; Frist/Überfälligkeit filterbar. Konkrete nächste Aktion statt allgemeiner Prüfhinweise |
| Arbeit → Eingänge | Mail und Upload gemeinsam; Dokumentart, Verwendung, Zuordnung, Einzelstatus und Herkunft. Mail bleibt Klammer, nicht zweite unabhängige Freigabe |
| Mitarbeitende | Suche nach Name/PN; Anstellung/OE bei Mehrfachanstellung; laufende Ereignisse und Historie über Jahre |
| Führungskräfte | Tatsächliche Verantwortung je Teil, offene Fälle zuerst; Sammelaktionen nach Auswahl; Historie und eigener Feedbackbereich |
| Arbeit → Versand | Erzeugte Fassungen, Empfänger, Entwürfe, tatsächlicher Versand und Wiederaufnahme. Einstieg auch direkt aus einer Fallauswahl |
| Stammdaten → Aktualisieren | SAP-Vorschau mit Alt-/Neuwerten und Auswirkungen; Übernahme getrennt von MD-Folgeentscheidungen |
| Feedback-Übersicht | Global filterbare Sammlungen je Führungskraft/Jahr; zusätzlich bei der Führungskraft erreichbar |
| Arbeit → Übergaben | Dossierbereitstellung und SAP-Export klar unterscheidbar; Voraussetzungen, Fehler und bestätigte Wirkung |
| Auswertungen | Fachliche Kennzahlen und Arbeitsstände mit Zeitraum/OE/weiteren Filtern |
| Administration / Hilfe | Separat erreichbar, nicht im Vordergrund der täglichen Fallarbeit |

Alle Einstiege referenzieren dieselben Fachobjekte und Aufgaben. Keine separat zu schliessenden Kopien einer Aufgabe. Menübezeichnungen dürfen im konsistenten Entwurf verfeinert werden, die fachliche Auffindbarkeit muss erhalten bleiben.

Fallseiten zeigen zuerst Person, Anstellung, Anlass/Zeitraum, Stand, Verantwortung und nächste Aktion; danach Bearbeitung und Verlauf. Originalvergleich und Korrektur direkt am Vorgang. Navigation aktiv markieren, Breadcrumbs, stabile Direktlinks und Rückkehr mit erhaltenen Filtern/Sortierung/Seite.

Listen kompakt, serverseitig suchen/filtern/paginieren. Zähleinheiten Personen/Gesprächsteile/Aufgaben benennen. Auswahl dieser Seite gegenüber allen Treffern eindeutig machen. Offene Altjahresfälle standardmässig sichtbar halten. Sammelaktionen zeigen Umfang, Empfänger und ausgeschlossene Einträge; Zustand vor Ausführung erneut prüfen.

Kurze handlungsbezogene Texte, Details aufklappbar. Fachlich relevante Warnungen nicht verstecken. Einheitliche Begriffe für dieselben Schritte. Deutsch mit Du-Ansprache und Schweizer Schreibweise.

## 4. Unverhandelbare Fachregeln

### Fortlaufender Betrieb und Verantwortung
- Jahr/Kampagne organisiert Planung und Auswertung, blockiert keine neuen oder offenen unterjährigen Vorgänge.
- Rückblick und Ausblick können unterschiedliche Führungskräfte, Zeiträume und Formular-OE haben.
- Bestätigtes Beispiel: Bei Übertritt im zweiten Halbjahr übernimmt die alte Führungskraft den Rückblick, die neue den Ausblick. Keine weiteren Zeitraumsregeln daraus erfinden.
- Vertretung auch aus anderen Gründen, für einen oder beide Teile; Personen/Führungskräfte aus Listen auswählen.
- Formular-OE je Teil aus Mitarbeiter-OE oder OE der zugewiesenen Führungskraft auswählen und historischen Stand erhalten.
- SAP-Updates respektieren manuelle MD-Entscheidungen. Fehlender Datensatz beweist keinen Austritt. Importzeitpunkt beweist kein Übertrittsdatum. Fehlende Historie bleibt unbekannt.

### Ziele, Korrektur, Versand
- Alte Ausblicke aus Mail/Upload führen in dieselbe direkte Zielprüfung; kein Download und erneuter Upload als notwendiger Prozessschritt.
- Original, Extraktion, bearbeiteter Entwurf und bestätigte Zielversion unterscheiden. Quellenwahl reproduzierbar halten.
- Mehrere freigegebene Personen gezielt gemeinsam bearbeiten, gruppiert nach tatsächlicher Verantwortung des Rückblicks. Teilfehler halten andere zulässige Einträge nicht pauschal auf.
- Bereits eingegangener Rückblick, auch ungeprüft: Korrekturbedarf klären, keine automatisch erzeugte leere Ersatzvorlage.
- Bereits bereitgestelltes Dokument: externe Wirkung sichtbar; keine stille Ersetzung.
- Erzeugung, Outlook-Entwurf und tatsächlicher Versand sind verschiedene Zustände. Wiederholung erzeugt keine doppelten Wirkungen.

### Rückläufe und Unterschriften
- Eindeutige reguläre PDFs dürfen nach belegten formatbezogenen Validierungen automatisch verarbeitet werden. Ausnahmen führen direkt zur Klärung.
- Bei Rückblickbeurteilung „genügend“ oder „ungenügend“ sind **Rückblick und Ausblick** von Führungskraft und mitarbeitender Person zu unterschreiben. HR kontrolliert beide Unterschriften auf jedem betreffenden Scan.
- Rücksendeanweisung bleibt: digitales, maschinenlesbares PDF plus unterschriebener Scan je Teil.
- **Ein Scan allein genügt**, wenn alle benötigten Daten vollständig und zuverlässig daraus gewonnen/validiert werden können und HR die erforderlichen Unterschriften bestätigt. Fehlendes digitales PDF allein erzeugt keine Blockade oder Nachforderung.
- Unsichere Auslesung konkret prüfen; bei nicht klärbaren Angaben digitales PDF nachfordern. OCR-Erfolg allein ist kein Vollständigkeitsnachweis. Erkennungsqualität anhand repräsentativer Scans nachweisen.
- Bei Uneinigkeit gilt fachlich dieselbe Rücksendepflicht. Mangels eindeutigem Formularmarker keine systematische HR-Prüfung und keine automatisch daraus abgeleitete Aufgabe; fehlender Marker bedeutet nicht bestätigte Einigkeit.
- Datenquelle und Unterschriftennachweis sind Rollen: eine Datei kann beide erfüllen. Zwei Fassungen erzeugen keine doppelten Daten. Inhaltsabweichungen klären.
- Prüfung je Version mit Person/Zeitpunkt. Neue Fassung erneut prüfen, identische Dublette nicht. Unterschrift bestätigt nicht die Einigkeit mit der Beurteilung.
- Fehlender Scan, offene Sichtprüfung, fehlende Unterschrift und tatsächlich erfolgte Nachforderung unterscheiden. Entwurf ist keine Nachforderung. Ein unverändert erneut versuchter technischer Übergabevorgang verlangt keine neue Sichtprüfung.
- Später eingehende Beurteilung kann auch für bereits vorhandenen Ausblick Prüfbedarf auslösen; keine stille Änderung externer Ablagen.

### Feedback, Mail und Übergaben
- Feedback je Führungskraft/Jahr sammeln; Bündel und Nachträge manuell auslösen. Keine automatische Vollständigkeitsmahnung.
- Feedback-Zuordnung nicht automatisch auf temporäre MD-Vertretung ändern; keine nicht vorhandene personenbezogene Zuordnung erfinden.
- Reine MD-Mails nach erfolgreicher Verarbeitung aller Anhänge ohne weitere ungeklärte Anliegen automatisch in konfigurierten Ordner „12 Mitarbeitenden-Dialog“ verschieben.
- Zusätzliche Mailanliegen, Fremdanlagen oder unklare Anhänge verhindern automatisches Verschieben.
- „Prüfung erledigt“ verschiebt keine Mail, auch nicht indirekt beim nächsten Scan. Nach manueller Klärung verschiebt HR bei Bedarf selbst.
- Mailablage beendet keine offene Folgearbeit. Externe Verarbeitung nicht aus lokaler Bereitstellung ableiten.

## 5. Umsetzung in kontrollierten Etappen

0. Aktuellen Code, Repository-Anweisungen und Dokumente lesen; Abweichungen vom früheren Abgleich festhalten. Gesamtseitenstruktur vervollständigen. Die frühe Vorschau ist keine vollzogene UX-Abnahme.
A. Versionierte Migrationen, stabile Vorgangs-/Dokumentverknüpfungen und zentrale Verantwortungsauflösung vorbereiten. Bestehende Dienste wiederverwenden.
B. Erste vollständige Lieferung: Zieleingang → direkte Bearbeitung → Quellenfreigabe → Folgeaktion → ausgewählte Rückblicke erstellen → Versand dokumentieren. In die neue Navigation einordnen; bereits notwendige Rückblick-Verantwortung korrekt behandeln.
C. Getrennte Zuständigkeiten in allen Verbrauchern vervollständigen: Ausgabe, Versand, Rücklauf, Erinnerungen, Formular-OE.
D. SAP-Staging/Vorschau und fortlaufende unterjährige MDs; bestehende automatische Deaktivierungs-/Synchronisierungswirkung gezielt ablösen.
E. Rücklaufautomatik, selektive Unterschriftenprüfung und Scan-Annahmeregel mit nachgewiesenen Validierungen.
F. Gesamtoberfläche konsolidieren, Feedback/Auswertung/Übergaben vollständig einbinden, redundante Einstiege entfernen.

Erste Lieferung B ist kein Versprechen, dass C–F bereits funktionieren. Zwischenstände in UI und Übergabe ehrlich kennzeichnen. Nicht erst in F über die Gesamtoberfläche nachdenken. Kein Frameworkwechsel allein für diesen Auftrag.

## 6. Fachliche Abnahmefälle

| ID | Szenario | Erwartetes Ergebnis |
|---|---|---|
| A01 | Regulärer eindeutiger Rücklauf | Richtiger Teil, validierte Daten, nachvollziehbare Bereitstellung ohne unnötige HR-Aufgabe |
| A02 | Fünf nachgereichte Ausblicke, einer unklar | Vier zulässige Rückblicke gemeinsam erstellbar; ein Klärungsfall bleibt offen; Einzelstatus und Versand nachvollziehbar |
| A03 | Rückblick bereits eingegangen, Ziele kommen später | Korrekturbedarf statt leerer Ersatzvorlage; begründeter Verzicht oder korrigierter Rücklauf |
| A04 | Übertritt mit alter/neuer Führungskraft | Beide Verantwortungen bei Person sichtbar, jeweilige Teile in FK-Ansicht; SAP-Reimport erhält Entscheidung |
| A05 | SAP-Update mit Eintritt, Wechsel und fehlendem Datensatz | Vorschau und Auswirkungen; kein stiller Verlust bestehender MDs; Folgeaufgaben direkt erreichbar |
| A06 | Eintritt während laufendem Jahresprozess | Passender manuell bestätigter Anlass/Zeitraum ohne Kampagnenbarriere bearbeitbar |
| A07 | Genügend/ungenügend, Rückblick und Ausblick getrennt geliefert | Prüfpflicht für beide Teile; jeweils beide Unterschriften prüfen; Nachforderung und neue Fassung nachvollziehbar |
| A08 | Nur gut auslesbarer unterschriebener Scan | Bei validierten vollständigen Daten und HR-Bestätigung kein digitales PDF nachfordern |
| A09 | Schlechter Scan / widersprüchliche Fassungen | Konkrete Klärung; keine ungeprüfte Übernahme und keine doppelte Datenerfassung |
| A10 | Uneinigkeit ohne verlässlichen Marker | Keine automatische Prüfpflicht aus Markerabwesenheit; keine Behauptung bestätigter Einigkeit |
| A11 | Feedback-Nachtrag | Bereits gebündelte und neue Eingänge unterscheidbar, Nachtrag ohne automatische Vollständigkeitsmahnung |
| A12 | Unterbrechung, erneuter Scan/Upload, technischer Teilfehler | Wiederaufnahme am letzten Stand, keine doppelten Aufgaben, Entwürfe oder Ablagen |
| A13 | Führungskraft / Person über mehrere Jahre | Alle offenen Teile, historische Zuständigkeit und mehrere Anstellungen nachvollziehbar |
| A14 | Mail mit Zusatzanliegen / manuell erledigte Prüfung | Keine unzulässige automatische Verschiebung; Folgearbeit unabhängig von Mailablage |
| A15 | Kampagne abgeschlossen, Altfall offen, neuer unterjähriger MD | Beide bearbeitbar und offene Arbeit in Standardansicht sichtbar |

Für jede Lieferung dokumentieren: umgesetzt, automatisiert geprüft, manuell geprüft, noch offen. Tabelle ist Prüfspezifikation, kein behauptetes Testergebnis.

Mengenprüfung mit synthetischem mehrjährigem Bestand: beispielsweise 1000 Mitarbeitende × fünf Jahre × zwei reguläre Teile, zusätzlich Probezeit, Versionen und Aufgaben. Serverseitige Suche/Paginierung und stabile Auswahl prüfen; reale Antwortzeiten auf vorgesehenem System messen. Kein Leistungsversprechen ohne Messung.

## 7. Offene Fragen gezielt behandeln

| Frage | Betroffene Umsetzung / Umgang bis zur Klärung |
|---|---|
| Eintritt, Probezeit, Austritt, andere Übertrittszeitpunkte: exakte Pflicht- und Zeitraumsmatrix | Keine neue automatische Fachentscheidung erfinden; vorhandene Regeln prüfen und strittige Konstellationen mit HR klären |
| Welche Beurteilung ist SAP-massgeblich; welche Voraussetzungen gelten für Export? | SAP-Automatik erst nach fachlicher Klärung vervollständigen |
| Verlässliche Wirksamkeitsdaten im SAP-Export | Importdatum nicht als Ereignisdatum verwenden |
| Korrektur nach externer Dossier-/SAP-Verarbeitung | Bereits erfolgte Wirkung anzeigen; tatsächlichen Korrektur-/Bestätigungsweg abstimmen |
| Welche Word/PDF/Scan-Varianten bestehen Validierung zuverlässig? | Repräsentative Dokumente, Sollwerte und vorhandene Parser prüfen; unbewiesene Formate zur Klärung |
| Zusätzliche Mailanliegen erkennen | Früherer Adapter hatte keinen Nachrichtentext. Aktuellen Stand prüfen; automatische Ablage nicht allein aus Anhangserfolg ableiten |
| Globale Erinnerungssperre oder Beschränkung auf betroffene Fälle? | Bestehendes Verhalten prüfen; keine falsche Mahnung bei vorhandenem, noch ungeprüftem Rücklauf |
| Versandbereitschaft einzelner Personen gegenüber ganzer Führungslinie | Bestehende Voraussetzungen erhalten, neue pauschale Blockaden vermeiden; ungelöste fachliche Kriterien gezielt klären |
| Befristete Vertretung ganzer OE | Nicht Voraussetzung für erste Lieferung; bestätigte Mehrfachauswahl konkreter Teile zuerst |

Diese Punkte blockieren nicht pauschal die gemeinsame Grundlage und den Nachreichungsablauf. Nur abhängige Automatik bis zur Klärung zurückhalten. Technische Fragen zunächst selbst im Code prüfen, statt sie ungeprüft an HR zurückzugeben.

## 8. Datenübernahme, Tests und Abschluss je Etappe

- Mit isolierter Datenkopie arbeiten; Originale, IDs, Dokumentversionen und Versandhistorie erhalten. Historie nicht erfinden.
- Migrationen versionieren und Wiederholbarkeit prüfen; Startinitialisierung darf neue Zustände nicht zurücksetzen.
- Vor produktiver Migration vollständige Sicherung und Wiederherstellung von Datenbank, Dateien und Konfiguration nachweisen.
- Fachliche Übergänge, Wiederanlauf, Zeitpunktkonflikte und Teilfehler testen; geeignete bestehende Tests nutzen, nicht nur UI-Texte prüfen.
- Mit Testadaptern externe Wirkungen prüfen; reale Windows-/Outlook-/Dossierintegration separat im HR-Umfeld testen. Testentwurf ist kein tatsächlich erfolgter Versand.
- UX-Abnahme durch HR: ohne Projekterklärung den Fall finden, Stand/Zuständigkeit erkennen, nächste Aktion ausführen und Ergebnis nachvollziehen.
- Je Etappe Änderungen, Tests, Grenzen und offene Punkte berichten; Dokumentation auf tatsächlichen Stand bringen.
- Codeänderungen auf separatem Branch reviewbar liefern. Produktive Aktivierung und Merge nicht aus der Zustimmung zum Konzept ableiten.
