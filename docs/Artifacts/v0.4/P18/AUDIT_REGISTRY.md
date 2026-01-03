# P18 Audit Registry (Evaluator stub)

Status: ROADMAP / UNLOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson

## What this module is
P18 defines a contract-only evaluator stub that links:
- P17 recommender outputs
- P16 calibration metrics contract

It performs schema/linkage checks only and emits a report stub.
No datasets are downloaded and no biological or edit-success claim is asserted.

## Promotion rule (must satisfy before LOCK)
- Frozen datasets + pipeline (P16 LOCK conditions met)
- Real evaluator implementation with deterministic execution + versioned hash
- Pre-registered null models + uncertainty policy + multiple-hypothesis policy
- Locked evaluation reports with staged evidence + checksums
- P1820260103T003605Z_P18_EVAL_PILOT_V01 — pilot v0.1 evaluator staged (real metric + CI + null)
- P1820260103T010353Z_P18_EVAL_PILOT_V02_PREPROCESSPIN — P18 v0.2 evaluator snapshot + report staged
