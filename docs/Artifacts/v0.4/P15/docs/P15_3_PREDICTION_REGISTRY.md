# P15.3 — Prediction Registry Stub (ROADMAP / UNLOCKED)

Status: ROADMAP / UNLOCKED

This module introduces a machine-checkable prediction registry for P15 portability work.
It does **not** download data and does **not** assert any biological result.

## Repo source-of-truth
- Registry JSON:
  - Glyph_Net_Browser/src/sim/portability/predictions/p15_predictions.json
- Loader:
  - Glyph_Net_Browser/src/sim/portability/predictions/p15_predictions.ts
- Smoke test:
  - Glyph_Net_Browser/src/sim/tests/P15_3_prediction_registry_smoke.test.ts

## Promotion rule (to any LOCK)
- Replace all TBD fields with preregistered metrics + null models + explicit PASS/FAIL thresholds
- Freeze datasetId + preprocessContractId to frozen versions with file hashes
