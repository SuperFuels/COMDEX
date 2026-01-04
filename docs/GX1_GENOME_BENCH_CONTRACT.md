# GX1 Genome Benchmark Contract (P21_GX1)

Deterministic, contract-only simulation baseline (no wetlab claims).

## Required outputs after a run

Output root (default):
- docs/Artifacts/v0.4/P21_GX1

Files:
- GIT_REV.txt
- runs/LATEST_RUN_ID.txt
- ARTIFACTS_INDEX.md
- ARTIFACTS_INDEX.sha256
- checksums/<RUN_ID>.sha256
- runs/<RUN_ID>/GIT_REV.txt
- runs/<RUN_ID>/cmd/repro.sh
- runs/<RUN_ID>/CONFIG.json
- runs/<RUN_ID>/METRICS.json
- runs/<RUN_ID>/TRACE.jsonl
- runs/<RUN_ID>/REPLAY_BUNDLE.json

Verify:
```bash
cd /workspaces/COMDEX || exit 1
ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
