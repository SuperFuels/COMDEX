# AUDIT_REGISTRY — P21_GX1 (v0.4)

RUN_ID: P21_GX1_f9fba438_S1337
GIT_REV: 87975b9e13a52f8f64ba3fae37391916bdf8225a

## Verify
```bash
cd /workspaces/COMDEX || exit 1
ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
```
## 2026-01-04 — GX1 schema-compat hotfix (metrics root sanitization)

**Change (plumbing only; no scientific claim change).**
- File: `backend/genome_engine/run_genomics_benchmark.py`
- Behavior: builder-internal trace controls are not part of the public metrics contract and MUST NOT appear at the metrics root.
- Fix: sanitize these keys prior to metrics schema validation / write-out:
  - `metrics.pop("mode", None)`
  - `metrics.pop("stride", None)`
  - `metrics.pop("max_events", None)`
- Reason: `gx1_genome_benchmark_metrics.schema.json` forbids additional root properties; builder was leaking `mode`.

**Evidence.**
- Tests: `backend/genome_engine/tests` — **17 passed** (with `TESSARIS_TEST_QUIET=1 TESSARIS_DETERMINISTIC_TIME=1`)

Lock ID: GX1-METRICS-SCHEMA-COMPAT-2026-01-04  
Status: RECORDED (plumbing hotfix; tests green)  
Maintainer: Tessaris AI  
Author: Kevin Robinson