-- 009_kg_containerref.sql
-- ContainerRef entities: external docs/spaces linked to threads/topics (A17)

CREATE TABLE IF NOT EXISTS kg_container_ref (
  kg           TEXT NOT NULL,          -- 'personal' | 'work'
  id           TEXT PRIMARY KEY,       -- 'cont:' + ulid/uuid

  -- External thing we point at
  container_id TEXT NOT NULL,          -- stable id: e.g. 'canvas:123', 'drive:abc', 'url:https://...'
  kind         TEXT NOT NULL,          -- 'canvas', 'doc', 'sheet', 'notebook', 'dashboard', etc.
  path         TEXT,                   -- optional subpath inside container (e.g. '#section-2', 'tab:Overview')

  -- Graph linkage (who/what this container is "about")
  thread_id    TEXT,                   -- optional: thread this container is attached to
  topic_wa     TEXT,                   -- optional: topic this container is about

  created_ts   INTEGER NOT NULL,       -- when KG first saw this link
  updated_ts   INTEGER NOT NULL,       -- last time metadata changed

  meta         TEXT                    -- optional small JSON, e.g. {"title":"Spec v1","role":"source-of-truth"}
);

-- Fast: "what containers are attached to this thread?"
CREATE INDEX IF NOT EXISTS idx_container_thread
  ON kg_container_ref (kg, thread_id, kind);

-- Fast: "what containers are about this topic?"
CREATE INDEX IF NOT EXISTS idx_container_topic
  ON kg_container_ref (kg, topic_wa, kind);

-- Fast: "where is this external container referenced in this KG?"
CREATE INDEX IF NOT EXISTS idx_container_id
  ON kg_container_ref (kg, container_id);