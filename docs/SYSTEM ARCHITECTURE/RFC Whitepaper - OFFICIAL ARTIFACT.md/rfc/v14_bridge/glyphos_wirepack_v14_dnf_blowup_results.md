# WirePack v14 Bridge Benchmark: DNF blowup vs canonical tree
- Generated (UTC): 2026-01-08T23:27:33Z
- gzip level: 9
- Python: CPython 3.11.2 (Linux-4.4.0-x86_64-with-glibc2.36)

## What this demonstrates
For the classic blowup family `F(n) = (x0 ∨ y0) ∧ (x1 ∨ y1) ∧ ... ∧ (x(n-1) ∨ y(n-1))`:
- Explicit DNF expansion has **2^n** terms.
- The canonical (unexpanded) operator tree has **O(n)** nodes.

This artifact stores the measured byte sizes (raw + gzip) for:
- `canon_*`: a compact canonical JSON operator tree
- `dnf_*`: an explicit DNF-as-data JSON representation

## Results table
| n | terms(DNF) | canon_raw (B) | canon_gz (B) | dnf_raw (B) | dnf_gz (B) | gz_ratio (dnf/canon) |
|---:|----------:|-------------:|------------:|-----------:|----------:|---------------------:|
| 1 | 2 | 43 | 53 | 17 | 37 | 0.70 |
| 2 | 4 | 78 | 61 | 33 | 45 | 0.74 |
| 3 | 8 | 113 | 67 | 73 | 59 | 0.88 |
| 4 | 16 | 148 | 73 | 169 | 86 | 1.18 |
| 5 | 32 | 183 | 79 | 393 | 119 | 1.51 |
| 6 | 64 | 220 | 84 | 969 | 182 | 2.17 |
| 7 | 128 | 257 | 91 | 2313 | 326 | 3.58 |
| 8 | 256 | 294 | 98 | 5385 | 634 | 6.47 |
| 9 | 512 | 331 | 105 | 12297 | 1244 | 11.85 |
| 10 | 1024 | 368 | 112 | 27657 | 2508 | 22.39 |
| 11 | 2048 | 405 | 118 | 61449 | 5187 | 43.96 |
| 12 | 4096 | 442 | 123 | 135177 | 10315 | 83.86 |
| 13 | 8192 | 479 | 127 | 294921 | 21553 | 169.71 |
| 14 | 16384 | 516 | 131 | 638985 | 42918 | 327.62 |
| 15 | 32768 | 553 | 138 | 1376265 | 85750 | 621.38 |
| 16 | 65536 | 590 | 142 | 2949129 | 171879 | 1210.42 |
| 17 | 131072 | 627 | 147 | 6291465 | 342916 | 2332.76 |
| 18 | 262144 | 664 | 151 | 13369353 | 685238 | 4538.00 |

## Copy into repo
Place this file (and the JSON sibling) into:
`/workspaces/COMDEX/docs/SYSTEM ARCHITECTURE/RFC Whitepaper - OFFICIAL ARTIFACT.md/rfc/`

Recommended filenames:
- `glyphos_wirepack_v14_dnf_blowup_results.md`
- `glyphos_wirepack_v14_dnf_blowup_results.json`
