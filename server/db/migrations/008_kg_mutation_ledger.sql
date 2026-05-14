-- 008_kg_mutation_ledger.sql
-- A58: Audit mutation ledger (hash-chained envelopes)

CREATE TABLE IF NOT EXISTS kg_mutation_ledger (
  kg         TEXT    NOT NULL,          -- 'personal' | 'work'
  seq        INTEGER NOT NULL,          -- monotonically increasing per kg
  ts         INTEGER NOT NULL,          -- ms since epoch
  op_kind    TEXT    NOT NULL,          -- 'events_batch' | 'forget' | 'upsert_entity' | 'retention_sweep' | ...
  op_desc    TEXT,                      -- optional: route or short description
  mutation   TEXT    NOT NULL,          -- JSON string (summary of the mutation)
  prev_hash  TEXT,                      -- previous hash in chain for this kg (or NULL for first)
  hash       TEXT    NOT NULL,          -- sha256(kg|seq|ts|op_kind|op_desc|mutation|prev_hash)

  PRIMARY KEY (kg, seq)
);

CREATE INDEX IF NOT EXISTS idx_kg_mutation_ledger_kg_seq
  ON kg_mutation_ledger (kg, seq DESC);