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

## Nonlinear trajectory and route-aware gates (2026-09-10)

Four further independent first-token families and two eight-token KV-linked
trajectories were captured as training-only data; calibration and both holdout
families stayed frozen. Both long trajectories repeated routes, hidden states
and logits bitwise. The explicit frozen manifest contains 288 verified rows,
including 21 training observations per captured layer. Canonical SHA-256:
`a2dfe446585f12466dba6decd210e195974759872410516e48f2240c960d5f3a`;
file SHA-256: `03b9384eafebd632bb7bb784454db2444918af8d28e1864d97b4736923e1a1e8`.

A nonlinear residual-kernel model reduced worst holdout p95 from 21.41 to 0.918
but accepted no layer. An impossible oracle projection then showed that a
training-residual dictionary is insufficient overall (holdout p95 0.663 and
0.808), while exposing a narrow opportunity at layers 6 and 9, whose individual
oracle holdout errors were approximately 0.015--0.017. Decision:
`STOP_RESIDUAL_DICTIONARY_SUBSPACE` globally. Canonical SHA-256:
`f997d884eb821774e63004735b761734dd2a49df3f63cdd000f18507e7a53b28`.

Adding the unrestricted route IDs and gates as an AION route Glyph materially
improved layer 6. Its polynomial route-aware candidate reached 0.0192
calibration error and 0.0282/0.0312 on the two frozen holdouts, at 0.0850 ms p50
and 0.1070 ms p95. This stayed below the 0.05 hard ceiling but missed the 0.02
p95 gate. One of twelve layers would yield only 1.0909x projected traffic
reduction, also below the 1.10x experimental rung. Decision:
`STOP_KERNEL_BASELINE`; this is a near-signal, not a promoted win. Report
canonical SHA-256:
`9f1b12cf4ca4660d9031abd51b2f1124c2b362a16ac7cbc142f0293ac9d153fb`;
identical local/SD file SHA-256:
`ef31a56cfac110d2fefabbdf1a8fe7e137e47cff26b8fa0a123e3238b37dcfa8`.

The route audit explains the remaining generalization problem: the median
held-out route overlaps only two of four experts with its closest training
route; one row has zero overlap and only eight of 24 rows have all four experts
represented anywhere in training. The next collection must therefore target
route coverage, not merely add random examples.

## GHX route-crystal falsification and retained selector (2026-09-10)

The earlier holdouts were explicitly reclassified as development-only after
they suggested a simple GHX route-crystal hypothesis. The configuration was
then frozen before two new synthetic-token families (85001 and 95001) were
captured. Both unrestricted 120B passes repeated routes, final hidden state and
logits bitwise. The layer-6 candidate combined the normalized router state with
the four gated expert identities and calculated in 0.0190 ms p50.

It did not generalize. Fresh relative L2 was 0.0560 and 0.0736, exceeding both
the 0.02 p95 target and the 0.05 maximum. One substituted layer would also
project only 1.0909x traffic reduction. Decision:
`STOP_GHX_ROUTE_CRYSTAL`. Report canonical SHA-256:
`562ed9cad0fb2c9a3f6fd6bbc0a7531c6a4a4d9e01efca532dc19c8a8ac43b87`;
file SHA-256: `207cdb9f1059ed517798a2fc4f0245ba2bdb2411f0d952dc24e2d07df303ea0b`.
The SD evidence inventory has SHA-256
`f6c3ad2c2e83f195a27b78a0d7a1007f0cff5050c1c81012cff1ca509b31062c`.

The failed numerical output is never eligible for injection. Its fast matching
primitive is retained separately as a hash-verified, non-authorizing selector:
it ranks route prototypes, reports expert coverage and a score margin, but can
only choose a future independently verified calculator or exact fallback. A
1,000-query check measured 0.0239 ms p50 and 0.0289 ms p95. The next strategy
remains route-coverage collection followed by a structured per-expert low-rank
surrogate for layers 6 and 9.

## Structured per-expert low-rank result (2026-09-10)

A dual-kernel implementation assigned a separate gated affine feature block to
each of 128 experts and compressed the combined residual into a learned low-rank
basis. Hyperparameters were selected using training-family leave-one-out only;
the calibration and holdout families did not participate in selection. The
calculator remained cheap at 0.0305 ms p50 and 0.0343 ms p95, but both target
layers failed calibration: layer 6 relative L2 was 0.1922 and layer 9 was
0.3463. No layer was accepted and projected traffic reduction was 1.0x.
Decision: `STOP_PER_EXPERT_LOW_RANK`. Report canonical/file SHA-256:
`4c61233adde48fd804371073e798c818f40f46805200aa0e7a8c05088445a262` /
`246c18e1e558b70d9f5c4f8d725fb72d3428a8b5abb01650b527d0e521a4a2e6`.
The SD inventory SHA-256 is
`99acf071b3df6ea44977622b0b0f6e062f352a04feb7ab6ca18f93c0052aee68`.
Do not scale this form. The next exact opportunity is multi-token block
verification, which may amortize one expert load across several drafted token
positions without altering 120B mathematics.

## Exact multi-token block breakthrough (2026-09-10)

Two bitwise-repeatable eight-token 120B traces first established an analytical
layer-major load bound of 1.8611x and 1.9136x across all 36 layers. A real
SD-backed layer-12 gate then fetched each unique expert once and reused it for
all applicable positions. The two cases reduced 32 sequential expert faults to
13 and 16; compressed traffic fell from approximately 406.7 MB to 165.2 MB and
203.3 MB. Traffic reductions were 2.4616x and 2.0001x. Wall speedups were
2.4784x and 2.2137x, or 2.3461x median. All 16 candidate outputs matched their
captured exact outputs bitwise. Peak live expert bytes were 212,060,160, below
the 512 MiB gate. Decision: `ADVANCE_EXACT_BLOCK_RUNTIME`.

The runtime report canonical/file SHA-256 values are
`e22f692a633aa269a4d0280e4db004d95f6466fbc4fb2c26c8f7351558e963f1` /
`af978a55c128973beb5253f507fa2a7f1b615b37aaafb62389515ad891cb2f3e`.
The analytical report canonical/file SHA-256 values are
`6b9a801146fbb15feaa8b41ba9e465d8923c56723f79fb1305bb05ae25481c45` /
`e198aa323cb1fcca0fdbfb0afe2af0e902d5157bd8d4df3122c3dff1d42df420`.
The SD inventory SHA-256 is
`a3182fe9c40c19e3594c13ff12b546b7986e2890dcb98508498e7161aaa92b2a`.
This is an exact layer microgate, not a generated-token result. It excludes
draft cost, rejection, batched causal attention and the remaining 35 layers.
The next implementation must process a complete token block layer-major and
retain exact teacher logits for speculative acceptance.

## Full-block and adaptive-expert closure (2026-09-10)

The exact block mechanism was subsequently executed through all 36 layers and
the full output head at two, four and eight positions. Bitwise hidden/logit
equivalence passed throughout, but maximum whole-model wall improvement was
only 1.0383x despite 1.8617x logical traffic reduction. Exact block scheduling
is therefore stopped as the primary speed strategy; operating-system page-cache
reuse had already captured most repeated physical reads.

Changed-model continuation experiments must record active-expert count and
whether dropped gate mass is preserved. Fixed two-expert and fixed three-expert
policies failed the frozen arithmetic completion/coherence boundary. The 0.75
preserved-mass adaptive policy passed narrow correctness and repeatability but
did not beat the four-expert 8 GiB control median. It may advance only to the
already-frozen broader semantic families, never as an unrestricted-exact claim.

The first broader extraction family failed: `A-104` survived but `EUR 287.50`
did not. The 0.75 preserved-mass policy is therefore stopped for extraction.
Confidence-gated exact escape is not promoted from this trace because most
routes have substantial missing unrestricted gate mass and would reinstate most
SD faults. Future adaptive policies require a disjoint broader training family
and unchanged frozen extraction validation.
