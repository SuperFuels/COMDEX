EVIDENCE_BLOCK
Claim: C01 Shortcut Routing — throat-coupled (ER=EPR-inspired) Sigma-control reduces arrival time
       (correlation-threshold crossing) vs open-loop and random jitter baselines (model-only).
Scope: CONNECTIVITY / C01
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/CONNECTIVITY/src python -m pytest \
  CONNECTIVITY/tests/programmable_connectivity/test_c01_shortcut_routing.py -q

Artifact_Paths:
  - CONNECTIVITY/artifacts/programmable_connectivity/C01/<RUN_HASH>/run.json
  - CONNECTIVITY/artifacts/programmable_connectivity/C01/<RUN_HASH>/metrics.csv
  - CONNECTIVITY/artifacts/programmable_connectivity/C01/<RUN_HASH>/meta.json

Pinned_Runs:
  - C01 tessaris_sigma_hold: <RUN_HASH>
  - C01 open_loop: <RUN_HASH>
  - C01 random_jitter_sigma: <RUN_HASH>

Results (from run.json):
  - Tessaris: arrival_step=..., C_final=..., eta=0.9974, C_thresh=0.90
  - Open-loop: ...
  - Random jitter: ...

Notes:
  - Model-only: “throat coupling” is a lattice operator for cross-site amplitude mixing.
  - “Isomorphism constraints” are represented by pinned protocol constants (hbar,G,Lambda0,alpha)
    and fixed seed/config (determinism).
  - No physical ER=EPR, no FTL, no real-world connectivity claims.
/EVIDENCE_BLOCK
