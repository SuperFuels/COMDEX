# PAEV — ARTIFACTS_INDEX (v0.4.2 composite)

This folder is an umbrella index for the PAEV engineered baselines staged under:

- docs/Artifacts/v0.4/P5v
- docs/Artifacts/v0.4/P6
- docs/Artifacts/v0.4/P6_1
- docs/Artifacts/v0.4/P7A
- docs/Artifacts/v0.4/P7B
- docs/Artifacts/v0.4/P8

## Recorded run IDs (2026-01-01 runs referenced by PAEV v0.4.2 docs)
- P7A: P7A20260101T134526Z_P7_LOOM (non-discriminative; discriminative_pass=False)
- P7B: P7B20260101T135228Z_P7_LINK
- P8:  P820260101T135216Z_P8_MUX (overall_pass=True)

## Audit rule
The Truth Chain treats TC-10 as LOCKED when each submodule folder above is LOCKED
(i.e., has ARTIFACTS_INDEX.md + ARTIFACTS_INDEX.sha256 + per-run checksums that verify).

This umbrella index is reviewer convenience only.
