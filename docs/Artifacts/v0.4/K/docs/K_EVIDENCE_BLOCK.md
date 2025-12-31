# K Evidence Block — Computational Causality (K1–K5)

## Claim (model-only)
Under the Tessaris Unified Constants & Verification Protocol, the K-series demonstrates:
- bounded entropy propagation (K2),
- finite correlation length / locality (K2),
- cross-field causal coupling (K3),
- global synchrony (K4),
- invariance of causal ordering metrics across boosts (K5).

This is a **simulation / lattice-model** result only. No physical-world claims are made.

## Pinned Run
- RUN_ID: 20251230T191749Z_K
- Git revision: 5a271385a6156344e43dee93cd8779876d38a797

## Canonical Repro Commands
NOTE: run from repo root with PYTHONPATH set.

cd /workspaces/COMDEX || exit 1
export PYTHONPATH=.

python backend/photon_algebra/tests/paev_test_K1_causal_mesh.py
python backend/photon_algebra/tests/paev_test_K1_causal_stencil.py
python backend/photon_algebra/tests/paev_test_K1_stable_causal_stencil.py
python backend/photon_algebra/tests/paev_test_K1_sympy_roundtrip.py

python backend/photon_algebra/tests/paev_test_K2_correlation_decay.py
python backend/photon_algebra/tests/paev_test_K2_entropy_causality.py
python backend/photon_algebra/tests/paev_test_K2_multidomain_stress.py

python backend/photon_algebra/tests/paev_test_K3_crossfield_coupling.py
python backend/photon_algebra/tests/paev_test_K3_soliton_propagation.py
python backend/photon_algebra/tests/paev_test_K3b_damped_soliton.py

python backend/photon_algebra/tests/paev_test_K4_causal_synchrony.py
python backend/photon_algebra/tests/paev_test_K5_global_invariance.py

## Notes on Diagnostics (preserve warnings)
Some subtests emit warning/violation verdicts for an internal “front-speed” estimator (K1 stencil / K1 stable stencil / K3).
These warnings are preserved in pinned logs.
Canonical causal-bound evidence for this lock uses **K2 entropy-causality**, **K3b damped soliton**, and **K5 boost invariance**.

## Artifact Anchors
- Run folder:
  - docs/Artifacts/v0.4/K/runs/20251230T191749Z_K/
- Logs folder:
  - docs/Artifacts/v0.4/K/logs/
- Audit registry:
  - docs/Artifacts/v0.4/K/AUDIT_REGISTRY.md
- Checksums:
  - docs/Artifacts/v0.4/K/checksums/20251230T191749Z_K.sha256

## Verification
cd /workspaces/COMDEX || exit 1
sha256sum -c docs/Artifacts/v0.4/K/checksums/20251230T191749Z_K.sha256

Lock ID: K_LOCK_v0.4_20251230T191749Z_K
Status: LOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson
