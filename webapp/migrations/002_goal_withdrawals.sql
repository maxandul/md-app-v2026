CREATE TABLE hr_goal_withdrawals (
 id INTEGER PRIMARY KEY,
 source_id INTEGER NOT NULL REFERENCES hr_goal_sources(id),
 confirmed_revision_id INTEGER NOT NULL REFERENCES hr_goal_revisions(id),
 through_revision INTEGER NOT NULL,
 reason TEXT NOT NULL,
 impact_json TEXT NOT NULL,
 user_id INTEGER REFERENCES app_users(id),
 created_at TEXT NOT NULL,
 UNIQUE(source_id,through_revision)
);
CREATE INDEX idx_hr_goal_withdrawal_source ON hr_goal_withdrawals(source_id,through_revision);
ALTER TABLE hr_goal_decisions ADD COLUMN withdrawal_id INTEGER REFERENCES hr_goal_withdrawals(id);
CREATE INDEX idx_hr_goal_withdrawal_decision ON hr_goal_decisions(withdrawal_id,case_id,id);
