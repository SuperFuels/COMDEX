# ENERGY Audit Registry

Canonical index of reproducible verification artifacts for Tessaris “Programmable Energy”.
Each entry points to a deterministic pytest, its artifact folders, and an `EVIDENCE_BLOCK` suitable for paper citation.

Conventions:
- Repo root: `/workspaces/COMDEX`
- Artifacts: `ENERGY/artifacts/programmable_energy/<TEST_ID>/<run_hash>/`
- Reproduce via the pytest command inside each block
- Sealed repo commit for these entries: `62af6f62d81a56418fc8daee2ce539cf02b9c1d5`

---

## PE01 — Focus Lock (VERIFIED)

**Test:** `ENERGY/tests/programmable_energy/test_pe01_focus_lock.py`

**Repro:**
```bash
python -m pytest ENERGY/tests/programmable_energy/test_pe01_focus_lock.py -q
```

**Primary Artifact (Tessaris):**
- `ENERGY/artifacts/programmable_energy/PE01/f5b939f/`

**Baseline Artifacts:**
- Open-loop: `ENERGY/artifacts/programmable_energy/PE01/3194902/`
- SPGD:      `ENERGY/artifacts/programmable_energy/PE01/2959371/`

**Primary visuals (in artifact folder):**
- `ENERGY/artifacts/programmable_energy/PE01/f5b939f/plots/target_intensity.png`
- `ENERGY/artifacts/programmable_energy/PE01/f5b939f/plots/intensity_final.png`
- `ENERGY/artifacts/programmable_energy/PE01/f5b939f/plots/metrics_over_time.png`

```text
EVIDENCE_BLOCK
Claim: PE01 Focus Lock — closed-loop phase control maintains ROI energy under disturbance and beats baselines.
Scope: Programmable Energy / PE01
Metric(s):
  - Final ROI efficiency: eta_final >= 10x open_loop_eta_final + 1e-6
  - Mean over last 20 steps: mean(eta_last20)_tess >= mean(eta_last20)_spgd - 1e-12
  - Non-collapse: min(eta_last20) >= 0.20 * mean(eta_last20) - 1e-12
Result:
  - Reference target ROI mass (geometry limit): eta_target ≈ 0.753479
  - Tessaris (run f5b939f): eta_final ≈ 0.7204986 (step=59)
  - Open-loop (run 3194902): eta_final ≈ 0.0000850 (step=59)
  - SPGD (run 2959371):      eta_final ≈ 0.0000850 (step=59)
Artifact_ID: PE01_FOCUS_DEC24_2025
Code_Path: ENERGY/src/programmable_energy/
Data_Path:
  - ENERGY/artifacts/programmable_energy/PE01/f5b939f/
  - ENERGY/artifacts/programmable_energy/PE01/3194902/
  - ENERGY/artifacts/programmable_energy/PE01/2959371/
Run_Hash: f5b939f
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Repro_Command: python -m pytest ENERGY/tests/programmable_energy/test_pe01_focus_lock.py -q
Status: VERIFIED
Verified_On: 2025-12-24
Notes:
  - Disturbance model is synthetic; see simulate_pe() in ENERGY/src/programmable_energy/controllers.py and config.json in each artifact folder.
  - This entry is the canonical citation target for downstream docs/papers referencing PE01.
 /EVIDENCE_BLOCK
```

---

## PE02 — Split Ratio Control (VERIFIED)

**Test:** `ENERGY/tests/programmable_energy/test_pe02_split_ratio.py`

**Repro:**
```bash
python -m pytest ENERGY/tests/programmable_energy/test_pe02_split_ratio.py -q
```

**Primary Artifact (Tessaris):**
- `ENERGY/artifacts/programmable_energy/PE02/50c3b5e/`

**Baseline Artifacts:**
- Open-loop: `ENERGY/artifacts/programmable_energy/PE02/84c8e1f/`
- SPGD:      `ENERGY/artifacts/programmable_energy/PE02/5067175/`

**Primary visuals (in artifact folder):**
- `ENERGY/artifacts/programmable_energy/PE02/50c3b5e/plots/target_intensity.png`
- `ENERGY/artifacts/programmable_energy/PE02/50c3b5e/plots/intensity_final.png`
- `ENERGY/artifacts/programmable_energy/PE02/50c3b5e/plots/metrics_over_time.png`

```text
EVIDENCE_BLOCK
Claim: PE02 Split Ratio — closed-loop phase control achieves a target left/right split ratio under disturbance and beats baselines.
Scope: Programmable Energy / PE02
Metric(s):
  - Split ratio error: err_tess <= 0.5 * err_open + 1e-6
  - Split ratio error: err_tess <= err_spgd + 1e-6
  - Absolute accuracy: err_tess <= 0.10
Result (run hashes):
  - Tessaris:   50c3b5e
  - Open-loop:  84c8e1f
  - SPGD:       5067175
Artifact_ID: PE02_SPLIT_DEC24_2025
Code_Path: ENERGY/src/programmable_energy/
Data_Path:
  - ENERGY/artifacts/programmable_energy/PE02/50c3b5e/
  - ENERGY/artifacts/programmable_energy/PE02/84c8e1f/
  - ENERGY/artifacts/programmable_energy/PE02/5067175/
Run_Hash: 50c3b5e
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Repro_Command: python -m pytest ENERGY/tests/programmable_energy/test_pe02_split_ratio.py -q
Status: VERIFIED
Verified_On: 2025-12-24
Notes: See config.json + plots in artifact folders for target and achieved intensity distributions.
 /EVIDENCE_BLOCK
```

---

## PE03 — Top-hat Hold (VERIFIED)

**Test:** `ENERGY/tests/programmable_energy/test_pe03_tophat_hold.py`

**Repro:**
```bash
python -m pytest ENERGY/tests/programmable_energy/test_pe03_tophat_hold.py -q
```

**Primary Artifact (Tessaris):**
- `ENERGY/artifacts/programmable_energy/PE03/27e3b26/`

**Baseline Artifacts:**
- Open-loop: `ENERGY/artifacts/programmable_energy/PE03/bb608c9/`
- SPGD:      `ENERGY/artifacts/programmable_energy/PE03/60fe754/`

**Primary visuals (in artifact folder):**
- `ENERGY/artifacts/programmable_energy/PE03/27e3b26/plots/target_intensity.png`
- `ENERGY/artifacts/programmable_energy/PE03/27e3b26/plots/intensity_final.png`
- `ENERGY/artifacts/programmable_energy/PE03/27e3b26/plots/metrics_over_time.png`

```text
EVIDENCE_BLOCK
Claim: PE03 Top-hat Hold — closed-loop phase control approximates a top-hat disk intensity profile under disturbance and beats baselines.
Scope: Programmable Energy / PE03
Metric(s):
  - Shape error: MSE_tess <= MSE_open + 1e-12
  - Shape error: MSE_tess <= MSE_spgd + 1e-12
  - Flatness in disk: (std/mean)_tess <= (std/mean)_open + 1e-12
  - Flatness in disk: (std/mean)_tess <= (std/mean)_spgd + 1e-12
  - Absolute sanity: MSE_tess <= 5e-5
Result (run hashes):
  - Tessaris:   27e3b26
  - Open-loop:  bb608c9
  - SPGD:       60fe754
Artifact_ID: PE03_TOPHAT_DEC24_2025
Code_Path: ENERGY/src/programmable_energy/
Data_Path:
  - ENERGY/artifacts/programmable_energy/PE03/27e3b26/
  - ENERGY/artifacts/programmable_energy/PE03/bb608c9/
  - ENERGY/artifacts/programmable_energy/PE03/60fe754/
Run_Hash: 27e3b26
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Repro_Command: python -m pytest ENERGY/tests/programmable_energy/test_pe03_tophat_hold.py -q
Status: VERIFIED
Verified_On: 2025-12-24
Notes: See config.json + plots in artifact folders for target and achieved intensity distributions.
 /EVIDENCE_BLOCK
```

---

## PE01 — Robustness Check (Seeds 1–5)

Purpose: confirm PE01 Focus Lock performance is not a lucky seed.

Config: `N=256, steps=60, drift_sigma=1e-3, roi_radius=10, target sigma=6.0`  
Controller: `TessarisGSController(max_phase_step=0.25)`  
Reference target ROI mass: `eta_target ≈ 0.753479`

Seed sweep summary (eta_final):
- Values: `0.753977, 0.752167, 0.750423, 0.750245, 0.753878`
- Mean ± std(pop): `0.752138 ± 0.001608`

| Seed | Run_Hash | eta_final | mean(eta_last20) | std(eta_last20) | Artifacts |
|---:|:---:|---:|---:|---:|:--|
| 1 | 973cc13 | 0.753977 | 0.753003 | 0.000553 | `ENERGY/artifacts/programmable_energy/PE01_SEEDS/973cc13/` |
| 2 | 1e88f8f | 0.752167 | 0.753013 | 0.001334 | `ENERGY/artifacts/programmable_energy/PE01_SEEDS/1e88f8f/` |
| 3 | 429687e | 0.750423 | 0.746065 | 0.002215 | `ENERGY/artifacts/programmable_energy/PE01_SEEDS/429687e/` |
| 4 | 1f13d09 | 0.750245 | 0.746590 | 0.002334 | `ENERGY/artifacts/programmable_energy/PE01_SEEDS/1f13d09/` |
| 5 | cb00d4f | 0.753878 | 0.752868 | 0.000694 | `ENERGY/artifacts/programmable_energy/PE01_SEEDS/cb00d4f/` |

Interpretation: PE01 Focus Lock is stable and reproducible across multiple seeds; performance approaches the target+ROI geometry limit in this toy model.


COMMIT=62af6f62d81a56418fc8daee2ce539cf02b9c1d5
perl -0777 -i -pe "s/(Run_Hash:\\s*f5b939f\\s*\\n)/\$1Git_Commit: $COMMIT\\n/; s/(Run_Hash:\\s*50c3b5e\\s*\\n)/\$1Git_Commit: $COMMIT\\n/; s/(Run_Hash:\\s*27e3b26\\s*\\n)/\$1Git_Commit: $COMMIT\\n/" /workspaces/COMDEX/ENERGY/AUDIT_REGISTRY.md
grep -n \"Git_Commit\" /workspaces/COMDEX/ENERGY/AUDIT_REGISTRY.md