"""Exercise selection and client pagination together in a real, offline browser."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    browser = next((found for name in ('google-chrome', 'chromium', 'chromium-browser')
                    if (found := shutil.which(name))), None)
    if not browser:
        raise SystemExit('A Chromium browser is required for this CI check only.')
    static = Path(__file__).resolve().parents[1] / 'webapp' / 'static'
    rows = ''.join(f'<tr><td><input type="checkbox" name="selected" value="{i}" '
                   f'{"disabled" if i == 1174 else ""}></td><td>Person {i:04}</td></tr>'
                   for i in range(1175))
    page = f'''<!doctype html><html><meta charset="utf-8"><body>
<form><div class="table-wrap"><table data-bulk-selection="selected">
<thead><tr><th>Auswahl</th><th>Person</th></tr></thead><tbody>{rows}</tbody></table></div>
<label><input type="checkbox" name="checked" required>Prüfung bestätigen</label></form>
<form id="other" data-bulk-selection="source"><input type="checkbox" name="source">
<input type="checkbox" name="source" data-bulk-skip><input type="checkbox" name="checked"></form>
<script src="{(static / 'bulk_selection.js').as_uri()}"></script>
<script src="{(static / 'table_controls.js').as_uri()}"></script>
<script>
try {{
  const check = (condition, message) => {{ if (!condition) throw new Error(message); }};
  const table = document.querySelector('table');
  const selected = () => table.querySelectorAll('input:checked').length;
  const [all, none] = document.querySelectorAll('.selection-controls button');
  const search = document.querySelector('.table-controls input');
  const filter = value => {{ search.value = value; search.dispatchEvent(new Event('input')); }};
  const next = document.querySelector('[data-page="next"]');
  check([...table.tBodies[0].rows].filter(row => !row.hidden).length === 50, 'initial pagination');
  all.click();
  check(selected() === 1174, 'select across every page, skip disabled');
  check(!document.querySelector('input[name="checked"]').checked, 'confirmation unchanged');
  next.click();
  check(selected() === 1174, 'pagination retains selection');
  none.click();
  check(selected() === 0, 'clear all pages');
  filter('Person 00');
  check(all.textContent === 'Alle 100 Treffer auswählen', 'filtered count');
  all.click();
  check(selected() === 100, 'filter selects both pages');
  next.click();
  check([...table.tBodies[0].rows].filter(row => !row.hidden && row.querySelector('input').checked).length === 50, 'next filtered page');
  filter('Person 1100');
  all.click();
  check(selected() === 101, 'existing hidden selections are retained');
  none.click();
  check(selected() === 0, 'clear also removes filtered-out selections');
  const other = document.querySelector('#other');
  other.querySelector('button').click();
  check(other.querySelectorAll('input[name="source"]:checked').length === 1, 'ambiguous source skipped');
  check(!other.querySelector('input[name="checked"]').checked, 'form confirmation unchanged');
  check(selected() === 0, 'selection groups remain independent');
  document.body.dataset.result = 'passed';
}} catch (error) {{ document.body.dataset.result = 'failed'; document.body.dataset.error = error.message; }}
</script></body></html>'''
    with tempfile.TemporaryDirectory(prefix='md-browser-') as temporary:
        root = Path(temporary)
        html = root / 'selection.html'
        html.write_text(page, encoding='utf-8')
        result = subprocess.run([
            browser, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--disable-background-networking', '--no-first-run', '--no-default-browser-check',
            '--allow-file-access-from-files', f'--user-data-dir={root / "profile"}',
            '--dump-dom', html.as_uri(),
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
        if result.returncode != 0 or '<body data-result="passed">' not in result.stdout:
            import re
            error = re.search(r'data-error="([^"]*)"', result.stdout)
            raise AssertionError(error.group(1) if error else result.stderr[-2000:] or 'No browser result')
    print('Browser: 1175 rows, filtered selection across pages, clear all, disabled items and separate confirmations passed.')


if __name__ == '__main__':
    main()
