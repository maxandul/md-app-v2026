-- Temporary selections and immutable previews, not another conversation status.
CREATE TABLE hr_part_selections (
 id TEXT PRIMARY KEY,
 owner TEXT NOT NULL,
 filters_json TEXT NOT NULL,
 ids_json TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1,
 created_at INTEGER NOT NULL
);
CREATE TABLE hr_part_action_previews (
 id TEXT PRIMARY KEY,
 owner TEXT NOT NULL,
 selection_id TEXT NOT NULL REFERENCES hr_part_selections(id),
 plan_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'preview' CHECK(status IN ('preview','running','complete')),
 result_json TEXT NOT NULL DEFAULT '{}',
 created_at INTEGER NOT NULL
);
CREATE TABLE hr_part_action_reminders (
 preview_id TEXT NOT NULL REFERENCES hr_part_action_previews(id),
 reminder_id INTEGER NOT NULL REFERENCES reminders(id),
 PRIMARY KEY(preview_id,reminder_id)
);
