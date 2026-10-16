"""Import unambiguous Word outlooks as goal sources, never as dossier PDFs."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil

from .legacy_forms import parse_legacy_form, _match_assignment, _goal_content_key, import_legacy_forms
from .word_packages import prior_goals

WORD_SUFFIXES = {'.docx', '.docm'}


def process_word_goals(connection, message_id):
    rows = connection.execute("SELECT * FROM inbound_mail_attachments WHERE mail_message_id=? AND status='review_required'", (message_id,)).fetchall()
    candidates = []
    errors = {
        'missing_person_number': 'Personalnummer fehlt im Dokument.',
        'person_not_active': 'Keine aktive Anstellung für diese Personalnummer gefunden.',
        'assignment_not_found': 'Die angegebene Anstellung wurde nicht gefunden.',
        'ambiguous_assignment': 'Mehrfachanstellung: Ans. fehlt. Anstellung anhand von Funktion und Führungskraft manuell klären.',
        'no_goals': 'Keine ausgefüllten Ziele erkannt.',
        'extraction_uncertain': 'Zielinhalt nicht eindeutig auslesbar.',
    }
    def save(row, status, note):
        connection.execute("UPDATE inbound_mail_attachments SET status=?,error_message=? WHERE id=?", (status, note, row['id']))
        connection.commit()
    for row in rows:
        path = Path(row['stored_path'])
        if Path(row['original_filename']).suffix.lower() not in WORD_SUFFIXES or not path.is_file():
            continue
        try:
            item = parse_legacy_form(path)
            if item['document_type'] != 'outlook':
                raise ValueError('Kein Word-Ausblick als Zielquelle erkannt. Rückblicke und andere Word-Dokumente werden hier nicht übernommen.')
            years = item.get('detected_years', [])
            if len(years) != 1:
                raise ValueError('Zieljahr im Ausblick-Zeitraum fehlt oder ist mehrdeutig. Jahr am Original klären und über Stammdaten → Vorjahresziele importieren.')
            year = years[0]
            status, assignment = _match_assignment(connection, employee_pn=item['employee_pn'], assignment_number=item['assignment_number'])
            if status != 'matched':
                raise ValueError(errors[status])
            if item.get('issues'):
                raise ValueError('Zielinhalt nicht eindeutig auslesbar: ' + ' '.join(item['issues']))
            if not item['performance_goals'] and not item['development_goals']:
                raise ValueError(errors['no_goals'])
            key = (item['employee_pn'], assignment, year)
            content = _goal_content_key(item['performance_goals'], item['development_goals'])
            candidates.append((row, item, key, content))
        except Exception as exc:
            save(row, 'review_required', str(exc))
    for row, item, key, content in candidates:
        try:
            if any(other_key == key and other_content != content for _, _, other_key, other_content in candidates):
                raise ValueError('Mehrere unterschiedliche Ausblicke für dieselbe Person, Anstellung und dasselbe Zieljahr in dieser Mail. Quellen vergleichen; keine automatische Auswahl.')
            pn, assignment, year = key
            selected = prior_goals(connection, employee_pn=pn, assignment=assignment, year=year)
            sources = [selected] if selected[0] or selected[1] else []
            if sources:
                if not all(_goal_content_key(p, d) == content for p, d, _ in sources):
                    raise ValueError('Abweichende Zielquelle bereits vorhanden. Unter Stammdaten die Zielquellen vergleichen; keine automatische Ersetzung.')
                save(row, 'duplicate', f'Ziele {year}, PN {pn}, Ans. {assignment} bereits vorhanden; keine doppelte Übernahme.')
                continue
            with TemporaryDirectory(prefix='md-mail-goals-') as tmp:
                target = Path(tmp) / Path(row['stored_path']).name
                shutil.copyfile(row['stored_path'], target)
                result = import_legacy_forms(connection, forms_root=Path(tmp), goal_year=year, selected_hashes={row['sha256']})
            if result['imported'] != 1:
                state = result['items'][0]['status'] if result['items'] else 'read_error'
                raise ValueError(errors.get(state, 'Zielquelle nicht übernommen: ' + state))
            save(row, 'imported', f'Ziele {year}, PN {pn}, Ans. {assignment} übernommen: {len(item["performance_goals"])} Leistungsziele, {len(item["development_goals"])} Entwicklungsziele. Original im Projekt; keine Roboterübergabe für Word-Zielquellen.')
        except Exception as exc:
            save(row, 'review_required', str(exc))
