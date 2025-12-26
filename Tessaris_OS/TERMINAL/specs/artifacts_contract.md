# Artifacts Contract (Phase 0)

## Required files per run folder
- run.json
  - MUST contain: test_id, run_hash, controller, seed
- metrics.csv
  - MUST be a CSV with headers; time series columns may vary
- meta.json
  - SHOULD contain: timestamp, versions, controller
- config.json
  - Full config sufficient to re-run deterministically

Folder convention (recommended):
<PILLAR>/artifacts/<namespace>/<TEST_ID>/<run_hash>/

## Optional files
- telemetry.jsonl
  - JSON Lines, one object per timestep
  - recommended keys: t, controller, action, metrics (or flattened)
- field.npz
  - numpy savez with arrays for replay (e.g. psi_real, psi_imag, p, etc.)
- frames/
  - PNG frames if you want video export later
