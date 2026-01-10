#!/usr/bin/env bash
set -euo pipefail

ROOT="/workspaces/COMDEX"

BRIDGE_DIR="$ROOT/docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge"
mkdir -p "$BRIDGE_DIR"

# Prefer bridge_only for Lean source (no Mathlib fetch); fall back to workspace if needed.
LEAN_SRC_BRIDGE_ONLY="$ROOT/backend/modules/lean/bridge_only/SymaticsBridge/V39_FenwickIndexNoMaterialization.lean"
LEAN_SRC_WORKSPACE="$ROOT/backend/modules/lean/workspace/SymaticsBridge/V39_FenwickIndexNoMaterialization.lean"

if [[ -f "$LEAN_SRC_BRIDGE_ONLY" ]]; then
  LEAN_SRC="$LEAN_SRC_BRIDGE_ONLY"
  LEAN_WS="$ROOT/backend/modules/lean/bridge_only"
  LEAN_REL="SymaticsBridge/V39_FenwickIndexNoMaterialization.lean"
else
  LEAN_SRC="$LEAN_SRC_WORKSPACE"
  LEAN_WS="$ROOT/backend/modules/lean/workspace"
  LEAN_REL="SymaticsBridge/V39_FenwickIndexNoMaterialization.lean"
fi

BENCH="$ROOT/backend/tests/glyphos_wirepack_v39_fenwick_index_no_materialization_benchmark.py"

# Artifact filenames to match your requested v39_bridge layout
LEAN_DST="$BRIDGE_DIR/V39_RangePrefixIndexNoMaterialization.lean"
OUT_TXT="$BRIDGE_DIR/v39_range_prefix_index_no_materialization_out.txt"
LOCK_SHA="$BRIDGE_DIR/v39_range_prefix_index_no_materialization_lock.sha256"
LOCK_TXT="$BRIDGE_DIR/LOCK_v39_range_prefix_index.txt"
BRIDGE_MD="$BRIDGE_DIR/v39_range_prefix_index_no_materialization_bridge.md"

# 1) Mirror Lean theorem into docs (public artifact folder)
cp -f "$LEAN_SRC" "$LEAN_DST"

# 2) Run benchmark and capture proof snapshot (includes LEAN_OK + SHA256 lines from benchmark itself)
python "$BENCH" | tee "$OUT_TXT"

# 3) Re-check Lean (single file) using the chosen workspace to ensure it compiles right now
#    (This is redundant if the benchmark already does it, but keeps the artifact pipeline deterministic.)
set +e
( cd "$LEAN_WS" && lake env lean "$LEAN_REL" ) >/dev/null 2>&1
LEAN_RC=$?
set -e

if [[ "$LEAN_RC" -ne 0 ]]; then
  echo "ERROR: Lean file failed to compile in $LEAN_WS ($LEAN_REL)."
  exit 1
fi

# 4) Compute sha256s (store paths relative to $ROOT like the older bridges)
sha_line () {
  local p="$1"
  sha256sum "$p" | sed "s|$ROOT/||"
}

LEAN_SHA="$(sha256sum "$LEAN_DST" | awk '{print $1}')"
BENCH_SHA="$(sha256sum "$BENCH" | awk '{print $1}')"
OUT_SHA="$(sha256sum "$OUT_TXT" | awk '{print $1}')"
MD_SHA="" # filled after writing md

GEN_DATE="$(date -I)"

# 5) Write Bridge MD (v38-style)
cat > "$BRIDGE_MD" <<EOF
# Bridge v39 — Range / Prefix Index over delta stream (Fenwick-first, no materialization)

Generated: $GEN_DATE

## Investor-grade claim (one sentence)

**We typecheck (Lean) the semantic update identity that makes maintained prefix/range indexes correct under point-set deltas, and we empirically verify (Python) that a Fenwick-maintained index answers prefix/range queries exactly without materializing full snapshots.**

## Artifacts

- Lean proof (bridge): \`docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/V39_RangePrefixIndexNoMaterialization.lean\`
- Benchmark: \`backend/tests/glyphos_wirepack_v39_fenwick_index_no_materialization_benchmark.py\`
- Lock stub: \`docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/LOCK_v39_range_prefix_index.txt\`
- Locked output: \`docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/v39_range_prefix_index_no_materialization_out.txt\`
- Lock hashes: \`docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/v39_range_prefix_index_no_materialization_lock.sha256\`

## Formal statement (Lean)

- Prefix update identity:
  \`prefix(setAt s idx new) j = prefix(s) j + (if idx ≤ j then (new-old) else 0)\`
- Range update identity:
  \`rangeSum(setAt s idx new) L R = rangeSum(s) L R + (if L ≤ idx ∧ idx ≤ R then (new-old) else 0)\`

## Proof snapshot (benchmark output)

\`\`\`text
$(cat "$OUT_TXT")
\`\`\`

## SHA256 (v39)

$(sha_line "$LEAN_DST")
$(sha_line "$BENCH")
$(sha_line "$OUT_TXT")

## Reproduce

\`\`\`bash
python backend/tests/glyphos_wirepack_v39_fenwick_index_no_materialization_benchmark.py

# Lean bridge check (use bridge_only if present to avoid Mathlib fetch)
cd backend/modules/lean/bridge_only && lake env lean SymaticsBridge/V39_FenwickIndexNoMaterialization.lean
# or (workspace)
cd backend/modules/lean/workspace && lake env lean SymaticsBridge/V39_FenwickIndexNoMaterialization.lean
\`\`\`

Lock ID: GLYPHOS-BRIDGE-V39-RANGE-PREFIX
Status: Draft
Maintainer: Tessaris AI
Author: Kevin Robinson.
EOF

# 6) Write lock stub (v38-style)
cat > "$LOCK_TXT" <<EOF
Lock ID: GLYPHOS-BRIDGE-V39-RANGE-PREFIX
Status: Draft
Maintainer: Tessaris AI
Author: Kevin Robinson

[Proof Snapshot]
see: docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/v39_range_prefix_index_no_materialization_bridge.md (section “Proof snapshot”)

[SHA256]
$(sha_line "$LEAN_DST")
$(sha_line "$BENCH")
$(sha_line "$OUT_TXT")
EOF

# 7) Write lock sha file (machine-checked list)
# Include the 3 critical locked files + the md itself.
MD_SHA="$(sha256sum "$BRIDGE_MD" | awk '{print $1}')"

cat > "$LOCK_SHA" <<EOF
$LEAN_SHA  docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/V39_RangePrefixIndexNoMaterialization.lean
$BENCH_SHA  backend/tests/glyphos_wirepack_v39_fenwick_index_no_materialization_benchmark.py
$OUT_SHA  docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/v39_range_prefix_index_no_materialization_out.txt
$MD_SHA  docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/v39_bridge/v39_range_prefix_index_no_materialization_bridge.md
EOF

echo "OK: populated v39 artifacts in:"
echo "  $BRIDGE_DIR"