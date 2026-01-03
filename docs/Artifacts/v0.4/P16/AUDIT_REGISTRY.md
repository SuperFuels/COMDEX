# P16 Audit Registry (Calibration on ground-truth datasets)

Status: ROADMAP / UNLOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson

## What this module is
P16 defines the calibration contract: which datasets, which metrics, and what PASS/FAIL means.
In v0.4.5 it contains contracts only (no downloads, no external results).

## Promotion rule (must satisfy before LOCK)
- Frozen dataset list (DOI/accessions) + file hashes
- Deterministic preprocessing pipeline (pinned code + seed + stable serialization)
- Null models + uncertainty bounds + multiple-hypothesis policy
- Locked calibration report(s) with staged evidence + checksums
- P1620260103T003536Z_P16_CALIBRATION_PILOT_FREEZE1 — pilot freeze snapshots staged
- P1620260103T005650Z_P16_CALIBRATION_PILOT_FREEZE2_PREPROCESS — pilot preprocess output pinned (sha256) + snapshots staged
