"""Bulk SAP selection crosses page boundaries while keeping review/version guards."""
from html.parser import HTMLParser
import unittest
import pandas as pd
from tests import test_goal_workflow as fixtures
from webapp.services import sap_staging as sap


class SelectionParser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.selected = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'input' and attrs.get('name') == 'selected':
            self.selected.append(attrs['value'])


class BulkSelectionTest(unittest.TestCase):
    setUp = fixtures.GoalWorkflowTest.setUp
    tearDown = fixtures.GoalWorkflowTest.tearDown

    def preview(self, count=4):
        template = pd.read_excel(self.root / 'sap.xlsx', dtype=object).iloc[0].to_dict()
        rows = []
        for n in range(count):
            rows.append({**template, 'ID_NO_ZERO': str(770000+n), 'Rufname': 'Synthetisch',
                         'Nachname': f'Person {n:04}', 'lange ID/Nummer': f'bulk{n}@example.invalid'})
        path = self.root / f'bulk-{count}.xlsx'
        pd.DataFrame(rows).to_excel(path, index=False)
        return sap.stage(self.db, path, original_filename=path.name)

    def choose_all(self, batch, **filters):
        return self.client.post('/stammdaten/abgleich/auswahl', data={
            'csrf_token': self.csrf, 'selection_scope': 'all_filtered', 'batch_id': batch,
            'state': 'open', **filters,
        })

    def apply(self, selected, batch, **extra):
        return self.client.post('/stammdaten/abgleich/uebernehmen', data={
            'csrf_token': self.csrf, 'batch_id': batch, 'selected': selected,
            'checked': 'yes', 'reason': 'Synthetischen Originalexport und Umfang geprüft', **extra,
        }, follow_redirects=True)

    def test_optional_reason_accepts_empty_and_single_character(self):
        batch=self.preview(2)
        response=self.choose_all(batch,state='new')
        selected=SelectionParser(response.text).selected
        for selection,reason in zip(selected,('', 'x')):
            response=self.apply([selection],batch,reason=reason)
            self.assertEqual(response.status_code,200)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM employees WHERE pn LIKE '77%'").fetchone()[0],2)
        reasons=[row[0] for row in self.db.execute("SELECT d.reason FROM hr_sap_decisions d JOIN hr_sap_changes c ON c.id=d.change_id WHERE c.batch_id=? AND d.action='apply' ORDER BY d.id",(batch,))]
        self.assertEqual(reasons,['','x'])

    def test_47_pages_selected_together_and_individual_exclusions_are_respected(self):
        batch = self.preview(1175)
        page = self.client.get(f'/stammdaten/abgleich?batch_id={batch}&state=new')
        self.assertEqual(len(SelectionParser(page.text).selected), 25)
        self.assertIn('Seite 1 von 47', page.text)
        self.assertIn('Alle 1175 passenden Einträge über alle Seiten auswählen', page.text)
        response = self.choose_all(batch, state='new', page=47)
        self.assertEqual(response.status_code, 200)
        selected = SelectionParser(response.text).selected
        self.assertEqual(len(selected), 1175)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM employees WHERE pn LIKE '77%'").fetchone()[0], 0)
        response = self.apply(selected[1:-1], batch, state='new')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM employees WHERE pn LIKE '77%'").fetchone()[0], 1173)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hr_sap_changes WHERE batch_id=? AND category='new' AND data_status='pending'", (batch,)).fetchone()[0], 2)
        self.assertIsNone(self.db.execute('PRAGMA foreign_key_check').fetchone())

    def test_filter_export_and_eligibility_limit_the_global_selection(self):
        batch = self.preview(8)
        rows = self.db.execute("SELECT id FROM hr_sap_changes WHERE batch_id=? AND category='new' ORDER BY id", (batch,)).fetchall()
        with self.db:
            self.db.execute("UPDATE hr_sap_changes SET category='conflict' WHERE id=?", (rows[0][0],))
            self.db.execute("UPDATE hr_sap_changes SET data_status='applied' WHERE id=?", (rows[1][0],))
            self.db.execute("UPDATE hr_sap_changes SET data_status='retained' WHERE id=?", (rows[2][0],))
            self.db.execute('UPDATE hr_sap_changes SET superseded_by=? WHERE id=?', (rows[7][0], rows[3][0]))
        response = self.choose_all(batch, state='all', q='Synthetisch')
        selected = SelectionParser(response.text).selected
        self.assertEqual({int(value.split(':')[0]) for value in selected}, {row[0] for row in rows[4:]})
        response = self.choose_all(batch, state='new', q='Person 0007')
        self.assertEqual(SelectionParser(response.text).selected, [f'{rows[7][0]}:0'])
        response = self.choose_all(batch, state='conflict')
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'batch_id={batch}', response.location)
        self.assertFalse(SelectionParser(self.choose_all(None).text).selected)

    def test_newer_export_supersedes_old_selection_and_revision_changes_block_apply(self):
        batch = self.preview(3)
        selected = SelectionParser(self.choose_all(batch).text).selected
        row_id = int(selected[-1].split(':')[0])
        with self.db:
            self.db.execute('UPDATE hr_sap_changes SET revision=revision+1 WHERE id=?', (row_id,))
        response = self.apply(selected, batch)
        self.assertIn('inzwischen geändert', response.text)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM employees WHERE pn LIKE '77%'").fetchone()[0], 0)
        newer = self.preview(4)
        self.assertEqual(SelectionParser(self.choose_all(batch).text).selected, [])
        self.assertEqual(len(SelectionParser(self.choose_all(newer).text).selected), 4)

    def test_clear_selection_and_missing_confirmation_do_not_apply_data(self):
        batch = self.preview()
        selected = SelectionParser(self.choose_all(batch).text).selected
        response = self.apply([], batch, q='Synthetisch')
        self.assertIn('Bitte mindestens eine Person auswählen', response.text)
        self.assertIn('value="Synthetisch"', response.text)
        response = self.apply(selected, batch, checked='')
        self.assertIn('Umfang der Datenübernahme bestätigen', response.text)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM employees WHERE pn LIKE '77%'").fetchone()[0], 0)
        self.assertEqual(self.client.post('/stammdaten/abgleich/auswahl', data={
            'selection_scope': 'all_filtered', 'batch_id': batch,
        }).status_code, 400)


if __name__ == '__main__':
    unittest.main()
