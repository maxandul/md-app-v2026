# Seitenentwurf: Nachgereichte Ziele bis zum Korrekturversand

Stand: 26. Oktober 2026  
Status: Erster fachlicher Seitenentwurf, nicht implementiert. Alle Namen und Zahlen in Beispielen sind fiktiv.  
Grundlage: [Prozessübersicht](PROZESSUEBERSICHT_NUTZERFUEHRUNG.md), insbesondere P03, P04, P10 und S02.

## 1. Entwurfsentscheidung

HR bleibt vom Eingang bis zum Korrekturversand im Zusammenhang derselben Nachreichung. Drei Arbeitsansichten führen durch den Vorgang:

1. **Arbeitsübersicht:** Anlass erkennen und passende Aufgabe öffnen.
2. **Nachreichung bearbeiten:** Personen und Dokumente zuordnen, Ziele prüfen und bestätigen.
3. **Rückblicke erstellen und versenden:** Freigegebene Fälle auswählen, Ergebnisse prüfen und Übermittlung je Empfänger dokumentieren.

Die Person und ihre weiteren Dialoge sind verlinkt, ohne dass ein Wechsel dorthin zur regulären Bearbeitung erforderlich ist. Ein Durchlauf muss vor dem Einstieg nicht ausgewählt werden.

## 2. Ansicht A – Arbeitsübersicht

### Aufbau von oben nach unten

| Bereich | Inhalt / Bedienung |
|---|---|
| Seitentitel | „Arbeitsübersicht“ mit kurzer Orientierung: „Offene Aufgaben aus allen Dialogen.“ |
| Schnelle Einstiege | „Dokumente einlesen“, „SAP-Daten aktualisieren“, „Dialog anlegen“ |
| Arbeitszustand | Filter „Bei HR“, „Warten auf Rückmeldung“, „Technisch blockiert“, „Alle offenen“; erledigte Vorgänge über Verlauf erreichbar |
| Suche und weitere Filter | Person, Führungskraft, OE, Anlass/Dialogart, Jahr; aktive Filter sichtbar und gemeinsam zurücksetzbar |
| Aufgabenliste | Konkreter Anlass, Umfang, nächste Handlung, Datum bzw. relevante Frist |
| Betriebsinformation | Letzter Postfachscan und Automatikstatus kompakt; Fehler mit direktem Lösungsweg |

Eine lange technische Prozessbeschreibung wird hier nicht eingeblendet. Erklärungen stehen bei der jeweiligen Aktion. Anzahl der Vorgänge und Anzahl betroffener Dokumente werden ausdrücklich unterschieden.

### Beispiel einer Aufgabenliste

| Aufgabe | Kontext | Nächste Aktion |
|---|---|---|
| 5 nachgereichte Ausblicke prüfen | Von Führungskraft A · Eingang heute · Ziele 2026 | „Nachreichung prüfen“ |
| Rückblick: Anstellung zuordnen | Person B · 2 mögliche Anstellungen | „Zuordnung klären“ |
| Neue Person: Dialogbedarf prüfen | Person C · neuer SAP-Stand | „Dialog prüfen“ |
| 3 aktualisierte Rückblicke versenden | Quellen bestätigt · Ausgaben erstellt | „Versand fortsetzen“ |

Die erste und letzte Zeile illustrieren verschiedene Vorgänge bzw. verschiedene Zeitpunkte. Derselbe Vorgang wird nicht als doppelte Mail-, Import- und Versandaufgabe gezählt. Wenn innerhalb einer Nachreichung gleichzeitig Quellen ungeklärt und Ausgaben versandbereit sind, zeigt eine Zeile beide Teilstände mit den passenden Aktionen.

### Verhalten

- Klick öffnet genau den Vorgang, nicht den Beginn einer allgemeinen Rücklaufseite.
- Nach Rückkehr bleiben Filter und Position erhalten.
- Ein neu angelegter unterjähriger Dialog erscheint in derselben Übersicht.
- Wartende Aufgaben verschwinden nicht; der Filter macht sie ausdrücklich zugänglich.
- Leere Filteransicht sagt „Keine Aufgaben für diese Auswahl“ und bietet „Filter zurücksetzen“.
- „Keine offenen Aufgaben“ ist nur innerhalb des sichtbar angegebenen Filterumfangs zulässig.

## 3. Ansicht B – Nachreichung bearbeiten

### Kopfbereich

**Titel:** „Nachgereichte Ausblicke – Führungskraft A“  
**Kontext:** Eingang, Herkunft, fünf Dokumente; tatsächliche MD-Verantwortlichkeit kann je Person abweichen.  
**Bearbeitungsstand:** „4 Quellen bestätigt · 1 Klärung offen · 0 Rückblicke neu erstellt“.

Der Kopf zeigt die Schritte „Ziele prüfen“, „Rückblicke erstellen“, „Versand“. Sie sind Orientierung und Einstieg in verfügbare Arbeiten; eine ungeklärte Person blockiert nicht den Fortschritt aller anderen.

### Arbeitsbereich

| Position | Inhalt |
|---|---|
| Personenliste links | Name, Anstellung/OE, Zieljahr, Prüfstatus und konkreter offener Punkt; Auswahl der zu bearbeitenden Person |
| Kopf der Einzelprüfung | Person, Anstellung, Verwendung „Zielquelle“, Zieljahr; Zuordnung direkt korrigierbar |
| Originalbereich | Original bzw. geeignete Vorschau mit Dateiname und Herkunft; Originaldownload zusätzlich verfügbar |
| Zielbereich neben Original | Erkannte Leistungs-/Entwicklungsziele als bearbeitbare Abschnitte; Unsicherheiten konkret an der Fundstelle |
| Ergänzende Informationen | Bestehende Quellen und betroffene Rückblicke bei Bedarf aufklappen |
| Aktionsleiste | „Entwurf speichern“, „Rückfrage vermerken“, „Ziele bestätigen und weiter“ |

Die Personenliste kann für mehr Platz eingeklappt werden. Bei begrenzter Bildschirmbreite wechseln Original und Zielbearbeitung über klar benannte Ansichten; Bearbeitungsstand bleibt erhalten.

### Zielbearbeitung

Jedes Ziel bietet die vorhandenen Angaben Zieltext, gegebenenfalls Kompetenz, Messkriterien, Weg zum Ziel und Termin. HR kann Inhalte ergänzen, fehlende Ziele hinzufügen und irrtümlich erkannte Zeilen entfernen.

Ein Beispielhinweis lautet: „Der Text auf Seite 2 konnte diesem Ziel nicht eindeutig zugeordnet werden. Bitte am Original prüfen.“ Allgemeine Hinweise wie „Erkennung unklar“ ohne betroffene Stelle sollen nach Möglichkeit entfallen.

**Speicherwirkung:**
- Entwurf: Änderungen gespeichert, Quelle noch nicht freigegeben.
- Rückfrage: Grund und benötigte Klärung gespeichert, kein automatischer Mailversand.
- Bestätigung: Zuordnung und bearbeitete Zielversion freigegeben; bestehende unklare Stellen müssen dabei ausdrücklich geklärt sein.
- „Bestätigen und weiter“ öffnet die nächste ungeklärte Person; sind keine mehr offen, führt es zur Übersicht der freigegebenen Rückblicke.

Beim Verlassen mit ungespeicherten Änderungen erscheint eine Warnung. Das Original wird nie durch die bearbeiteten Zieltexte ersetzt. Bei konkurrierenden Quellen wird vor Freigabe ein gezielter Vergleich angeboten.

### Gruppenaktion

Unter der Personenliste bzw. im Kopf: **„4 freigegebene Rückblicke vorbereiten“**.

Der Button führt zur Auswahl in Ansicht C. Er bestätigt keine ungeprüften Quellen und erstellt noch keine Formulare. Eine Rückkehr zu den offenen Quellen bleibt jederzeit möglich.

### Technische Grenze

Für Word ist eine originalgetreue Vorschau noch technisch zu klären. Bis dahin darf der Entwurf eine verfügbare Textextraktion nicht als Originalansicht ausgeben. Original öffnen und bearbeitete Ziele bleiben jedenfalls direkt zugänglich.

## 4. Ansicht C – Rückblicke erstellen und versenden

Diese Ansicht hat drei aufeinander aufbauende Abschnitte. Abgeschlossene Abschnitte werden kompakt dargestellt; Ergebnisse bleiben zugänglich.

### C1 – Rückblicke auswählen

| Auswahl | Person / Anstellung | Verantwortlich für Rückblick | Grundlage | Hinweis |
|---|---|---|---|---|
| Wählbar | Person A · Ans. 1 | Führungskraft A | Bestätigte Zielversion | Bisherige Ausgabe bereits versendet |
| Wählbar | Person B · Ans. 1 | Führungskraft A | Bestätigte Zielversion | Rückblick aktualisieren |
| Wählbar | Person C · Ans. 2 | Führungskraft B | Bestätigte Zielversion | Abweichende Rückblick-Zuständigkeit |
| Nicht wählbar | Person D · Ans. 1 | Führungskraft A | Quelle ungeklärt | „Ziele weiter prüfen“ |

Hier erscheinen nur die konkret betroffenen Rückblicke. Unveränderte Ausblicke werden nicht automatisch mit erzeugt. Formular-OE und Zeitraum sind zur Kontrolle sichtbar, bei Bedarf als aufgeklappte Details.

**Hauptaktion:** „3 ausgewählte Rückblicke erstellen“.

Bereits bearbeitete oder zurückgegebene Rückblicke erhalten einen sichtbaren Korrekturhinweis und benötigen die noch fachlich festzulegende Entscheidung. Die App darf nicht allein aus einem alten Versandstatus auf gefahrlose Ersetzbarkeit schliessen.

### C2 – Ergebnisse prüfen

- Pro Person: erstellt / fehlgeschlagen, Dateilink und verwendete Zielversion.
- Erfolgreiche Ausgaben prüfen und für Versand auswählen.
- Fehler mit konkreter Wiederholungsaktion nur für betroffene Ausgaben.
- „Versand für 3 geprüfte Rückblicke vorbereiten“ führt zu C3.
- Wiederholter Einstieg verwendet vorhandene gültige Ergebnisse; keine unnötige Neuerzeugung.

Ändert sich eine Zielquelle oder Zuständigkeit seit Erstellung, kennzeichnet die App die betroffene Ausgabe als erneut zu prüfen. Eine historische Fassung bleibt erhalten.

### C3 – Versand je Empfänger

**Beispiel:** Drei geprüfte Rückblicke ergeben zwei Versandgruppen:
- Führungskraft A: Person A und Person B;
- Führungskraft B: Person C.

Je Gruppe werden Empfänger, enthaltene Dokumente, Betreff und Nachricht angezeigt. Die Nachricht beschreibt die korrigierten Unterlagen und den Umgang mit einer bereits bearbeiteten alten Fassung.

**Aktionen:** „Outlook-Entwurf erstellen“ und anschliessend „Versand bestätigen“, soweit der tatsächliche Versand geprüft wurde. Die erste Aktion bedeutet ausdrücklich noch keinen Versand.

**Nachweis:** Versandgruppe und jede enthaltene Ausgabe erhalten eine verknüpfte Bestätigung. Bei Unterbrechung wird der bestehende Outlook-Vorgang geklärt, bevor ein weiterer Entwurf entsteht.

**Ergebnis:** „3 Rückblicke übermittelt · 1 Quelle noch ungeklärt“. Der Vorgang bleibt wegen der ungeklärten Quelle offen; abgeschlossene Ausgaben erscheinen nicht erneut als versandbereit.

## 5. Zustandswechsel aus Sicht von HR

| Ereignis | Sichtbarer Stand | Nächste Handlung |
|---|---|---|
| Eingang gesichert | „Ziele prüfen“ | Dokumentprüfung öffnen |
| Korrektur als Entwurf gespeichert | „Prüfung begonnen“ | Fortsetzen |
| Rückfrage nötig | „Warten auf Rückmeldung: [Grund]“ | Antwort einarbeiten |
| Quelle bestätigt | „Rückblick zur Erstellung bereit“ | Auswahl prüfen und erstellen |
| Ausgabe erstellt | „Ergebnis prüfen“ | Ausgabe prüfen |
| Ausgabe geprüft | „Versand vorbereiten“ | Empfängergruppe öffnen |
| Outlook-Entwurf erstellt | „Versand noch nicht bestätigt“ | Tatsächlichen Versand prüfen |
| Versand bestätigt | „Übermittelt“ | Nur noch offene Personen bearbeiten |
| Neuer relevanter Datenstand | „Änderung prüfen“ | Betroffene Quelle/Ausgabe erneut beurteilen |

Diese Bezeichnungen beschreiben den vorgeschlagenen Bedienablauf, keine bereits vorhandenen Datenbankstatus. Mehrere Personen können innerhalb eines Vorgangs unterschiedliche Stände haben.

## 6. Mail und Verlauf

Mailbetreff, Absender und Anhänge bleiben im Vorgang erreichbar. Eine kompakte Verlaufsliste zeigt Eingang, Korrektur/Freigabe, Ausgabe und Übermittlung. Die Mailablage ist separat sichtbar.

Die erfolgreiche Verarbeitung wird soweit möglich aus den tatsächlichen Ergebnissen abgeleitet. Eine zusätzliche pauschale Aktion „Alles erledigt“ soll keine offenen Quellen, Korrekturen oder Versandaufträge schliessen können.

## 7. Prüfung des Entwurfs gegen die vereinbarten Anforderungen

| Anforderung | Im Entwurf berücksichtigt |
|---|---|
| Kein Download und erneuter Upload für bereits gesicherten Anhang | Direkte Weiterverarbeitung in Ansicht B |
| Ziele direkt korrigieren | Originalzugang und Bearbeitung nebeneinander |
| Mehrere Rückblicke in einem Zug | Auswahl und Sammelerstellung in C1 |
| Unklare Einzelquelle blockiert nicht die Gruppe | Einzelstatus und eingeschränkte Auswahl |
| Zuständigkeit je Gesprächsteil | Gruppierung nach Rückblick-Verantwortlichkeit |
| Aktuelle OE nicht immer richtige Formular-OE | Prüfung des gespeicherten Werts je Rückblick |
| Unterjährige und Jahresdialoge parallel | Gemeinsame Arbeitsübersicht ohne obligatorischen Durchlauffilter |
| Unterbrochene Bearbeitung fortsetzen | Entwürfe, erhaltene Ergebnisse und Versandklärung |
| Mailprüfung nicht gleich fachlicher Abschluss | Getrennte Anzeige von Herkunft, Aufgaben und Mailablage |

## 8. Grenzen und nächster Entwurfsschritt

Dieser Entwurf konkretisiert die Bedienung des Zielnachreichungsfalls. Er ist noch kein grafisch getesteter Prototyp und keine Änderung an der App.

Vor Umsetzung sind die bestehenden Datenmodelle und Übergänge insbesondere für Vorgangsverknüpfung, Zielversionen, Zuständigkeit je Teil und Sammelversand zu prüfen. Offene Fachregeln aus der Prozessübersicht bleiben offen; dieser Seitenentwurf entscheidet sie nicht implizit.

Nächster Entwurfsschritt: Die drei Ansichten visuell gegenüberstellen und anhand von S02 prüfen, ob Einstieg, Hauptaktion, Teilfortschritt und Wiederaufnahme ohne zusätzliche Erklärung verständlich sind. Danach P04-Rücklauf und P09-Stammdatenabgleich in dieselbe Bedienlogik einordnen.
