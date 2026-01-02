# Artifacts Index — v0.4/P12_1

## Scope
Stage C (P12) — SIM verification lock for:
- A2 Resonant Addressing (SIM)
- A4 k_link vs distance (SIM)
- A3.1 Chiral Handshake (SIM)
- B0 Lexicon Contract (Stage B)
- B1 Ablation Matrix (Stage B)

## Reproduction
```bash
pnpm exec vitest run Glyph_Net_Browser/src/sim/tests
```

## Contents
### docs/
- LOCK_NOTE.md — human-readable lock summary
- METRICS_DEFS.md — canonical metric definitions used by tests (as implemented)

### tests/
- Snapshot list of test files (optional copy) or references

### runs/
- run_command.txt
- env.txt

### logs/
- vitest_stdout.txt
- vitest_version.txt

### checksums/
- SHA256SUMS.txt — sha256 of all tracked artifacts in this bundle
- ARTIFACTS_INDEX.sha256 — sha256 of ARTIFACTS_INDEX.md

Lock ID: P12-SIM-2026-01-02-A2A4A31
Status: LOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson.
