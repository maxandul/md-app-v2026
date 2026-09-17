"""Startet die lokale MD-Verwaltungsanwendung."""

from __future__ import annotations

import argparse

from webapp import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind-Adresse. Ohne Authentisierung nicht auf 0.0.0.0 setzen.",
    )
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Flask-Entwicklungsserver statt Waitress verwenden (nur lokal).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()
    print(f"MD-Verwaltung läuft auf http://{args.host}:{args.port}")
    if args.dev:
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise SystemExit("Der Entwicklungsmodus darf nur lokal gebunden werden.")
        print("Entwicklungsmodus aktiv. Nicht im Netzwerk freigeben.")
        app.run(host=args.host, port=args.port, debug=True, use_reloader=False)
        return 0
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNUNG: Netzwerkzugriff erst nach Klärung von Authentisierung und TLS freigeben.")
    from waitress import serve

    serve(app, host=args.host, port=args.port, threads=4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
