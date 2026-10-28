-- Preserve every existing case and reference while permitting additional conversations.
DROP VIEW hr_resolved_obligations;
CREATE TABLE hr_case_sequence_migration (seq INTEGER NOT NULL);
INSERT INTO hr_case_sequence_migration SELECT seq FROM sqlite_sequence WHERE name='dialog_cases';
CREATE TABLE dialog_cases_d (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL UNIQUE,
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    employee_pn TEXT NOT NULL REFERENCES employees(pn),
    employment_assignment TEXT NOT NULL DEFAULT '',
    manager_pn TEXT NOT NULL,
    suggested_scope TEXT NOT NULL,
    suggestion_reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'offen'
        CHECK (status IN ('offen', 'in_bearbeitung', 'vollstaendig', 'kein_md')),
    official_scope TEXT NOT NULL DEFAULT '',
    dialog_date TEXT NOT NULL DEFAULT '',
    period_start TEXT NOT NULL DEFAULT '',
    period_end TEXT NOT NULL DEFAULT '',
    overall_rating_code TEXT NOT NULL DEFAULT '',
    agreement TEXT NOT NULL DEFAULT '',
    data_json TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    updated_at TEXT NOT NULL
);


INSERT INTO dialog_cases_d SELECT * FROM dialog_cases;
DROP TABLE dialog_cases;
ALTER TABLE dialog_cases_d RENAME TO dialog_cases;
UPDATE sqlite_sequence SET seq=MAX(seq,COALESCE((SELECT MAX(seq) FROM hr_case_sequence_migration),0)) WHERE name='dialog_cases';
DROP TABLE hr_case_sequence_migration;
CREATE INDEX idx_dialog_cases_cycle_manager ON dialog_cases(cycle_id,manager_pn);
CREATE VIEW hr_resolved_obligations AS
SELECT o.*,de.legacy_case_id AS case_id,de.cycle_id,de.event_type,de.status AS event_status,
       COALESCE(dc.active,1) AS active,ea.person_number AS employee_pn,
       ea.assignment_number,ea.org_unit AS employee_org_unit,p.first_name,p.last_name,
       COALESCE(r.manager_pn,dc.manager_pn,ma.manager_person_number) AS manager_pn,
       COALESCE(r.form_org_unit,fo.org_unit,ea.org_unit) AS form_org_unit,
       COALESCE(r.revision,0) AS responsibility_revision,
       r.period_start AS assigned_period_start,r.period_end AS assigned_period_end,
       CASE WHEN NULLIF(dc.period_start,'') IS NOT NULL AND NULLIF(dc.period_end,'') IS NOT NULL
                  AND (o.document_kind='review' OR de.event_type<>'annual') THEN dc.period_end
            WHEN o.document_kind='review' AND de.event_type='probation_review' THEN NULLIF(e.probation_end,'')
       END AS legacy_period_end
FROM document_obligations o
JOIN dialog_events de ON de.id=o.dialog_event_id
JOIN employment_assignments ea ON ea.id=de.employment_id
JOIN persons p ON p.person_number=ea.person_number
LEFT JOIN dialog_cases dc ON dc.case_id=de.legacy_case_id
LEFT JOIN employees e ON e.pn=ea.person_number
LEFT JOIN manager_assignments ma ON ma.id=de.manager_assignment_id
LEFT JOIN dialog_form_org_units fo ON fo.dialog_event_id=de.id
LEFT JOIN hr_part_responsibilities r ON r.obligation_id=o.id;


ALTER TABLE hr_part_responsibilities ADD COLUMN origin TEXT NOT NULL DEFAULT 'manual' CHECK(origin IN ('manual','preserved'));
CREATE TABLE hr_sap_batches (
 id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, original_filename TEXT NOT NULL,
 stored_path TEXT NOT NULL, created_at TEXT NOT NULL, user_id INTEGER REFERENCES app_users(id),
 base_import_id INTEGER REFERENCES sap_imports(id), summary_json TEXT NOT NULL
);
CREATE TABLE hr_sap_changes (
 id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES hr_sap_batches(id),
 person_number TEXT NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
 before_json TEXT NOT NULL, after_json TEXT NOT NULL, issues_json TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('new','changed','unchanged','missing','conflict','excluded')),
 data_status TEXT NOT NULL DEFAULT 'pending' CHECK(data_status IN ('pending','applied','retained')),
 applied_import_id INTEGER REFERENCES sap_imports(id), followup_status TEXT NOT NULL DEFAULT 'none' CHECK(followup_status IN ('none','open','done')),
 revision INTEGER NOT NULL DEFAULT 0, superseded_by INTEGER REFERENCES hr_sap_changes(id),
 UNIQUE(batch_id,person_number)
);
CREATE INDEX idx_hr_sap_changes_open ON hr_sap_changes(superseded_by,data_status,followup_status,batch_id);
CREATE TABLE hr_sap_decisions (
 id INTEGER PRIMARY KEY, change_id INTEGER NOT NULL REFERENCES hr_sap_changes(id), action TEXT NOT NULL,
 reason TEXT NOT NULL, details_json TEXT NOT NULL, user_id INTEGER REFERENCES app_users(id), created_at TEXT NOT NULL
);
CREATE TABLE hr_sap_observations (
 id INTEGER PRIMARY KEY, sap_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
 person_number TEXT NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(sap_import_id,person_number)
);
