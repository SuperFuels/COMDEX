# PAEV-10 — Entanglement & Steering Suite (E2–E6) — v0.4 Evidence Block

**Model-scope only.** All results refer to photon-algebra simulation variables and engineered measurement protocol.

## Pinned run
- RUN_ID: `PAEV10_Entanglement_20260106T223946Z`
- Run folder:
  `docs/Artifacts/v0.4/PAEV10/entanglement/runs/PAEV10_Entanglement_20260106T223946Z/`
- GIT_REV:
  `.../GIT_REV.txt`
- Checksums:
  `.../SHA256SUMS.txt`

## Repro commands
```bash
cd /workspaces/COMDEX || exit 1
export PYTHONPATH=.

PYTHONPATH=. python backend/photon_algebra/tests/paev_test_E2_cv_entanglement.py
PYTHONPATH=. python backend/photon_algebra/tests/paev_test_E3_epr_steering.py
PYTHONPATH=. python backend/photon_algebra/tests/paev_test_E4_chsh_surrogate.py
PYTHONPATH=. python backend/photon_algebra/tests/paev_test_E6_bell_violation_feedback.py

cd docs/Artifacts/v0.4/PAEV10/entanglement/runs/PAEV10_Entanglement_20260106T223946Z || exit 1
sha256sum -c SHA256SUMS.txt