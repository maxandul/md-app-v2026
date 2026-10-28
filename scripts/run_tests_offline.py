"""Run synthetic repository tests without Python network or child processes.

CI additionally runs this inside a fresh Linux network namespace and an empty
environment. No production configuration or local HR data is copied to CI.
"""
import os
from pathlib import Path
import sys


def block_external_effects(event, args):
    if event in {
        'socket.__new__', 'socket.connect', 'socket.sendto', 'socket.getaddrinfo',
        'socket.gethostbyname', 'socket.gethostbyaddr', 'subprocess.Popen',
        'os.system', 'os.posix_spawn', 'os.spawn', 'os.exec',
    }:
        raise PermissionError('Offline test runner blocked external operation: ' + event)


sys.addaudithook(block_external_effects)
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

raise SystemExit(pytest.main(sys.argv[1:]))
