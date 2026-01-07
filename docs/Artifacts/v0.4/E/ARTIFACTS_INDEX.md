# Artifacts Index — v0.4 / E-Series (E1–E6h)

- Series: **E** (universality / cross-constant robustness)
- Scope: **E1–E6h**
- Maintainer: **Tessaris AI**
- Author: **Kevin Robinson**
- Run ID (UTC): **2026-01-06T20-17Z**
- Commit: see `GIT_REV.txt`
- Status: **LOCKED**

## Canonical suite scripts (copied into `tests/`)
- `paev_test_E1_ensemble_repro.py`
- `paev_test_E2_discretization.py`
- `paev_test_E3_boundary_geometry.py`  *(produces E3b refined output in current implementation)*
- `paev_test_E4_noise_greybody.py`
- `paev_test_E5b_entropy_propagation_stable.py`
- `paev_test_E6h_zero_mean_universality.py`

## Evidence produced by the suite
JSON evidence (source location prior to artifact copy):
- `backend/modules/knowledge/E1_ensemble_repro.json`
- `backend/modules/knowledge/E2_discretization.json`
- `backend/modules/knowledge/E3b_boundary_geometry_refined.json`
- `backend/modules/knowledge/E4_noise_greybody.json`
- `backend/modules/knowledge/E5b_entropy_propagation_stable.json`
- `backend/modules/knowledge/E6h_zero_mean_universality.json`

Plots referenced by the suite (as emitted by scripts):
- `PAEV_E5b_EntropyPropagation.png`
- `PAEV_E5b_SpectralLock.png`
- `PAEV_E6h_ZeroMeanUniversality.png`
- `PAEV_E6h_GammaTrace.png`

## Artifact layout
- `runs/2026-01-06T20-17Z/`
  - `stdout/` — captured stdout for each test
  - `json/` — copied JSON evidence listed above
  - `plots/` — copied plots listed above
- `tests/` — copied canonical test scripts
- `checksums/SHA256SUMS.txt` — sha256 of all files under `runs/2026-01-06T20-17Z/`

