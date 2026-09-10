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

A candidate may advance from a layer microgate only if the accuracy and
confidence conditions below are met. Traffic progress is now recorded in
three honest rungs so a real smaller win is not discarded:

- experimental rung: greater than 1.10x measured traffic reduction;
- useful rung: at least 2x measured traffic reduction; and
- breakthrough rung: at least 10x measured traffic reduction.

Only the breakthrough rung satisfies the original programme target. Lower
rungs remain explicitly experimental and must demonstrate repeatable net
token-speed improvement before runtime use. For every rung all are true:

1. Cartridge storage is at least 10x smaller than the expert traffic it aims
   to replace.
2. Candidate calculation is below 1 ms p50 and 2 ms p95 per layer on the
   existing M3 Pro.
3. Held-out combined-residual relative L2 is at most 0.02 p95 and 0.05 maximum.
4. The confidence gate captures at least 99.9% of violations above the error
   limit; undetected high-error predictions fail the candidate.
5. The projected accepted fraction is reported as measured physical expert
   bytes per token and assigned to the appropriate rung. A fast but frequently
   rejected candidate with no net win does not advance.

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

## Target capture and fallback evaluator readiness (2026-09-10)

The exact 120B runner now has a v2 capture path that records the post-attention
FFN input, router input, complete layer output and the observable combined
four-expert residual. Every numerical blob is SHA-256 bound to its metadata,
warehouse manifest and verified source-model shard hashes. The record explicitly
excludes prompt text and personal/customer data. Existing v1 captures remain
valid historical evidence but cannot be mistaken for training-ready rows because
they contain no residual targets.

A separate frozen evaluator now verifies the dataset manifest, target and
candidate hashes, calculates held-out residual error, applies a declared
confidence threshold, and simulates rejection to the unchanged exact SD path.
It refuses tiny-corpus promotion: even perfect predictions on two holdout rows
can demonstrate at most a conservative 2x traffic bound, not the required 10x.
This completes capture/evaluator plumbing only. No derived weights were trained,
loaded or injected.

The v2 path was then exercised through all 36 genuine GPT-OSS 120B layers and
two repeat passes. Routes, final hidden state and logits remained bitwise
repeatable, and four selected layers produced 4/4 fully verified residual-target
rows. The capture run canonical SHA-256 is
`cf3aebf7fc00f6cd3e6b6e724923802e676f8ea04191c0390db00f17eeb1205a`;
its identical local/SD file SHA-256 is
`5f1f8e097d522c04cf77b6f8e71286e3a606a450a8e29ee559f1caadd9282789`.
The resulting target-manifest canonical SHA-256 is
`da0cfd31c517b1269f5f15487c6cfa0f7e01fadd6ca69052bc3522bd76285a54`;
its identical local/SD file SHA-256 is
`bc7ccb7700370cbcf6babcabc3aea0582d5eec139ce778271938f9b1458fccfe`.
It remains `INSUFFICIENT_FAMILY_COVERAGE`, as designed: a successful single
family validates collection, not generalization or authorization.

## Four-family frozen split readiness (2026-09-10)

Three additional independent synthetic token families were captured through
the same real 36-layer path. Every run repeated routes, final hidden state and
logits bitwise. Together with the BOS family, the frozen manifest now contains
four family-disjoint groups and 16/16 verified residual targets, with no
cross-family activation-hash collision. It is marked
`READY_FOR_AUTHORIZED_TRAINING` while retaining `training_authorized: false`.
The manifest canonical SHA-256 is
`6564bc3fef79e40528046a7c05af104791eb24a0663b14e0349d9785d49b9b27`;
its identical local/SD file SHA-256 is
`fd0279e8f3eb9887470205e266183a8531bd116f1c89f2a5f21054606010394b`.

Non-trained oracle and zero controls exercised the evaluator. The oracle had
zero residual error, but correctly failed promotion because eight holdout rows
can demonstrate only an 8x conservative traffic bound, below 10x. The zero
control produced relative L2 error 1.0 and detected no violations at its false
high confidence, so also failed. This proves the evaluator distinguishes
perfect arithmetic, inadequate evidence volume and unsafe confidence. It does
not show that a compact predictor exists.

## Evidence-volume gate closure (2026-09-10)

Each of the four frozen families was recaptured at 12 distributed layers,
yielding 48/48 verified targets and 24 holdout observations. All eight complete
120B passes (two per family) remained route-, hidden-state- and logit-bitwise
repeatable. The expanded manifest has no activation-hash leakage and canonical
SHA-256
`f91d9c8c1e9f4db2ffae76e2dcecf2b2500e6668ec8ecd38d79f75d0d35b37e3`;
its identical local/SD file SHA-256 is
`688192f92c0c18d9a19070d38976c48e3f58b6c31364cd11cb74d2173fabc07f`.

The evaluator now reports explicit failure reasons, requires at least ten
holdout observations, and labels deterministic controls separately from real
candidates. On 24 holdout rows, the oracle control passed its control gate with
zero error and a conservative 24x traffic bound. The false-high-confidence zero
control failed with p50/p95/max relative L2 all 1.0, 24 violations and zero
violation capture. This establishes that the collection and refusal machinery
can reach both expected outcomes. It is not evidence for a learned predictor;
training remains unauthorized.

## First authorized trained baseline (2026-09-10)

The user explicitly authorized local training from this frozen numerical
dataset, while retaining the data and claim boundaries above. A 2,860-byte
per-layer affine cartridge was trained as the cheapest falsification test. It
was extremely fast (0.0182 ms p50, 0.0186 ms p95) but numerically unusable:
calibration accepted no layer, holdout p95 relative L2 reached 21.41, and
projected traffic reduction remained 1.0x. Decision:
`STOP_AFFINE_BASELINE`. Exact fallback therefore handled every layer.

The report canonical SHA-256 is
`c7ff59cb0b96bdb3ae3eeea67d5536f5c08f251113a9c81b8dbf5aaee0c1ee32`;
its identical local/SD file SHA-256 is
`e443ba15b37dbfd273c0801ccb43b3314339de7e161dcf5f4659e51a6423aea5`.
This falsifies a simple elementwise polynomial mapping; it does not falsify a
nonlinear low-rank residual model trained on substantially more activation
trajectories.
