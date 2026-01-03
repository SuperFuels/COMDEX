#!/usr/bin/env bash
set -euo pipefail
cd /workspaces/COMDEX || exit 1
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests/P14_search_ga_es_smoke.test.ts
