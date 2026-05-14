# Bridge v16 — DAG reuse vs tree duplication

## Investor-grade claim (v16)
**We formally prove (Lean) that for a reuse-heavy program family, any tree-unfolded representation must scale as Ω(k·|S|) (duplicating a shared subgraph S k times) while an interned/DAG representation scales as O(|S|+k), and we empirically measure that the gzipped tree-duplicated IR becomes ~66.81× larger than the canonical/interned form by k=4096 (depth=6, fanout=2, seed=1337).**

## What is proved (Lean)
This bridge targets a different failure mode than Boolean normal-form blowups: **graph reuse vs tree duplication**.

We define a family that repeats the *same* subtree `S` exactly `k` times under a root. We compare:
- **Canonical / DAG-style size**: count `S` once + pay a small per-reference overhead.
- **Tree-expanded size**: duplicate `S` structurally `k` times (as in ordinary JSON AST trees).

**Lean file path:**
`backend/modules/lean/workspace/SymaticsBridge/DAGReuseBlowup.lean`

## What is measured (same-task bytes)
Benchmark compares two concrete encodings of the same reuse-heavy structure:
- **canon**: canonical DAG/interned-style encoding (subtree sent once; references reused)
- **tree**: explicit tree duplication (subtree bytes repeated k times)

We report raw bytes and gzip(bytes) (level 9), and the ratio `tree_gz / canon_gz`.

**Proof snapshot output (v16):**

=== ✅ Bridge Benchmark v16: DAG reuse vs tree duplication ===
subtree: depth=6, fanout=2, seed=1337

=== ✅ Bridge Benchmark v16: DAG reuse vs tree duplication ===
subtree: depth=6, fanout=2, seed=1337
k | canon_raw | canon_gz | tree_raw | tree_gz | gz_ratio(tree/canon)
--|----------:|---------:|---------:|--------:|--------------------:
   1 |      1587 |      523 |     1580 |     509 |                 0.97
   2 |      1587 |      523 |     3153 |     530 |                 1.01
   4 |      1587 |      521 |     6299 |     559 |                 1.07
   8 |      1587 |      523 |    12591 |     609 |                 1.16
  16 |      1588 |      523 |    25175 |     695 |                 1.33
  32 |      1588 |      523 |    50343 |     845 |                 1.62
  64 |      1588 |      523 |   100679 |    1124 |                 2.15
 128 |      1589 |      524 |   201351 |    1662 |                 3.17
 256 |      1589 |      523 |   402695 |    2735 |                 5.23
 512 |      1589 |      524 |   805383 |    4882 |                 9.32
1024 |      1590 |      523 |  1610759 |    9169 |                17.53
2048 |      1590 |      524 |  3221511 |   17758 |                33.89
4096 |      1590 |      523 |  6443015 |   34942 |                66.81

### Key takeaway
Even with gzip, **byte duplication from tree-only structure does not disappear** at scale.
At k=4096, the gzipped tree-duplicated representation is **~66.81× larger** than the canonical/interned form.

## Repro commands
Lean proof check:

cd /workspaces/COMDEX/backend/modules/lean/workspace
lake env lean SymaticsBridge/DAGReuseBlowup.lean
echo “LEAN_OK=1”

Benchmark run:

cd /workspaces/COMDEX
python backend/tests/glyphos_wirepack_v16_dag_reuse_blowup_benchmark.py



cat > v16_bridge/LOCK_v16_dag.txt <<'EOF'
Lock ID: GLYPHOS-BRIDGE-V16-DAG-REUSE
Status: Draft
Maintainer: Tessaris AI
Author: Kevin Robinson.
