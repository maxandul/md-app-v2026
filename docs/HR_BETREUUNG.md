# HR-Betreuung vom Erststart bis zum Folgejahr

Stand: 9. Oktober 2026 · Word-/PDF-Ablauf auf `plan-b-word-pdf`.

## Wo beginne ich?

Server starten und mit dem persönlichen Konto anmelden. Bei der ersten Einrichtung
ein Administrationskonto anlegen. Unter **Hilfe → Einrichtung** die Voraussetzungen
prüfen. Die automatisch erkennbaren Dateipfade und Einstellungen ersetzen keinen
Test von Word, klassischem Outlook, S/MIME oder Dossierablage. Diese richtet die
Systemadministration mit HR ein. Bei vergessenem Passwort ein temporäres Passwort
bei der Systemadministration anfordern.

Der Serverlink steht unter Administration. Ein geprüfter Rechner-/DNS-Name kann
als `PUBLIC_BASE_URL` hinterlegt werden; die IT muss Namensauflösung und Zugriffe
einrichten. Die Angabe allein macht den Server nicht im Netzwerk erreichbar.

## Welche Arbeit ist als Nächstes nötig?

**Arbeitsliste** zeigt alle ermittelten Aufgaben des gewählten Durchlaufs. PDF-Eingang,
Postfachprüfung und Ereignisse ohne Durchlauf gelten durchlaufübergreifend.
Aufgaben lassen sich nach Art und Text filtern. Das Cockpit zeigt zusätzlich
ungeprüfte PDFs und offene Unterschriftenprüfungen. Menüwechsel behalten den
gewählten Durchlauf bei; dessen Jahreszahlen immer mit dem bearbeiteten Dokument
vergleichen.

Unter Stammdaten einen vollständigen freigegebenen SAP-Export importieren. Eine
Teilliste kann fehlende Zuordnungen in offenen Durchläufen deaktivieren. Konflikte
an der SAP-Quelle klären und neu importieren. Das Rückblickjahr bezeichnet das
beurteilte Jahr; der Ausblick gilt für das Folgejahr. Nach Eröffnung Fälle, Umfang,
Führungslinien und Fristen prüfen. Phasenwechsel lösen keinen Versand aus.

## Wie bearbeite ich Rückläufe und Unterbrechungen?

PDFs einlesen und am Original prüfen. **Prüfentwurf speichern** sichert auch
unvollständige Eingaben und die gewählte Zuordnung; es übernimmt keine Fachdaten.
Beim Verlassen ungespeicherter Änderungen warnt der Browser. Wenn jemand dieselbe
Prüfung inzwischen geändert hat, wird eine veraltete Speicherung abgelehnt.

**Begründet zurückstellen** ist für falsche oder nicht weiter zu bearbeitende
Eingänge vorgesehen. Benötigte ungeklärte Rückläufe offen lassen. Zurückgestellte
Dateien bleiben mit Original und Begründung über den Warteschlangenfilter auffindbar
und lassen sich wieder öffnen. Suche und Seitennavigation erschliessen die gesamte
Warteschlange.

Nach fachlicher Übernahme die Fallprüfung öffnen und Unterschriften beziehungsweise
Scan prüfen. Erst dann erfolgt die Dossierbereitstellung. Bereits eingegangene
Dokumente werden wegen einer noch offenen HR-Prüfung nicht nochmals angefordert.
Solange ungeprüfte PDFs im Eingang liegen, pausieren Erinnerungsentwürfe. Fehlende
Unterlagen, beanstandete Rückläufe und nötige Scans bleiben mögliche Erinnerungsfälle.

## Was mache ich bei Sonderfällen?

| Situation | Weiteres Vorgehen |
|---|---|
| Ereignis ohne Durchlauf | Unter Dialoge den gleichnamigen Link öffnen und einem offenen Durchlauf desselben Rückblickjahres begründet zuordnen. |
| Manuelle Fehlanlage | Ohne gespeicherte offizielle Dokumente begründet aufheben. Der Vorgang bleibt nachvollziehbar; seine Pflichten werden aufgehoben. |
| Bereits vorhandener Fall derselben Person, Anstellung und Führungslinie | Bestehenden Fall prüfen. Eine doppelte Fehlanlage aufheben; fachlich unterschiedliche Gespräche durch die zuständige Stelle klären lassen. Das Datenmodell unterstützt derzeit nur einen solchen Fall pro Durchlauf. |
| Verspäteter Rücklauf nach Austritt/Wechsel | Inaktiven Fall wählen und historische Zuordnung begründen. Dadurch wird er nicht wieder zum Versand aktiviert. Geschlossenen Durchlauf vorher wieder öffnen. |
| Alte Vorjahresziele | Unter Stammdaten frühere DOCX-Ausblicke mit Vorschau importieren oder PDF-Ausblick unter Rückläufe als Zielquelle nachreichen. |
| Mehrere Zielquellen | Unter Stammdaten → Zielquellen anhand von PN, Anstellung und Zieljahr vergleichen und eine Quelle begründet wählen. Keine automatische Zusammenführung. Ändern sich Quellen, Auswahl neu prüfen. |
| Unterbrochener Outlook-Vorgang | Outlook auf tatsächlichen Versand/Entwurf prüfen und alte Serverprozesse beenden. Unter Versand den Vorgang als versendet oder nicht versendet und bereinigt klären. Eine Betriebssystemsperre verhindert die Freigabe eines noch laufenden Vorgangs. |
| Ablage-/Dateifehler | Netzwerk, Ordner und Rechte mit Systemadministration prüfen. Gespeicherten Status und Zielordner vor Wiederholung vergleichen. Fehlerreferenz und Zeitpunkt mitteilen. |
| Bereits abgelegtes Dokument korrigieren | Mit Dossier- und gegebenenfalls SAP-Verantwortlichen klären; abgelegte Belege werden nicht automatisch ersetzt. |

## Wie schliesse ich ab und beginne erneut?

SAP-Batch exportieren und tatsächlichen SAP-Import separat kontrollieren. Der
Export erfordert weiterhin den vollständigen führenden Fall, gegebenenfalls
einschliesslich Ausblick. «Bereitgestellt» bestätigt die lokale Dossierübergabe,
nicht die RPA-Verarbeitung.

In der Rücklaufphase die Abschlussprüfung öffnen. Sie zeigt offene Pflichten,
Unterschriften, Word-Versandvorgänge, noch nicht exportierte vollständige Rückblicke
sowie globale ungeprüfte PDFs und Ereignisse ohne Durchlauf. Externe Verarbeitung
prüfen. Verbleibende Aufgaben mit Begründung und zuständiger Person dokumentieren;
die Übersicht wird beim Abschluss gespeichert. Spätere Nachbearbeitung erfolgt
nach Wiederöffnung. Alte Restfälle regelmässig über die Durchlaufauswahl prüfen.

Der Folgejahreslink schlägt das nächste Rückblickjahr vor. Vor der Eröffnung einen
aktuellen vollständigen SAP-Stand bereitstellen; Fristen, Vorlagen und Vorjahresziele
erneut prüfen. Bereits erzeugte Word-Ausgaben werden bei späteren Änderungen nicht
nachträglich verändert.

## Umfang der Prüfung

Die gesamte automatisierte Suite umfasst 119 erfolgreiche Tests. HTTP- und Diensttests decken die neuen Arbeitswege, Parallelbearbeitung,
Warteschlangen über 100 Dateien, Quellenänderungen, Aufhebung/Zuordnung, Nachzügler,
Erinnerungen, Abschluss und unterbrochene Vorgänge mit synthetischen Daten ab.
Outlook wird in diesen Tests simuliert; es werden keine echten Nachrichten versendet.
Visuelle Browserbedienung sowie Windows/Word, S/MIME, DNS/Netzwerk, RPA und tatsächlicher
SAP-Import brauchen weiterhin den [Bürotest](BUEROTEST.md). Eine Garantie für alle
organisatorischen Sonderfälle lässt sich daraus nicht ableiten.
