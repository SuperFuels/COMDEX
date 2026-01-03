# P15 Audit Registry (Portability Bridge)

Status: ROADMAP / UNLOCKED
Maintainer: Tessaris AI
Author: Kevin Robinson

## What this module is
P15 defines a portability mapping from model-scoped objects to measurable bio-facing proxies.

## What is now concretely staged (still ROADMAP)
- A stable spec contract in code (P15Spec + P15Prediction), with at least one shaped prediction record.
- Placeholder dataset + preprocessing + PASS/FAIL schema, explicitly marked TBD.

## Promotion rule (must satisfy before LOCK)
- Named public dataset(s) with frozen version identifiers + checksum/DOI/accession list
- Deterministic preprocessing pipeline with pinned code + seed control + stable serialization
- Explicit metrics + null models + multiple-hypothesis handling (if applicable)
- Negative controls + ablations with pre-registered PASS/FAIL rules
- Artifact-staged runs with checksums under docs/Artifacts/v0.4/P15/runs/<RUN_ID>/
