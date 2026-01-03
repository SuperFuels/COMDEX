# P15.4 — Cross-Consistency Smoke (ROADMAP / UNLOCKED)

Status: ROADMAP / UNLOCKED

Adds a machine-checkable cross-consistency gate:
- Every prediction.datasetId must exist in the dataset registry.
- Every prediction.preprocessContractId must match the preprocess contract id.

No external downloads. No biological result asserted.

## Repo source-of-truth
- Test:
  - Glyph_Net_Browser/src/sim/tests/P15_4_cross_consistency_smoke.test.ts
- Registries/contracts:
  - Glyph_Net_Browser/src/sim/portability/datasets/p15_datasets.json
  - Glyph_Net_Browser/src/sim/portability/preprocess/p15_preprocess_contract.json
  - Glyph_Net_Browser/src/sim/portability/predictions/p15_predictions.json
