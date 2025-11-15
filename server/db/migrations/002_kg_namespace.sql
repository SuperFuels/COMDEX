-- 002_kg_namespace.sql
-- Enforce {kg, owner_wa} presence and sane values.
-- Use lightweight CHECK + triggers so we don't rewrite the table.

-- Ensure kg is either 'personal' or 'work'
CREATE TABLE IF NOT EXISTS _kg_flags (v TEXT PRIMARY KEY);
INSERT OR IGNORE INTO _kg_flags(v) VALUES ('personal'), ('work');

-- CHECK constraints are gentle; triggers provide error messages.
CREATE TRIGGER IF NOT EXISTS kg_events_namespace_ins
BEFORE INSERT ON kg_events
FOR EACH ROW
BEGIN
  -- kg required and valid
  SELECT
    CASE
      WHEN NEW.kg IS NULL OR NEW.kg NOT IN ('personal','work')
      THEN RAISE(ABORT, 'kg_events: invalid kg (expected personal|work)')
    END;

  -- owner required (non-empty)
  SELECT
    CASE
      WHEN NEW.owner_wa IS NULL OR length(trim(NEW.owner_wa)) = 0
      THEN RAISE(ABORT, 'kg_events: owner_wa is required')
    END;

  -- thread_id must match 'kg:{kg}:{topic_wa}' if provided
  SELECT
    CASE
      WHEN NEW.thread_id IS NOT NULL
       AND NOT (NEW.thread_id LIKE 'kg:' || NEW.kg || ':%')
      THEN RAISE(ABORT, 'kg_events: thread_id must be prefixed with kg:{kg}:')
    END;
END;

CREATE TRIGGER IF NOT EXISTS kg_events_namespace_upd
BEFORE UPDATE ON kg_events
FOR EACH ROW
BEGIN
  SELECT
    CASE
      WHEN NEW.kg IS NULL OR NEW.kg NOT IN ('personal','work')
      THEN RAISE(ABORT, 'kg_events:update: invalid kg')
    END;

  SELECT
    CASE
      WHEN NEW.owner_wa IS NULL OR length(trim(NEW.owner_wa)) = 0
      THEN RAISE(ABORT, 'kg_events:update: owner_wa is required')
    END;

  SELECT
    CASE
      WHEN NEW.thread_id IS NOT NULL
       AND NOT (NEW.thread_id LIKE 'kg:' || NEW.kg || ':%')
      THEN RAISE(ABORT, 'kg_events:update: thread_id must be prefixed with kg:{kg}:')
    END;
END;