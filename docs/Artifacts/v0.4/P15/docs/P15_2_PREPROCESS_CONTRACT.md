# P15.2 — Preprocess Contract Stub (ROADMAP / UNLOCKED)

Status: ROADMAP / UNLOCKED

This module introduces a machine-checkable preprocessing contract for P15 portability work.
It does **not** download data and does **not** assert any biological result.

## Repo source-of-truth
- Contract JSON:
  - Glyph_Net_Browser/src/sim/portability/preprocess/p15_preprocess_contract.json
- Loader:
  - Glyph_Net_Browser/src/sim/portability/preprocess/p15_preprocess_contract.ts
- Smoke test:
  - Glyph_Net_Browser/src/sim/tests/P15_2_preprocess_contract_smoke.test.ts

## Promotion rule (to any LOCK)
- Replace all TBD fields with a real pipeline implementation + pinned versions
- Record the pipeline hash and exact commit
- Emit real outputs with recorded file hashes
