# P17 Audit Registry (Compiler v1 → design recommender)

Status: ROADMAP / UNLOCKED  
Maintainer: Tessaris AI  
Author: Kevin Robinson

## What this module is
P17 defines a contract-only "design recommender" that emits candidate motif/schedule/topology designs and predicted metrics.
It does not execute edits and makes no wetlab success claims.

## What is concretely staged (still ROADMAP)
- Recommender spec contract (P17_RECOMMENDER_SPEC_V0)
- Output contract stub (P17_OUTPUT_CONTRACT_V0)
- Evaluator wiring contract stub (P17_EVAL_WIRING_V0) referencing P16 calibration registries
- Smoke tests for spec/output/wiring + P16 crosslink parsing

## Promotion rule (must satisfy before LOCK)
- P16 calibration must be promoted beyond contract-only (frozen datasets + metrics + audited evidence)
- Evaluator implementation must be pinned and audited (deterministic, versioned, checksummed)
- Output contract fields must be backed by an audited evaluation run (with uncertainty reporting)
- P1720260103T003555Z_P17_RECOMMENDER_ROADMAP_SNAPSHOT2_P16PILOT — snapshot refresh (P16 pilot metricId)
