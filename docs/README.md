# Dokumentation MD-App 2026

Stand: 28. Oktober 2026. Standard ist Word-Erzeugung mit geprüftem PDF-Rücklauf.
Die neue HR-Version ist für den gewünschten direkten Einstieg vorbereitet;
offene Funktionsnachweise werden bei der ersten Nutzung erbracht.

| Dokument | Zweck |
|---|---|
| [Direkter Einstieg](../START_HIER_PRODUKTIV.txt) | Neue Oberfläche im Alltag, bestehende Daten behalten, Rückläufe manuell prüfen |
| [Neue HR-Version starten](START_NEUE_HR_VERSION.md) | Testpaket, Windows-Abnahme, Sicherung, Aktivierung und Rückkehr |
| [E2-Prüfergebnisse](UMSETZUNG_E2_RELEASE.md) | Sechs Originale, Parserkorrekturen, begrenzte Automatik und offene Nachweise |
| [HR-Betreuung](HR_BETREUUNG.md) | Erststart, laufende Arbeit, Ausnahmen und Folgejahr |
| [Selbständigkeitsprüfung](HR_SELBSTAENDIGKEITSPRUEFUNG.md) | Ursprüngliche Befunde mit Verweis auf die Nachbearbeitung |
| [Anforderungen](ANFORDERUNGEN.md) | Aktueller fachlicher Umfang und Grenzen |
| [Word/PDF](PLAN_B_WORD_PDF.md) | Implementierung, Einrichtung und Versionierung |
| [Technik](FLASK_SQLITE_MVP.md) | Architektur und Betriebseinstieg |
| [Bürotest](BUEROTEST.md) | Durchgehender Test auf Windows |
| [Betriebskonzept](BETRIEBSKONZEPT.md) | Rollen, Sicherung und Betriebsverantwortung |
| [Ablaufprüfung](ABLAUFPRUEFUNG_WORD_PDF.md) | Befunde des Prüfstands vom 9. Oktober; keine laufende Bedienungsanleitung |
| [Ursprüngliche Architekturentscheidung](ADR-001-ARCHITEKTUR.md) | Historische Entscheidung mit aktuellem Nachtrag |

Frühere Arbeitsmappen-Anforderungen, Architekturdetails und Testschritte bleiben
unter `historisch/` als Referenz erhalten. Sie gelten nicht als Anleitung für den
Word-/PDF-Ablauf. Die technische Kompatibilität ist weiterhin vorhanden; ihre
Oberfläche wird nur mit `LEGACY_WORKBOOKS: "enabled"` ausdrücklich eingeblendet.
