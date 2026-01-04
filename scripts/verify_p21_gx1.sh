#!/usr/bin/env bash
set -euo pipefail

cd "/workspaces/COMDEX" || exit 1

ROOT="docs/Artifacts/v0.4/P21_GX1"
RUN_ID="$(cat "$ROOT/runs/LATEST_RUN_ID.txt")"

( cd "$ROOT" && sha256sum -c "checksums/$RUN_ID.sha256" )
( cd "$ROOT" && sha256sum -c "ARTIFACTS_INDEX.sha256" )

echo "✅ P21_GX1 verify OK: $RUN_ID"
