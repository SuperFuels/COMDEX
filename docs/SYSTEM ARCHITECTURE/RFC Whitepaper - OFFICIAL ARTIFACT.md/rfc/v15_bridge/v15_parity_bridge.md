# Bridge v15 — Parity (XOR) minterm blowup vs canonical operator tree

Generated: 2026-01-09

## Investor-grade claim (one sentence)

**We formally prove (Lean) a parity/XOR program family where Boolean minterm materialization produces 2^n terms while the canonical operator tree stays 1+2n nodes, and we empirically measure that the gzipped Boolean-expanded IR becomes >8,200× larger than the canonical form by n=18.**

## Artifacts

- Lean proof: `backend/modules/lean/workspace/SymaticsBridge/ParityBlowup.lean`
- Benchmark: `backend/tests/glyphos_wirepack_v15_parity_blowup_benchmark.py`
- Lock stub: `rfc/LOCK_v15_parity.txt`

## Formal statement (Lean)

- `dnfTerms(parity n) = 2^n`  (exponential minterm blowup under XOR materialization)
- `nodes(parity n) = 1 + 2n`  (linear canonical tree size)

## Proof snapshot (benchmark output)

```text
=== ✅ Bridge Benchmark v15: Parity (XOR) minterm blowup vs canonical tree ===
n | terms(DNF) | canon_raw | canon_gz | dnf_raw | dnf_gz | gz_ratio(dnf/canon)
--|-----------:|----------:|---------:|--------:|-------:|-------------------:
 1 |          2 |        25 |       41 |      23 |     43 |                1.05
 2 |          4 |        43 |       45 |      47 |     53 |                1.18
 3 |          8 |        61 |       48 |     105 |     68 |                1.42
 4 |         16 |        79 |       51 |     241 |     96 |                1.88
 5 |         32 |        97 |       54 |     553 |    146 |                2.70
 6 |         64 |       115 |       57 |    1257 |    227 |                3.98
 7 |        128 |       133 |       60 |    2825 |    396 |                6.60
 8 |        256 |       151 |       62 |    6281 |    752 |               12.13
 9 |        512 |       169 |       65 |   14345 |   1420 |               21.85
10 |       1024 |       188 |       69 |   32265 |   2858 |               41.42
11 |       2048 |       207 |       71 |   71689 |   5845 |               82.32
12 |       4096 |       226 |       74 |  157705 |  11773 |              159.09
13 |       8192 |       245 |       77 |  344073 |  23206 |              301.38
14 |      16384 |       264 |       80 |  745481 |  46180 |              577.25
15 |      32768 |       283 |       84 | 1605641 |  96092 |             1143.95
16 |      65536 |       302 |       87 | 3440649 | 189305 |             2175.92
17 |     131072 |       321 |       90 | 7340041 | 380896 |             4232.18
18 |     262144 |       340 |       92 | 15597577 | 756301 |             8220.66
LEAN_OK=1

SHA256 (v15)

845043eb70b3677f3601be07b4666b42a14b78b4079bdd970220fed50e4e7559  backend/modules/lean/workspace/SymaticsBridge/ParityBlowup.lean
982127b62245ca4b3e01e8d9298924422b291458d632998f3f97e34694f2b5b6  backend/tests/glyphos_wirepack_v15_parity_blowup_benchmark.py

Reproduce

python backend/tests/glyphos_wirepack_v15_parity_blowup_benchmark.py

cd backend/modules/lean/workspace
lake env lean SymaticsBridge/ParityBlowup.lean

Lock ID: GLYPHOS-BRIDGE-V15-PARITY
Status: Draft
Maintainer: Tessaris AI
Author: Kevin Robinson.
EOF

cat > v15_bridge/LOCK_v15_parity.txt <<‘EOF’
Lock ID: GLYPHOS-BRIDGE-V15-PARITY
Status: Draft
Maintainer: Tessaris AI
Author: Kevin Robinson

[Proof Snapshot]
see: v15_bridge/v15_parity_bridge.md (section “Proof snapshot”)

[SHA256]
845043eb70b3677f3601be07b4666b42a14b78b4079bdd970220fed50e4e7559  backend/modules/lean/workspace/SymaticsBridge/ParityBlowup.lean
982127b62245ca4b3e01e8d9298924422b291458d632998f3f97e34694f2b5b6  backend/tests/glyphos_wirepack_v15_parity_blowup_benchmark.py
