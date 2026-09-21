CREATE TABLE IF NOT EXISTS sap_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    employee_count INTEGER NOT NULL,
    reporting_line_count INTEGER NOT NULL,
    warning_count INTEGER NOT NULL DEFAULT 0,
    warnings_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('hr_admin', 'system_admin')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    password_temporary INTEGER NOT NULL DEFAULT 0 CHECK (password_temporary IN (0, 1)),
    session_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES app_users(id),
    action TEXT NOT NULL,
    object_type TEXT NOT NULL DEFAULT '',
    object_id TEXT NOT NULL DEFAULT '',
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at);

CREATE TABLE IF NOT EXISTS sap_import_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sap_import_id INTEGER NOT NULL REFERENCES sap_imports(id) ON DELETE CASCADE,
    issue_type TEXT NOT NULL CHECK (issue_type IN (
        'multiple_employment', 'multiple_permissions', 'exact_duplicate',
        'conflicting_duplicate', 'missing_person_number', 'missing_manager'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'blocking')),
    person_number TEXT NOT NULL DEFAULT '',
    employment_assignment TEXT NOT NULL DEFAULT '',
    row_numbers_json TEXT NOT NULL DEFAULT '[]',
    details_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'ignored')),
    resolution_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sap_import_issues_import
    ON sap_import_issues (sap_import_id, severity, status);

CREATE TABLE IF NOT EXISTS persons (
    person_number TEXT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    last_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employment_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_number TEXT NOT NULL REFERENCES persons(person_number),
    assignment_number TEXT NOT NULL,
    position TEXT NOT NULL DEFAULT '',
    org_unit TEXT NOT NULL DEFAULT '',
    employment_degree TEXT NOT NULL DEFAULT '',
    entry_date TEXT NOT NULL DEFAULT '',
    exit_date TEXT NOT NULL DEFAULT '',
    probation_end TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    last_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
    updated_at TEXT NOT NULL,
    UNIQUE (person_number, assignment_number)
);

CREATE TABLE IF NOT EXISTS secondary_activity_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employment_id INTEGER NOT NULL REFERENCES employment_assignments(id) ON DELETE CASCADE,
    valid_from TEXT NOT NULL DEFAULT '',
    valid_to TEXT NOT NULL DEFAULT '',
    permission TEXT NOT NULL DEFAULT '',
    permission_for TEXT NOT NULL DEFAULT '',
    source_fingerprint TEXT NOT NULL,
    last_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
    UNIQUE (employment_id, source_fingerprint)
);

CREATE TABLE IF NOT EXISTS manager_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employment_id INTEGER NOT NULL REFERENCES employment_assignments(id),
    manager_person_number TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('sap', 'manual')),
    sap_import_id INTEGER REFERENCES sap_imports(id),
    valid_from TEXT NOT NULL DEFAULT '',
    valid_to TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_manager_assignments_current
    ON manager_assignments (employment_id, active, manager_person_number);

CREATE UNIQUE INDEX IF NOT EXISTS idx_manager_assignments_sap_unique
    ON manager_assignments (employment_id, manager_person_number, sap_import_id)
    WHERE source = 'sap';

CREATE TABLE IF NOT EXISTS employees (
    pn TEXT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    org_unit TEXT NOT NULL DEFAULT '',
    employment_degree TEXT NOT NULL DEFAULT '',
    entry_date TEXT NOT NULL DEFAULT '',
    exit_date TEXT NOT NULL DEFAULT '',
    probation_end TEXT NOT NULL DEFAULT '',
    employment_assignment TEXT NOT NULL DEFAULT '',
    secondary_employment TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    last_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sap_import_id INTEGER NOT NULL REFERENCES sap_imports(id) ON DELETE CASCADE,
    employee_pn TEXT NOT NULL REFERENCES employees(pn),
    employment_assignment TEXT NOT NULL DEFAULT '',
    manager_pn TEXT NOT NULL,
    org_unit TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    UNIQUE (sap_import_id, employee_pn, employment_assignment, manager_pn)
);

CREATE INDEX IF NOT EXISTS idx_reporting_lines_import_manager
    ON reporting_lines (sap_import_id, manager_pn);

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_year INTEGER NOT NULL,
    outlook_year INTEGER NOT NULL,
    sap_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
    review_due_date TEXT NOT NULL DEFAULT '',
    outlook_due_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'vorbereitung'
        CHECK (status IN ('vorbereitung', 'versand', 'ruecklauf', 'abgeschlossen')),
    created_at TEXT NOT NULL,
    UNIQUE (review_year, outlook_year)
);

CREATE TABLE IF NOT EXISTS dialog_cases (
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
    updated_at TEXT NOT NULL,
    UNIQUE (cycle_id, employee_pn, employment_assignment, manager_pn)
);

CREATE INDEX IF NOT EXISTS idx_dialog_cases_cycle_manager
    ON dialog_cases (cycle_id, manager_pn);

CREATE TABLE IF NOT EXISTS package_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    manager_pn TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('versand', 'ruecklauf')),
    package_kind TEXT NOT NULL DEFAULT 'start'
        CHECK (package_kind IN ('start', 'update', 'return')),
    revision INTEGER NOT NULL DEFAULT 0,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_package_events_package
    ON package_events (package_id, direction, created_at);

CREATE TABLE IF NOT EXISTS mail_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_event_id INTEGER NOT NULL REFERENCES package_events(id) ON DELETE CASCADE,
    sender_email TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'prepared'
        CHECK (status IN ('prepared', 'draft_created', 'sent_confirmed', 'failed')),
    encryption_required INTEGER NOT NULL DEFAULT 1 CHECK (encryption_required IN (0, 1)),
    encryption_flag_verified INTEGER NOT NULL DEFAULT 0 CHECK (encryption_flag_verified IN (0, 1)),
    outlook_entry_id TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (package_event_id)
);

CREATE INDEX IF NOT EXISTS idx_mail_deliveries_status
    ON mail_deliveries (status, updated_at);

CREATE TABLE IF NOT EXISTS inbound_mail_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outlook_entry_id TEXT NOT NULL UNIQUE,
    internet_message_id TEXT NOT NULL DEFAULT '',
    sender_email TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    received_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN (
            'new', 'ready_to_move', 'review_required', 'moved', 'ignored', 'failed'
        )),
    contains_probation INTEGER NOT NULL DEFAULT 0 CHECK (contains_probation IN (0, 1)),
    target_folder TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inbound_mail_status
    ON inbound_mail_messages (status, received_at);

CREATE TABLE IF NOT EXISTS inbound_mail_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mail_message_id INTEGER NOT NULL
        REFERENCES inbound_mail_messages(id) ON DELETE CASCADE,
    attachment_index INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL,
    file_kind TEXT NOT NULL
        CHECK (file_kind IN ('md_pdf', 'html_workbook', 'other')),
    status TEXT NOT NULL
        CHECK (status IN ('stored', 'imported', 'duplicate', 'review_required', 'failed')),
    official_document_id INTEGER REFERENCES official_documents(id),
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (mail_message_id, attachment_index)
);

CREATE INDEX IF NOT EXISTS idx_inbound_attachment_sha
    ON inbound_mail_attachments (sha256, status);

CREATE TABLE IF NOT EXISTS official_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES dialog_cases(case_id) ON DELETE CASCADE,
    dialog_event_id INTEGER REFERENCES dialog_events(id),
    document_obligation_id INTEGER REFERENCES document_obligations(id),
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    employee_pn TEXT NOT NULL,
    manager_pn TEXT NOT NULL,
    document_kind TEXT NOT NULL
        CHECK (document_kind IN ('review', 'outlook', 'no_md')),
    variant TEXT NOT NULL
        CHECK (variant IN ('digital', 'scan', 'administrative')),
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    received_at TEXT NOT NULL,
    data_block_json TEXT NOT NULL DEFAULT '{}',
    extracted_text TEXT NOT NULL DEFAULT '',
    fill_sign_detected INTEGER NOT NULL DEFAULT 0,
    fill_sign_count INTEGER NOT NULL DEFAULT 0,
    signature_checked INTEGER NOT NULL DEFAULT 0,
    scan_required INTEGER NOT NULL DEFAULT 0,
    handoff_status TEXT NOT NULL DEFAULT 'not_applicable'
        CHECK (handoff_status IN (
            'not_applicable', 'needs_signature_check', 'waiting_scan', 'staged'
        )),
    handoff_filename TEXT NOT NULL DEFAULT '',
    handoff_at TEXT NOT NULL DEFAULT '',
    replaces_document_id INTEGER REFERENCES official_documents(id),
    replacement_reason TEXT NOT NULL DEFAULT '',
    replaced_at TEXT NOT NULL DEFAULT '',
    is_current INTEGER NOT NULL DEFAULT 1
        CHECK (is_current IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_official_documents_case
    ON official_documents (case_id, document_kind, variant, is_current);

CREATE UNIQUE INDEX IF NOT EXISTS idx_official_documents_current
    ON official_documents (case_id, document_kind, variant)
    WHERE is_current = 1;

CREATE TABLE IF NOT EXISTS case_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES dialog_cases(case_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES app_users(id),
    field_name TEXT NOT NULL CHECK (field_name IN (
        'official_scope', 'dialog_date', 'period_start', 'period_end',
        'overall_rating_code', 'agreement'
    )),
    old_value TEXT NOT NULL DEFAULT '',
    new_value TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_case_corrections_case
    ON case_corrections (case_id, created_at);

CREATE TABLE IF NOT EXISTS dialog_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    cycle_id INTEGER REFERENCES cycles(id) ON DELETE CASCADE,
    legacy_case_id TEXT REFERENCES dialog_cases(case_id) ON DELETE SET NULL,
    employment_id INTEGER NOT NULL REFERENCES employment_assignments(id),
    manager_assignment_id INTEGER NOT NULL REFERENCES manager_assignments(id),
    review_year INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'annual', 'probation_review', 'probation_outlook', 'interim',
        'transfer_review', 'departure_review', 'location_meeting'
    )),
    source TEXT NOT NULL CHECK (source IN ('rule', 'manual', 'workbook')),
    source_reason TEXT NOT NULL DEFAULT '',
    required_scope TEXT NOT NULL CHECK (required_scope IN (
        'full', 'review_only', 'outlook_only', 'none'
    )),
    period_start TEXT NOT NULL DEFAULT '',
    period_end TEXT NOT NULL DEFAULT '',
    dialog_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN (
        'planned', 'open', 'in_progress', 'completed', 'no_md', 'cancelled'
    )),
    sap_leading INTEGER NOT NULL DEFAULT 0 CHECK (sap_leading IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dialog_events_cycle
    ON dialog_events (cycle_id, status, event_type);

CREATE INDEX IF NOT EXISTS idx_dialog_events_assignment
    ON dialog_events (manager_assignment_id, period_start, period_end);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dialog_events_leading_sap
    ON dialog_events (employment_id, review_year)
    WHERE sap_leading = 1;

CREATE TABLE IF NOT EXISTS document_obligations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    obligation_id TEXT NOT NULL UNIQUE,
    dialog_event_id INTEGER NOT NULL REFERENCES dialog_events(id) ON DELETE CASCADE,
    document_kind TEXT NOT NULL CHECK (document_kind IN ('review', 'outlook', 'no_md')),
    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0, 1)),
    due_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
        'open', 'received', 'review', 'scan_pending', 'complete', 'waived', 'rejected'
    )),
    fulfilled_document_id INTEGER REFERENCES official_documents(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (dialog_event_id, document_kind)
);

CREATE INDEX IF NOT EXISTS idx_document_obligations_due
    ON document_obligations (status, due_date, document_kind);

CREATE TABLE IF NOT EXISTS sap_export_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    row_count INTEGER NOT NULL CHECK (row_count > 0),
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created')),
    user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sap_export_batches_cycle
    ON sap_export_batches (cycle_id, created_at);

CREATE TABLE IF NOT EXISTS sap_export_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES sap_export_batches(id) ON DELETE CASCADE,
    dialog_event_id INTEGER NOT NULL REFERENCES dialog_events(id),
    case_id TEXT NOT NULL REFERENCES dialog_cases(case_id),
    source_document_id INTEGER REFERENCES official_documents(id),
    source_version TEXT NOT NULL,
    employee_pn TEXT NOT NULL,
    employment_assignment TEXT NOT NULL,
    assessment_type INTEGER NOT NULL DEFAULT 1 CHECK (assessment_type = 1),
    it9075_start TEXT NOT NULL,
    it9075_end TEXT NOT NULL,
    dialog_date TEXT NOT NULL,
    assessment_period_start TEXT NOT NULL,
    assessment_period_end TEXT NOT NULL,
    overall_rating TEXT NOT NULL CHECK (overall_rating IN ('A', 'B', 'C', 'D', 'E')),
    UNIQUE (dialog_event_id)
);

CREATE INDEX IF NOT EXISTS idx_sap_export_rows_batch
    ON sap_export_rows (batch_id, employee_pn);

CREATE TABLE IF NOT EXISTS deadline_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    obligation_id INTEGER NOT NULL REFERENCES document_obligations(id) ON DELETE CASCADE,
    manager_pn TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('cycle', 'manager', 'case')),
    document_kind TEXT NOT NULL CHECK (document_kind IN ('review', 'outlook')),
    old_due_date TEXT NOT NULL,
    new_due_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deadline_changes_cycle
    ON deadline_changes (cycle_id, created_at);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    manager_pn TEXT NOT NULL,
    sender_email TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_html TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'prepared', 'draft_created', 'sent_confirmed', 'failed'
    )),
    encryption_required INTEGER NOT NULL DEFAULT 1 CHECK (encryption_required IN (0, 1)),
    encryption_flag_verified INTEGER NOT NULL DEFAULT 0 CHECK (encryption_flag_verified IN (0, 1)),
    outlook_entry_id TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reminders_manager
    ON reminders (cycle_id, manager_pn, id);

CREATE TABLE IF NOT EXISTS reminder_obligations (
    reminder_id INTEGER NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
    obligation_id INTEGER NOT NULL REFERENCES document_obligations(id) ON DELETE CASCADE,
    due_date_snapshot TEXT NOT NULL,
    PRIMARY KEY (reminder_id, obligation_id)
);
