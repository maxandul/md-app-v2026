"""Startet die lokale MD-Verwaltungsanwendung."""

from __future__ import annotations

import argparse
from threading import Thread
import webbrowser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind-Adresse. Ohne Authentisierung nicht auf 0.0.0.0 setzen.",
    )
    parser.add_argument("--port", type=int, default=5050)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--open-browser", action="store_true",
        help="Nach erfolgreichem Serverstart den lokalen Browser öffnen.",
    )
    mode.add_argument(
        "--dev",
        action="store_true",
        help="Flask-Entwicklungsserver statt Waitress verwenden (nur lokal).",
    )
    return parser.parse_args()


def open_browser(url: str) -> None:
    try:
        opened = webbrowser.open(url)
    except Exception as exc:
        print(f"Browser konnte nicht geöffnet werden: {exc}", flush=True)
        opened = False
    if not opened:
        print(f"Bitte diese Adresse im Browser öffnen: {url}", flush=True)


def main() -> int:
    args = parse_args()
    print("Initialisiere MD-App, Konfiguration und Datenbank ...", flush=True)
    try:
        from webapp import create_app
        app = create_app()
    except (ValueError, OSError) as exc:
        print(f"MD-Verwaltung konnte nicht gestartet werden: {exc}")
        print("Bitte Konfiguration in instance/organisation.json und instance/word_config.json "
              "sowie Zugriffe auf Datenbank und Ablage mit der Systemadministration prüfen. "
              "Bestehende Daten nicht löschen. Hilfe: docs/BETRIEBSKONZEPT.md.")
        return 1
    app.config.update(SERVER_BIND_HOST=args.host, SERVER_BIND_PORT=args.port)
    if args.dev:
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise SystemExit("Der Entwicklungsmodus darf nur lokal gebunden werden.")
        print("Entwicklungsmodus aktiv. Nicht im Netzwerk freigeben.")
        app.run(host=args.host, port=args.port, debug=True, use_reloader=False)
        return 0
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNUNG: Netzwerkzugriff erst nach Klärung von Authentisierung und TLS freigeben.")
    from waitress import create_server
    try:
        server = create_server(app, host=args.host, port=args.port, threads=4)
    except OSError as exc:
        print(f"Server konnte nicht auf {args.host}:{args.port} gestartet werden: {exc}", flush=True)
        return 1
    port = getattr(server, "effective_port", args.port)
    url = f"http://{args.host}:{port}/arbeit"
    print(f"MD-Verwaltung läuft auf {url}", flush=True)
    print("Dieses Fenster offen lassen. Strg+C beendet die App.", flush=True)
    if args.open_browser:
        Thread(target=open_browser, args=(url,), daemon=True).start()
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nMD-Verwaltung wird beendet.", flush=True)
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
