# Phase 45 — Multimodal World Grounding with GlyphChain Proofs

**Date:** 30 July 2026

**Status:** Bounded V1 passed and promoted.

## Why GlyphChain is used

The GlyphChain architecture is directly useful to AION as a proof rail rather than a payment rail. The existing repository already contains:

- canonical proof-envelope hashing;
- AION job, evidence and settlement-readiness proof types;
- proof commitment verification;
- tamper detection;
- internal proof records and receipt contracts;
- deterministic ChainSim roots and inclusion proofs;
- wallet-signature, replay, restart and consensus regression tests.

Phase 45 uses the guarded evidence-proof adapter. It does not submit a live chain transaction and does not require PHO, a wallet, payment or escrow.

## Research question

Can AION ground one decision in several distinct evidence modalities, preserve exact provenance, identify contradictions and bind the resulting evidence set into a tamper-detecting proof?

## Evidence modalities

Every world contains four real artifacts:

1. A text policy document containing a limit, revision and reported observation.
2. A CSV table containing the primary measured value.
3. A PGM pixel image containing a visually encoded gauge reading.
4. A JSON software-state record containing the active state and current policy revision.

Each parser produces an `aion.multimodal.evidence_capsule.v1` capsule with:

- evidence identifier;
- modality;
- source URI;
- exact evidence location;
- content hash;
- observation time;
- extracted value;
- confidence;
- reported-versus-parsed status.

## Decision policy

AION accepts only when:

- image and table readings agree;
- the operator-reported value agrees with the table;
- the document revision matches the live software revision;
- the software control state is active;
- the verified reading does not exceed the policy limit.

An aligned value above the limit is a verified rejection. Any unresolved cross-modal conflict causes abstention rather than forced acceptance.

## GlyphChain binding

The final decision, contradiction list and canonical capsule hashes are inserted into an `AION_EVIDENCE_PROOF_V1` envelope. The existing GlyphChain canonical codec produces the commitment hash. Verification recomputes both payload and commitment hashes.

Every evaluation also changes the committed decision after hashing. All such tampered envelopes must fail verification.

## Official sealed results

The official evaluation contained 140 worlds: 100 sealed worlds and 40 external-namespace worlds across five contradiction families.

| Measure | Result |
|---|---:|
| Multimodal decision accuracy | 100% |
| Weakest-family accuracy | 100% |
| External accuracy | 100% |
| Text-only control accuracy | 40% |
| Accuracy gain | +60 points |
| Provenance-complete evidence sets | 100% |
| Verified GlyphChain commitments | 100% |
| Tampered commitments accepted | 0 |
| Unsafe false acceptances | 0 |
| Restart retention | 100% |
| Live chain transactions | 0 |
| Payment side effects | 0 |

Promoted procedure:

`procedure_multimodal_grounding_9bc5141c1e09`

## Interpretation

The result shows that AION can require evidence from more than language, preserve modality-specific provenance, detect contradictions that a text-only path misses and make the evidence set tamper-evident through GlyphChain.

The +60-point result is against the deliberately limited text-only control, not against a frontier multimodal model.

## Boundary

The image is a controlled scalar gauge and each parser is engineered. The result does not establish general computer vision, arbitrary diagram understanding, audio/video cognition, live sensor deployment or AGI.

Phase 45 V2 should add natural images, diagrams, audio and live application state. The next numbered programme phase is Phase 46: the large continual-learning arena.
