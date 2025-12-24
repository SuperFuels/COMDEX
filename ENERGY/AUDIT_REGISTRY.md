# ENERGY Audit Registry

This registry is the canonical index of reproducible verification artifacts for Tessaris “Programmable Energy”.
Each entry points to a deterministic test, its artifact folder, and an EVIDENCE_BLOCK suitable for paper citation.

Conventions:
- Repo root assumed: /workspaces/COMDEX
- Artifacts live under: ENERGY/artifacts/programmable_energy/<TEST_ID>/<run_hash>/
- Reproduce by running the pytest command listed in the block.

---

## PE01 — Focus Lock (VERIFIED)

**Test:** `ENERGY/tests/programmable_energy/test_pe01_focus_lock.py`  
**Repro:**
```bash
python -m pytest ENERGY/tests/programmable_energy/test_pe01_focus_lock.py -q

Primary Artifact (Tessaris):
	•	ENERGY/artifacts/programmable_energy/PE01/f5b939f/

Baseline Artifacts:
	•	Open-loop: ENERGY/artifacts/programmable_energy/PE01/3194902/
	•	SPGD:      ENERGY/artifacts/programmable_energy/PE01/2959371/

EVIDENCE_BLOCK
Claim: PE01 Focus Lock — closed-loop phase control maintains ROI energy under disturbance and beats baselines.
Scope: Programmable Energy / PE01
Metric(s):
  - Final ROI efficiency eta_final >= 10x open_loop_eta_final + 1e-6
  - Mean eta over last 20 steps >= SPGD mean (last 20) - 1e-12
  - Non-collapse: min(last20_eta) >= 0.20 * mean(last20_eta) - 1e-12
Result:
  - Tessaris eta_final ≈ 0.059603 (run f5b939f)
  - Open-loop eta_final ≈ 0.0000850 (run 3194902)
  - SPGD eta_final ≈ 0.0000850 (run 2959371)
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
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5

PE02 — Split Ratio (PENDING)

Status: SKIPPED (enable after PE01 is stable and PE02 thresholds are defined)
	•	Test stub: ENERGY/tests/programmable_energy/test_pe02_split_ratio.py
	•	Artifacts path: ENERGY/artifacts/programmable_energy/PE02/<run_hash>/

⸻

PE03 — Top-Hat Hold (PENDING)

Status: SKIPPED (enable after PE02 and PE03 thresholds are defined)
	•	Test stub: ENERGY/tests/programmable_energy/test_pe03_tophat_hold.py
	•	Artifacts path: ENERGY/artifacts/programmable_energy/PE03/<run_hash>/


## PE02 — Split Ratio Control (VERIFIED)

**Test:** `ENERGY/tests/programmable_energy/test_pe02_split_ratio.py`  
**Repro:**
```bash
python -m pytest ENERGY/tests/programmable_energy/test_pe02_split_ratio.py -q


Primary Artifact (Tessaris):
	•	ENERGY/artifacts/programmable_energy/PE02/50c3b5e/

Baseline Artifacts:
	•	Open-loop: ENERGY/artifacts/programmable_energy/PE02/84c8e1f/
	•	SPGD:      ENERGY/artifacts/programmable_energy/PE02/5067175/


EVIDENCE_BLOCK
Claim: PE02 Split Ratio — closed-loop phase control achieves a target left/right split ratio under disturbance and beats baselines.
Scope: Programmable Energy / PE02
Metric(s):
  - Split ratio error: err_tess <= 0.5 * err_open + 1e-6
  - Split ratio error: err_tess <= err_spgd + 1e-6
  - Absolute accuracy: err_tess <= 0.10
Result (run hashes):
  - Tessaris: 50c3b5e
  - Open-loop: 84c8e1f
  - SPGD: 5067175
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
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5

## PE03 — Top-hat Hold (VERIFIED)

**Test:** `ENERGY/tests/programmable_energy/test_pe03_tophat_hold.py`  
**Repro:**
```bash
python -m pytest ENERGY/tests/programmable_energy/test_pe03_tophat_hold.py -q

Primary Artifact (Tessaris):
	•	ENERGY/artifacts/programmable_energy/PE03/27e3b26/

Baseline Artifacts:
	•	Open-loop: ENERGY/artifacts/programmable_energy/PE03/bb608c9/
	•	SPGD:      ENERGY/artifacts/programmable_energy/PE03/60fe754/

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
  - Tessaris: 27e3b26
  - Open-loop: bb608c9
  - SPGD: 60fe754
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
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5

## PE01 — Focus Lock (UPDATED: centroid/tilt servo improvement)

EVIDENCE_BLOCK
Claim: PE01 Focus Lock — closed-loop phase control maintains ROI energy under disturbance and beats baselines.
Scope: Programmable Energy / PE01
Metric(s):
  - Tessaris beats Open-loop on final eta (see Result)
  - Tessaris beats SPGD on final eta (see Result)
Result:
  - Tessaris eta_final ≈ 0.72050 (run_hash: f5b939f, step=59)
  - SPGD eta_final ≈ 0.0000850 (run_hash: 2959371, step=59)
  - Open-loop eta_final ≈ 0.0000850 (run_hash: 3194902, step=59)
Artifact_ID: PE01_FOCUS_DEC24_2025
Code_Path: ENERGY/src/programmable_energy/
Data_Path:
  - ENERGY/artifacts/programmable_energy/PE01/f5b939f/
  - ENERGY/artifacts/programmable_energy/PE01/2959371/
  - ENERGY/artifacts/programmable_energy/PE01/3194902/
Repro_Command: python -m pytest ENERGY/tests/programmable_energy/test_pe01_focus_lock.py -q
Env: Python 3.12.1, pytest 8.4.1, TUPS_V1.2
Status: VERIFIED
Verified_On: 2025-12-24
Notes: PE01 controller updated with centroid/tilt servo + ROI-weighted GS; visuals frozen under ENERGY/docs/programmable_energy/figures/PE01_LOCKED/
/EVIDENCE_BLOCK
Git_Commit: 62af6f62d81a56418fc8daee2ce539cf02b9c1d5

COMMIT=62af6f62d81a56418fc8daee2ce539cf02b9c1d5
perl -0777 -i -pe "s/(Run_Hash:\\s*f5b939f\\s*\\n)/\$1Git_Commit: $COMMIT\\n/; s/(Run_Hash:\\s*50c3b5e\\s*\\n)/\$1Git_Commit: $COMMIT\\n/; s/(Run_Hash:\\s*27e3b26\\s*\\n)/\$1Git_Commit: $COMMIT\\n/" /workspaces/COMDEX/ENERGY/AUDIT_REGISTRY.md
grep -n \"Git_Commit\" /workspaces/COMDEX/ENERGY/AUDIT_REGISTRY.md