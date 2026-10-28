-- Resolve each existing obligation without rewriting cases or historical documents.
CREATE INDEX idx_hr_part_manager ON hr_part_responsibilities(manager_pn,obligation_id);
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

CREATE TABLE hr_reminder_resolutions (
 reminder_id INTEGER PRIMARY KEY REFERENCES reminders(id),
 outcome TEXT NOT NULL CHECK(outcome IN ('sent_confirmed','cancelled')),
 reason TEXT NOT NULL,
 user_id INTEGER REFERENCES app_users(id),
 created_at TEXT NOT NULL
);
