EVIDENCE_BLOCK
Claim: MG02 Causal Containment — closed-loop kappa controller reduces packet leakage (mass outside radius R) under deterministic drive and beats baselines.
Scope: MAGNETISM / MG02
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/MAGNETISM/src python -m pytest MAGNETISM/tests/programmable_magnetism/test_mg02_causal_containment.py -vv

Artifact_Paths:
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/run.json
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/metrics.csv
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/meta.json

Pinned_Runs:
  - MG02 tessaris_flux_hold:   <RUN_HASH>
  - MG02 open_loop:            <RUN_HASH>
  - MG02 random_jitter_kappa:  <RUN_HASH>

Results (from run.json):
  - Tessaris: leakage_final=..., spread_final=..., ang_err_final=..., kappa_initial=..., kappa_final=...
  - Open-loop: ...
  - Random jitter: ...

Notes:
  - Model-only: packet containment is a scalar transport proxy coupled to kappa; no physical claims.
  - Leakage = mass outside radius R under periodic distance to center.
/EVIDENCE_BLOCK

Pin the MG02 runs (use these hashes)
	•	tessaris_flux_hold: 10d97b5
	•	open_loop: 216dc9e (or 7ffee86 / e4277ef / fa239df, but pick one and stick to it)
	•	random_jitter_kappa: 54980ed
	•	(gamma variants exist; don’t pin them unless MG02 is explicitly “gamma”)

  EVIDENCE_BLOCK
Claim: MG02 Causal Containment — closed-loop controller reduces (or matches within tolerance) leakage of a bounded “packet” metric versus baselines under deterministic lattice dynamics.
Scope: MAGNETISM / MG02
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/MAGNETISM/src python -m pytest MAGNETISM/tests/programmable_magnetism/test_mg02_causal_containment.py -q

Artifact_Paths:
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/run.json
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/metrics.csv
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/meta.json

Pinned_Runs:
  - MG02 tessaris_flux_hold:   10d97b5
  - MG02 open_loop:           216dc9e
  - MG02 random_jitter_kappa: 54980ed

Notes:
  - Model-only: containment/leakage is a proxy metric in a periodic lattice; no real-world electromagnetic claims.
 /EVIDENCE_BLOCK