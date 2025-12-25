# THERMO — AUDIT REGISTRY

This registry pins deterministic pytest anchors (simulation-only) to reproducible artifact runs.

## X01 — Entropic Recycling (Cooling / Coherence Recovery)

**Pytest anchor:** `THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py::test_x01_entropic_recycling_beats_baselines`

**Pinned trio (canonical):**
- **tessaris_entropic_recycler:** `479a09f`
- **open_loop:** `675cb4a`
- **random_jitter_gain:** `c47422e`

**Git commit (pinned):** `c9bc43d49`

**Repro (canonical):**
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/THERMO/src python -m pytest \
  THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py -vv

---

## 2) `THERMO/docs/X01_EVIDENCE_BLOCK.md`

```md
# X01 Evidence Block — Entropic Recycling (Simulation-Only)

## Claim (audit-safe)
Under a fixed noise level (“temperature proxy”), the Tessaris closed-loop recycler **reduces entropy proxy S** and **increases coherence proxy R** compared to baselines, while remaining bounded (no norm blow-up).

This is a deterministic, simulation-only demonstration on a complex lattice model. It makes **no physical-world thermodynamics claims**.

## Scope / Guardrails
- Model-only: information-field lattice + deterministic controller loop.
- No claims about real cooling, Maxwell-demon physical devices, or violations of thermodynamics.
- Verified only via pytest anchor + emitted artifacts.

## Environment Pin
- **GIT_COMMIT:** `c9bc43d49`

## Repro Command
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/THERMO/src python -m pytest \
  THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py -vv

Pinned Runs (Canonical Trio)

Artifacts live at:
THERMO/artifacts/programmable_thermo/X01/<run_hash>/

1) Tessaris controller (closed-loop)
	•	controller: tessaris_entropic_recycler
	•	run_hash: 479a09f
	•	metrics:
	•	S_initial = 0.9914859055905577
	•	S_final   = 0.08201637859451572
	•	R_initial = 0.008514094409442232
	•	R_final   = 0.9179836214054843
	•	max_norm  = 19.999999999999005

2) Baseline: open loop
	•	controller: open_loop
	•	run_hash: 675cb4a
	•	metrics:
	•	S_initial = 0.9914859055905577
	•	S_final   = 0.9743916280545185
	•	R_initial = 0.008514094409442232
	•	R_final   = 0.025608371945481535
	•	max_norm  = 18.86728481538823

3) Baseline: random jitter gain
	•	controller: random_jitter_gain
	•	run_hash: c47422e
	•	metrics:
	•	S_initial = 0.9914859055905577
	•	S_final   = 0.12621507059620962
	•	R_initial = 0.008514094409442232
	•	R_final   = 0.8737849294037904
	•	max_norm  = 19.999999999999005

What this proves (in-model)
	•	Entropy proxy decreases substantially under recycler vs both baselines.
	•	Coherence proxy increases substantially under recycler vs both baselines.
	•	Boundedness holds (max_norm <= 20), so improvements are not from instability.

Artifact Checklist (per run folder)

Expected files (minimum):
	•	meta.json (controller + test_id + run_hash)
	•	run.json (S/R series + summary metrics)
	•	any metrics.csv if emitted by writer

Pinned folders:
	•	THERMO/artifacts/programmable_thermo/X01/479a09f/
	•	THERMO/artifacts/programmable_thermo/X01/675cb4a/
	•	THERMO/artifacts/programmable_thermo/X01/c47422e/

---

## Apply in terminal

cd /workspaces/COMDEX

# write registry

# THERMO — AUDIT REGISTRY

This registry pins deterministic pytest anchors (simulation-only) to reproducible artifact runs.

## X01 — Entropic Recycling (Cooling / Coherence Recovery)

**Pytest anchor:** `THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py::test_x01_entropic_recycling_beats_baselines`

**Pinned trio (canonical):**
- **tessaris_entropic_recycler:** `479a09f`
- **open_loop:** `675cb4a`
- **random_jitter_gain:** `c47422e`

**Git commit (pinned):** `c9bc43d49`

**Repro (canonical):**
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/THERMO/src python -m pytest \
  THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py -vv

MD

write evidence block
