## C01 — Shortcut Routing (Sigma / throat coupling)

EVIDENCE_BLOCK
Claim: C01 Shortcut Routing — throat-coupled Sigma-control reduces arrival time (correlation-threshold crossing)
       vs open-loop and random jitter baselines (model-only).
Scope: CONNECTIVITY / C01
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/CONNECTIVITY/src python -m pytest \
  CONNECTIVITY/tests/programmable_connectivity/test_c01_shortcut_routing.py -q

Artifact_Paths:
  - CONNECTIVITY/artifacts/programmable_connectivity/C01/<RUN_HASH>/run.json
  - CONNECTIVITY/artifacts/programmable_connectivity/C01/<RUN_HASH>/metrics.csv
  - CONNECTIVITY/artifacts/programmable_connectivity/C01/<RUN_HASH>/meta.json

Pinned_Runs:
  - C01 tessaris_sigma_hold: d9c8e20
  - C01 open_loop: 6096c20
  - C01 random_jitter_sigma: db6b9b8

Results (from run.json):
  - Tessaris: arrival_step=..., C_final=..., C_thresh=..., eta=...
  - Open-loop: arrival_step=..., C_final=..., C_thresh=..., eta=...
  - Random jitter: arrival_step=..., C_final=..., C_thresh=..., eta=...

Notes:
  - Model-only: “throat coupling” is a lattice operator for cross-site amplitude mixing.
  - No physical ER=EPR, no FTL, no real-world connectivity claims.
/EVIDENCE_BLOCK

## C01 — Shortcut Routing (Pinned)

- Status: VERIFIED (pytest anchor)
- Evidence: CONNECTIVITY/docs/C01_EVIDENCE_BLOCK.md
- Pinned runs:
  - tessaris_sigma_hold: d9c8e20
  - open_loop: 6096c20
  - random_jitter_sigma: db6b9b8