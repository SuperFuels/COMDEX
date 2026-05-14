# MATTER / MT02 Evidence Block — Causal Collision (Audit-Pinned)

## Scope (Audit-Safe)
This evidence block certifies **model-only** behavior in the MATTER lattice simulator.  
Claims are restricted to **programmable operators** and **reproducible metrics** inside the controlled simulation harness.

We do **not** claim real-world particle physics, forces, or laboratory effects.

---

## Test Anchor
- **Pytest anchor:** `MATTER/tests/programmable_matter/test_mt02_causal_collision.py`
- **Test name:** `test_mt02_causal_collision_beats_baselines`

---

## Reproduction Command (Canonical)

```bash
cd /workspaces/COMDEX || exit 1
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt02_causal_collision.py -vv

Pinned Runs (MT02)
	•	tessaris_causal_collision: 20ba5f5
	•	open_loop: 8e04064
	•	random_jitter_chi: f93a791

Pinned artifact folders:
	•	MATTER/artifacts/programmable_matter/MT02/20ba5f5/
	•	MATTER/artifacts/programmable_matter/MT02/8e04064/
	•	MATTER/artifacts/programmable_matter/MT02/f93a791/

⸻

Claims (Audit-Safe)

Within the MT02 collision scenario, the Tessaris controller demonstrates:
	1.	Peak stability under collision

	•	Maintains post-collision peak retention in a safe band (no runaway focusing), while improving stability vs baselines.

	2.	Causal symmetry preservation proxy

	•	Preserves left/right symmetry under the test’s symmetry proxy metric better than open-loop and jitter baselines.

	3.	Boundedness

	•	Norm remains bounded (no numerical blow-up) under the pinned configuration.

⸻

Notes for Reviewers

Each pinned run folder contains:
	•	run.json (summary metrics + key series)
	•	metrics.csv (time series table for inspection)
	•	config.json (exact config used)
	•	meta.json (controller label + environment metadata)

This evidence block is valid only for the pinned runs above.

---

## 2) Update `MATTER/AUDIT_REGISTRY.md`

Append this **MT02 section** (or add it under the existing MT01 section):

```md
## MT02 — Causal Collision (Audit-Pinned)

Pinned runs:
- **tessaris_causal_collision:** `20ba5f5`
- **open_loop:** `8e04064`
- **random_jitter_chi:** `f93a791`

Artifacts:
- `MATTER/artifacts/programmable_matter/MT02/20ba5f5/`
- `MATTER/artifacts/programmable_matter/MT02/8e04064/`
- `MATTER/artifacts/programmable_matter/MT02/f93a791/`

Evidence block:
- `MATTER/docs/MT02_EVIDENCE_BLOCK.md`
