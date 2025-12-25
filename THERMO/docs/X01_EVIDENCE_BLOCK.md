# X01 Evidence Block — Entropic Recycling (THERMO)

## Scope / guardrails
Model-only programmable thermo proxies. No real-world thermodynamics claims.

## Claim (audit-safe)
Under fixed noise settings (T, noise_sigma), the closed-loop **tessaris_entropic_recycler** reduces the entropy proxy S and increases coherence proxy R vs baselines, while remaining bounded (max_norm <= 20).

## Pinned git commit
- GIT_COMMIT: c9bc43d49

## Repro command
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/THERMO/src python -m pytest THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py -vv

## Pinned runs (X01)
- tessaris_entropic_recycler: 479a09f
- open_loop: 675cb4a
- random_jitter_gain: c47422e

## Summary metrics (from pinned run.json)

tessaris_entropic_recycler — 479a09f
- S_initial = 0.9914859055905577
- S_final   = 0.08201637859451572
- R_initial = 0.008514094409442232
- R_final   = 0.9179836214054843
- max_norm  = 19.999999999999005

open_loop — 675cb4a
- S_initial = 0.9914859055905577
- S_final   = 0.9743916280545185
- R_initial = 0.008514094409442232
- R_final   = 0.025608371945481535
- max_norm  = 18.86728481538823

random_jitter_gain — c47422e
- S_initial = 0.9914859055905577
- S_final   = 0.12621507059620962
- R_initial = 0.008514094409442232
- R_final   = 0.8737849294037904
- max_norm  = 19.999999999999005
