"""Names and current reporting context for paged HR views.

An event's responsible manager is deliberately kept separate from today's
reporting line. Never pick an arbitrary assignment for a person with several.
"""
from datetime import date


def enrich(connection, rows):
    if not rows:
        return rows
    numbers = {str(row.get('person_number') or row.get('employee_pn') or '') for row in rows}
    numbers.discard('')
    assignments = {}
    if numbers:
        placeholders = ','.join('?' for _ in numbers)
        today = date.today().isoformat()
        for value in connection.execute(f'''SELECT e.*,m.manager_person_number,
            COALESCE(NULLIF(trim(p.first_name||' '||p.last_name),''),
                     NULLIF(trim(old.first_name||' '||old.last_name),''),'Zuordnung ohne Namen') AS manager_name
            FROM employment_assignments e
            LEFT JOIN manager_assignments m ON m.employment_id=e.id AND m.active=1
                AND (m.valid_from='' OR m.valid_from<=?) AND (m.valid_to='' OR m.valid_to>=?)
            LEFT JOIN persons p ON p.person_number=m.manager_person_number
            LEFT JOIN employees old ON old.pn=m.manager_person_number
            WHERE e.person_number IN ({placeholders}) AND e.active=1
            ORDER BY e.assignment_number,manager_name''', [today, today, *sorted(numbers)]):
            item = dict(value)
            assignments.setdefault(item['person_number'], []).append(item)
    managers = {r['pn']: (r['first_name']+' '+r['last_name']).strip()
                for r in connection.execute('SELECT pn,first_name,last_name FROM employees')}
    for row in rows:
        pn = str(row.get('person_number') or row.get('employee_pn') or '')
        assignment = row.get('assignment_number') or row.get('employment_assignment')
        contexts = [a for a in assignments.get(pn, [])
                    if assignment is None or str(a['assignment_number']) == str(assignment)]
        row['current_contexts'] = list({(a['id'], a['manager_person_number']): a for a in contexts}.values())
        row['responsible_name'] = managers.get(row.get('manager_pn'), '') or 'Zuständigkeit ohne Namen'
    return rows
