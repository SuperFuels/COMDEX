# Bridge Benchmark v15: Parity (XOR) minterm blowup vs canonical tree
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

**Investor-grade claim (v15):** We formally prove (Lean) a parity program family where Boolean minterm DNF materialization produces 2^n terms while the canonical XOR operator tree stays 1+2n nodes, and we empirically measure that the gzipped Boolean-expanded IR becomes >8,220× larger than the gzipped canonical form by n=18.
