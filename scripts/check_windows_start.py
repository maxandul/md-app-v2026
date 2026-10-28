"""Exercise the shipped BAT files and real HTTP startup on a Windows CI runner."""
from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile


def run_batch(app, filename, env):
    return subprocess.run(
        [os.environ['COMSPEC'], '/d', '/c', filename], cwd=app, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace', timeout=180,
    )


def check_start(app, env, marker, label):
    marker.unlink(missing_ok=True)
    log = app.parent / f'{label}-start.log'
    with log.open('wb') as output:
        process = subprocess.Popen(
            [os.environ['COMSPEC'], '/d', '/c', 'MD-Web.bat'], cwd=app, env=env,
            stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and process.poll() is None:
                if marker.exists():
                    assert marker.read_text() == 'http://127.0.0.1:5050/arbeit'
                    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with opener.open('http://127.0.0.1:5050/static/app.css', timeout=5) as response:
                        assert response.status == 200
                        assert response.read() == (app / 'webapp/static/app.css').read_bytes()
                    break
                time.sleep(0.2)
            else:
                raise AssertionError('No ready app/browser: ' + log.read_text(encoding='utf-8', errors='replace'))
        finally:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            process.wait(timeout=15)
    text = log.read_text(encoding='utf-8', errors='replace')
    assert 'Alle benoetigten Pakete sind vorhanden' in text, text
    assert 'MD-Verwaltung läuft auf' in text, text
    print(f'{label}: BAT startup, HTTP, assets and browser handoff passed', flush=True)


def main():
    if sys.platform != 'win32':
        raise SystemExit('Run this smoke check on Windows.')
    repo = Path(__file__).resolve().parents[1]
    archive = subprocess.check_output(['git', 'archive', '--format=zip', 'HEAD'], cwd=repo)
    with tempfile.TemporaryDirectory(prefix='md-start-') as temporary:
        root = Path(temporary)
        app = root / 'MD App (Starttest)'
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            source.extractall(app)
        env = {key: value for key, value in os.environ.items() if not key.startswith('MD_')}
        env['PYTHONIOENCODING'] = 'utf-8'
        # Also exercise launchers delivered as .cmd wrappers, as on managed PCs.
        wrappers = root / 'python wrapper'
        wrappers.mkdir()
        (wrappers / 'py.cmd').write_bytes(
            f'@echo off\r\n"{sys.executable}" %2 %3 %4 %5 %6 %7 %8 %9\r\n'.encode()
        )
        env['PATH'] = str(wrappers) + os.pathsep + env['PATH']
        marker = root / 'browser.txt'
        browser = root / 'browser_probe.py'
        browser.write_text(
            "import pathlib, sys, urllib.request\n"
            "opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))\n"
            "with opener.open(sys.argv[1], timeout=10) as response:\n"
            "    assert response.status == 200\n"
            "    assert '/auth/setup' in response.url\n"
            f"pathlib.Path({str(marker)!r}).write_text(sys.argv[1])\n"
        )
        env['BROWSER'] = f'"{Path(sys.executable).as_posix()}" "{browser.as_posix()}" %s'
        for label in ('python-wrapper', 'venv'):
            if label == 'venv':
                subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages', str(app / '.venv')], check=True)
            installed = run_batch(app, 'INSTALL_MD.bat', env)
            assert installed.returncode == 0, installed.stdout
            assert 'Installation abgeschlossen.' in installed.stdout, installed.stdout
            assert 'Alle benoetigten Pakete sind vorhanden' in installed.stdout, installed.stdout
            print(f'{label}: INSTALL_MD.bat completed', flush=True)
            check_start(app, env, marker, label)
        # Import failures must stop the launcher visibly before any browser handoff.
        broken = root / 'broken dependency'
        broken.mkdir()
        (broken / 'pandas.py').write_text("raise ImportError('synthetic DLL load failure')\n")
        env['PYTHONPATH'] = str(broken)
        marker.unlink(missing_ok=True)
        failed = run_batch(app, 'MD-Web.bat', env)
        assert failed.returncode != 0, failed.stdout
        assert 'synthetic DLL load failure' in failed.stdout, failed.stdout
        assert 'FEHLER beim Laden von pandas' in failed.stdout, failed.stdout
        assert not marker.exists()
        print('Broken dependency: visible error, nonzero exit, no browser passed', flush=True)


if __name__ == '__main__':
    main()
