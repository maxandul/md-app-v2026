# Feedback-Rücklauf mit Word und PDF

Ergänzung zu Plan B, 13. Oktober 2026. Die bisherigen Word-Vorlagen bleiben
verwendbar. Beim nächsten App-Start werden die zusätzlichen Datenbanktabellen
automatisch angelegt; ein manuelles Migrationsskript ist nicht erforderlich.

## Bedienung

1. Unter **Rückläufe** PDFs hochladen oder das Outlook-Postfach prüfen.
   Feedbacks werden anhand der Überschrift oder des Dateinamens erkannt.
   Bei nicht erkannten Scans in der normalen PDF-Prüfung **Als Feedback prüfen**
   wählen. Die Zuordnung lässt sich vor der Übernahme zurückwechseln.
2. In der eigenen Feedback-Prüfung das **Original öffnen**, Führungskraft und
   **Rückblickjahr** bestätigen. Die Personalnummer wird aus Formular oder
   Dateiname vorgeschlagen. Widersprüche bleiben offen. Das Gesprächsdatum
   bestimmt nicht automatisch das Jahr. Bei einer fehlenden/abweichenden
   Personalnummer ist eine Prüfnotiz erforderlich.
3. Erkannte Kompetenztexte und offene Textfelder vergleichen und ergänzen.
   Geprüfte leere Felder können ausdrücklich bestätigt werden. Unbekannte
   Felder bleiben unbekannt. Bei Scans ist keine OCR enthalten.
4. **Feedback übernehmen** speichert es in der Sammlung der Führungskraft für
   dieses Rückblickjahr. Es erstellt noch kein Dossier-PDF. Entwürfe können
   gespeichert und unpassende Eingänge begründet zurückgestellt werden.
5. Unter **Rückläufe → Feedbacks → Sammlung prüfen** die Originale kontrollieren
   und **Sammel-PDF erstellen und bereitstellen** wählen, sobald die Sammlung
   abgeschlossen ist. Ungeprüfte Feedbacks werden als Hinweis angezeigt.
6. Das Sammel-PDF besteht aus Deckblatt und Originalseiten. Es liegt im
   konfigurierten Dossier-Übergabeordner. Eine zusätzliche Archivkopie bleibt
   in der App herunterladbar, auch wenn der Roboter die Übergabedatei abholt.

Dateiname: `Feedback_{Rückblickjahr}_{NachnameVG}_{VornameVG}_{PersonalnummerVG}.pdf`.
Spätere Eingänge erhalten einen eigenen `_Nachtrag_2`, `_Nachtrag_3` usw.;
bereits bereitgestellte Dateien werden nicht überschrieben.

## Schutz und Korrekturen

- Identische PDF-Dateien werden anhand ihrer Prüfsumme nur einmal angenommen,
  auch bei anderem Dateinamen oder Eingang über mehrere Mails. Ein erneut
  exportiertes PDF mit anderer Prüfsumme muss HR vergleichen; gleiche Antworten
  allein führen nicht zur Unterdrückung eines weiteren Feedbacks.
- Zuordnung ausschliesslich zu einer Führungskraft des gewählten Jahresprozesses.
  Eine Mitarbeitenden-Personalnummer oder Fall-ID wird nicht erfunden.
- Vor der Bündelung kann HR ein bestätigtes Feedback **Zur Korrektur wieder öffnen**.
  Es wird aus der Sammlung genommen und muss danach erneut bestätigt werden.
  Die vorherige Zuordnung und die Begründung werden protokolliert.
- Bereits gebündelte Feedbacks bleiben unverändert. Korrekturen an der externen
  Dossierablage müssen mit der zuständigen Stelle abgestimmt werden.
- Parallele Prüfstände sowie eine inzwischen veränderte Sammlung werden
  abgewiesen. Originaldateien werden vor Übernahme und Bündelung auf Veränderung
  geprüft. Wiederholtes Bündeln erzeugt keine zweite Ausgabe derselben Eingänge.
- Ein geschlossener Jahresprozess muss für Korrekturen/Nachträge wieder geöffnet
  werden. Noch ungebündelte Feedbacks erscheinen in der Abschlussprüfung.
- Es entstehen keine Rückblick-/Ausblickpflichten und keine Erinnerungen an
  fehlende Feedbacks. Eingegangene PDFs bleiben in der HR-Prüfwarteschlange.
- Der Postfacheingang kann erst nach Abschluss oder begründetem Zurückstellen
  der PDF-Prüfung als erledigt markiert werden. Die spätere Bündelung erfolgt
  unabhängig von der Nachricht.

## Erfasste Angaben

Nach HR-Bestätigung werden die ausgefüllten Kompetenzen sowie die Zeichenanzahl
je geprüftem Kompetenz-/Freitextfeld gespeichert. Die Prüfmaske zeigt die Texte
und ihre Zeichenanzahlen. Eine eigene aggregierte Feedback-Auswertung ist
hiermit noch nicht Bestandteil der Auswertungsseite.

Das bisherige HTML-Datenblockverfahren bleibt kompatibel und bündelt seine
Feedbacks weiterhin je Nachricht. Word-Feedbacks verwenden die neue ausdrückliche
Sammlung/Freigabe. Bereits vor diesem Update in der allgemeinen Warteschlange
liegende Word-Feedbacks über **Als Feedback prüfen** umordnen.

## Prüfung

13 neue Tests decken echte synthetische PDFs und HTTP-Aktionen ab: Erkennung,
Textfelder, manueller Scanweg, Zuordnung, Entwurf, konkurrierende Prüfstände,
Korrektur, Postfachabschluss, Dubletten, Manager-/Jahrestrennung, Bündelung,
Nachträge, bestehende Übergabedateien, manipulierte Originale und Archivdownload.
Alle 152 App-Tests erfolgreich. Microsoft Word, S/MIME und die tatsächliche
Dossier-RPA bleiben vor Ort zu prüfen. Browserdarstellung nicht live geprüft.
