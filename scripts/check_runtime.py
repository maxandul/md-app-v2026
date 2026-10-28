"""Check installed packages visibly, without opening application data or Outlook."""
from __future__ import annotations

import importlib
import platform
import sys
import traceback
from importlib.metadata import version


def main() -> int:
    print(f"Python {platform.python_version()}: {sys.executable}", flush=True)
    packages = [
        ("flask", "Flask"), ("waitress", "waitress"), ("numpy", "numpy"),
        ("pandas", "pandas"), ("openpyxl", "openpyxl"), ("pypdf", "pypdf"),
        ("reportlab", "reportlab"),
    ]
    if sys.platform == "win32":
        packages.extend([("pythoncom", "pywin32"), ("win32com.client", "pywin32")])
    for module, distribution in packages:
        print(f"Pruefe {module} ...", flush=True)
        try:
            importlib.import_module(module)
            print(f"  OK - {distribution} {version(distribution)}", flush=True)
        except Exception:
            traceback.print_exc()
            print(f"FEHLER beim Laden von {module}. Bitte diese Ausgabe weitergeben.", flush=True)
            return 1
    print("Alle benoetigten Pakete sind vorhanden und lassen sich laden.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
