-- 008_kg_cookie.sql
-- Cookie / habit-style key–value ledger (A15)

CREATE TABLE IF NOT EXISTS kg_cookie (
  kg          TEXT NOT NULL,           -- 'personal' | 'work'
  id          TEXT PRIMARY KEY,        -- 'cookie:' + ulid/uuid (or hash)

  -- Who/what this cookie is scoped to
  scope       TEXT NOT NULL,           -- 'agent', 'thread', 'topic', 'global', etc.
  agent_wa    TEXT,                    -- optional: specific agent WA if scope='agent'
  thread_id   TEXT,                    -- optional: thread-scoped cookie
  topic_wa    TEXT,                    -- optional: topic-scoped cookie

  -- Key/value metadata
  key         TEXT NOT NULL,           -- logical key: 'last_host', 'pref:theme', etc.
  value_hash  TEXT NOT NULL,           -- hashed/normalized value (no raw secrets)
  policy      TEXT,                    -- 'habit', 'analytics', 'strict', etc.

  -- Lifetime / retention hints
  created_ts  INTEGER NOT NULL,        -- when we first wrote this
  updated_ts  INTEGER NOT NULL,        -- last refresh/update
  expires_ts  INTEGER,                 -- optional soft expiry (ms epoch)

  -- Optional: free-form JSON blob (no PII; keep small)
  meta        TEXT                     -- JSON string (e.g. {"count":3})
);

-- Fast lookups: "what cookies do I have for this scope + key?"
CREATE INDEX IF NOT EXISTS idx_cookie_scope_key
  ON kg_cookie (kg, scope, key);

-- Per-thread scoped habits (e.g. per-conversation preferences)
CREATE INDEX IF NOT EXISTS idx_cookie_thread
  ON kg_cookie (kg, thread_id, key);

-- Per-agent scoped habits
CREATE INDEX IF NOT EXISTS idx_cookie_agent
  ON kg_cookie (kg, agent_wa, key);

-- Optional: expiry sweep helper
CREATE INDEX IF NOT EXISTS idx_cookie_expires
  ON kg_cookie (kg, expires_ts);