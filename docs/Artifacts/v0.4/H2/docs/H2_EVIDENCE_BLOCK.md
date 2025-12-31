# H2 Evidence Block — Emergent Arrow of Time (HAEV)

## Claim (Model-only)
In the Tessaris Photon Algebra H2 scenario, a persistent **Forward** entropy drift emerges under symmetric initial conditions, producing a directional “arrow” in proxy metrics:

- arrow_direction: Forward
- entropy_drift_mean: 9.201438522528822e-05
- mutual_information_asymmetry: 0.13947774398695087
- entropy_cycle_mean: 8.00599489387453

This is a **simulation / lattice-model** result only. No physical-world claims are made.

## Scope / Guardrails
- This evidence block certifies a **reproducible run** plus pinned artifacts (log, JSON, plot) and checksums.
- Claims apply only to the controlled model and parameters embedded in the test and emitted JSON.

## Test
- Canonical test:
  - docs/Artifacts/v0.4/H2/tests/haev_test_H2_arrow_of_time_emergence.py
- Runtime source:
  - backend/photon_algebra/tests/haev_test_H2_arrow_of_time_emergence.py

## Canonical Repro Command
```bash
cd /workspaces/COMDEX || exit 1
python backend/photon_algebra/tests/haev_test_H2_arrow_of_time_emergence.py
```

## Pinned Run
- RUN_ID: 20251230T183919Z_H2
- Git revision: 5a271385a6156344e43dee93cd8779876d38a797

## Pinned Artifacts
- Log:
  - docs/Artifacts/v0.4/H2/logs/20251230T183919Z_H2.log
- JSON:
  - docs/Artifacts/v0.4/H2/runs/20251230T183919Z_H2/H2_arrow_of_time_emergence.json
- Plot:
  - docs/Artifacts/v0.4/H2/runs/20251230T183919Z_H2/HAEV_H2_EntropyPerCycle.png
- Checksums:
  - docs/Artifacts/v0.4/H2/checksums/20251230T183919Z_H2.sha256

## Verification
```bash
cd /workspaces/COMDEX || exit 1
sha256sum -c docs/Artifacts/v0.4/H2/checksums/20251230T183919Z_H2.sha256
```

Lock ID: H2_LOCK_v0.4_20251230T183919Z_H2
Status: LOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson
