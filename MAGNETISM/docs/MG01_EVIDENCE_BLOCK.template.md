EVIDENCE_BLOCK
Claim: MG01 Flux Alignment — closed-loop kappa controller minimizes B_eff alignment error under deterministic drive and beats baselines.
Scope: MAGNETISM / MG01
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/MAGNETISM/src python -m pytest MAGNETISM/tests/programmable_magnetism/test_mg01_curl_control.py -q

Artifact_Paths:
  - MAGNETISM/artifacts/programmable_magnetism/MG01/<RUN_HASH>/run.json
  - MAGNETISM/artifacts/programmable_magnetism/MG01/<RUN_HASH>/metrics.csv
  - MAGNETISM/artifacts/programmable_magnetism/MG01/<RUN_HASH>/meta.json

Pinned_Runs:
  - MG01 tessaris_flux_hold: <RUN_HASH>
  - MG01 open_loop: <RUN_HASH>
  - MG01 random_jitter_kappa: <RUN_HASH>

Results:
  - Tessaris: ang_err_final=..., b_final=[..., ...], b_target=[1.0, 0.0], kappa_initial=..., kappa_final=...
  - Open-loop: ...
  - Random jitter: ...

Notes:
  - Model-only: B_eff is a finite-difference rotational observable computed from J_info proxies (vx, vy) in a periodic lattice.
  - No real-world electromagnetic claims.
/EVIDENCE_BLOCK
