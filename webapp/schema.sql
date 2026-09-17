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
    last_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sap_import_id INTEGER NOT NULL REFERENCES sap_imports(id) ON DELETE CASCADE,
    employee_pn TEXT NOT NULL REFERENCES employees(pn),
    manager_pn TEXT NOT NULL,
    org_unit TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    UNIQUE (sap_import_id, employee_pn, manager_pn)
);

CREATE INDEX IF NOT EXISTS idx_reporting_lines_import_manager
    ON reporting_lines (sap_import_id, manager_pn);

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_year INTEGER NOT NULL,
    outlook_year INTEGER NOT NULL,
    sap_import_id INTEGER NOT NULL REFERENCES sap_imports(id),
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
    updated_at TEXT NOT NULL,
    UNIQUE (cycle_id, employee_pn, manager_pn)
);

CREATE INDEX IF NOT EXISTS idx_dialog_cases_cycle_manager
    ON dialog_cases (cycle_id, manager_pn);

CREATE TABLE IF NOT EXISTS package_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id TEXT NOT NULL,
    cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    manager_pn TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('versand', 'ruecklauf')),
    revision INTEGER NOT NULL DEFAULT 0,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_package_events_package
    ON package_events (package_id, direction, created_at);

CREATE TABLE IF NOT EXISTS official_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL REFERENCES dialog_cases(case_id) ON DELETE CASCADE,
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
    is_current INTEGER NOT NULL DEFAULT 1
        CHECK (is_current IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_official_documents_case
    ON official_documents (case_id, document_kind, variant, is_current);

CREATE UNIQUE INDEX IF NOT EXISTS idx_official_documents_current
    ON official_documents (case_id, document_kind, variant)
    WHERE is_current = 1;
