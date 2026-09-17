"""Strukturierter Auswahlkatalog gemäss Kompetenzmodell Kanton Zürich 2022."""

from __future__ import annotations


COMPETENCY_MODEL = [
    {
        "category": "Persönlichkeit",
        "motto": "Wir wissen, wer wir sind, und nehmen unsere Verantwortung wahr.",
        "competencies": [
            {
                "name": "Entwicklungsfähigkeit",
                "parts": {
                    "Lernbereitschaft": [
                        "interessiert sich aktiv für Erfahrungen anderer und ist bereit, Neues zu lernen",
                        "lernt aus Erfolgen und Misserfolgen",
                    ],
                    "Veränderungsfähigkeit": [
                        "begegnet Veränderungen mit Interesse und stellt sich auf neue Situationen ein",
                        "erkennt Möglichkeiten und Chancen von Veränderungen",
                    ],
                    "Reflexionsfähigkeit": [
                        "reflektiert eigenes Verhalten und dessen Wirkung kritisch",
                        "holt Feedback ein und leitet Entwicklungsschritte ab",
                    ],
                },
            },
            {
                "name": "Werteorientierung",
                "parts": {
                    "Integrität": [
                        "handelt umsichtig entlang von Vorgaben, Gesetzen und Vereinbarungen",
                        "verhält sich loyal und trägt Entscheidungen mit",
                    ],
                    "Ethisches Handeln": [
                        "setzt sich gegen Diskriminierung ein",
                        "spricht unprofessionelles oder unethisches Verhalten an",
                    ],
                    "Inklusionsfähigkeit": [
                        "begegnet Vielfalt vorurteilsfrei und respektvoll",
                        "zeigt Interesse und Offenheit gegenüber unterschiedlichen Lebensformen und Kulturen",
                    ],
                },
            },
            {
                "name": "Selbstmanagement",
                "parts": {
                    "Eigenverantwortung": [
                        "überprüft den eigenen Arbeitsfortschritt und übernimmt Verantwortung",
                        "nutzt den persönlichen Handlungs- und Entscheidungsspielraum",
                    ],
                    "Resilienz": [
                        "erkennt eigene Belastungsgrenzen und fordert bei Bedarf Unterstützung an",
                        "achtet auf angemessene Erholung und Ausgleich",
                    ],
                },
            },
        ],
    },
    {
        "category": "Expertise",
        "motto": "Wir kennen uns aus und wissen wie.",
        "competencies": [
            {
                "name": "Fach- und Spezialwissen",
                "parts": {
                    "Funktionsbezogenes Wissen": [
                        "verfügt über funktionsspezifisches Fachwissen und Berufserfahrung",
                        "versteht interne Abläufe und die Zusammenarbeit mit Kontaktpersonen",
                    ],
                    "Projektmanagement": [
                        "kennt die eigene Rolle und den Beitrag zur Zielerreichung im Projekt",
                        "unterstützt die erfolgreiche Umsetzung aktiv",
                    ],
                    "Verwaltungs- und Politikwissen": [
                        "kennt die politischen und rechtlichen Rahmenbedingungen",
                        "bewegt sich souverän in komplexen politischen Situationen",
                    ],
                    "Wissensmanagement": [
                        "teilt Wissen und fördert den Informationsaustausch",
                        "stellt Wissenserhalt und Wissensausbau sicher",
                    ],
                },
            },
            {
                "name": "Problemlösefähigkeit",
                "parts": {
                    "Analysefähigkeit": [
                        "erkennt Problemstellungen und geht sie methodisch und strukturiert an",
                        "analysiert Ursachen und Wechselwirkungen",
                    ],
                    "Konzeptionsfähigkeit": [
                        "erarbeitet situations- und stufengerechte Konzepte",
                        "berücksichtigt verschiedene Perspektiven und denkt in Szenarien",
                    ],
                    "Umsetzungsfähigkeit": [
                        "steuert das Vorgehen und berücksichtigt Vorgaben sowie Ressourcen",
                        "erkennt Risiken frühzeitig und initiiert Massnahmen",
                    ],
                },
            },
            {
                "name": "Planungs- und Organisationsfähigkeit",
                "parts": {
                    "Prozesskompetenz": [
                        "definiert und setzt relevante Prozesse um",
                        "prüft Prozesse auf Effizienz und zukünftige Anforderungen",
                    ],
                    "Ressourcenmanagement": [
                        "setzt Zeit, Geld und Materialien zweckmässig ein",
                        "organisiert vorausschauend und setzt Prioritäten",
                    ],
                    "Delegationsfähigkeit": [
                        "überträgt Aufgaben, Verantwortung und Entscheidungskompetenz",
                        "fördert Eigeninitiative und Selbstorganisation",
                    ],
                    "Kreativitäts- und Innovationstechnik": [
                        "wendet innovative Arbeits- und Kollaborationstechniken an",
                        "entwickelt kreative und unübliche Lösungen",
                    ],
                },
            },
        ],
    },
    {
        "category": "Tatkraft",
        "motto": "Wir gestalten Leistung und erzielen Wirkung.",
        "competencies": [
            {
                "name": "Ergebnisorientiertes Handeln",
                "parts": {
                    "Strategisches Denken und Handeln": [
                        "erkennt wesentliche Entwicklungen und zieht Schlussfolgerungen",
                        "bewertet Chancen und Risiken mit Blick auf das grosse Ganze",
                    ],
                    "Entscheidungsfähigkeit": [
                        "trifft Entscheidungen fundiert und zeitgerecht",
                        "bezieht Betroffene sinnvoll in die Entscheidungsfindung ein",
                    ],
                    "Vernetztes Denken und Handeln": [
                        "betrachtet Situationen aus verschiedenen Perspektiven",
                        "handelt bereichsübergreifend und im Interesse der Gesamtorganisation",
                    ],
                },
            },
            {
                "name": "Leistungskonstanz",
                "parts": {
                    "Durchhaltevermögen": [
                        "bleibt am Thema, auch wenn Schwierigkeiten auftreten",
                        "behält bei hohen Anforderungen eine gleichbleibende Qualität",
                    ],
                    "Belastbarkeit": [
                        "handelt auch unter erschwerten Bedingungen zielorientiert",
                        "verhält sich in Stresssituationen adäquat und verantwortungsbewusst",
                    ],
                },
            },
            {
                "name": "Leistungsorientierung",
                "parts": {
                    "Dienstleistungsorientierung": [
                        "nimmt das Gegenüber und seine Anliegen ernst",
                        "findet tragfähige Lösungen für verschiedene Anspruchsgruppen",
                    ],
                    "Qualitätsbewusstsein": [
                        "strebt hochwertige Ergebnisse an und arbeitet genau",
                        "sucht kontinuierlich nach Verbesserungsmöglichkeiten",
                    ],
                    "Wirtschaftliches Denken und Handeln": [
                        "achtet auf ein optimales Aufwand-Nutzen-Verhältnis",
                        "fokussiert auf Aktivitäten mit dem grössten Mehrwert",
                    ],
                    "Mitarbeitendenförderung": [
                        "nutzt Stärken und Potenziale der Mitarbeitenden",
                        "gibt konkrete, zeitnahe und wertschätzende Rückmeldungen",
                    ],
                },
            },
            {
                "name": "Gestaltungsfähigkeit",
                "parts": {
                    "Innovationsfähigkeit": [
                        "sucht und entwickelt neue Lösungen",
                        "sieht Fehler als Chance für Weiterentwicklung und Innovation",
                    ],
                    "Transformationsfähigkeit": [
                        "sieht und nutzt Chancen von Veränderungen",
                        "beteiligt sich aktiv an Veränderungsprozessen",
                    ],
                },
            },
        ],
    },
    {
        "category": "Soziabilität",
        "motto": "Wir gestalten Beziehungen und kommunizieren bewusst.",
        "competencies": [
            {
                "name": "Kommunikationsfähigkeit",
                "parts": {
                    "Auftrittskompetenz": [
                        "tritt glaubwürdig, selbstsicher und überzeugend auf",
                        "verhält sich situationsgerecht und schafft Vertrauen",
                    ],
                    "Ausdrucksfähigkeit": [
                        "drückt sich mündlich und schriftlich klar aus",
                        "kommuniziert kontext- und adressatengerecht",
                    ],
                    "Informationsmanagement": [
                        "filtert und hinterfragt Informationen kritisch",
                        "gibt Informationen zeitnah und gezielt weiter",
                    ],
                },
            },
            {
                "name": "Konfliktmanagement",
                "parts": {
                    "Kritikfähigkeit": [
                        "gibt Kritik konstruktiv und nimmt sie offen entgegen",
                        "zeigt Bereitschaft, das eigene Verhalten zu verändern",
                    ],
                    "Konfliktlösungsfähigkeit": [
                        "nimmt Spannungen frühzeitig wahr und spricht sie an",
                        "löst Unstimmigkeiten auf sachlicher und zwischenmenschlicher Ebene",
                    ],
                    "Widerstandsfähigkeit": [
                        "findet einen konstruktiven Umgang mit Widerständen",
                        "reagiert gelassen auf unveränderbare Rahmenbedingungen",
                    ],
                },
            },
            {
                "name": "Beziehungsmanagement",
                "parts": {
                    "Empathie": [
                        "erkennt emotionale Gefühlslagen und kann sich in andere hineinversetzen",
                        "nimmt den Stimmungsgehalt einer Situation wahr und agiert adäquat",
                    ],
                    "Integrationsfähigkeit": [
                        "integriert sich aktiv in eine Gruppe",
                        "hilft Kolleginnen und Kollegen, sich ins Team zu integrieren",
                    ],
                    "Teamfähigkeit": [
                        "arbeitet gerne mit anderen zusammen und ist kompromissfähig",
                        "trägt zu gegenseitiger Wertschätzung und zum Teamerfolg bei",
                    ],
                    "Kollaborationsfähigkeit": [
                        "erarbeitet mit unterschiedlichen Personen Lösungen für komplexe Aufgaben",
                        "nutzt in interdisziplinären Teams das Wissen aller Beteiligten",
                    ],
                    "Netzwerkfähigkeit": [
                        "kennt wichtige interne und externe Ansprechpersonen",
                        "baut tragfähige Beziehungen und Netzwerke auf und pflegt sie",
                    ],
                },
            },
        ],
    },
]


COMPETENCY_NAMES = [
    competency["name"]
    for category in COMPETENCY_MODEL
    for competency in category["competencies"]
]
