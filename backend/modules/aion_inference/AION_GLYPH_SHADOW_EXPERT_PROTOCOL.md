# AION Glyph Shadow Expert Protocol

Status: design and evaluation protocol only. No derived neural weights have
been trained or injected.

## Purpose

The exact GPT-OSS 120B SD path moves about 1.4--1.5 GB of missing expert data
per generated token. Exact storage, cache, layout, decode, Metal, omission and
sparsity experiments have not produced the required 10x--300x traffic
reduction. The Shadow Expert is a separately labelled changed-arithmetic track
that attempts to predict the combined four-expert residual from information
already resident on the Mac.

## AION execution contract

For every transformer layer AION already has the current 2,880-value router
activation, the unrestricted top-four expert identities, and their normalized
gates. The proposed cartridge receives:

- a model/version Glyph;
- a layer Glyph;
- the current router activation;
- the four original expert IDs and gates; and
- a compact request-family Glyph that may select, but never modify, a signed
  cartridge.

It predicts one 2,880-value combined expert contribution and a calibrated
confidence/error bound. The decision is:

```text
router activation + layer + route + gates
                    |
                    v
          signed Shadow Expert
                    |
          candidate + confidence
             /             \
       accepted          rejected
          |                 |
   changed-arithmetic   fetch all four original
   quality track        experts from SD exactly
```

The original router remains unrestricted. A rejection executes the existing
verified warehouse path. A cartridge may never change the exact fallback,
expert identities, source model, or evidence history.

## Why this differs from failed omission

The stopped top-k gate discarded expert contributions and produced large
errors. The Shadow Expert must learn the *combined residual* of all four routed
experts. It is not allowed to claim that an omitted expert was unnecessary.
The intended speedup comes from representing the local input/output function
compactly, not from relabelling a smaller expert count as the full model.

## Required data boundary

Only model-generated numerical activations from synthetic or explicitly
approved prompts may be used. No personal, customer, email, document, Pilot or
Boardroom data may enter training. Prompt text must not be persisted in the
cartridge dataset. Each row binds:

- source-model and warehouse hashes;
- prompt-family identifier;
- layer and token position;
- input activation hash;
- unrestricted route and gates;
- exact four-expert residual target hash; and
- collection implementation/precision identifiers.

Training, calibration and evaluation prompt families must be disjoint.
Duplicate activation hashes must remain in one split only.

## Predeclared mechanism gates

A candidate may advance from a layer microgate only if all are true:

1. Cartridge storage is at least 10x smaller than the expert traffic it aims
   to replace.
2. Candidate calculation is below 1 ms p50 and 2 ms p95 per layer on the
   existing M3 Pro.
3. Held-out combined-residual relative L2 is at most 0.02 p95 and 0.05 maximum.
4. The confidence gate captures at least 99.9% of violations above the error
   limit; undetected high-error predictions fail the candidate.
5. The projected accepted fraction is high enough to reduce physical expert
   bytes per token by at least 10x. A fast but frequently rejected candidate
   does not advance.

## Full-model gates

Mechanism success does not authorize runtime promotion. The complete
36-layer candidate must then pass:

- a frozen arithmetic, extraction, reasoning and business-task suite;
- unchanged safety/policy results;
- separately reported exact-token agreement and semantic-quality scores;
- cold/warm TTFT and generated-token p50/p95;
- physical SD bytes, fallback frequency and confidence calibration;
- peak memory within the declared ceiling;
- repeatability across at least two balanced runs; and
- an immutable SD evidence receipt and append-only technical record.

The mode must always be named `AION_SHADOW_120B_QUALITY_TRACK`. It must never be
described as bit-exact unrestricted GPT-OSS 120B. The exact warehouse runtime
remains available as the authority and fallback.

## Authorization boundary

This protocol does not authorize training or injection. Training a first
cartridge requires explicit user approval for local model-derived training,
the declared dataset boundary above, and the frozen gates. Until then, work is
limited to data-schema, capture, split, evaluator and fallback implementation.

## Initial readiness state (2026-09-10)

The hash-bound split builder has been implemented and run on the existing
capture corpus. It verified 16 numerical activation records, no prompt text and
no personal/customer data. The corpus contains only one BOS/two-token family,
so it is correctly marked `INSUFFICIENT_FAMILY_COVERAGE`. At least four
independent synthetic prompt families are required for train, calibration,
numerical holdout and semantic holdout. No existing record is silently reused
as held-out evidence.

Dataset-manifest canonical SHA-256:
`d9896a4188b9a8d4ca1ff1af84cbd7904a5775acb562f26fdc5520d35f2768a8`.
