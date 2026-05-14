# THERMO / X01 Evidence Block — Entropic Recycling (Audit-Pinned)

## Scope / Guardrail
Model-only, simulation-first.
Claims are strictly about programmable operators + proxy metrics in a controlled lattice model.
No physical-world thermodynamics claims.

## Pytest Anchor
- Test: THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py::test_x01_entropic_recycling_beats_baselines

## Pinned Git Commit
- GIT_COMMIT: 947c24450

## Repro Command (Canonical)
    cd /workspaces/COMDEX
    env PYTHONPATH=$PWD/THERMO/src python -m pytest \
      THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py -vv

## Pinned Runs (Artifacts)
Artifacts live under:
- THERMO/artifacts/programmable_thermo/X01/<run_hash>/

Pinned run hashes:
- tessaris_entropic_recycler: 479a09f
- open_loop:                675cb4a
- random_jitter_gain:       c47422e

## Observed Results (Pinned run.json)

tessaris_entropic_recycler (479a09f)
- S_initial = 0.9914859055905577
- S_final   = 0.08201637859451572
- R_initial = 0.008514094409442232
- R_final   = 0.9179836214054843
- max_norm  = 19.999999999999005

open_loop (675cb4a)
- S_initial = 0.9914859055905577
- S_final   = 0.9743916280545185
- R_initial = 0.008514094409442232
- R_final   = 0.025608371945481535
- max_norm  = 18.86728481538823

random_jitter_gain (c47422e)
- S_initial = 0.9914859055905577
- S_final   = 0.12621507059620962
- R_initial = 0.008514094409442232
- R_final   = 0.8737849294037904
- max_norm  = 19.999999999999005

## Acceptance Criteria (as enforced by test)
- Entropy proxy decreases under recycler.
- Recycler beats baselines on final entropy proxy.
- Stability: max(norm_series) <= 20.0 (bounded).
