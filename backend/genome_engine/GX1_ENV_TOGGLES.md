# GX1 Environment Toggles

This document defines the **runtime semantics** of environment variables used by the GX1 genomics benchmark
and its associated tests.

These toggles are **orthogonal**:

- `TESSARIS_TEST_QUIET` controls **noise** (gated prints; optional warning filtering in tests).
- `TESSARIS_DETERMINISTIC_TIME` controls **time determinism** (timestamps + any time-derived behavior).

---

## Toggle: `TESSARIS_DETERMINISTIC_TIME`

### Summary
When enabled, GX1 **MUST avoid wall-clock time** so repeated runs with the same seed/config produce identical
outputs (including trace digests).

### Expected values
- Set `TESSARIS_DETERMINISTIC_TIME=1` to enable deterministic time.

### What it affects
When `TESSARIS_DETERMINISTIC_TIME=1`, code paths that support deterministic time MUST:

- **Avoid wall-clock timestamps** (no `datetime.utcnow()`, no `time.time()` for artifact/trace timestamps).
- Use deterministic time surfaces (tick-driven time derived from `tick` + `dt` where applicable).
- Ensure any timestamp fields in deterministic artifacts use the canonical sentinel:
  - `created_utc` / `timestamp` ⇒ `0000-00-00T00:00:00Z`

### What it does NOT affect
This flag does **not** change:

- Seeded randomness that is already deterministic via configured seeds (RNG determinism is controlled by seeds, not time).
- Pure functions / stable hashing / stable JSON / artifact layout (those are deterministic by construction).
- External OS-level nondeterminism (thread scheduling, filesystem ordering) unless the code explicitly stabilizes it.

### Notes
- If you see a real UTC timestamp in GX1 artifacts/tests while this is set, something is still calling wall clock (bug/regression).
- This flag is intended for **tests + reproducible benchmark runs**.

---

## Toggle: `TESSARIS_TEST_QUIET`

### Summary
When enabled, test/CI runs SHOULD be quiet: suppress noisy internal prints/logs in GX1 paths.

### Expected values
- Set `TESSARIS_TEST_QUIET=1` to enable quiet mode.

### What it gates
When `TESSARIS_TEST_QUIET=1`:

- GX1 entrypoints and other noisy modules SHOULD use the Tessaris log gate:
  - Use `backend.utils.log_gate.tprint(...)` instead of `print(...)`
- Test harness MAY apply warning filters (if configured) to reduce irrelevant warning spam.

### What it does NOT affect
- Logging done outside the log gate (direct `print`, third-party loggers, etc.).
- Pytest’s own reporting and assertion output.

### Implementation contract
- Prefer `tprint(...)` in noisy GX1-facing code paths.
- If warning-filter hygiene is desired, apply it in pytest session configuration (not in production code).

---

## Recommended commands

### Run GX1 benchmark (deterministic + quiet)
```bash
cd /workspaces/COMDEX || exit 1
TESSARIS_TEST_QUIET=1 TESSARIS_DETERMINISTIC_TIME=1 PYTHONPATH=/workspaces/COMDEX \
python -m backend.genome_engine.run_genomics_benchmark \
  --config /workspaces/COMDEX/backend/genome_engine/examples/gx1_config.json
```

### Run GX1 test suite (quiet)
```bash
cd /workspaces/COMDEX || exit 1
TESSARIS_TEST_QUIET=1 \
pytest -q backend/genome_engine/tests
```

### Verify artifact checksums for the latest run
```bash
cd /workspaces/COMDEX || exit 1
ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
```
