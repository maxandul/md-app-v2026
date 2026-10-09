# Umstellung auf Word-Vorlagen und PDF-Rücklauf

Entscheid vom 09.10.2026: Word-Vorlagen pro Mitarbeitenden für den aktuellen
Durchlauf. Das bestehende Repository wird weitergeführt; die HTML-Arbeitsmappe
bleibt erhalten. Die Implementierung beginnt auf `plan-b-word-pdf`.

## Implementierter erster Schritt

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

## Festgelegte Anforderungen für die nächsten Schritte

1. Word-Erzeugung: drei freigegebene Vorlagen lokal konfigurieren; Stammdaten,
   Zeiträume und Nebenbeschäftigungen abfüllen. Eine Leistungszielzeile als
   Ausgangspunkt, weitere Zeilen dynamisch ergänzen. Entwicklungsziele direkt
   bei der Kompetenz; graue Eingabefelder bleiben auch ohne importierte Ziele.
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
Automatische Word-Erzeugung, Zieltabellenextraktion, Altvorlagenunterstützung
und die vollständige Fall-/Versionszuordnung sind folgende Arbeitspakete.
