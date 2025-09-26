# Photon Benchmarks

## Core (small expressions) — Raw Numbers

| Expr | Photon ms | PhotonC Basic ms | PhotonC Adv ms | SymPy ms | Photon size | Basic size | Adv size | SymPy size | CompRaw | CompBasic | CompAdv | SpeedRaw | SpeedBasic | SpeedAdv |
|------|-----------|------------------|----------------|----------|-------------|------------|----------|------------|---------|-----------|---------|----------|-----------|----------|
| add_chain | 14.522 | 0.591 | 0.647 | 5.651 | 6 | 8 | 8 | 8 | 25.00% | 0.00% | 0.00% | 2.57× | 0.10× | 0.11× |
| mul_chain | 13.259 | 0.483 | 0.599 | 2.508 | 6 | 8 | 8 | 8 | 25.00% | 0.00% | 0.00% | 5.29× | 0.19× | 0.24× |
| grad_add | 26.579 | 0.692 | 0.672 | 3.756 | 7 | 5 | 5 | 5 | -40.00% | 0.00% | 0.00% | 7.08× | 0.18× | 0.18× |
| grad_mul | 41.751 | 0.764 | 0.720 | 4.114 | 14 | 6 | 6 | 6 | -133.33% | 0.00% | 0.00% | 10.15× | 0.19× | 0.18× |
| nested | 47.762 | 1.027 | 1.022 | 7.796 | 30 | 9 | 9 | 9 | -233.33% | 0.00% | 0.00% | 6.13× | 0.13× | 0.13× |

## Core (small expressions) — Emoji View

| Expr | 🕒 Speed Winner | 📦 Compression Winner | Notes |
|------|----------------|------------------------|-------|
| add_chain | 🏆 Basic 🟢 | Photon 📉 | Basic faster |
| mul_chain | 🏆 Basic 🟢 | Photon 📉 | Basic faster |
| grad_add | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |
| grad_mul | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |
| nested | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |

## Stress (large chains) — Raw Numbers

| Expr | Photon ms | PhotonC Basic ms | PhotonC Adv ms | SymPy ms | Photon size | Basic size | Adv size | SymPy size | CompRaw | CompBasic | CompAdv | SpeedRaw | SpeedBasic | SpeedAdv |
|------|-----------|------------------|----------------|----------|-------------|------------|----------|------------|---------|-----------|---------|----------|-----------|----------|
| add_chain_10 | 14.910 | 0.793 | 0.802 | 8.703 | 11 | 11 | 11 | 11 | 0.00% | 0.00% | 0.00% | 1.71× | 0.09× | 0.09× |
| add_chain_50 | 25.660 | 2.667 | 2.529 | 37.511 | 51 | 51 | 51 | 51 | 0.00% | 0.00% | 0.00% | 0.68× | 0.07× | 0.07× |
| add_chain_100 | 41.118 | 5.510 | 5.277 | 75.591 | 101 | 101 | 101 | 101 | 0.00% | 0.00% | 0.00% | 0.54× | 0.07× | 0.07× |
| mul_chain_10 | 13.635 | 0.600 | 0.592 | 2.570 | 11 | 11 | 11 | 11 | 0.00% | 0.00% | 0.00% | 5.31× | 0.23× | 0.23× |
| mul_chain_50 | 16.816 | 1.477 | 1.415 | 8.713 | 51 | 51 | 51 | 51 | 0.00% | 0.00% | 0.00% | 1.93× | 0.17× | 0.16× |
| grad_add_10 | 29.156 | 1.133 | 1.112 | 8.876 | 21 | 12 | 12 | 12 | -75.00% | 0.00% | 0.00% | 3.28× | 0.13× | 0.13× |
| grad_add_50 | 51.608 | 4.291 | 4.097 | 38.748 | 101 | 52 | 52 | 52 | -94.23% | 0.00% | 0.00% | 1.33× | 0.11× | 0.11× |

## Stress (large chains) — Emoji View

| Expr | 🕒 Speed Winner | 📦 Compression Winner | Notes |
|------|----------------|------------------------|-------|
| add_chain_10 | 🏆 Basic 🟢 | Photon 📉 | Basic faster |
| add_chain_50 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| add_chain_100 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| mul_chain_10 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| mul_chain_50 | 🏆 Adv 🟢 | Photon 📉 | Basic faster, Adv faster |
| grad_add_10 | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |
| grad_add_50 | 🏆 Adv 🟢 | Basic 📉 | Basic compressed better, Basic faster, Adv faster |