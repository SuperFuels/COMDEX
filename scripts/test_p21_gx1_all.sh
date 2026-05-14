#!/usr/bin/env bash
set -euo pipefail

cd "/workspaces/COMDEX" || exit 1

# Python GX1 tests (contract + determinism + schemas)
python -m pytest -q backend/genome_engine/tests

# TS smoke: artifact ladder exists and checksums verify
cd "/workspaces/COMDEX/Glyph_Net_Browser" || exit 1
npx vitest run src/sim/tests/P21_gx1_artifacts_smoke.test.ts
