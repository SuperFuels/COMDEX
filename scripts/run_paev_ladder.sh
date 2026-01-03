#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "== A — Simulation =="
pnpm exec vitest run \
  Glyph_Net_Browser/src/sim/tests/A2_resonant_addressing.test.ts \
  Glyph_Net_Browser/src/sim/tests/A31_chiral_handshake.test.ts \
  Glyph_Net_Browser/src/sim/tests/A4_klink_vs_distance.test.ts \
  Glyph_Net_Browser/src/sim/tests/A1_topology_gate_causality.test.ts

echo
echo "== B/C — Physical + Bench (validators only; require results JSON) =="
pytest -q backend/paev_ladder/tests || true

echo
echo "Done."
