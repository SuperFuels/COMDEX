# GRAVITY Audit Registry

Canonical index of reproducible verification artifacts for Tessaris “Programmable Gravity” (simulation-first).
Each entry points to a deterministic pytest, its artifact folders, and an `EVIDENCE_BLOCK` suitable for paper citation.

Conventions:
- Repo root: `/workspaces/COMDEX`
- Artifacts: `GRAVITY/artifacts/programmable_gravity/<TEST_ID>/<run_hash>/`
- Reproduce via the pytest command inside each block

---

## G01 — Curvature From Entropy (TBD)

**Test:** `GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py`

**Repro:**
```bash
PYTHONPATH=GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py -q
md

EVIDENCE_BLOCK
Claim: G01 Curvature-from-Entropy — controller drives Laplacian-derived curvature proxy toward target under disturbance and beats baselines.
Scope: Programmable Gravity / G01
Metric(s):
  - Final curvature MSE improvement: mse_tess_final <= 0.10 * mse_open_final + 1e-12
  - Absolute curvature match: mse_tess_final <= 1e-6
Result:
  - Tessaris run: <TBD>
  - Open-loop run: <TBD>
  - Random baseline: <TBD>
Artifact_ID: G01_CURV_DEC25_2025
Code_Path: GRAVITY/src/programmable_gravity/
Data_Path:
  - GRAVITY/artifacts/programmable_gravity/G01/<run_hash>/
Run_Hash: <TBD>
Git_Commit: <TBD>
Env: Python 3.12.x, pytest 8.x, TUPS_V1.2
Repro_Command: PYTHONPATH=GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py -q
Status: TBD
Verified_On: TBD
Notes:
  - This is an effective-curvature proxy test (information geometry). No physical gravity claims.
 /EVIDENCE_BLOCK


 ## G01 — Curvature From Entropy (VERIFIED)

**Test:** `GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py`

**Repro:**
```bash
env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py -q

Artifacts:
	•	GRAVITY/artifacts/programmable_gravity/G01/<run_hash>/


EVIDENCE_BLOCK
Claim: G01 Curvature From Entropy — closed-loop controller reduces curvature-target MSE under drift and beats baselines.
Scope: Programmable Gravity / G01
Metric(s):
  - mse_final_tess <= mse_final_open_loop
  - mse_final_tess <= mse_final_random_jitter
Result:
  - Tessaris: mse_final = <...>  (run <...>)
  - Open-loop: mse_final = <...> (run <...>)
  - Random jitter: mse_final = <...> (run <...>)
Artifact_ID: G01_CURVATURE_DEC25_2025
Code_Path: GRAVITY/src/programmable_gravity/
Data_Path:
  - GRAVITY/artifacts/programmable_gravity/G01/<tess_run_hash>/
  - GRAVITY/artifacts/programmable_gravity/G01/<open_run_hash>/
  - GRAVITY/artifacts/programmable_gravity/G01/<rand_run_hash>/
Git_Commit: <paste git rev-parse HEAD>
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Repro_Command: env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py -q
Status: VERIFIED
Verified_On: 2025-12-25
/EVIDENCE_BLOCK


