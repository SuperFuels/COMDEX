# P15.1 — Dataset Registry Stub (ROADMAP / UNLOCKED)

Status: ROADMAP / UNLOCKED

This module introduces a machine-checkable dataset registry for P15 portability work.
It does **not** download data and does **not** assert any biological result.

## Repo source-of-truth
- Registry JSON:
  - Glyph_Net_Browser/src/sim/portability/datasets/p15_datasets.json
- Loader:
  - Glyph_Net_Browser/src/sim/portability/datasets/p15_datasets.ts
- Smoke test:
  - Glyph_Net_Browser/src/sim/tests/P15_1_dataset_registry_smoke.test.ts

## Promotion rule (to any LOCK)
- Replace all TBD fields with frozen accession/version/DOI
- Add file list with sha256 for each downloaded artifact (or equivalent canonical checksum)
- Pin preprocessing pipeline hash to a real pipeline implementation
