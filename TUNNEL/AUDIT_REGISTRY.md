# TUNNEL — AUDIT REGISTRY

## TN01 — Transmission Lock (Pinned)

Claim: closed-loop barrier controller tunes transmission toward a target band and beats baselines.

Repro:
env PYTHONPATH=$PWD/TUNNEL/src python -m pytest TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -q

Pinned runs:
- TN01 tessaris_transmission_lock: 26155ae
- TN01 open_loop: 301c1ed
- TN01 random_jitter_barrier: ed16af4

## TN01 — Transmission Lock (VERIFIED)

- Git_Commit: c9bc43d49
- Repro: `env PYTHONPATH=$PWD/TUNNEL/src python -m pytest TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -vv`

Pinned runs:
- tessaris_transmission_lock: 26155ae
- open_loop: 301c1ed
- random_jitter_barrier: ed16af4

Primary metric (final):
- Tessaris T_err_final = 0.03855035055914269
- Open-loop T_err_final = 0.14764589162053793
- Random jitter T_err_final = 0.13733284147924552

# TUNNEL — AUDIT REGISTRY

This registry pins deterministic pytest anchors and canonical evidence runs.
Model-only claims. No physical-world tunneling claims.
MD
fi

cat >> TUNNEL/AUDIT_REGISTRY.md <<'MD'

## TN01 — Transmission Lock (VERIFIED)

**Claim:** closed-loop barrier controller reduces transmission error vs open-loop and random jitter baselines (model-only).

**Repro:**
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/TUNNEL/src python -m pytest \
  TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -q

Pinned runs:
	•	tessaris_transmission_lock: 26155ae
	•	open_loop: 301c1ed
	•	random_jitter_barrier: ed16af4

Evidence block: TUNNEL/docs/TN01_EVIDENCE_BLOCK.md

