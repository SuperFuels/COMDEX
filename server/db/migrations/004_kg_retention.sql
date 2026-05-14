-- 004_kg_retention.sql (fixed: no expressions in PRIMARY KEY)

CREATE TABLE IF NOT EXISTS kg_retention (
  kg   TEXT NOT NULL,           -- 'personal'|'work'
  type TEXT NOT NULL,           -- event type: 'visit'|'message'|...
  kind TEXT NOT NULL DEFAULT '',-- '' means "all kinds" (was NULL)
  days INTEGER NOT NULL,        -- retention window in days
  PRIMARY KEY (kg, type, kind)
);

-- Normalize any preexisting NULLs (idempotent)
UPDATE kg_retention SET kind = '' WHERE kind IS NULL;

-- Defaults (A55)
INSERT OR IGNORE INTO kg_retention (kg, type, kind, days) VALUES
  ('personal','visit','',30),   -- 30d visits in personal
  ('work','visit','',90);       -- example default for work

-- Optional: compatibility view (presents '' back as NULL if you prefer)
CREATE VIEW IF NOT EXISTS v_kg_retention AS
SELECT kg, type, NULLIF(kind,'') AS kind, days
FROM kg_retention;