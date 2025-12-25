# INERTIA Audit Registry

Canonical index of reproducible verification artifacts for Tessaris “Programmable Inertia” (simulation-first).
Each entry points to a deterministic pytest, its artifact folders, and an `EVIDENCE_BLOCK` suitable for paper citation.

Conventions:
- Repo root: `/workspaces/COMDEX`
- Artifacts: `INERTIA/artifacts/programmable_inertia/<TEST_ID>/<run_hash>/`
- Reproduce via the pytest command inside each block

---

## I01 — Inertial Scaling (VERIFIED)

**Test:** `INERTIA/tests/programmable_inertia/test_i01_inertial_scaling.py`

**Repro:**
```bash
env PYTHONPATH=$PWD/INERTIA/src python -m pytest INERTIA/tests/programmable_inertia/test_i01_inertial_scaling.py -q
```

**Artifacts:**
- `INERTIA/artifacts/programmable_inertia/I01/7a54bba/` (tessaris_alpha_hold)
- `INERTIA/artifacts/programmable_inertia/I01/287c929/` (open_loop)
- `INERTIA/artifacts/programmable_inertia/I01/0b9dbc7/` (random_jitter_alpha)

EVIDENCE_BLOCK
Claim: I01 Inertial Scaling — closed-loop alpha controller drives velocity to target (low “inertial drag”) and beats open-loop + random-jitter baselines.
Scope: Programmable Inertia / I01
Metric(s):
  - Target tracking: err_final_tess <= 0.50 * err_final_open + 1e-12
  - Baseline dominance: err_final_tess <= err_final_random + 1e-12
Result:
  - Tessaris (7a54bba): err_final = 0.2279146147301252; v_final = 3.227914614730125; v_target = 3.0
  - Open-loop (287c929): err_final = 1.0126459987739407; v_final = 1.9873540012260593; v_target = 3.0
  - Random jitter (0b9dbc7): err_final = 2.75703378310234; v_final = 5.75703378310234; v_target = 3.0
Artifact_ID: I01_INERTIA_SCALING_DEC25_2025
Code_Path: INERTIA/src/programmable_inertia/
Data_Path:
  - INERTIA/artifacts/programmable_inertia/I01/7a54bba/
  - INERTIA/artifacts/programmable_inertia/I01/287c929/
  - INERTIA/artifacts/programmable_inertia/I01/0b9dbc7/
Git_Commit: <fill: git rev-parse HEAD after commit>
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Repro_Command: env PYTHONPATH=$PWD/INERTIA/src python -m pytest INERTIA/tests/programmable_inertia/test_i01_inertial_scaling.py -q
Status: VERIFIED
Verified_On: 2025-12-25
Notes:
  - “Inertia” here is an effective response/drag proxy in the lattice dynamics; no physical mass claims.
 /EVIDENCE_BLOCK

---

## I02 — Relativistic Inertial Surge (NEXT)

**Goal:** test controller behavior as `v` approaches an effective causal ceiling (`c_eff`) with a non-linear “wall” (modified dispersion / lattice cutoff proxy).

**Planned Test:** `INERTIA/tests/programmable_inertia/test_i02_relativistic_inertial_surge.py`

**Planned Assertions (audit-safe):**
- Reach high-velocity regime: `v_final >= v_floor` where `v_floor = 0.60 * c_eff` (or whichever threshold the L-Series specifies).
- Active decoupling evidence: `alpha_final < alpha_initial` (controller reduces coupling as velocity rises).
- Tracking: `abs(v_final - v_target)` beats open-loop and random-jitter.
- Optional: bounded dispersion residual proxy (if implemented): `dispersion_residual <= cutoff_tol`.

**Repro (after implementation):**
```bash
env PYTHONPATH=$PWD/INERTIA/src python -m pytest INERTIA/tests/programmable_inertia/test_i02_relativistic_inertial_surge.py -q
```

EVIDENCE_BLOCK
Claim: I02 Relativistic Inertial Surge — controller maintains low effective drag as velocity approaches causal ceiling by reducing coupling (alpha) and preserves target tracking under lattice cutoff nonlinearity.
Scope: Programmable Inertia / I02
Metric(s):
  - High-velocity reach: v_final_tess >= v_floor
  - Active decoupling: alpha_final_tess < alpha_initial_tess
  - Tracking dominance: err_final_tess <= k * err_final_open and err_final_tess <= err_final_random
Result:
  - Tessaris: <TBD>
  - Open-loop: <TBD>
  - Random jitter: <TBD>
Artifact_ID: I02_INERTIAL_SURGE_DEC25_2025
Code_Path: INERTIA/src/programmable_inertia/
Data_Path:
  - INERTIA/artifacts/programmable_inertia/I02/<tess_run_hash>/
  - INERTIA/artifacts/programmable_inertia/I02/<open_run_hash>/
  - INERTIA/artifacts/programmable_inertia/I02/<rand_run_hash>/
Git_Commit: <TBD>
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Repro_Command: env PYTHONPATH=$PWD/INERTIA/src python -m pytest INERTIA/tests/programmable_inertia/test_i02_relativistic_inertial_surge.py -q
Status: TBD
Verified_On: TBD
Notes:
  - “Relativistic / cutoff / dispersion” here is a controlled non-linear saturation proxy inside the simulation.
 /EVIDENCE_BLOCK

	•	INERTIA closure commit: 4ef9c8e76 (includes I01 + I02 + artifacts + INERTIA/AUDIT_REGISTRY.md)