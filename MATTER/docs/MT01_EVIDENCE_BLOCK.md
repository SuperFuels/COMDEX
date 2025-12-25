# MATTER / MT01 Evidence Block — Soliton Persistence (Audit-Pinned)

## Scope / Guardrail
Model-only, simulation-first.
Claims are strictly about programmable operators + proxy metrics in a controlled lattice model.
No “create atoms” claims. This is stable attractor / soliton persistence in-model.

## Pytest Anchor
- Test: MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py::test_mt01_soliton_persistence_beats_baselines

## Pinned Commit
- GIT_COMMIT: `a73e9e146`

## Repro Command
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv
```

## Pinned Runs (MT01)
- tessaris_soliton_hold: `3fda94d`
- open_loop:            `848448d`
- random_jitter_gain:   `c282b54`

## Artifact Paths
- MATTER/artifacts/programmable_matter/MT01/3fda94d/
- MATTER/artifacts/programmable_matter/MT01/848448d/
- MATTER/artifacts/programmable_matter/MT01/c282b54/

## Metrics (run.json)
Reviewer should confirm:
- peak_retention (higher is better; retention of localized peak)
- width_drift_pct (lower is better; FWHM drift proxy)
- max_norm (boundedness / stability proxy)
