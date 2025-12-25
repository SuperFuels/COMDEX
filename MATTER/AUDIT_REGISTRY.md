# MATTER — AUDIT REGISTRY

This registry lists shipped anchors and their pinned runs/commits.

## MT01 — Soliton Persistence (bound-state proxy)
- **tessaris_soliton_pinner:** `TBD`
- **open_loop:** `TBD`
- **random_jitter_chi:** `TBD`

**Git commit (pinned):** `TBD`

### Repro
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv

Artifacts
	•	MATTER/artifacts/programmable_matter/MT01/<run_hash>/

    # MATTER — AUDIT REGISTRY

This registry pins shipped, reproducible anchors for the MATTER pillar.

## MT01 — Soliton Persistence (Bound-State Attractor Proxy)
- **tessaris_soliton_hold:** `TBD`
- **open_loop:** `TBD`
- **random_jitter_chi:** `TBD`

**Git commit (pinned):** `TBD`

### Repro
```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MATTER/src python -m pytest \
  MATTER/tests/programmable_matter/test_mt01_soliton_persistence.py -vv

  Artifact paths (expected)
	•	MATTER/artifacts/programmable_matter/MT01/<run_hash>/

    
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
