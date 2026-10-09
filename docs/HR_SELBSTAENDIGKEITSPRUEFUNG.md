# Kann HR den gesamten Ablauf ohne Einführung betreuen?

Prüfung vom 9. Oktober 2026. Lokaler Prüfstand `aad8886`, inhaltsgleich mit dem veröffentlichten Stand `ea3e5bcb` auf `plan-b-word-pdf`.

## Nachbearbeitung der Befunde

Die folgende Bewertung dokumentiert den Ausgangsstand. Inzwischen wurden Einrichtung und Hilfe, vollständige Arbeitsliste, PDF-Prüfentwürfe und Zurückstellung, Filter/Seitennavigation, Erinnerungslogik, Ereigniszuordnung, begründete Nachzügler, Outlook-Wiederaufnahme, Quellenklärung und Abschlussprüfung umgesetzt. Details und verbliebene Grenzen: [HR_BETREUUNG.md](HR_BETREUUNG.md). Das ersetzt keine Windows-/Integrationsabnahme.

## Ursprüngliches Urteil

Noch nicht durchgängig. Viele fachliche Funktionen sind vorhanden, und der reguläre Word-/PDF-Ablauf ist technisch nutzbar. Die Anwendung benötigt aber weiterhin implizites Projektwissen. Besonders bei Ersteinrichtung, Konfliktklärung, Rücklaufsteuerung, Störungen und Jahreswechsel fehlt eine vollständige Handlungsführung. Für eine selbständige Stellvertretung würde ich den aktuellen Stand deshalb noch nicht abnehmen.

Eine vollständig vorbereitete Umgebung und eine eingewiesene HR-Person sind andere Voraussetzungen als eine neue Person mit leerem System. Letzteres war der Massstab dieser Prüfung. Nicht jede seltene Ausnahme braucht eine automatische Lösung; sie braucht aber einen sichtbaren Bearbeitungsstatus, einen verantwortlichen Bearbeitungsweg und eine verständliche Erklärung.

## Prüfverfahren

- Quellcode, gerenderte HTML-Seiten, Formulare, aktuelle Dokumentation und Berechtigungen gelesen.
- Ersten Kontoeinstieg mit tatsächlich aktivierter Anmeldung und leerer isolierter Datenbank ausgeführt.
- Gezielte HTTP-/Diensttests mit synthetischen Personen: PDF-Eingang, Aufgabenübersicht, Unterschriftenfreigabe, Mahnkandidaten, unterjähriges Ereignis ohne Durchlauf, Durchlaufabschluss trotz offener Pflichten, deaktivierter Fall und Nachzügler, zweiter Jahresdurchlauf mit Zielübernahme.
- Nicht beschreibbaren Übergabeordner kontrolliert durch einen simulierten Dateisystemfehler geprüft.
- Keine echten E-Mails, produktiven Daten oder Netzwerkablagen verändert.
- Kein visueller Browser-Klicktest und keine Abnahme von Word/Outlook, S/MIME, Windows, Dossier-RPA oder SAP-Zielsystem. Aus den HTTP-Tests folgt keine Freigabe dieser Integrationen.
- Dieser Bericht bewertet den damaligen Stand. Die Nachbearbeitung ist oben sowie in HR_BETREUUNG.md festgehalten.

## Weg durch den Prozess

| Schritt aus HR-Sicht | Was bereits hilft | Was für selbständige Betreuung fehlt |
|---|---|---|
| Serverstart und Anmeldung | Starter, erstes Administrationskonto, individuelle Konten, verständliche Passwortvalidierung | Vollständige Einrichtungskontrolle; Rollen verständlich erklären; Hilfe bei nicht startendem Server oder vergessenem Passwort; benannte Zuständigkeit |
| Technische Einrichtung | Vorlagenhilfe auf Versand/Führungslinie; Serveradresse unter Administration | Zentrale Liste: Vorlagen, Pfade, Postfach, Absender, Ablage, Backup, benötigte Zugriffe – jeweils bereit/offen/Fehler, mit passender Handlung |
| SAP-Import | Import, Historie, Fundstellen betroffener Excel-Zeilen | Bezugsquelle und erwartetes Exportformat; verständliche Konfliktarten; Entscheidung und weiterer Weg nach jedem Konflikt |
| Ersten Durchlauf eröffnen | Jahr, SAP-Stand, Fristen, Phasen | Vorschau von Umfang und Folgen; Warnung bei älterem Import; Erklärung von Rückblick-/Ausblickjahr und Spezialfällen |
| Vorjahresziele | Importierte und nachgereichte Ziele werden verwendet | Alter DOCX-Import ist ein separates Kommandozeilenwerkzeug; keine geführte Bedienung oder Quellenklärung im Cockpit |
| Word-Dateien bereitstellen | Einzelausgabe, Führungslinie, Sammelausgabe, erneuter Download, Versionierung | Einfache Prüfung von Anzahl/Empfängern/Quellen; Zeitbedarf und Sammelfehler erklären; Quellenkonflikte direkt lösen können |
| Versand betreuen | Erzeugung, Entwurf, Versand und Fehler getrennt; eigene Anhänge | Sicherer Wiederanlauf nach Prozessabbruch; offene/alte Vorgänge übersichtlich bearbeiten; Weiterleitung bei fehlender Empfängeradresse |
| Rückläufe bearbeiten | Prüfmaske, Original-PDF, Fallzuordnung, Freigabe und Scan-Upload | Vollständige zentrale Aufgabenliste; Entwürfe speichern; unzuständige/falsche Dateien zurückweisen; skalierbare Warteschlange |
| Fristen und Erinnerungen | Friständerung mit Grund; Erinnerungsentwürfe | Eingereicht und von HR noch ungeprüft darf nicht dieselbe Nachforderung auslösen wie nicht eingereicht |
| Unterjährige Ereignisse | Manuelle Ereignisse mit Personalnummer und Anstellung | Ereignisse ohne Durchlauf weiterbearbeiten; Auswahlhilfen; Fehlanlage berichtigen; Nachzügler nach Wechsel/Austritt zuordnen |
| Dossier und SAP | Getrennte Übergabe und Exportbatches; Schutz vor Doppelverarbeitung | Bereitstellung von tatsächlicher externer Übernahme unterscheiden; Fehlerweg; Abgleich offener Exporte; fachliche Entscheidung über Rückblickexport vor Ausblickabschluss |
| Abschliessen und nächstes Jahr | Phasenwechsel; neuer Durchlauf; technische Zielübernahme | Abschlussprüfung mit begründeten Ausnahmen; Übergabe der Restfälle; gezielter Start des Folgejahrs mit Quellenkontrolle |

## Vor selbständigem Betrieb erforderlich

### P1 – Aufgabenübersicht vollständig und verlässlich machen

**Reproduziert:** Ein neues PDF erzeugte einen offenen Prüfdatensatz, aber Aufgabenanzahl und sämtliche Kennzahlen der Startseite blieben unverändert. Nach Bestätigung des Rückblicks war der Dokumentstatus `needs_signature_check`; es gab dennoch keine Rücklaufaufgabe für die offene Unterschriftenprüfung.

**Folge:** HR kann sich nicht darauf verlassen, dass «Jetzt zu erledigen» alle erforderlichen Arbeiten enthält. Auf der Rücklaufseite kann gleichzeitig keine weitere Fallaufgabe angezeigt werden, obwohl eine Freigabe fehlt.

**Benötigt:** Eigene Arbeitslisten und Kennzahlen für PDF-Prüfung, Zuordnung, Unterschriften, Scan, Klärung, Versand und Export. Jeder Eintrag braucht Person/Dokument, Grund, Status und direkte Aktion. Die ersten zehn Dashboard-Aufgaben dürfen nur eine Vorschau einer vollständig erreichbaren Liste sein.

Nachweis: `webapp/services/cockpit.py`, `webapp/templates/dashboard.html`, `webapp/templates/returns.html`.

### P1 – Erinnerung nach Eingang und HR-Arbeit unterscheiden

**Reproduziert:** Ein bereits übernommener Rückblick mit Pflichtstatus `received`, der auf HR-Unterschriftenprüfung wartete, wurde bei überschrittener Frist als überfällige Unterlage in die Erinnerungsmenge aufgenommen. Es wurde keine Nachricht gesendet.

**Folge:** Eine Führungskraft kann wegen einer bereits eingereichten Unterlage erinnert werden, während der offene Schritt bei HR liegt.

**Benötigt:** Getrennte Zustände «nicht eingegangen», «eingegangen, HR prüft», «Rückfrage an Führungskraft», «Scan fehlt». Nur tatsächlich extern ausstehende Leistungen nachfordern. Die Erinnerungsansicht muss die betroffenen Personen und Dokumente nachvollziehbar machen.

Nachweis: `webapp/services/reminders.py`, `document_obligations` und simulierte Fristüberschreitung.

### P1 – Unterjährige Fälle und Nachzügler durchgängig bearbeitbar machen

**Reproduziert:** Ein Ereignis mit «Ausserhalb eines Durchlaufs» wurde erfolgreich gespeichert, hatte aber keinen verknüpften Fall und erschien bei vorhandenem Durchlauf nicht auf der normal geöffneten Dialogseite. Dort wird automatisch ein Durchlauf gefiltert. Es gibt in der Auswahl keine Ansicht für unzugeordnete Ereignisse.

**Zusätzlich reproduziert:** Nach Deaktivierung eines Falls sank die Zahl passender Vorschläge für dessen verspäteten Rückblick von 1 auf 0. Die Übernahme weist einen nicht mehr aktiven Fall ausdrücklich zurück.

**Folge:** Gerade Wechsel, Austritte und verspätete Rückläufe verlangen technisches Wissen oder Umwege.

**Benötigt:** Sichtbarer Eingang für Ereignisse ohne Durchlauf, kontrollierte Zuordnung zu einem bearbeitbaren Fall, fachlich begründete Nachbearbeitung historischer/inaktiver Fälle. Fehlanlagen brauchen Berichtigung oder Aufhebung mit nachvollziehbarem Grund.

Nachweis: `create_manual_event`, `dialogs`, `matching_cases`, `confirm_import`.

### P1 – Abschluss und Jahreswechsel als eigenen Ablauf gestalten

**Reproduziert:** Über die zulässigen Phasenwechsel konnte ein Testdurchlauf auf «abgeschlossen» gesetzt werden, obwohl in der Testdatenbank noch 16 erforderliche Dokumentpflichten offen waren. Der Phasenwechsel prüft nur den erlaubten Übergang.

**Positiv reproduziert:** Ein übernommener Ausblick für 2026 lieferte beim zweiten Durchlauf 2026/2027 ein Leistungsziel und ein Entwicklungsziel als Vorjahresquelle. Die Grundlage ist vorhanden.

**Benötigt:** Abschlussvorschau mit offenen Fällen, PDFs, Versandvorgängen, Freigaben und Exporten. Restfälle entweder erledigen oder mit Grund und Verantwortlichkeit weiterführen. Anschliessend «Nächsten Durchlauf vorbereiten» mit Jahr, aktuellem SAP-Stand, Fristen, Vorlagen und Zielquellen. Abschluss ist kein Nachweis erfolgreicher RPA-/SAP-Verarbeitung.

Nachweis: `change_cycle_status`, `create_cycle`, `prior_goals`.

### P1 – Störungen verständlich und wiederaufnehmbar machen

**Reproduziert:** Ein simulierter nicht beschreibbarer Übergabeordner führte bei der Unterschriften-/Ablagefreigabe zu HTTP 500 «Internal Server Error» ohne HR-Handlungshinweis.

**Im Code bestätigt:** Für einen nach Prozessabbruch verbleibenden Word-Versandstatus `processing` fehlt die sichtbare Klärungsaktion; erneute Erzeugung und Zustellung werden blockiert. Das Verhindern einer Doppelzustellung ist richtig, der anschliessende Bearbeitungsweg fehlt.

**Benötigt:** Meldungen nach dem Muster «Was ist fehlgeschlagen? Was wurde bereits gespeichert/ausgelöst? Was soll ich jetzt tun? Wer hilft weiter?». Dateisystem-/Outlook-Fehler mit nachvollziehbarer Referenz erfassen. Wiederaufnahme darf keinen noch laufenden Versand entsperren und nicht automatisch doppelt senden.

Nachweis: `mark_signature_checked`, `confirm_digital_signature`, `word_dispatch`, `dispatch.html`.

### P1 – Einrichtung und Hilfe direkt erreichbar machen

**Reproduziert:** Nach erfolgreicher Erstkontoanlage führt die leere Startseite zum SAP-Import. Weder eine komplette Einrichtungsliste noch ein Hilfelink ist vorhanden. Die technischen Konfigurationsdateien werden erst an späteren Stellen thematisiert.

**Benötigt:** Geführter Einrichtungscheck oder eine klare Übergabe «Technische Einrichtung durch Systemadministration abgeschlossen». HR muss nicht zwingend selbst JSON-Dateien bearbeiten, muss aber erkennen können, was fehlt und wer es einrichtet. Ein Menüpunkt Hilfe mit Suche sowie passende Hilfelinks an Import, Versand, Prüfung, Export und Jahreswechsel.

Die aktuellen Dokumente sind überwiegend technische Beschreibung, Anforderungen und Testanleitung. Inhaltlich aktueller Stand ersetzt kein Anwenderhandbuch mit Fallbeispielen und Fehlersuche. Rollen müssen erklärt werden: HR-Administration hat keinen Zugriff auf den Administrationsbereich.

Nachweis: `auth/setup`, `dashboard.html`, `base.html`, `administration`, aktuelle `docs/`.

### P1 – Konfliktklärung als tatsächlichen Arbeitsweg anbieten

**Im Code und HTML bestätigt:** Die SAP-Prüfliste zeigt technische Werte wie `blocking`, `conflicting_duplicate` und `open`. Sie bietet keine Erklärung der einzelnen Konfliktarten und keine Bearbeitungsaktion. Bei mehreren Zielquellen lautet die Meldung sinngemäss «Bitte vor der Word-Erzeugung klären»; eine Quellenvergleichs- und Auswahlmaske fehlt.

**Benötigt:** Pro Konflikt verständlicher Befund, betroffene Datensätze, erlaubte Lösung und nächster Schritt. Falls die Korrektur zwingend im SAP-Export erfolgen soll, muss die App das ausdrücklich sagen und erklären, wie HR danach neu importiert und die Lösung prüft. Echte Mehrfachanstellungen und Berechtigungen dürfen nicht blind als Dubletten entfernt werden.

Nachweis: `import_detail.html`, `sap_import`, `prior_goals`; alter Word-Import in `import_legacy_forms.py`.

## P2 – Danach Bedienung und Übersicht vervollständigen

1. **Prüfwarteschlange skalieren:** Derzeit global, höchstens 100 Einträge. Filter nach Person, Jahr, Status und Zuständigkeit sowie Pagination. Falsche/nicht zuständige Dokumente begründet aus der offenen Prüfung nehmen können.
2. **Längere PDF-Prüfung sichern:** Keine Funktion zum Speichern eines unvollständigen Prüfentwurfs erkennbar; erst bestätigte Übernahme speichert geprüfte Angaben. Zwischenspeicherung und Warnung vor Verlust einbauen.
3. **Durchlaufkontext behalten:** Navigationslinks übernehmen den gewählten Durchlauf nicht. Übersicht wählt bevorzugt einen offenen Durchlauf, Dialoge standardmässig den jüngsten. Bei mehreren Jahren kann HR unbeabsichtigt den Kontext wechseln.
4. **Statusbegriffe erklären:** Technische Werte wie `received`, `completed` oder `in_bearbeitung` nicht direkt anzeigen. Versand-, Dokument-, Fall- und Durchlaufstatus unterscheiden; Bedeutung und nächste Aktion erklären.
5. **Nachbearbeitung fachlich entscheiden:** Bereits abgelegte Belege können nicht automatisch ersetzt werden. Dafür braucht HR einen dokumentierten Eskalations- und Korrekturweg. Ob ein fertiger Rückblick vor dem Ausblick nach SAP darf, ist separat zu entscheiden.
6. **Prüfmaske vereinfachen:** Relevante Felder nach Rückblick, Ausblick, Probezeit und Nichtdurchführung zeigen; Anstellung und Fall möglichst über Namen und verständliche Auswahlhilfen finden.
7. **Quellen und Ausgabe prüfen:** Vor dem Massenversand Anzahl Formulare, betroffene Personen, fehlende Ziele und blockierte Führungslinien in einer verständlichen Zusammenfassung zeigen.
8. **Übergaben abschliessen:** «Für Dossier bereitgestellt» und «SAP-Datei erzeugt» sind nicht «extern verarbeitet». Verantwortlichkeit und allenfalls manuelle Verarbeitungsbestätigung festlegen.
9. **Stellvertretung unterstützen:** Ansprechpartner, Backup-/Wiederherstellungshinweise, Start-/Stop-Anleitung und Hilfe bei Passwortverlust an den passenden Stellen verfügbar machen.
10. **Resttexte bereinigen:** Die Startseite erwähnt bei Scans noch Uneinigkeit; der Word-PDF-Weg erhebt diese nicht. Erinnerungsnachrichten verwenden weiterhin die Sie-Form. Auch nach Ausblenden alter Oberflächen bleiben fachliche Altannahmen zu prüfen.

## Empfohlene Reihenfolge der nächsten Arbeiten

1. Zuerst die operativ kritischen Lücken schliessen: Aufgabenübersicht, korrekte Erinnerungen, Nachzügler/unterjährige Fälle und sichere Störungsbearbeitung.
2. Danach Einrichtung, Konfliktklärung und Hilfe zu einem zusammenhängenden HR-Arbeitsablauf verbinden.
3. Abschluss und Folgejahr mit Übergabe offener Fälle ergänzen; fachliche Export-/Korrekturregeln dabei ausdrücklich festlegen.
4. Anschliessend dieselbe Prüfung mit einer fachkundigen HR-Person durchführen, die das Projekt nicht kennt. Sie erhält nur Testdaten und Aufgaben, keine mündliche Anleitung. Jede erforderliche Nachfrage ist ein konkreter Verbesserungsbefund.

Abnahmekriterium: Bei jedem üblichen Fall kann die Person erkennen, was passiert ist, wer als Nächstes handeln muss und wie sie diesen Schritt ausführt. Bei einer Ausnahme bleibt der Fall sichtbar und es gibt einen erklärten Lösungs- oder Eskalationsweg.
