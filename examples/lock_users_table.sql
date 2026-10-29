-- 2026_10_29_add_user_flags.sql
ALTER TABLE users ADD COLUMN last_seen_at timestamptz DEFAULT now() NOT NULL;
CREATE INDEX idx_users_last_seen ON users (last_seen_at);
ALTER TABLE users ADD CONSTRAINT fk_users_team FOREIGN KEY (team_id) REFERENCES teams (id);
