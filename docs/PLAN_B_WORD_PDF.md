# Umstellung auf Word-Vorlagen und PDF-Rücklauf

Entscheid vom 09.10.2026: Word-Vorlagen pro Mitarbeitenden für den aktuellen
Durchlauf. Das bestehende Repository wird weitergeführt; die HTML-Arbeitsmappe
bleibt erhalten. Die Implementierung beginnt auf `plan-b-word-pdf`.

## Implementierter Stand

In der Führungslinie erzeugt das Cockpit ein ZIP mit den benötigten Formularen
pro Person. Wahlweise kann eine einzelne Person gewählt werden. Der bestätigte
Umfang hat Vorrang vor dem SAP-Vorschlag; Fälle ohne Dokumentpflicht werden
übersprungen. Probezeit-Ereignisse verwenden die Probezeitvorlage. Bestehende
Spezialfall-/Umfangsregeln wurden in diesem Schritt nicht geändert.

Stammdaten, Zeitraum und vorhandene Nebenbeschäftigungen werden frisch aus der
Datenbank gelesen. Der Rückblick erhält die Ziele des zugehörigen Zieljahres und
der Anstellung. Bei mehreren konkurrierenden Quellen oder unbekannter Kompetenz
wird die Erzeugung angehalten, statt Ziele zu vermischen oder wegzulassen. Noch
nicht importierte PDFs liefern derzeit keine Ziele; ihre Übernahme folgt mit
dem vollständigen PDF-Import.

Zusätzliche Zielzeilen werden dynamisch erzeugt. Leere Entwicklungszielzeilen
bleiben bei jeder Kompetenz bestehen. Zieltexte werden einheitlich in 9 pt mit
Zeilenumbrüchen und sichtbaren Listenzeichen ausgegeben. Tabellenüberschriften
einschliesslich Kompetenz werden bei Seitenfortsetzungen wiederholt. Alte,
unsichtbare Datumswerte der Vorlagen werden entfernt; Gesprächs- und
Unterschriftsdatum werden nicht vorbelegt.

Jede Ausgabe erhält ein eigenes Verzeichnis unter `STORAGE_ROOT/word_packages`
mit ZIP und Manifest (Fall, Zeitraum, Zielquelle und Prüfsummen). Sie wird als
Erzeugung im Administrationsprotokoll erfasst und verändert weder den Versand-
noch den Rücklaufstatus. Eine neue Erzeugung berücksichtigt nachträglich
importierte Ziele. Bereits ausgegebene oder lokal bearbeitete Word-Dateien
werden dadurch nicht verändert. Bei einem Fehler wird keine Teilausgabe
behalten.

Unter Rückläufe gibt es eine separate Vorprüfung für Word-PDFs. Sie liest
Dokumenttyp, Personalnummern, Zeitraum, Gesprächsdatum und die explizite Angabe
zur Durchführung aus. Fehlende, widersprüchliche oder ungültige Angaben bleiben
Prüffälle. Die Vorschau ist lesend: keine Fallzuordnung, keine Datenübernahme,
keine Dossierbereitstellung. Temporäre Uploads werden auch bei Fehlern entfernt.
Arbeitsmappen-PDFs behalten ihren bestehenden Importweg.

Zwei Exportwege des synthetischen Beispielrückblicks wurden geprüft:
Word «Speichern als PDF» und Microsoft «Print to PDF». Beide liefern sechs
Seiten mit lesbarem Text, aber keine AcroForm-Felder. Alle vier Textbestandteile
der sechs Leistungs- und vier Entwicklungsziele sind nach Berücksichtigung der
Silbentrennung im extrahierten Text enthalten. Dies ist noch kein Nachweis für
eine korrekte strukturierte Tabellenextraktion oder unterschriebene Rückläufe.
Die Dateien bleiben ausserhalb des öffentlichen Repositorys.

## Lokale Word-Vorlagen einrichten

1. `config/word.example.json` nach `instance/word_config.json` kopieren.
2. Die drei freigegebenen DOCX-Vorlagen unter `instance/templates/` ablegen
   und die Dateinamen in der Konfiguration anpassen. Relative Pfade beziehen
   sich auf den Ordner der Konfigurationsdatei; absolute Pfade sind möglich.
3. App neu starten. Die Führungslinie zeigt an, welche Vorlagen noch fehlen.

Alternativ verweist die Umgebungsvariable `MD_WORD_CONFIG` auf eine andere
lokale JSON-Datei. `instance/` sowie DOCX/PDF-Dateien sind bereits vom Commit
ausgeschlossen. Die Beispieldatei enthält keine internen Links oder Pfade.
Die Originalvorlagen müssen die freigegebenen Feldkennungen enthalten; eine
falsche oder veraltete Vorlage führt zu einem verständlichen Fehler.

Die neuen Module benötigen nur die Python-Standardbibliothek und vorhandene
Projektabhängigkeiten. Word/LibreOffice ist zur Erzeugung auf dem HR-Gerät
nicht erforderlich; die Führungskraft öffnet und bearbeitet die DOCX in Word.

## Festgelegte Anforderungen für die nächsten Schritte

1. Word-Versand: Erzeugung ist umgesetzt; Sammelauswahl über mehrere
   Führungslinien und Anbindung an Outlook/Versandstatus folgen.
2. PDF-Extraktion: Tabellen anhand ihrer Struktur rekonstruieren, getrennte
   Zellen und Seitenfortsetzungen berücksichtigen. Ziel, Messkriterien, Weg zum
   Ziel und Termin separat speichern. Absätze und erkennbare Listen erhalten;
   keine Zusage originalgetreuer Rich-Text-Formatierung. Silbentrennungen nicht
   pauschal mit echten Bindestrichen gleichsetzen.
3. Rücklauf: neue und alte Vorlagen unterscheiden, Unsicherheit sichtbar
   machen. Nur ausgefüllte aktuelle Einschätzungen zählen als besprochene
   Kompetenzen. Vorjahresziele zählen dafür nicht. Einigkeit wird in den neuen
   Formularen weder verlangt noch aus fehlenden Angaben abgeleitet.
4. Zuordnung und Versionen: Personalnummer, Anstellung und Zielzeitraum
   verwenden; das Gesprächsdatum kann im Folgejahr liegen. Mehrdeutige Fälle
   manuell klären. Spät eingereichte Vorjahresausblicke separat verarbeiten;
   bereits bearbeitete Rückblicke niemals still überschreiben. Inhaltliche
   Dubletten auch bei verschiedenen PDF-Exportwegen berücksichtigen.
5. Cockpit und Versand: Word-Pakete statt Arbeitsmappen als Standard anbieten;
   bestehende HTML-Erzeugung als alternative Option behalten. PDF-Import,
   Prüfabschluss, Dossierbereitstellung und SAP-Export gemeinsam testen.
6. Konfiguration: interne Links und organisationsspezifische Pfade aus dem
   veröffentlichten Code in lokale Konfiguration verschieben. Lokale Vorlagen,
   PDFs und Konfigurationen nicht ins öffentliche Repository aufnehmen.

## Noch nicht umgestellt

Der reguläre PDF-Import und die Postfachverarbeitung verlangen weiterhin den
Arbeitsmappen-Datenblock. Die neue Vorprüfung ersetzt diese Wege noch nicht.
Zieltabellenextraktion, Altvorlagenunterstützung, Word-Mailversand und die
vollständige Fall-/Versionszuordnung im PDF-Rücklauf sind folgende Arbeitspakete.
