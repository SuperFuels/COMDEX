# AUDIT_REGISTRY — P14_2 (v0.4)

RUN_ID: P14_220260102T220043Z_P14_P12SIM_EVAL_V02
GIT_REV: 30b5ab16eb695f028a8ce6aa23000f6101418f63

## Verify
```bash
cd /workspaces/COMDEX || exit 1
ROOT="docs/Artifacts/v0.4/P14_2"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"
( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )
```
