-- kg schema v1
CREATE TABLE IF NOT EXISTS kg_events (
  id         TEXT PRIMARY KEY,         -- snowflake/uuid
  kg         TEXT NOT NULL,            -- 'personal' | 'work'
  owner_wa   TEXT NOT NULL,            -- e.g., 'kevin@wave.tp'
  thread_id  TEXT,                     -- stable synthetic for (kg, topic)
  topic_wa   TEXT,                     -- human-ish topic (ucs://... or handle)
  type       TEXT NOT NULL,            -- 'message'|'visit'|'file'|'call'|'ptt_session'|'floor_lock'
  kind       TEXT,                     -- subtype: 'text'|'voice'|'mail'|...
  ts         INTEGER NOT NULL,         -- ms epoch
  size       INTEGER,                  -- optional size bytes
  sha256     TEXT,                     -- for files/attachments
  payload    TEXT NOT NULL             -- compact JSON blob (stringified)
);

CREATE INDEX IF NOT EXISTS idx_kg_thread_ts ON kg_events (kg, thread_id, ts, id);
CREATE INDEX IF NOT EXISTS idx_kg_topicwa   ON kg_events (kg, topic_wa);
CREATE INDEX IF NOT EXISTS idx_kg_sha       ON kg_events (kg, sha256);