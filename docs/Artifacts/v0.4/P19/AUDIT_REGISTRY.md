# P19 Audit Registry (Runner / Orchestrator)

Status: ROADMAP / UNLOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson

## What this module is
P19 is a contract-only orchestrator that runs the evaluation wiring from P17 outputs through the P18 evaluator stub.
In v0.4.5 it performs no dataset downloads, no preprocessing, and makes no wetlab or edit-success claims.

## Promotion rule (must satisfy before LOCK)
- P16 calibration locked on frozen datasets + metrics
- P18 evaluator upgraded beyond stub and locked
- Deterministic run/report policy (inputs pinned, reproducible run IDs, stable serialization)
- Audit-grade run bundles with checksums and evidence blocks
- P1920260103T003617Z_P19_RUNNER_PILOT_REFRESH1 — pilot refresh staged (delegates to P18 v0.1)
- P1920260103T010506Z_P19_RUNNER_PILOT_REFRESH2_V02 — P19 runner contract snapshot staged
