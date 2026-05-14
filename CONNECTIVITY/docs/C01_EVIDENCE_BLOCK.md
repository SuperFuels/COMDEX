EVIDENCE_BLOCK
Claim: C01 Shortcut Routing — Sigma-controlled throat coupling reduces arrival time
       (correlation-threshold crossing) versus open-loop baseline (model-only).
Scope: CONNECTIVITY / C01
Git_Commit: c9bc43d49
Repro_Command: env PYTHONPATH=$PWD/CONNECTIVITY/src python -m pytest \
  CONNECTIVITY/tests/programmable_connectivity/test_c01_shortcut_routing.py -q

Pinned_Runs:
  - C01 tessaris_sigma_hold: d9c8e20
  - C01 open_loop: 6096c20
  - C01 random_jitter_sigma: db6b9b8

Key_Metrics (from run.json):
  - tessaris_sigma_hold: arrival_step=1,   C_final=0.9984387276393732, C_thresh=0.9, eta=0.9974
  - open_loop:         arrival_step=600, C_final=1.678669920329105e-05, C_thresh=0.9, eta=0.9974
  - random_jitter:     arrival_step=1,   C_final=0.9972178946670885, C_thresh=0.9, eta=0.9974

Notes:
  - Model-only operator: throat coupling mixes amplitudes between two lattice coordinates.
  - Arrival metric: first t where windowed complex correlation C(t) >= C_thresh at destination.
  - No physical ER=EPR, no FTL, no real-world connectivity claims.
/EVIDENCE_BLOCK
