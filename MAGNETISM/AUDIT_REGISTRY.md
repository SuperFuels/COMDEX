# MAGNETISM — AUDIT REGISTRY

Scope: Model-only programmable rotation/containment in a lattice simulator.
No real-world electromagnetic claims.

## Shipped Anchors
- MG01 — Flux Alignment (Curl Control): kappa closed-loop beats baselines on final alignment error (model-only).
- MG02 — Causal Containment (Magnetic Bottle): controller reduces leakage proxy vs baselines (model-only).

## Canonical Repro
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MAGNETISM/src python -m pytest MAGNETISM/tests/programmable_magnetism -q

Pinned Runs

MG02 (Pinned)
	•	tessaris_flux_hold: e4277ef
	•	open_loop: 216dc9e
	•	random_jitter_kappa: 54980ed

MG01 (Pinned)
	•	tessaris_flux_hold: 
	•	open_loop: 
	•	random_jitter_kappa: 

Evidence Blocks
	•	docs/MG01_EVIDENCE_BLOCK.md (filled from template)
	•	docs/MG02_EVIDENCE_BLOCK.md (filled from template)
MD

### B) Fill MG02 evidence block (using your pinned hashes)
```bash
cat > /workspaces/COMDEX/MAGNETISM/docs/MG02_EVIDENCE_BLOCK.md <<'MD'
EVIDENCE_BLOCK
Claim: MG02 Causal Containment — controller reduces leakage proxy and beats baselines in the same lattice model.
Scope: MAGNETISM / MG02
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/MAGNETISM/src python -m pytest MAGNETISM/tests/programmable_magnetism/test_mg02_causal_containment.py -q

Artifact_Paths:
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/run.json
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/metrics.csv
  - MAGNETISM/artifacts/programmable_magnetism/MG02/<RUN_HASH>/meta.json

Pinned_Runs:
  - MG02 tessaris_flux_hold: e4277ef
  - MG02 open_loop: 216dc9e
  - MG02 random_jitter_kappa: 54980ed

Results (from run.json):
  - Tessaris (e4277ef): leak_final=..., controller=tessaris_flux_hold
  - Open-loop (216dc9e): leak_final=..., controller=open_loop
  - Random jitter (54980ed): leak_final=..., controller=random_jitter_kappa

Notes:
  - Model-only containment/leakage proxy. No physical strong-force claims.
/EVIDENCE_BLOCK
MD

C) Pin MG01 hashes the same way (one good run each)

Run once, then copy the three newest MG01 folder names into the registry + MG01 evidence block:

@SuperFuels ➜ /workspaces/COMDEX (main) $ ls -1 MAGNETISM/artifacts/programmable_magnetism/MG01 | tail -n 10
77d0402
9e07d5b
c501145
@SuperFuels ➜ /workspaces/COMDEX (main) $ 

