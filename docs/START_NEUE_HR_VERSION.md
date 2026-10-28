# Neue HR-Version prüfen und einsetzen

Stand: 28. Oktober 2026. Version auf `feat/hr-e2-release-preparation`, aufgebaut
auf dem vollständigen A–F-Stand. E2-Prüfergebnisse:
[UMSETZUNG_E2_RELEASE.md](UMSETZUNG_E2_RELEASE.md).

Der Nutzer wünscht den direkten Einstieg und laufende Mängelbehebung. Deshalb ist
die separate vollständige Abnahme keine vorgeschaltete Nutzungsbedingung mehr.
Die offenen Integrationsnachweise bleiben offen und werden bei der ersten Nutzung
der jeweiligen Funktion erbracht. GitHub-Schreibzugriff ist inzwischen verfügbar;
die Version wird auf dem separaten Branch bereitgestellt. `main` bleibt unverändert.

## Direkter Einstieg in den Alltag

Die kurze Schrittfolge steht in [START_HIER_PRODUKTIV.txt](../START_HIER_PRODUKTIV.txt).
Nach Sicherung, Beenden der alten App und Aktualisierung des Codes **MD-HR.bat**
starten. Der Starter verwendet den normalen App-Datenbestand, aktiviert die neue
HR-Oberfläche und setzt die automatische PDF-Übernahme ausdrücklich auf aus.
Damit sind die neuen Abläufe sofort nutzbar, während HR die Rückläufe weiterhin
vor der Übernahme prüft. Die verbesserte Feldauslesung steht bereits zur Verfügung.
Eine vorhandene `.venv` wird bevorzugt; andernfalls verwendet der Starter das
installierte Python. Er bindet wie bisher lokal an Port 5050.

Im bestehenden Git-Projekt nach Sicherung und mit sauberem Arbeitsstand:

```powershell
git fetch origin
git switch feat/hr-e2-release-preparation
.\MD-HR.bat
```

Bei ZIP-Updates nur den Programmstand aktualisieren; den bisherigen App-Ordner,
`instance`, Konfiguration und eigene Word-Vorlagen erhalten. Bei einer echten
Erstinstallation ist ein neuer Bestand beabsichtigt. Falls dagegen vorhandene
Mitarbeitende fehlen, die App beenden und den bisherigen Ordner verwenden.

Vor dem ersten echten Versand die erzeugten Dateien und Empfänger ansehen; die
erste Dossier-/SAP-Übergabe bis zum Ziel nachvollziehen. Bedienmängel können
anschliessend laufend korrigiert werden. Falsche Personenzuordnung, beschädigte
Daten oder unklare externe Übergaben im betroffenen Vorgang zuerst klären.

Die ausführlichen Schritte unten bleiben als Referenz und freiwillige Übung erhalten.

## 1. Aktualisierte Übung starten

**Mit dem Testpaket:** `MD_App_E2_Testversion.zip` vollständig in einen neuen
Ordner entpacken. Darin `START_HIER_E2.txt` öffnen. Das ZIP enthält den vollständigen
Programmstand mit A–F und E2, aber keine vorhandenen Datenbanken, Original-PDFs
oder persönlichen Einstellungen. Den bestehenden App-Ordner nicht überschreiben.

**Alternativ mit Git:** In einer getrennten Arbeitskopie mit sauberem Arbeitsstand
den mitgelieferten Patch auf den verifizierten F-Stand anwenden:

```powershell
git fetch origin
git switch -c feat/hr-e2-release-preparation d171e96cf3cfb61a1efeeafbd92298fc5529099c
git am "C:\Pfad\zum\Download\MD_App_E2_Aenderungen.patch"
```

Der Patch enthält nur die Ergänzungen seit Etappe F. Er ist kein Patch direkt
für `main`. Falls der Branchname bereits lokal existiert, dessen Stand zuerst
prüfen; keinen bestehenden Branch zurücksetzen.

`INSTALL_MD.bat` installiert die Laufzeitabhängigkeiten für das Windows-Konto.
Bei bereits eingerichteter `.venv` genügen die dort installierten Pakete aus
`requirements.txt`. Dann **HR_TEST_NEU.bat** doppelklicken und im Browser
<http://127.0.0.1:5056/arbeit> öffnen. Der bisherige Starter HR_TEST_AB.bat bleibt
als gleichwertiger Einstieg erhalten.

Jeder Start erzeugt eine neue Testdatenbank und einen neuen Testablageordner.
Outlook und Postfachscan sind gesperrt. Es werden keine vorhandenen Daten migriert.
Zum Beenden im Konsolenfenster Strg+C drücken. Ein weiterer Start erzeugt eine
frische Übung, keine Fortsetzung der vorherigen Übung.

| Prüfung | Person / Einstieg | Soll |
|---|---|---|
| Übersicht und Suche | Arbeit, Mitarbeitende, Führungskräfte | Person, Zeitraum, Verantwortung und nächste Aktion sind ohne Umwege sichtbar |
| Reguläre Automatik | Noah Keller → Rückblick und Ausblick | Beide als automatisch verarbeitet und lokal bereitgestellt sichtbar; keine behauptete HR-Unterschriftenprüfung |
| Widerspruch | Mira Steiner → Eingang `e2-klaerung.pdf` | Konkreter Hinweis zu Ja plus Nichtdurchführungsbegründung; Original öffnen, korrigieren, Entwurf speichern und wieder öffnen |
| D/E und getrennte Nachweise | Alex Huber → Rückblick und Ausblick | Jeweils passende fiktive Scankopie zuordnen; beide Unterschriften/Inhaltsgleichheit bestätigen; getrennt in den Testordner bereitstellen |
| Zielnachreichung | Arbeit → Ziele, Lena Meier | Bearbeiten, bestätigen, passenden Rückblick erstellen; kein echter Outlook-Aufruf |
| SAP-Änderungen | Stammdaten | Wechsel, Eintritt und fehlender Datensatz in Vorschau; keine stillen Folgeentscheidungen |
| Historie / Feedback / Übergaben | entsprechende Listen | Richtiger Stand, Direktlink und Rückkehr mit erhaltenen Filtern |
| Darstellung | Desktop und schmaleres Browserfenster | Kein verdeckter Hauptknopf; Tabellen bedienbar; Original/PDF lässt sich öffnen |

Die sechs gelieferten PDFs können zusätzlich über Eingänge hochgeladen werden.
Ihre Test-PNs sind nicht im synthetischen Personalbestand: deshalb ist dort eine
fehlende Zuordnung korrekt. Nicht auf eine beliebige erfundene Person umstellen,
um einen erfolgreichen Import zu erzwingen. Ihre feldgenaue Erkennung wird mit
dem separaten E2-Prüfskript geprüft.

## 2. Offene Funktionsnachweise bei der ersten Nutzung

Diese Schritte sind noch offen und können aus dem Linux-Testlauf nicht bestätigt
werden. Der direkte Einstieg ist davon zu unterscheiden. Die erste Nutzung jeder
externen Funktion gezielt begleiten; bei Bedarf eine getrennte Testkopie verwenden.
Die gesperrte synthetische Übung nicht zu produktiven Pfaden umbiegen.

- Word-Ausgaben mit den tatsächlich konfigurierten Vorlagen erzeugen, öffnen,
  ausfüllen und als PDF zurückgeben. Rückblick, Ausblick und Probezeit prüfen.
- Ausblick-Unterschriftenhinweis an die bestätigte D/E-Regel angleichen; der
  gelieferte Vorlagenstand nennt dort bisher nur «ungenügend».
- Klassisches Outlook/S-MIME: Testentwurf, Versandstatus, Eingang und Wiederaufnahme.
  Kein Test an produktive Empfänger. Zusatzanliegen weiterhin in Outlook prüfen.
- Lokale Bereitstellung, RPA-Abholung und SAP-Testimport getrennt nachweisen.
  Mehrere unterjährige Rückläufe mit gleichem externem Dateinamen bleiben bis
  zur Klärung des RPA-Namensvertrags gesperrt.
- Im realistischen Bestand Suche/Listen und offene Altjahre prüfen.

Für jeden Schritt Datum, getestete Version, Ergebnis und offene Abweichung
festhalten. Die offene fachliche SAP-Auswahl-/Zeitraummatrix wird durch dieses
Update nicht neu festgelegt. Externe Korrekturen bleiben mit der zuständigen
Dossier-/SAP-Stelle zu klären.

## 3. Sicherung vor der ersten produktiven Aktivierung

1. Automatische Postfachverarbeitung pausieren, laufende Vorgänge beenden und
   zusätzliche App-Prozesse stoppen. Die verbleibende App nur noch zum Sichern nutzen.
2. Vollständiges App-Backup über Administration erstellen und
   validieren; zusätzlich `instance/organisation.json` bzw. die verwendete
   externe Konfigurationsdatei, `word_config.json`, verwendete Word-Vorlagen,
   `instance/secret_key` und den bisherigen Code-Commit geschützt sichern.
   Das bestehende App-Backup umfasst Datenbank, Dokumentablage und Dossierordner,
   nicht automatisch sämtliche externen Konfigurationsdateien/Vorlagen.
   Danach auch diese App-Instanz beenden; bis zur abgeschlossenen Sicherung
   keine weiteren Schreibvorgänge oder Übergaben ausführen.
3. Die Sicherungsdatei aufbewahren; eine Wiederherstellung in einer getrennten
   Kopie bleibt als offener Betriebsnachweis empfohlen. Nachweise/IDs,
   Originale, Zielversionen und Versandhistorie prüfen. RPA-Eingangsordner bei
   einem Restore nicht unkontrolliert erneut mit bereits abgeholten Dateien füllen.
4. Für den gewünschten direkten Einstieg den neuen Code im bestehenden
   Projekt übernehmen. Bestehenden `instance`-Ordner und Originale erhalten;
   keinen neuen leeren Produktivbestand als vermeintliches Update anlegen.

## 4. Automatik später gesondert einschalten

`MD-HR.bat` belässt die Rücklaufautomatik ausdrücklich bei aus. Zum späteren
Einschalten der geprüften, begrenzten Automatik im Projektordner setzen und den
normalen Starter verwenden:

```powershell
$env:MD_HR_GOAL_WORKFLOW = "1"
$env:MD_HR_RETURN_AUTOMATION = "1"
.\MD-Web.bat
```

Das aktiviert die neue HR-Oberfläche und die eng begrenzte PDF-Automatik.
Die versionierten Migrationen 001–005 laufen beim Start. E2 ergänzt keine neue
Schema-Migration und verändert die veröffentlichten Migrationen nicht.
Die obigen PowerShell-Werte gelten nur für diesen Prozess und seine Kinder;
für spätere Doppelklickstarts müssen sie im freigegebenen Startverfahren gesetzt
werden. Ohne sie startet der bisherige Standardmodus.

Ein risikobegrenzter erster Betrieb ist auch mit neuer Oberfläche und
`MD_HR_RETURN_AUTOMATION="0"` möglich: Rückläufe werden dann manuell geprüft.
Der Postfachscan wird dadurch nicht automatisch eingeschaltet; seine bestehende
Einrichtung bleibt separat.

## 5. Rückkehr bei Problemen

App und alle automatischen Prozesse stoppen. Nach neuen Schreibvorgängen ist
das Abschalten von `MD_HR_GOAL_WORKFLOW` **kein Datenbank-Rollback**. Entweder den
Fehler auf dem neuen Datenstand beheben oder den gesicherten Code **und** den
dazugehörigen vollständigen Daten-/Konfigurationsstand kontrolliert wiederherstellen.
Bereits extern übergebene Dokumente, Mails und SAP-Importe werden durch Restore
nicht zurückgenommen und dürfen nicht doppelt ausgelöst werden.

## Noch nicht als erledigt markieren

Windows-Bedien-/Integrationstest und reale Wiederherstellungsprobe stehen aus.
Der Nutzer hat den direkten Einstieg gewählt; ein tatsächlicher Start auf seinem
Gerät ist damit noch nicht belegt. Automatische Inhalts-/Unterschriftenbewertung beliebiger
Scans und automatische Mailverschiebung bei unbekanntem Nachrichtentext sind
nicht freigegeben. `main` wurde für diese Vorbereitung nicht verändert.
