# MATTER — AUDIT REGISTRY

This registry lists shipped anchors and their pinned runs/commits.

## MT01 — Soliton Persistence (Audit-Pinned)

- **tessaris_soliton_hold:** `3fda94d`
- **open_loop:** `848448d`
- **random_jitter_gain:** `c282b54`

**Git commit (pinned):** `a73e9e146`

**Repro:**
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv
```

**Artifacts:**
- `MATTER/artifacts/programmable_matter/MT01/3fda94d/`
- `MATTER/artifacts/programmable_matter/MT01/848448d/`
- `MATTER/artifacts/programmable_matter/MT01/c282b54/`
