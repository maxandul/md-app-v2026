# Prüfung des Ordnerimports für Vorjahresziele

Die Oberfläche unter Stammdaten unterstützt Ordner mit Unterordnern und die
Einzelauswahl alter/neuer Word- und PDF-Ausblicke. Dateien werden vor einer
expliziten Quellenauswahl und Bestätigung ausschliesslich als Vorschau eingelesen.

## Nachweise

136 Python-App-Tests und fünf JavaScript-Tests erfolgreich.

- Geliefertes altes Word-/PDF-Beispiel: je ein Leistungsziel und drei
  Entwicklungsziele. Alle vier Zielfelder und Kompetenzen stimmen nach
  Vereinheitlichung von Leerzeichen/Zeilenumbrüchen zwischen Word und PDF überein.
  Die Originale und ihre personenbezogenen Inhalte sind nicht im Repository.
- Verschachtelte Word-Controls werden durch Lesen der sichtbaren Tabellenzellen
  einmal erfasst. Frei eingegebene Kriterien werden ebenfalls gelesen. Aktuelle
  Tabellen ohne Ziel-Controls werden mit derselben Methode verarbeitet.
- Fortsetzungen ohne Titel am Anfang der unmittelbar nächsten PDF-Seite werden
  bei gleicher Kompetenz an das vorhergehende Ziel angehängt; unzuordenbare
  Fragmente blockieren die Übernahme. Getrennte PDF-Textruns erhalten anhand
  eingebetteter einfacher Schriftbreiten fehlende Wortzwischenräume.
- Synthetische HTTP-Tests decken Stapelanlage, Upload, Vorschau, Quellenauswahl,
  Import und Nutzung durch den Word-Zielexport ab; ausserdem falsches Jahr,
  Rückblick statt Ausblick, beschädigte Datei, identische/abweichende Quellen,
  wiederholte Bestätigung und unzulässige Dateipfade.
- JavaScript-Tests prüfen Einzelübertragung aus Ordnerauswahl, Ausschluss anderer
  Dateitypen, Grössenbegrenzung und Wiederaufnahme nach Teilfehlern über die Vorschau.

## Grenzen

Keine OCR und keine freie Dokumenten-KI: Zieltabellen müssen zur erkannten
MD-Struktur passen. Die vier Seiten des gelieferten alten PDFs wurden visuell
geprüft. Ein echter Browser-Klicktest des nativen Ordnerdialogs war hier nicht
möglich: Der Playwright-Browserdownload lieferte kein gültiges Archiv. Der
Browserablauf ist durch HTTP-Tests und simuliertes DOM abgedeckt und am
Windows-Arbeitsplatz einmal mit Edge/Chrome zu prüfen. Keine produktiven
Personendaten importiert, keine Originaldateien verändert.
