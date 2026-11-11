"""Filename hints supplement document identities; contradictions stay explicit."""
import re


def filename_pn(filename, *, feedback=False):
    name = filename.replace('\\', '/').rsplit('/', 1)[-1]
    if not feedback:
        name = re.sub(r'_Ans_[^_]+_[a-f0-9]{8}(?=\.pdf$)', '', name, flags=re.I)
    prefix = r'.*Feedback_an_.+' if feedback else r'(?:Rückblick|Rueckblick|Ausblick)_.+'
    match = re.fullmatch(prefix + r'_(\d+)\.pdf', name, re.I)
    return match[1] if match else ''


def supplement_identity(parsed, filename):
    data = parsed.get('data', {})
    feedback = data.get('document_kind') == 'feedback'
    if not feedback and data.get('document_kind') not in ('review', 'outlook'):
        return
    key = 'manager_pn' if feedback else 'pn'
    number = filename_pn(filename, feedback=feedback)
    if not number:
        return
    label = 'Personalnummer der Führungskraft' if feedback else 'Personalnummer'
    if data.get(key) and data[key] != number:
        parsed.setdefault('identity_conflicts', []).append(
            f'{label}: Dokument ({data[key]}) und Dateiname ({number}) widersprechen sich. Zuordnung am Original klären.')
        parsed.setdefault('issues', []).extend(parsed['identity_conflicts'])
    elif not data.get(key):
        # A conflicting/multiple printed identity must never become a certain
        # filename identity. Leave that choice to the original-document review.
        if len(set(re.findall(r'\b(?:PN|Personalnummer)\s*:\s*(\d+)\b', parsed.get('text', ''), re.I))) > 1:
            return
        data[key] = number
        parsed.setdefault('identity_hints', {})[key] = {'value': number, 'origin': 'filename'}
        parsed['issues'] = [issue for issue in parsed.get('issues', [])
                            if issue != label + ': nicht eindeutig lesbar oder nicht ausgefüllt.']
