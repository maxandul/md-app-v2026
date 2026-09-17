# ADR-001: Architektur der MD-App v2026

**Status:** Angenommen  
**Datum:** 17. September 2026

## Kontext

Die Anwendung soll auf einem verwalteten HR-Windows-Gerät laufen, mit SQLite
arbeiten und HR administrativ entlasten. Führungskräfte bearbeiten aus Gründen
der Erreichbarkeit und Datensicherheit eigenständige Offline-HTML-Arbeitsmappen.
Outlook, S/MIME und bestehende Windows-Infrastruktur müssen genutzt werden können.

Die bestehenden Projekte `abw_tool` und `md_app` enthalten erprobte technische
Muster. Die neue Anwendung muss trotzdem vollständig aus dem Repository
`md-app-v2026` installiert, gestartet, getestet und betrieben werden können.

## Entscheidung

1. Das HR-Cockpit bleibt eine serverseitig gerenderte Flask-Anwendung. Für den
   ersten produktiven Stand wird kein React-Build benötigt.
2. SQLite ist die administrative Datenquelle. Das fachliche Modell trennt Person,
   Anstellung, Bewilligung, Führungslinie, Dialogereignis, Dokumentversion und
   Exportbatch.
3. Schemaänderungen werden versioniert. Die bestehende MVP-Datenbank wird
   schrittweise auf SQLAlchemy/Flask-Migrate überführt; fachliche Funktionen
   bleiben während dieser Migration testbar.
4. Die Anmeldung übernimmt die im `abw_tool` erprobten Prinzipien: persönliche
   Konten, starke Einweg-Hashes (hier `scrypt` aus Werkzeug), Rollen, temporäre Passwörter, Sitzungsentzug und
   Begrenzung fehlgeschlagener Anmeldungen. Der Code wird in diesem Repository
   eigenständig gepflegt.
5. Outlook-Funktionen werden als Windows-Adapter gekapselt. Grundlage sind die im
   `md_app` erprobten COM-Muster für klassisches Outlook, Gruppenpostfach,
   Entwurfsmodus, Anhänge und Mailverschiebung. Fachlogik ruft COM nie direkt auf.
6. S/MIME-Versand muss vor Produktivfreigabe mit der konkreten Outlook-Version,
   dem HR-Postfach und den Zertifikaten integriert getestet werden. Ein blosses
   Setzen einer Outlook-Option gilt nicht als ausreichender Nachweis.
7. Führungskräfte erhalten weiterhin eine vollständig eigenständige HTML-Datei
   ohne externe Skripte oder Netzabhängigkeit. Das HR-Cockpit und diese
   Arbeitsmappe sind bewusst getrennte Benutzeroberflächen.
8. Analysen sind Muss-Bestandteil, werden zunächst aber als klare Filtertabellen
   und Exporte umgesetzt. Die operative Übersicht über offene Fälle hat bei der
   UI-Entwicklung Vorrang.

## Technische Randbedingungen aus den Vorgängerprojekten

- Windows-Ausführungsrichtlinien können PowerShell-Aktivierung blockieren. Starter
  rufen deshalb den Python-Interpreter der virtuellen Umgebung direkt auf.
- Paketinstallation kann im Firmennetz einen Proxy erfordern und über VPN
  abweichen. Der laufende Betrieb darf keine Internetverbindung benötigen.
- Outlook-COM setzt Windows und eine installierte, konfigurierte klassische
  Outlook-Desktopanwendung voraus. Das neue Outlook ist gesondert zu prüfen.
- Der Server darf nicht im Netzwerk freigegeben werden, bevor Anmeldung,
  Berechtigungen, Bind-Adresse und TLS beziehungsweise ein gleichwertig geschützter
  interner Zugriff geklärt sind.
- Datenbank, SAP-Exporte, PDFs, Mailanhänge, Protokolle mit Personendaten und
  Geheimnisse bleiben ausserhalb des öffentlichen Repositorys.

## Folgen

Die Lösung bleibt mit wenig Infrastruktur betreibbar und die bewährte
Windows-/Outlook-Integration kann weiterverwendet werden. Gleichzeitig entstehen
zwei klar getrennte Ausführungsumgebungen: das zentrale HR-Cockpit und die
offline verteilten Arbeitsmappen. Update-, Versions- und Rücklaufprotokolle sind
deshalb fachlich notwendige Bestandteile und keine optionale Zusatzfunktion.
