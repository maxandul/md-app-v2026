"""Startup failures must remain visible and must not open a broken browser page."""
from unittest.mock import Mock, patch

import pytest

import run_web
from scripts import check_runtime


def test_runtime_check_reports_the_package_that_cannot_load(capsys):
    def load(name):
        if name == 'pandas':
            raise ImportError('synthetic DLL load failure')
    with patch.object(check_runtime.importlib, 'import_module', side_effect=load), \
            patch.object(check_runtime, 'version', return_value='test'):
        assert check_runtime.main() == 1
    output = capsys.readouterr()
    assert 'Pruefe pandas ...' in output.out
    assert 'FEHLER beim Laden von pandas' in output.out
    assert 'synthetic DLL load failure' in output.err
    assert 'Alle benoetigten Pakete' not in output.out


@pytest.mark.parametrize('failure_stage', ['configuration', 'port'])
def test_startup_failure_does_not_announce_running_or_open_browser(failure_stage, capsys):
    with patch('sys.argv', ['run_web.py', '--open-browser']), \
            patch('webapp.create_app') as factory, \
            patch('waitress.create_server') as server, \
            patch.object(run_web, 'Thread') as thread:
        if failure_stage == 'configuration':
            factory.side_effect = ValueError('synthetic invalid configuration')
        else:
            server.side_effect = OSError('synthetic port in use')
        assert run_web.main() == 1
        thread.assert_not_called()
    output = capsys.readouterr().out
    assert 'konnte nicht' in output
    assert 'läuft auf' not in output


def test_browser_starts_after_socket_binding_and_server_closes_on_interrupt(capsys):
    order = []
    server = Mock(effective_port=5050)
    def bind(*args, **kwargs):
        order.append('bind')
        return server
    def start_thread(*args, **kwargs):
        order.append('browser')
        assert kwargs['args'] == ('http://127.0.0.1:5050/arbeit',)
        return Mock()
    server.run.side_effect = KeyboardInterrupt
    with patch('sys.argv', ['run_web.py', '--open-browser']), \
            patch('webapp.create_app'), patch('waitress.create_server', side_effect=bind), \
            patch.object(run_web, 'Thread', side_effect=start_thread):
        assert run_web.main() == 0
    assert order == ['bind', 'browser']
    server.close.assert_called_once()
    assert 'läuft auf http://127.0.0.1:5050/arbeit' in capsys.readouterr().out


@pytest.mark.parametrize('result', [False, OSError('no browser association')])
def test_browser_failure_keeps_the_manual_address_visible(result, capsys):
    options = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
    with patch.object(run_web.webbrowser, 'open', **options):
        run_web.open_browser('http://127.0.0.1:5050/arbeit')
    assert 'Bitte diese Adresse im Browser öffnen: http://127.0.0.1:5050/arbeit' in capsys.readouterr().out
