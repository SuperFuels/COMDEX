# AION SD Model Path and Optimisation Surface

Status: engineering map, 2026-09-07. This document separates measured facts,
exact-output opportunities, and deliberately non-exact research tracks.

## The model actually under test

The SD-backed reasoning model is Granite 3.1 3B A800M, a sparse mixture-of-
experts causal language model. It has 32 transformer layers, 40 experts in each
layer, and selects eight experts per generated token. Each serialized expert is
approximately 4.7 MB. The complete expert library is approximately 6.04 GB in
its source execution representation. The host is an 18 GB M3 Pro MacBook Pro.
The model and immutable evidence live on the built-in SDXC reader's removable
Class 10 card.

The selected experts change by layer and token. Therefore SD execution is not a
single sequential model read. It is a repeated working-set problem: determine
which experts are required, find the resident ones, fetch the misses, decode and
materialize them for Metal, perform the expert matrix calculations, then decide
which weights stay resident for later tokens.

## End-to-end request path

1. The Semantic Gateway canonicalizes the request, preserves constraints, and
   assigns a Glyph family.
2. Replay, an AtomSheet, or a verified workflow may answer without an LLM.
3. If language inference is required, model routing selects an installed model.
4. The tokenizer creates the prompt token sequence.
5. Granite's resident attention and router weights calculate eight required
   experts at each of its 32 layers.
6. AION checks the bounded per-layer Metal cache.
7. Missing expert frames are read from the SD pack in physical route-aware
   order. Adjacent frames are coalesced into a small number of physical reads.
8. Independent frames are decoded concurrently. A reversible two-byte shuffle
   is undone to recover the original BF16 bytes exactly.
9. The exact bytes are exposed as CPU tensors and materialized as Metal tensors.
10. Metal performs the selected expert calculations and combines their output.
11. AION retains or evicts experts under the declared memory ceiling.
12. The process repeats for every layer and generated token.

## What has been changed successfully

- Physical route-aware packs replaced thousands of tiny file opens.
- Lossless Zstandard compression reduced the 6,039,797,760-byte expert library
  to 4,708,753,870 bytes without changing a weight.
- Reversible BF16 byte shuffling plus Zstandard level 1 reduced it further to
  4,134,132,737 bytes, a 31.55% reduction from source.
- Coalesced reads plus bounded parallel frame decoding reduced the mechanism's
  median read/decode time by 60.37% on the original compressed representation.
- In a stage-instrumented exact ABBA generation test, the compressed parallel
  pipeline reduced median generation time by 28.83%. Every generated token and
  every generation-step logit matched the control exactly.

These results establish a working exact SD execution format. They do not imply
that SD bandwidth equals unified memory or HBM, and they do not yet establish a
universally reproducible production throughput figure.

## Exact-output optimisation order

The following changes preserve the model's weights and retain full-model demand
fallback, so they can be promoted only after exact token and step-logit tests.

1. **Tune decode concurrency.** Four workers appear sufficient in the mechanism
   probe; an SD-bound live ABBA run must decide whether four beats eight.
2. **Reduce repeat faults safely.** Learn future reuse to protect resident
   experts, never to trigger speculative reads. The first dictionary failed its
   live gate despite strong offline replay, so a replacement needs longer route
   observations, family-disjoint validation, and a live win before promotion.
3. **Two-tier working set.** Evaluate a bounded cache of compressed host frames
   behind the Metal tensor cache. It may avoid SD reads after Metal eviction,
   but must beat the operating system's warm file cache under the same total
   memory ceiling.
4. **Request batching by Glyph family.** At modest queue depth, calculate the
   same resident expert for several requests before eviction. This can increase
   completed tasks per hour even when single-request token latency is unchanged.
5. **Verified draft execution.** Use replay, AtomSheets, or a compatible small
   draft model to propose multiple tokens, then accept only tokens verified by
   Granite. This targets fewer serial Granite steps; cross-tokenizer drafting is
   not assumed safe.
6. **Storage-first startup receipts.** Replace repeated full-pack hashing with a
   signed installation receipt plus bounded challenge verification, while still
   failing closed on substitution or corruption. This improves startup, not
   steady-state tokens per second.
7. **Direct shared-buffer materialization.** A native Metal path could decode
   into reusable shared buffers and avoid repeated tensor construction. PyTorch
   MPS does not currently expose the required stable buffer contract here, so
   this requires a separately tested native execution path.

## Quality-gated, non-exact research track

The largest possible speedups require changing representation or work, so they
must never be described as exact-output improvements:

- four- or eight-bit expert quantization to cut storage traffic and resident
  memory by multiples;
- reducing routed experts per token, expert pruning, merging, or distillation;
- an MLX/native Metal Granite MoE implementation designed around unified memory;
- a smaller specialist model or adapter for a bounded Glyph family; and
- task-level LLM avoidance using signed AtomSheets and Business/Personal Maps.

These candidates need semantic quality suites, calibration, safety checks, and
explicit comparison with the unchanged model. Token equality is not expected.

## Stop rules

- Never promote an offline cache prediction that loses live timing.
- Never prefetch from SD unless useful-read benefit exceeds contention and waste.
- Never trade exactness for speed inside the exact track.
- Never count a disk counter unless it is bound to the mounted evidence volume.
- Stop micro-optimising expert arithmetic while storage, decode, or
  materialization remains the dominant measured cost.
- Report cold, warm, p50, p95, memory, faults, bytes, and all regressions.

## Path to an exceptional system

The intended advantage is not to make a cheap SD card physically equal to HBM.
It is to make the fast machine request far fewer warehouse deliveries, pack each
delivery efficiently, reuse it intelligently, and avoid the large model entirely
when verified AION intelligence can complete the task. Single-request tokens per
second, multi-request tokens per second, and successful business tasks per hour
must remain separate metrics.
