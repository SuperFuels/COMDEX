# GRAVITY Audit Registry

Canonical index of reproducible verification artifacts for Tessaris “Programmable Gravity” (simulation-first).
Each entry points to a deterministic pytest, its artifact folders, and an `EVIDENCE_BLOCK` suitable for paper citation.

Conventions:
- Repo root: `/workspaces/COMDEX`
- Artifacts: `GRAVITY/artifacts/programmable_gravity/<TEST_ID>/<run_hash>/`
- Reproduce via the pytest command inside each block

---

## G01 (VERIFIED)

**Test:** `GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py`

**Repro:**
```bash
env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py -q
```

**Artifacts:**
```
  - GRAVITY/artifacts/programmable_gravity/G01/e2b8382/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G01/e2b8382/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G01/f68243a/ (open_loop)
  - GRAVITY/artifacts/programmable_gravity/G01/f2abffe/ (random_jitter)
  - GRAVITY/artifacts/programmable_gravity/G01/f2abffe/ (random_jitter)
  - GRAVITY/artifacts/programmable_gravity/G01/f2abffe/ (random_jitter)
```

```
EVIDENCE_BLOCK
Claim: G01 — deterministic audit anchor (information-geometry / effective-curvature proxy).
Scope: Programmable Gravity / G01
Result:
  - tessaris_curvature_hold (e2b8382): mse_R = 4.55501343997e-05
  - tessaris_curvature_hold (e2b8382): mse = 4.55501343997e-05
  - open_loop (f68243a): mse = 0.0020513974111
  - random_jitter (f2abffe): mse = 0.609705297898
  - random_jitter (f2abffe): mse_R = 0.609705297898
Artifact_ID: G01_DEC25_2025
Code_Path: GRAVITY/src/programmable_gravity/
Data_Path:
  - GRAVITY/artifacts/programmable_gravity/G01/e2b8382/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G01/e2b8382/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G01/f68243a/ (open_loop)
  - GRAVITY/artifacts/programmable_gravity/G01/f2abffe/ (random_jitter)
  - GRAVITY/artifacts/programmable_gravity/G01/f2abffe/ (random_jitter)
  - GRAVITY/artifacts/programmable_gravity/G01/f2abffe/ (random_jitter)
Git_Commit: f957124e9359981858892acc0572b7f269a03fa8
Env: Python 3.12.x, pytest 8.x, TUPS_V1.2
Repro_Command: env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g01_curvature_from_entropy.py -q
Status: VERIFIED
Verified_On: 2025-12-25
Notes:
  - Effective-curvature proxy test in an information-geometry lattice model. No physical gravity/weight claims.
/EVIDENCE_BLOCK
```

## G02 (VERIFIED)

**Test:** `GRAVITY/tests/programmable_gravity/test_g02_geodesic_bending.py`

**Repro:**
```bash
env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g02_geodesic_bending.py -q
```

**Artifacts:**
```
  - GRAVITY/artifacts/programmable_gravity/G02/a3e37d2/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G02/963b289/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G02/aff203d/ (open_loop)
  - GRAVITY/artifacts/programmable_gravity/G02/b6475e0/ (open_loop)
  - GRAVITY/artifacts/programmable_gravity/G02/aff203d/ (random_jitter)
  - GRAVITY/artifacts/programmable_gravity/G02/a823bd6/ (random_jitter)
```

```
EVIDENCE_BLOCK
Claim: G02 — deterministic audit anchor (information-geometry / effective-curvature proxy).
Scope: Programmable Gravity / G02
Result:
  - tessaris_curvature_hold (a3e37d2): mse_R = 0.00193813214552
  - tessaris_curvature_hold (963b289): mse = 0.00193813214552
  - open_loop (aff203d): mse_R = 0.00768799991635
  - open_loop (b6475e0): mse = 0.00768799991635
  - random_jitter (aff203d): mse_R = 0.693462995317
  - random_jitter (a823bd6): mse = 0.693462995317
Artifact_ID: G02_DEC25_2025
Code_Path: GRAVITY/src/programmable_gravity/
Data_Path:
  - GRAVITY/artifacts/programmable_gravity/G02/a3e37d2/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G02/963b289/ (tessaris_curvature_hold)
  - GRAVITY/artifacts/programmable_gravity/G02/aff203d/ (open_loop)
  - GRAVITY/artifacts/programmable_gravity/G02/b6475e0/ (open_loop)
  - GRAVITY/artifacts/programmable_gravity/G02/aff203d/ (random_jitter)
  - GRAVITY/artifacts/programmable_gravity/G02/a823bd6/ (random_jitter)
Git_Commit: f957124e9359981858892acc0572b7f269a03fa8
Env: Python 3.12.x, pytest 8.x, TUPS_V1.2
Repro_Command: env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g02_geodesic_bending.py -q
Status: VERIFIED
Verified_On: 2025-12-25
Notes:
  - Effective-curvature proxy test in an information-geometry lattice model. No physical gravity/weight claims.
/EVIDENCE_BLOCK
```

## G03 (VERIFIED)

**Test:** `GRAVITY/tests/programmable_gravity/test_g03_curvature_energy_scaling.py`

**Repro:**
```bash
env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g03_curvature_energy_scaling.py -q
```

**Artifacts:**
```
  - GRAVITY/artifacts/programmable_gravity/G03/9c70a08/ (static_sweep)
  - GRAVITY/artifacts/programmable_gravity/G03/9c70a08/ (static_sweep)
```

```
EVIDENCE_BLOCK
Claim: G03 — deterministic audit anchor (information-geometry / effective-curvature proxy).
Scope: Programmable Gravity / G03
Result:
  - static_sweep (9c70a08): slope = -5.95102423836e-11
  - static_sweep (9c70a08): metric_final = N/A
Artifact_ID: G03_DEC25_2025
Code_Path: GRAVITY/src/programmable_gravity/
Data_Path:
  - GRAVITY/artifacts/programmable_gravity/G03/9c70a08/ (static_sweep)
  - GRAVITY/artifacts/programmable_gravity/G03/9c70a08/ (static_sweep)
Git_Commit: f957124e9359981858892acc0572b7f269a03fa8
Env: Python 3.12.x, pytest 8.x, TUPS_V1.2
Repro_Command: env PYTHONPATH=$PWD/GRAVITY/src python -m pytest GRAVITY/tests/programmable_gravity/test_g03_curvature_energy_scaling.py -q
Status: VERIFIED
Verified_On: 2025-12-25
Notes:
  - Effective-curvature proxy test in an information-geometry lattice model. No physical gravity/weight claims.
/EVIDENCE_BLOCK
```

