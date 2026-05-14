-- 007_kg_file.sql
-- File + Attachment entities

-- ─────────────────────────────────────────
-- Master file rows (A16)
-- One row per logical file, partitioned by kg.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kg_file (
  kg         TEXT NOT NULL,          -- 'personal' | 'work'

  file_id    TEXT NOT NULL,          -- stable id (e.g. 'file:' + ulid/uuid)
  name       TEXT,                   -- original filename: 'invoice.pdf'
  mime       TEXT,                   -- 'application/pdf', 'audio/webm', ...
  size       INTEGER,                -- bytes
  sha256     TEXT NOT NULL,          -- content hash for dedupe
  location   TEXT,                   -- 's3://...', 'rf://...', 'local://...' etc.
  version    INTEGER NOT NULL DEFAULT 1,  -- for future multi-version support

  created_ts INTEGER NOT NULL,       -- first time KG saw this file
  updated_ts INTEGER NOT NULL,       -- last time metadata changed

  PRIMARY KEY (kg, file_id)
);

-- Fast lookup by hash (satisfies A29 {kg, file.sha256})
CREATE INDEX IF NOT EXISTS idx_file_kg_sha
  ON kg_file (kg, sha256);

-- Optional helper: search by name per kg
CREATE INDEX IF NOT EXISTS idx_file_kg_name
  ON kg_file (kg, name);


-- ─────────────────────────────────────────
-- Attachments (A10)
-- Link kg_events rows (messages/calls/ptt) to files.
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kg_attachment (
  id         TEXT PRIMARY KEY,       -- attachment id (e.g. 'att:' + ulid)

  kg         TEXT NOT NULL,          -- 'personal' | 'work'
  event_id   TEXT NOT NULL,          -- fk → kg_events.id (message/file/call event)
  thread_id  TEXT,                   -- denormalized from kg_events.thread_id
  topic_wa   TEXT,                   -- denormalized from kg_events.topic_wa

  file_id    TEXT NOT NULL,          -- fk → kg_file.file_id (within same kg)
  mime       TEXT,                   -- override if different from kg_file.mime
  size       INTEGER,                -- override if specific to this attachment
  sha256     TEXT,                   -- usually same as kg_file.sha256

  created_ts INTEGER NOT NULL        -- when this attachment row was created
);

-- Look up all attachments for a given event (message/voice/mail)
CREATE INDEX IF NOT EXISTS idx_att_kg_event
  ON kg_attachment (kg, event_id);

-- Look up all events that reference a given file
CREATE INDEX IF NOT EXISTS idx_att_kg_file
  ON kg_attachment (kg, file_id);

-- Optional: quick per-thread attachment scans
CREATE INDEX IF NOT EXISTS idx_att_kg_thread_ts
  ON kg_attachment (kg, thread_id, created_ts);