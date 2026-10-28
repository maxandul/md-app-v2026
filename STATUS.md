# MD-App: aktuelle HR-Oberfläche als Standard

Stand: 28. Oktober 2026.

- A–F und E2 sind in der Anwendung integriert.
- Installation über `INSTALL_MD.bat`, täglicher Start über `MD-Web.bat`.
- Auch der direkte Python-Start verwendet immer die neue Oberfläche.
- Die PDF-Automatik bleibt standardmässig aus; HR bestätigt die ausgelesenen Angaben.
- Zusätzliche HR-, Übungs- und Entwicklungsstarter sowie HTML-Arbeitsmappe, Demo,
  Generator und deren Versand-/Rücklaufaktionen sind entfernt.
- Gemeinsam benötigte Word-/SAP-Hilfsfunktionen sind von der entfernten Arbeitsmappe getrennt.
- Vorjahresziele, PDF-Altformate, unveränderte Migrationen und Prüfnachweise bleiben erhalten.

Aktuelle Anleitung: [Einrichtung und Betrieb](docs/START_NEUE_HR_VERSION.md).
Der E2-Bericht dokumentiert die sechs Originalprüfungen; Etappenberichte halten
historische Implementierungsstände fest. Windows-Darstellung und reale
Word-/Outlook-/RPA-/SAP-Anbindung sind weiterhin beim ersten Einsatz zu prüfen.

Geprüft nach der Bereinigung: 308 Python-Tests, 50 Unterprüfungen, acht
JavaScript-Prüfungen und alle sechs E2-Originaldateien erfolgreich. Die geringere
Testzahl gegenüber E2 folgt aus entfernten HTML-Funktionen; Erststart, Anmeldung,
Neustart und Word-Auswahl bei getrennten Zuständigkeiten sind zusätzlich geprüft.
