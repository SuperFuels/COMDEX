# P15 — Portability Spec (Bridge) (ROADMAP / UNLOCKED)

## Scope (model-only)
This document defines a translation from internal (model-scoped) protocol objects to measurable proxies.
It is a specification and planning artifact only. It makes no biology/physics claims.

## Mapping (definitions)
- message ↔ measurable assay signal (TBD: assay class, units, acquisition, preprocessing)
- key ↔ motif / binding family / targeting rule (TBD: motif DB + matching rule)
- topology ↔ contact/3D adjacency / co-factor interaction graph proxy (TBD: assay + resolution)
- separation ↔ orthogonality in binding/contact space (TBD: metric + null model)

## Requirements (before any “RECORDED/LOCKED”)
1) Select target assay types and measurable outputs (units + acquisition + preprocessing).
2) Choose dataset(s) and version them (DOI / accession / checksum).
3) Define metrics and null models.
4) Define falsifiable predictions with negative controls and ablations.
5) Stage artifacts under docs/Artifacts/v0.4/P15 with reproducible runs + checksums.

## Contract note
The repo includes a P15Spec + P15Prediction schema and a smoke test asserting at least one prediction record exists,
to keep the portability spec “non-empty” and auditable even while TBD.
