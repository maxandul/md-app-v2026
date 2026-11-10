"""Session-owned selections and reviewed bulk actions over canonical obligations."""
import json
import secrets
import time
from datetime import date, datetime

from . import part_queries, reminders, person_display
from .deadlines import _valid_date
from .outlook_lock import serialized_goal_delivery

TTL = 24 * 60 * 60
FILTER_KEYS = ('q', 'manager', 'kind', 'state', 'year', 'org_unit', 'due')


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def filter_basis(filters):
    return {k: filters.get(k) for k in FILTER_KEYS}


def owned(connection, table, key, owner):
    if table not in ('hr_part_selections', 'hr_part_action_previews'):
        raise ValueError('Ungültige Auswahl.')
    row = connection.execute('SELECT * FROM '+table+' WHERE id=? AND owner=?', (key, owner)).fetchone()
    if not row or row['created_at'] < time.time() - TTL:
        raise ValueError('Diese Auswahl ist abgelaufen oder gehört zu einer anderen Sitzung. Bitte neu auswählen.')
    return dict(row)


def selection(connection, key, owner, filters=None):
    row = owned(connection, 'hr_part_selections', key, owner)
    if filters is not None and row['filters_json'] != packed(filter_basis(filters)):
        raise ValueError('Die Filter wurden geändert. Bitte eine neue Auswahl beginnen.')
    row['ids'] = json.loads(row['ids_json'])
    return row


def select(connection, *, owner, filters, key='', revision=0, mode='page', checked=()):
    """Update only the current server page, or explicitly freeze all matches."""
    with connection:
        connection.execute('BEGIN IMMEDIATE')
        previous = selection(connection, key, owner, filters) if key else None
        if previous and previous['revision'] != revision:
            raise ValueError('Die Auswahl wurde in einem anderen Fenster geändert. Bitte die Liste neu laden.')
        ids = set(previous['ids']) if previous else set()
        if mode == 'all':
            ids = set(part_queries.selection_ids(connection, **filters))
        elif mode == 'clear':
            ids = set()
        elif mode == 'page':
            page_ids = {r['id'] for r in part_queries.listing(connection, **filters)['rows']}
            chosen = {int(v) for v in checked}
            if not chosen <= page_ids:
                raise ValueError('Die Seitenauswahl ist nicht mehr gültig. Bitte neu laden.')
            ids = (ids - page_ids) | chosen
        else:
            raise ValueError('Unbekannte Auswahlaktion.')
        if not previous:
            key = secrets.token_urlsafe(24)
            connection.execute('INSERT INTO hr_part_selections VALUES (?,?,?,?,?,?)',
                (key, owner, packed(filter_basis(filters)), packed(sorted(ids)), 1, int(time.time())))
        else:
            connection.execute('UPDATE hr_part_selections SET ids_json=?,revision=revision+1 WHERE id=?',
                               (packed(sorted(ids)), key))
    return selection(connection, key, owner)


def plan(connection, *, ids, action, new_due_date='', reason='', sender_email='', today=None):
    if action not in ('deadline', 'reminder'):
        raise ValueError('Bitte Fristanpassung oder Erinnerung wählen.')
    if not ids:
        raise ValueError('Bitte zuerst Gesprächsteile auswählen.')
    if action == 'deadline':
        new_due_date = _valid_date(new_due_date)
        reason = reason.strip()
        if not reason:
            raise ValueError('Bitte begründe die Fristanpassung.')
    cutoff = (today or date.today()).isoformat()
    rows = [dict(r) for r in connection.execute('''SELECT o.*,
        COALESCE(e.first_name||' '||e.last_name,'Zuständigkeit ohne Namen') AS manager_name
        FROM hr_resolved_obligations o LEFT JOIN employees e ON e.pn=o.manager_pn
        WHERE o.id IN (SELECT value FROM json_each(?)) ORDER BY o.last_name,o.first_name,o.id''', (packed(ids),))]
    person_display.enrich(connection, rows)
    groups = []
    if action == 'reminder':
        for cycle in sorted({r['cycle_id'] for r in rows if r['cycle_id'] is not None}):
            groups.extend(dict(g, cycle_id=cycle) for g in reminders.reminder_candidates(connection,
                cycle_id=cycle, sender_email=sender_email, today=today, obligation_ids=ids))
        from .mail_dispatch import configured_sender
        try:
            configured_sender(sender_email)
        except ValueError as exc:
            for group in groups:
                group.update(ready=False, readiness_error=str(exc))
    candidates = {i: g for g in groups for i in g['obligation_ids']}
    for row in rows:
        error = ''
        if not row['required'] or row['status'] in ('complete', 'waived'):
            error = 'Bereits abgeschlossen oder entfallen.'
        elif not row['active'] or row['event_status'] == 'cancelled':
            error = 'Fall inaktiv oder Ereignis aufgehoben.'
        elif row['cycle_id'] is None:
            error = 'Zuerst einem Durchlauf zuordnen.'
        elif action == 'deadline':
            if row['due_date'] == new_due_date:
                error = 'Die gewünschte Frist ist bereits gesetzt.'
        elif not row['due_date'] or row['due_date'] >= cutoff:
            error = 'Noch nicht überfällig oder keine Frist hinterlegt.'
        elif row['id'] not in candidates:
            error = 'Unterlagen bereits eingegangen oder keine offene Nachforderung. Rücklauf prüfen.'
        elif not candidates[row['id']]['ready']:
            group = candidates[row['id']]
            error = group['readiness_error'] or 'Geschäftliche E-Mail-Adresse der Führungskraft fehlt.'
        row['exclusion'] = error
    found = {r['id'] for r in rows}
    for missing in sorted(set(ids)-found):
        rows.append(dict(id=missing, first_name='Nicht mehr vorhandener', last_name='Gesprächsteil',
                         exclusion='Gesprächsteil nicht mehr vorhanden.'))
    return dict(ids=sorted(set(ids)), action=action, new_due_date=new_due_date, reason=reason,
                sender_email=sender_email if action == 'reminder' else '', cutoff=cutoff,
                rows=rows, eligible=[r['id'] for r in rows if not r['exclusion']], groups=groups)


def preview(connection, *, owner, selection_id, revision, **values):
    chosen = selection(connection, selection_id, owner)
    if chosen['revision'] != revision:
        raise ValueError('Die Auswahl wurde geändert. Bitte die Liste neu laden.')
    value = plan(connection, ids=chosen['ids'], **values)
    key = secrets.token_urlsafe(24)
    with connection:
        connection.execute('INSERT INTO hr_part_action_previews(id,owner,selection_id,plan_json,created_at) VALUES (?,?,?,?,?)',
                           (key, owner, selection_id, packed(value), int(time.time())))
    return key


def view(connection, key, owner):
    value = owned(connection, 'hr_part_action_previews', key, owner)
    value['plan'] = json.loads(value['plan_json'])
    value['result'] = json.loads(value['result_json'])
    value['reminders'] = [dict(r) for r in connection.execute('''SELECT r.*,rr.outcome AS resolution
        FROM reminders r JOIN hr_part_action_reminders a ON a.reminder_id=r.id
        LEFT JOIN hr_reminder_resolutions rr ON rr.reminder_id=r.id WHERE a.preview_id=? ORDER BY r.id''',(key,))]
    return value


@serialized_goal_delivery
def execute(connection, key, *, owner, sender_email='', user_id=None, today=None, adapter=None):
    """Revalidate everything, atomically reserve, then use the canonical mail path."""
    with connection:
        connection.execute('BEGIN IMMEDIATE')
        batch = view(connection, key, owner)
        if batch['status'] != 'preview':
            raise ValueError('Diese Aktion wurde bereits gestartet. Bitte den Ergebnisstand prüfen.')
        old = batch['plan']
        current = plan(connection, ids=old['ids'], action=old['action'], new_due_date=old['new_due_date'],
                       reason=old['reason'], sender_email=sender_email, today=today)
        if packed(current) != batch['plan_json']:
            raise ValueError('Frist, Zuständigkeit, Rücklauf oder Outlook-Stand hat sich geändert. Bitte eine neue Vorschau prüfen.')
        if not current['eligible']:
            raise ValueError('Für diese Auswahl ist keine Aktion möglich. Bitte die Ausschlussgründe prüfen.')
        if current['action'] == 'deadline':
            stamp = datetime.now().astimezone().isoformat(timespec='seconds')
            eligible=set(current['eligible'])
            for row in current['rows']:
                if row['id'] not in eligible:
                    continue
                connection.execute('UPDATE document_obligations SET due_date=?,updated_at=? WHERE id=?',
                                   (current['new_due_date'], stamp, row['id']))
                connection.execute('''INSERT INTO deadline_changes(cycle_id,obligation_id,manager_pn,scope,
                    document_kind,old_due_date,new_due_date,reason,user_id,created_at) VALUES (?,?,?,'case',?,?,?,?,?,?)''',
                    (row['cycle_id'],row['id'],row['manager_pn'],row['document_kind'],row['due_date'],
                     current['new_due_date'],current['reason'],user_id,stamp))
            result = dict(changed=len(current['eligible']), message='Fristen angepasst und je Gesprächsteil protokolliert.')
            connection.execute("UPDATE hr_part_action_previews SET status='complete',result_json=? WHERE id=?", (packed(result), key))
            return result
        # Reservation survives a crash or an uncertain COM result. Never retry blindly.
        connection.execute("UPDATE hr_part_action_previews SET status='running' WHERE id=?", (key,))
    result = dict(created=0, failed=0, errors=[], message='Outlook-Entwürfe vorbereitet. Bitte in Outlook prüfen und manuell senden.')
    try:
        for cycle in sorted({g['cycle_id'] for g in current['groups'] if g['ready']}):
            managers = [g['manager_pn'] for g in current['groups'] if g['ready'] and g['cycle_id'] == cycle]
            outcome = reminders._create_reminder_drafts(connection, cycle_id=cycle, manager_pns=managers,
                obligation_ids=current['eligible'], sender_email=sender_email, today=today, adapter=adapter, action_preview_id=key,
                expected_candidates={g['manager_pn']:{k:v for k,v in g.items() if k!='cycle_id'}
                    for g in current['groups'] if g['ready'] and g['cycle_id']==cycle})
            for field in ('created', 'failed'):
                result[field] += outcome[field]
            result['errors'].extend(outcome['errors'])
    except Exception as exc:
        connection.rollback()
        result['errors'].append(str(exc))
        result['message'] = 'Die Vorbereitung wurde unterbrochen. Es können bereits Entwürfe bestehen. Tatsächlichen Outlook-Stand vor einer neuen Aktion prüfen.'
    recorded = view(connection, key, owner)['reminders']
    result['created'] = sum(r['status'] in ('draft_created','sent_confirmed') for r in recorded)
    result['failed'] = sum(r['status']=='failed' for r in recorded)
    result['uncertain'] = sum(r['status']=='prepared' for r in recorded)
    with connection:
        connection.execute("UPDATE hr_part_action_previews SET status='complete',result_json=? WHERE id=?", (packed(result), key))
    return result
