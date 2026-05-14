EVIDENCE_BLOCK
Claim: TN01 Transmission Lock — closed-loop barrier controller reduces transmission error vs open-loop and random jitter baselines (model-only).
Scope: TUNNEL / TN01
Git_Commit: c9bc43d49
Repro_Command: env PYTHONPATH=$PWD/TUNNEL/src python -m pytest \
  TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -q

Artifact_Paths:
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/run.json
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/metrics.csv
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/meta.json
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/config.json

Pinned_Runs:
  - TN01 tessaris_transmission_lock: 26155ae
  - TN01 open_loop: 301c1ed
  - TN01 random_jitter_barrier: ed16af4

Results (from run.json):
  - Tessaris: T_target=0.4, T_final=0.36144964944085733, T_err_final=0.03855035055914269
  - Open-loop: T_target=0.4, T_final=0.2523541083794621,  T_err_final=0.14764589162053793
  - Random jitter: T_target=0.4, T_final=0.2626671585207545, T_err_final=0.13733284147924552

Notes:
  - Model-only: “tunneling / barrier” is a lattice transmission proxy under a programmable barrier operator.
  - No physical tunneling, no real-world barrier penetration claims.
/EVIDENCE_BLOCK
