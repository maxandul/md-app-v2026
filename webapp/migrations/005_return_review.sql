CREATE TABLE hr_return_reviews (
    document_id INTEGER PRIMARY KEY REFERENCES official_documents(id),
    source_role TEXT NOT NULL CHECK(source_role IN ('digital','scan')),
    validation_origin TEXT NOT NULL CHECK(validation_origin IN ('manual','automatic','legacy')),
    validated_at TEXT NOT NULL,
    validated_by INTEGER REFERENCES app_users(id),
    validation_json TEXT NOT NULL DEFAULT '{}',
    evidence_id INTEGER REFERENCES hr_return_evidence(id),
    signature_status TEXT NOT NULL DEFAULT 'missing_scan'
        CHECK(signature_status IN ('missing_scan','pending','missing','requested','confirmed','legacy_confirmed')),
    external_followup TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE hr_return_evidence (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES official_documents(id),
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    import_id INTEGER REFERENCES word_pdf_imports(id),
    legacy_document_id INTEGER REFERENCES official_documents(id),
    created_at TEXT NOT NULL,
    created_by INTEGER REFERENCES app_users(id),
    UNIQUE(document_id,sha256)
);
CREATE TABLE hr_return_decisions (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES official_documents(id),
    evidence_id INTEGER REFERENCES hr_return_evidence(id),
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    details_json TEXT NOT NULL,
    user_id INTEGER REFERENCES app_users(id),
    created_at TEXT NOT NULL
);
CREATE TABLE hr_return_handoffs (
    document_id INTEGER PRIMARY KEY REFERENCES official_documents(id),
    evidence_id INTEGER REFERENCES hr_return_evidence(id),
    source_sha256 TEXT NOT NULL,
    destination TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('processing','failed','uncertain','staged')),
    error_message TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX hr_return_decisions_document ON hr_return_decisions(document_id,id);
INSERT INTO hr_return_reviews(document_id,source_role,validation_origin,validated_at)
    SELECT id,'digital','legacy','' FROM official_documents
    WHERE variant='digital' AND document_kind IN ('review','outlook');
INSERT INTO hr_return_evidence(document_id,original_filename,stored_path,sha256,legacy_document_id,created_at)
    SELECT d.id,s.original_filename,s.stored_path,s.sha256,s.id,s.received_at
    FROM official_documents d JOIN official_documents s
      ON s.case_id=d.case_id AND s.document_kind=d.document_kind
    WHERE d.variant='digital' AND d.is_current=1 AND s.variant='scan' AND s.is_current=1;
UPDATE hr_return_reviews SET evidence_id=(SELECT id FROM hr_return_evidence e WHERE e.document_id=hr_return_reviews.document_id),
    signature_status=CASE WHEN EXISTS(SELECT 1 FROM hr_return_evidence e JOIN official_documents s ON s.id=e.legacy_document_id
        WHERE e.document_id=hr_return_reviews.document_id AND s.signature_checked=1)
        THEN 'legacy_confirmed' ELSE 'pending' END
    WHERE EXISTS(SELECT 1 FROM hr_return_evidence e WHERE e.document_id=hr_return_reviews.document_id);

-- One derived status for detail pages, manager counts and closure checks.
CREATE VIEW hr_return_status AS
WITH base AS (
    SELECT d.id AS document_id,d.cycle_id,d.is_current,
        COALESCE(o.manager_pn,d.manager_pn) AS manager_pn,
        r.evidence_id,r.signature_status,r.external_followup,
        COALESCE(c.overall_rating_code IN ('D','E'),0) AS required,
        (COALESCE(h.status='staged',0) OR d.handoff_status='staged'
            OR COALESCE(s.handoff_status='staged',0)) AS locally_staged
    FROM official_documents d JOIN hr_return_reviews r ON r.document_id=d.id
    JOIN dialog_cases c ON c.case_id=d.case_id
    LEFT JOIN hr_resolved_obligations o ON o.id=d.document_obligation_id
    LEFT JOIN hr_return_evidence e ON e.id=r.evidence_id
    LEFT JOIN official_documents s ON s.id=e.legacy_document_id
    LEFT JOIN hr_return_handoffs h ON h.document_id=d.id
), readiness AS (
    SELECT *, (NOT required OR signature_status IN ('confirmed','legacy_confirmed')) AS signature_ready,
        (external_followup<>'' OR (locally_staged AND required
            AND signature_status NOT IN ('confirmed','legacy_confirmed'))) AS external_open
    FROM base
)
SELECT *, (signature_ready AND locally_staged AND NOT external_open) AS complete
FROM readiness;
