# MATTER (Programmable Matter — Model-Only)

This pillar ships "matter" as **stable bound-state attractors** in a controlled lattice model.
No claims about creating atoms or real-world particles.

## Anchor
- MT01: Soliton Persistence (bound-state proxy)

## Repro
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv

Artifacts

Artifacts are written to:
MATTER/artifacts/programmable_matter/MT01/<run_hash>/

# MATTER (Programmable Matter) — Simulation-First, Audit-Ready

## What this is
Model-only "matter" as **stable bound-state attractors** (soliton-like localized packets) in a controlled lattice model.

## Shipped/Anchor
- MT01: Soliton Persistence (controller vs baselines), deterministic + artifact emission.

## Run
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv

  Artifacts

MATTER/artifacts/programmable_matter/MT01/<run_hash>/
	•	run.json, metrics.csv, meta.json, config.json
  
Guardrail

Claims are strictly about programmable operators + proxy metrics inside this simulation.

# MATTER (Model-only)

MT01: Soliton Persistence (audit-safe)

- Goal: maintain a localized "particle-like" attractor under noise in a controlled lattice model.
- Claims: strictly in-model operator control + proxy metrics. No physical-world claims.

Repro:
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv