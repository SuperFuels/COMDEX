# MATTER / MT01 Evidence Block — Soliton Persistence (Template)

## Scope / Guardrail
Model-only, simulation-first. Claims are strictly about programmable operators + proxy metrics
in a controlled lattice model. No physical-world particle/atom claims.

## Pytest Anchor
- Test: MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py::test_mt01_soliton_persistence_beats_baselines

## Repro Command
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv

Pinned Commit
	•	GIT_COMMIT: TBD

Pinned Runs
	•	tessaris_soliton_pinner: TBD
	•	open_loop:              TBD
	•	random_jitter_chi:      TBD

Metrics (from run.json)
	•	peak_retention >= 0.90
	•	width_drift_pct <= 2.0
	•	boundedness: max_norm <= cap

# MATTER / MT01 Evidence Block — Soliton Persistence (Template)

## Scope / Guardrail
Model-only, simulation-first.
Claims are strictly about programmable operators + proxy metrics in a controlled lattice model.
No physical-world matter/atoms claims.

## Pytest Anchor
- Test: `MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py::test_mt01_soliton_persistence_beats_baselines`

## Pinned Git Commit
- GIT_COMMIT: `TBD`

## Repro Command
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv

Pinned Runs
	•	tessaris_soliton_hold: TBD
	•	open_loop: TBD
	•	random_jitter_chi: TBD

Summary Metrics (copy from run.json)
	•	peak_retention (tessaris): TBD
	•	width_drift_pct (tessaris): TBD
	•	max_norm (tessaris): TBD

## Cross-series context (non-claim; background only)
This section provides *interpretive linkage* within the same controlled model family. It is not additional evidence beyond the pinned MT01 runs.

- **Mass-emergence proxy mapping:** “Matter” in MT01 is defined strictly as a *persistent localized attractor* in the lattice field (peak + width persistence metrics).
- **Causal-closure compatibility:** Any Lorentz-like invariance / causal-boundedness claims are *not re-proven here*. See the L-series documentation for invariance results; MT01 is executed under the same model-only causality assumptions.
- **Containment vs transition mapping:** Stability in MT01 is achieved via bounded nonlinearity/pinning (χ-control / containment proxy). Any “decay/reformation” language is only a mapping to the Transition framework; MT01’s claim remains: the attractor persists under the configured parameters.