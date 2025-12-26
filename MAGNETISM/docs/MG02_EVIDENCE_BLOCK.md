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
