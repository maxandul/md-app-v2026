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
    page = f'''<!doctype html><html><meta charset="utf-8"><link rel="stylesheet" href="{(static / 'app.css').as_uri()}"><body>
<form><div class="table-wrap"><table data-bulk-selection="selected">
<thead><tr><th>Auswahl</th><th>Person</th></tr></thead><tbody>{rows}</tbody></table></div>
<label><input type="checkbox" name="checked" required>Prüfung bestätigen</label></form>
<form id="other" data-bulk-selection="source"><input type="checkbox" name="source">
<input type="checkbox" name="source" data-bulk-skip><input type="checkbox" name="checked"></form>
<h1 id="heading">Rückblick prüfen</h1>
<form data-review-form id="review">
<label>Dokument<select name="document_kind"><option value="review">Rückblick</option><option value="outlook">Ausblick</option></select></label>
<select name="probation"><option value="nein">Regulär</option><option value="ja">Probezeit</option></select>
<select name="conducted"><option value="">Leer</option><option value="nein">Nein</option></select>
<select name="case_id"><option value="case" data-review-min="2025-03-01" data-review-max="2025-10-31">Fall</option></select>
<label>Von<input name="period_start" type="date"></label><label>Bis<input name="period_end" type="date"></label>
<label>Gesprächsdatum<input name="dialog_date" type="date"></label>
<select name="rating"><option value="">Leer</option><option value="C">C</option></select>
<label>Begründung<textarea name="no_md_reason"></textarea></label>
<button type="button" id="secondary" class="button">Speichern</button>
<button type="button" id="primary" class="button button--primary">Übernehmen</button>
<button type="button" id="danger" class="button button--danger">Verwerfen</button>
</form>
<script src="{(static / 'word_pdf_review.js').as_uri()}"></script>
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
  const input = document.querySelector('[name="period_start"]');
  const style = getComputedStyle(input);
  check(style.fontFamily.startsWith('Arial') && style.fontWeight === '400', 'normal Arial in nested input');
  check(getComputedStyle(document.querySelector('textarea')).fontWeight === '400', 'normal textarea weight');
  check(getComputedStyle(document.querySelector('#heading')).fontFamily.startsWith('"Arial Black"'), 'title font');
  const color = id => getComputedStyle(document.getElementById(id)).backgroundColor;
  check(color('secondary') !== 'rgb(255, 255, 255)', 'visible secondary button');
  check(new Set(['primary','secondary','danger'].map(color)).size === 3, 'three distinct button treatments');
  const f = name => document.querySelector(`[name="${{name}}"]`);
  const change = (name,value) => {{ f(name).value=value;f(name).dispatchEvent(new Event('change')); }};
  check(input.required && f('period_end').required && f('rating').required, 'review required fields');
  check(!f('dialog_date').required && !f('no_md_reason').required, 'optional date and reason');
  change('period_start','2025-02-28');check(input.validity.rangeUnderflow, 'employment entry bound');
  change('period_end','2025-11-01');check(f('period_end').validity.rangeOverflow, 'employment exit bound');
  change('period_start','2025-03-01');change('period_end','2025-10-31');change('rating','C');
  check(document.querySelector('#review').checkValidity(), 'blank optional inputs allowed');
  change('conducted','nein');change('rating','');check(!f('rating').required, 'waiver has no rating');
  change('document_kind','outlook');check(!input.required && !input.min && !input.max, 'outlook optional period');
  change('document_kind','review');change('probation','ja');check(!input.required && !f('rating').required, 'probation optional fields');
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
    print('Browser: selection across 1175 rows, Arial inputs, button variants, optional fields and date bounds passed.')


if __name__ == '__main__':
    main()
