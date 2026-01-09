# -----------------------------------------------------------------------------
# Tessaris Truth Chain — v0.4 (F16–F18 Artifact Bundle Index)
# Purpose: lock the F16–F18 paper artifact + executed tests + outputs (knowledge + plots).
# Maintainer: Tessaris AI
# Author: Kevin Robinson
# Last update: 2026-01-08 (Europe/Madrid)
# -----------------------------------------------------------------------------

## Run bundle
- RUN_ID: TC_F16F18_REBUILD_20260108T000000Z
- Run folder: docs/Artifacts/v0.4/F16F18/runs/TC_F16F18_REBUILD_20260108T000000Z/

## Contents (expected)
- paper/F16F18_quantum_multiverse_stabilization.tex
- tests/{paev_test_F16_quantum_gravity_multiverse.py,F17_test_quantum_domain_coupling.py,F18_test_landscape_equilibrium.py}
- knowledge/{F16_quantum_gravity_multiverse.json,F17_quantum_domain_coupling.json,F18_landscape_equilibrium.json}
- plots/{PAEV_F16_LambdaDiversity.png,PAEV_F16_SampleTraces.png,PAEV_F16_LandscapeMap.png,PAEV_F17_LambdaDomains.png,PAEV_F17_SynchronizationIndex.png,PAEV_F18_LandscapeConvergence.png,PAEV_F18_DriftHistogram.png}

## Lock semantics
This bundle is LOCKED only when SHA256SUMS.txt and SHA256SUMS.root.txt both verify.
