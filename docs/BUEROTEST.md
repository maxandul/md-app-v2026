# Bürotest MD-App v2026

## Ziel

Der Bürotest prüft den Ablauf mit den realen SAP-Strukturen, früheren
Word-Formularen, dem produktiven klassischen Outlook und der vorgesehenen lokalen
Ablage. Produktive Daten bleiben ausschliesslich auf dem verwalteten HR-Gerät.

## 1. Teststand vorbereiten

1. Den aktuellen Stand von `main` beziehen und einmalig `INSTALL_MD.bat`
   ausführen. Für den Produktivstarter wird keine virtuelle Umgebung benötigt.
2. Prüfen, dass die Anwendung nur unter `127.0.0.1:5050` erreichbar ist.
   Das parallel laufende ABW-Tool muss einen anderen Port verwenden.
3. Ein persönliches Systemadministrationskonto anlegen.
4. Unter **Administration** ein Backup erstellen und auf einem genehmigten,
   verschlüsselten Medium ablegen.
5. Zuerst mit einer Kopie der produktiven Dateien und nicht mit den einzigen
   Originalen arbeiten.

## 2. SAP-Import prüfen

Der Beispielexport umfasst 1'246 Datensätze, davon 1'186 aktive Personen und 183
unterschiedliche referenzierte Führungskräfte. Dieses Mengengerüst ist für die
lokale Verarbeitung vorgesehen.

Beim realen Import insbesondere kontrollieren:

- Anzahl aktiver und wegen `BsGrd = 0` ignorierter Personen,
- identische Dubletten gegenüber widersprüchlichen Mehrfacheinträgen,
- mehrere Anstellungen derselben Personalnummer,
- mehrere Bewilligungen derselben Anstellung,
- Führungskräfte, die selbst nicht als aktive Person im Export vorkommen,
- Eintritt, Austritt und Ende Probezeit an Stichproben.

## 3. Vorjahresziele aus Word-Formularen übernehmen

Die Datei `MD_Textfeldanalyse_20260917_140612.xlsx` ist nur eine anonymisierte
Strukturanalyse. Sie enthält keine Texte oder Personalnummern. Der Import liest
deshalb die ursprünglichen `.docx`- beziehungsweise `.docm`-Ausblickformulare.

Zuerst nur eine Vorschau ausführen:

```powershell
python import_legacy_forms.py "K:\Pfad\zu\den\Formularen" `
  --goal-year 2026 `
  --report "K:\Geschuetzter_Pfad\MD_Vorjahresimport_Vorschau.json"
```

`--goal-year` bezeichnet das Jahr, für das die im Ausblick vereinbarten Ziele
gelten. Die Vorschau verändert die Datenbank nicht. Der Detailbericht enthält
Dateinamen und Personalnummern und muss daher geschützt abgelegt werden.

Wichtige Statuswerte:

| Status | Bedeutung und Handlung |
|---|---|
| `matched` | Person und Anstellung sind eindeutig; Import ist möglich. |
| `already_imported` | Identischer Dateiinhalt wurde bereits übernommen. |
| `duplicate_in_batch` | Identischer Dateiinhalt kommt im aktuellen Ordner mehrfach vor; nur die erste Datei wird berücksichtigt. |
| `ambiguous_assignment` | Mehrere aktive Anstellungen, aber keine Anstellungsnummer im Formular; manuell klären. |
| `assignment_not_found` | Formular und aktueller SAP-Stand enthalten unterschiedliche Anstellungsnummern. |
| `person_not_active` | Personalnummer ist im aktuellen SAP-Stand nicht aktiv. |
| `missing_person_number` | Keine auswertbare Personalnummer im Formular. |
| `no_goals` | Ausblickformular enthält keine erkannten ausgefüllten Ziele. |
| `not_outlook` | Datei wurde nicht als Ausblick erkannt. |
| `read_error` | Datei ist kein lesbares Word-Open-XML-Dokument. |

Nach fachlicher Kontrolle und einem Backup denselben Befehl mit `--apply`
ausführen:

```powershell
python import_legacy_forms.py "K:\Pfad\zu\den\Formularen" `
  --goal-year 2026 `
  --report "K:\Geschuetzter_Pfad\MD_Vorjahresimport_Ergebnis.json" `
  --apply
```

Der Import ist fehlertolerant: Nur Dateien mit Status `matched` werden
übernommen. Dubletten, Rückblicke, leere beziehungsweise nicht auslesbare
Formulare sowie nicht eindeutig zuordenbare Fälle werden im Bericht ausgewiesen
und automatisch übersprungen. Identische Kopien müssen nicht vorgängig manuell
bereinigt werden.

Der Import übernimmt Leistungs- und Entwicklungsziele, Messkriterien, Schritte,
Termine und die zugehörige Kompetenz. Er ist anhand der Datei-Prüfsumme
idempotent. Bei der Erzeugung der neuen Arbeitsmappe erscheinen diese Angaben als
unveränderte Quelleninformation für den Rückblick.

## 4. Stichproben in der Arbeitsmappe

Mindestens folgende Konstellationen prüfen:

- regulärer Fall mit Vorjahreszielen,
- Person ohne Vorjahresformular,
- mehrere Leistungsziele,
- mindestens ein Entwicklungsziel mit Kompetenz,
- Neueintritt und Probezeitfall,
- interne Veränderung oder Mehrfachanstellung,
- sehr lange Texte gemäss P95 der Textfeldanalyse,
- Speichern, erneutes Öffnen sowie Rückblick- und Ausblick-PDF.

## 5. Outlook und Rücklauf

1. START- und Update-Dateien zunächst an ein internes Testkonto adressieren.
2. Im Outlook-Entwurf Absender, Empfänger, Anhang und S/MIME-Markierung prüfen.
3. Verschlüsselung vor dem manuellen Versand sichtbar kontrollieren.
4. Rücklauf mit einem Standard-PDF, D/E-/Uneinigkeitsfall und einer zusätzlichen
   Fremdbeilage testen.
5. Prüfen, dass ein wiederholter Postfachscan keine Dubletten erzeugt.
6. Nachrichten werden bis zur separaten Freigabe nicht automatisch verschoben.

## 6. Backup und Restore

Den Restore ausschliesslich mit einer Testkopie durchführen:

1. Einen klar erkennbaren Testfall anlegen und Backup erstellen.
2. Den Testfall verändern.
3. Backup über **Administration** wiederherstellen.
4. Neuanmeldung, Datenstand, Prozessdateien und Dossier-Übergabe prüfen.
5. Resultat und Dauer im Betriebsjournal festhalten.

## 7. Testergebnis festhalten

Für jede Abweichung mindestens Bildschirm, betroffene Personalnummer,
Anstellungsnummer, erwartetes Ergebnis und tatsächliches Ergebnis notieren. Keine
produktiven Dateien oder Personendaten in GitHub oder ungeschützte Kanäle laden.
