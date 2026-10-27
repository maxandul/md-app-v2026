-- Additive only: originals, legacy IDs and dispatch history are never rewritten.
CREATE TABLE hr_goal_sources (
 id INTEGER PRIMARY KEY,
 sha256 TEXT NOT NULL UNIQUE,
 original_filename TEXT NOT NULL,
 stored_path TEXT NOT NULL,
 extraction_json TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL
);
CREATE TABLE hr_goal_batches (
 id INTEGER PRIMARY KEY,
 origin_key TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL,
 mail_message_id INTEGER REFERENCES inbound_mail_messages(id),
 created_at TEXT NOT NULL
);
CREATE TABLE hr_goal_batch_sources (
 batch_id INTEGER NOT NULL REFERENCES hr_goal_batches(id),
 source_id INTEGER NOT NULL REFERENCES hr_goal_sources(id),
 PRIMARY KEY(batch_id,source_id)
);
CREATE TABLE hr_goal_origins (
 source_id INTEGER NOT NULL REFERENCES hr_goal_sources(id),
 origin_key TEXT NOT NULL UNIQUE,
 attachment_id INTEGER REFERENCES inbound_mail_attachments(id),
 pdf_import_id INTEGER REFERENCES word_pdf_imports(id),
 legacy_import_id INTEGER REFERENCES legacy_form_imports(id)
);
CREATE TABLE hr_goal_revisions (
 id INTEGER PRIMARY KEY,
 source_id INTEGER NOT NULL REFERENCES hr_goal_sources(id),
 revision INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('draft','waiting','confirmed','discarded')),
 employment_id INTEGER REFERENCES employment_assignments(id),
 goal_year INTEGER,
 goals_json TEXT NOT NULL,
 note TEXT NOT NULL DEFAULT '',
 issues_resolved INTEGER NOT NULL DEFAULT 0,
 user_id INTEGER REFERENCES app_users(id),
 created_at TEXT NOT NULL,
 UNIQUE(source_id,revision)
);
CREATE INDEX idx_hr_goal_revision_source ON hr_goal_revisions(source_id,revision);
CREATE INDEX idx_hr_goal_revision_assignment ON hr_goal_revisions(employment_id,goal_year,status);
CREATE TABLE hr_part_responsibilities (
 obligation_id INTEGER PRIMARY KEY REFERENCES document_obligations(id),
 manager_pn TEXT NOT NULL REFERENCES employees(pn),
 form_org_source TEXT NOT NULL CHECK(form_org_source IN ('employee','manager','existing')),
 form_org_unit TEXT NOT NULL,
 period_start TEXT NOT NULL,
 period_end TEXT NOT NULL,
 revision INTEGER NOT NULL,
 reason TEXT NOT NULL,
 user_id INTEGER REFERENCES app_users(id),
 updated_at TEXT NOT NULL
);
CREATE TABLE hr_goal_decisions (
 id INTEGER PRIMARY KEY,
 revision_id INTEGER NOT NULL REFERENCES hr_goal_revisions(id),
 case_id TEXT REFERENCES dialog_cases(case_id),
 outcome TEXT NOT NULL CHECK(outcome IN ('no_change','waiting','request_correction','corrected','no_output','resume')),
 reason TEXT NOT NULL,
 evidence_json TEXT NOT NULL,
 recipient_email TEXT NOT NULL DEFAULT '',
 requested_at TEXT NOT NULL DEFAULT '',
 corrected_document_id INTEGER REFERENCES official_documents(id),
 user_id INTEGER REFERENCES app_users(id),
 created_at TEXT NOT NULL
);
CREATE INDEX idx_hr_goal_decision ON hr_goal_decisions(revision_id,case_id,id);
CREATE TABLE hr_goal_outputs (
 id INTEGER PRIMARY KEY,
 revision_id INTEGER NOT NULL REFERENCES hr_goal_revisions(id),
 case_id TEXT NOT NULL REFERENCES dialog_cases(case_id),
 input_fingerprint TEXT NOT NULL,
 inputs_json TEXT NOT NULL,
 stored_path TEXT NOT NULL,
 manifest_json TEXT NOT NULL,
 approved_by INTEGER REFERENCES app_users(id),
 approved_at TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 UNIQUE(revision_id,case_id,input_fingerprint)
);
CREATE INDEX idx_hr_goal_output_case ON hr_goal_outputs(case_id,id);
CREATE TABLE hr_goal_dispatches (
 id INTEGER PRIMARY KEY,
 manager_pn TEXT NOT NULL REFERENCES employees(pn),
 recipient_email TEXT NOT NULL,
 subject TEXT NOT NULL,
 body_text TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'prepared' CHECK(status IN ('prepared','processing','draft_created','failed','sent_confirmed','cancelled')),
 outlook_entry_id TEXT NOT NULL DEFAULT '',
 sender_email TEXT NOT NULL DEFAULT '',
 error_message TEXT NOT NULL DEFAULT '',
 resolution_note TEXT NOT NULL DEFAULT '',
 user_id INTEGER REFERENCES app_users(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE hr_goal_dispatch_outputs (
 dispatch_id INTEGER NOT NULL REFERENCES hr_goal_dispatches(id),
 output_id INTEGER NOT NULL REFERENCES hr_goal_outputs(id),
 PRIMARY KEY(dispatch_id,output_id)
);
CREATE INDEX idx_hr_goal_dispatch_member ON hr_goal_dispatch_outputs(output_id,dispatch_id);
CREATE TABLE hr_goal_events (
 id INTEGER PRIMARY KEY,
 source_id INTEGER REFERENCES hr_goal_sources(id),
 case_id TEXT REFERENCES dialog_cases(case_id),
 dispatch_id INTEGER REFERENCES hr_goal_dispatches(id),
 action TEXT NOT NULL,
 details_json TEXT NOT NULL,
 user_id INTEGER REFERENCES app_users(id),
 created_at TEXT NOT NULL
);
CREATE INDEX idx_hr_goal_events_source ON hr_goal_events(source_id,id);
CREATE INDEX IF NOT EXISTS idx_hr_case_employment ON dialog_cases(employee_pn,employment_assignment,cycle_id);
CREATE INDEX IF NOT EXISTS idx_hr_event_case ON dialog_events(legacy_case_id);
CREATE INDEX IF NOT EXISTS idx_hr_obligation_event ON document_obligations(dialog_event_id,document_kind);
CREATE INDEX IF NOT EXISTS idx_hr_document_case ON official_documents(case_id,is_current,document_kind);
