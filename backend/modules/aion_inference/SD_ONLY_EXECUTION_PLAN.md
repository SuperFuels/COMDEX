# AION SD-Only Execution Plan

Status: LOCKED for execution until faster storage or additional hardware is available.

Baseline date: 6 September 2026  
Baseline implementation: `0138c2bf`  
Evidence root: `/Volumes/Install macOS Sonoma/AION-Inference`

## Objective

Make the Glyph-Addressed Adaptive Inference Runtime as correct, responsive,
memory-efficient and useful as possible on the current Mac and SD card. The
programme must determine how far commodity removable storage can extend local
AI before any NVMe or other hardware is introduced.

The commercial optimization target is not raw accelerator throughput. It is:

> Lowest hardware cost per successfully completed private task.

## Locked baseline

- Model: IBM Granite 3.1 MoE 3B Instruct, FP16 Transformers control.
- Architecture: 32 MoE layers, 40 experts per layer, 8 selected per token.
- External expert library: 1,280 content-addressed SD-backed experts.
- Current cache reference: corpus-trained bounded-frequency controller.
- Current longer-generation median: 24 tokens in 123.689 seconds.
- Current throughput: approximately 0.194 tokens per second.
- Previous controller: approximately 0.179 tokens per second.
- Fully resident same-model control: approximately 9.3 tokens per second.
- Current exactness: every tested token ID and generation-step logit matches.
- Automatic planner: explicit 1, 2 and 3 GiB expert-cache ceilings.
- Current byte-ceiling replay result: 2.24--3.87% lower held-out logical demand
  than equal per-layer allocation, with nine of nine fold/budget wins.

The baseline artifacts and hashes must never be overwritten. Failed or
invalidated results remain preserved with explicit sidecars.

## Non-negotiable integrity gates

No optimization may be promoted unless all applicable gates pass:

1. Every generated token ID equals the unrestricted control.
2. Every generation-step logit tensor equals the unrestricted control exactly.
3. Model, shard, pack, cache-plan and evidence hashes verify.
4. The declared resident-memory ceiling is never exceeded by the controller.
5. Every requested condition and condition order completes.
6. Timings report prompt count, generated tokens, p50 and p95, not only a best run.
7. Cold and warm storage conditions are reported separately.
8. Aggregate improvements include per-prompt regressions and worst cases.
9. A failed gate invalidates promotion but does not delete the experiment.
10. No result from route replay is described as a live latency or memory result.

## Scope while hardware is unchanged

Permitted:

- Current Mac, current SD card and models already present on the evidence volume.
- Changes to the AION inference package, focused tests and SD-backed evidence.
- Qwen 3 1.7B and Granite 3.1 MoE 3B as the initial two-model library.
- Long-running experiments when bounded, recoverable and evidence-producing.

Deferred until new hardware:

- Purchasing or recommending a final production storage configuration.
- Downloading a larger checkpoint merely to claim a larger parameter count.
- SD-versus-NVMe performance conclusions.
- Claims of production concurrency, NVIDIA-equivalent throughput or datacenter
  replacement.

## Execution stages

### Stage 1 - Locate the real bottleneck

Instrument every expert activation and generation step to separate:

- storage wait time;
- bytes requested and bytes returned;
- operating-system cache effects;
- Safetensors/index decoding;
- host-to-Metal tensor transfer;
- synchronization time;
- expert compute time; and
- cache lookup, eviction and planner overhead.

Add bounded cold/warm modes and record enough information to reconcile totals.
The output is a content-addressed bottleneck report, not an inferred diagnosis.

Exit gate: at least 95% of measured wall time is assigned to named stages, or
the report explicitly records the unassigned remainder.

### Stage 2 - Remove avoidable SD work

Evaluate, one change at a time:

- persistent verified handles for per-layer packs;
- memory-mapped or ranged access where compatible with exact tensor loading;
- coalesced reads for experts selected together;
- batched Metal transfer;
- fewer synchronization boundaries;
- immediate eviction of demonstrably low-value experts; and
- byte-ceiling allocations at 1, 2 and 3 GiB.

Each optimization receives an ABBA comparison with identical prompts and an
exact miss path. File-open reductions alone are not treated as success because
that hypothesis has already been falsified as the dominant bottleneck.

Promotion gate: at least 10% median live-time improvement, lower or equal
logical demand, no material p95 regression, and complete exactness.

### Stage 3 - Predict narrowly and overlap safely

Build per-layer transition statistics from prompt-private routes. Predict the
next token's likely experts from recent routes and begin loading only when
confidence and unused memory headroom justify it.

The predictor must:

- operate separately for every layer;
- remain inside the selected byte ceiling;
- load at most one or two layers ahead;
- cancel or discard stale predictions;
- record useful and wasted prefetch bytes separately; and
- fall through to the exact demand loader on every miss.

Broad family-wide prefetch remains rejected.

Promotion gate: useful prefetch exceeds wasted prefetch, demand stalls fall,
median and p95 improve, and exact tokens/logits remain unchanged.

### Stage 4 - Storage-first boot

Replace the temporary full-checkpoint startup with a model construction path
that does not first place all experts in Metal memory. Load shared tensors and
router components normally, bind expert placeholders to verified SD pack
addresses, and materialize an expert only through the governed cache.

Exit gates:

- startup peak is materially below full-model residency;
- all 1,280 experts remain addressable;
- corrupt, absent or substituted expert objects fail closed;
- first inference and subsequent inference pass exactness; and
- interrupted startup leaves no promoted partial state.

### Stage 5 - Long and randomized validation

Use multiple prompt families and 64, 128 and 256 generated-token targets.
Randomize or balance ABBA/BAAB order across separate runs. Report:

- tokens per second and time to first token;
- p50 and p95 latency;
- expert faults, retained hits and useful prefetch;
- logical and observable physical reads;
- peak Metal and process memory;
- temperature or throttling indicators available without privileged tools;
- failures, retries and exactness; and
- sensitivity to 1, 2 and 3 GiB cache ceilings.

Milestones are deliberately staged:

- first useful target: at least 0.30 tokens per second;
- strong SD result: at least 0.50 tokens per second;
- stretch result: at least 1.00 token per second.

These are engineering targets, not claims. If the bottleneck evidence shows the
SD medium cannot reach them, the result is a valid hardware-bound falsification.

### Stage 6 - Existing two-model routing

Use the models already present. The Semantic Gateway selects in this order:

1. verified replay;
2. promoted AtomSheet or bounded workflow;
3. Qwen 3 1.7B for an eligible low-cost language task;
4. Granite MoE storage-backed reasoning when its capability is required; and
5. safe refusal or explicit unsupported result.

Record route choice, reason, estimated cost, actual latency, correctness and
fallbacks. The router must never select a smaller model solely to improve a
speed metric when its quality gate fails.

Exit gate: the two-model system improves completed-task latency or resource use
on a blinded task set without reducing the accepted-task success rate.

### Stage 7 - Small-business usefulness and economics

Build a representative private workload spanning calculations, quotations,
policy checks, document extraction, short drafting, planning and coding. Measure
the complete task, not merely model generation.

Report:

- successful tasks per hour;
- median and p95 user-perceived latency;
- percentage served by replay, AtomSheets, Qwen and Granite;
- model calls and model tokens avoided;
- peak memory and storage traffic;
- operator-review or approval requirements; and
- hardware cost per successful private task using the already-owned host as a
  separately declared assumption.

This is the primary commercial metric for the SD prototype.

### Stage 8 - Glyph-addressed Business Map cartridge

After Stages 5--7 pass, prototype the Boardroom Business Map as a signed,
tenant-bound expert cartridge rather than modifying the foundation model
directly. Its first version combines:

- provenance-bound retrieval over company documents;
- promoted AtomSheets for exact rules and calculations;
- governed workflows, permissions and human-approval boundaries;
- minimal selected context and reusable prefix artifacts;
- content-addressed evidence and revocation records; and
- an optional adapter interface that remains disabled until separately trained,
  evaluated and authorized.

The cartridge router must select the correct business identity and fail closed
on cross-tenant, stale, unsigned or ambiguous evidence. Mutable business facts
remain in retrieval or AtomSheets rather than being hidden in neural weights.
No generated or replacement MoE expert may be injected into Granite without a
new training protocol, router integration, capability evaluation and safety
gate.

Define a separate Personal Map schema for Pilot, but do not ingest personal
data or train personal weights during this stage. Business and personal maps
must have distinct keys, storage roots, permissions and deletion boundaries.

Exit gate: a blinded business-task set shows improved completed-task latency or
resource use without reduced accepted-task success, every answer carries
source/contract provenance, and cross-map isolation tests pass.

## Stop and pivot rules

Stop optimizing a strategy when any of the following is demonstrated twice in
controlled evidence:

- it changes a token or logit;
- it moves rather than removes I/O and provides no latency benefit;
- it improves the median but causes an unacceptable p95 or family regression;
- it depends primarily on uncontrolled filesystem warming;
- it crosses the declared memory ceiling;
- it adds more speculative prefetch bytes than useful bytes; or
- its complexity is disproportionate to the measured gain.

On a stop, preserve the result, document the falsified hypothesis and advance
to the next bounded strategy.

## Hardware handoff package

Before attaching NVMe, freeze:

- the best SD implementation commit;
- exact model and artifact hashes;
- the full SD cold/warm benchmark corpus;
- 1, 2 and 3 GiB cache plans;
- storage-first startup measurements;
- two-model routing results;
- the business-task economics report; and
- a single reproducible command for the storage-medium comparison.

The same package will then run unchanged against USB SSD, 10 Gbps USB NVMe,
USB4/Thunderbolt NVMe, internal PCIe NVMe where available, and full-memory
execution. This prevents later hardware improvements from being confused with
software or workload changes.

## Current next action

Implement Stage 1 timing and read-accounting instrumentation, run it against
the current 24-token corpus, and choose the next optimization solely from the
largest measured wall-time component.

## Progress checkpoint: signed Boardroom cartridge (2026-09-07)

The earlier current-next-action statement is retained as historical plan text;
Stages 1--5 and the replicated four-family 256-token exact milestone have since
completed. Stage 6 established exact natural-EOS Granite execution for two
business tasks but did not promote task quality. The governed router selected
the existing Qwen route, which measured approximately 76--78 warm generated
tokens/s in an exploratory probe, but free-form policy completeness still
failed. Speed without rubric compliance is not promoted.

Stage 8 has therefore begun with the bounded dependency required to finish
Stage 6 safely: a signed supplier-payment Business Map cartridge. The v1
prototype provides provenance-bound retrieval content, six immutable AtomSheet
controls, workflow and role gates, required human approval, deterministic proof
receipts, a disabled adapter, a separate Personal Map boundary, and an absolute
prohibition on payment execution. Ed25519 and semantic verification fail closed.
Fifty-seven focused tests passed. A 1,000-iteration synthetic contract benchmark
measured 0.301480 ms median and 0.348792 ms p95, but this is not a real supplier
verification and does not authenticate evidence content.

Current next action: install the unchanged signed cartridge bundle on the SD
evidence volume, implement labeled bounded extraction fixtures, and compare
three governed paths: zero-model AtomSheet execution, warm Qwen extraction into
the AtomSheet, and exact Granite fallback. Promote only completed correct tasks;
separate model-load time, warm execution, generated tokens, p50/p95, human-review
state, and fail-closed outcomes.

### Stage 6/8 hybrid promotion result

The signed cartridge bundle is now installed and independently reverified on
the SD evidence volume. The first eight-case Qwen extraction run failed exact
quality at 7/8 because one supplier name retained a leading role label. The run
was preserved. A bounded Semantic Transformer rule removed only leading
standalone `Vendor` or `Supplier` labels while retaining raw and canonical
values. The unchanged eight cases were then repeated twice each.

The v2 run passed all gates: 8/8 exact labeled extractions on both repetitions,
deterministic raw responses, valid cartridge signatures and proof receipts,
complete synthetic control contracts, and no payment authority. After an
explicit cold unload, the first call took 18.9786 s including 18.2724 s model
load. Fifteen warm calls measured 0.740786 s median and 0.817896 s p95 wall time,
with 75.527 median generated tokens/s. This promotes the bounded extraction plus
signed-AtomSheet path for the labeled synthetic workload, not real supplier or
evidence authentication.

Current next action: adversarial and negative evidence fixtures, including
missing or conflicting bank details, duplicate invoices, unauthorized roles,
threshold breaches, prompt injection, cross-business cartridge selection,
tampered bundles and revocation. Fail closed or require human review whenever
the labeled safe-extraction boundary is not satisfied.

### Adversarial gate checkpoint

A deterministic supplier-payment safety gate now blocks cross-tenant requests,
duplicate invoices, role-limit breaches, prompt injection, bank-detail changes,
missing fields and noncanonical amounts before cartridge execution. Eight
labeled SD fixtures ran 1,000 times each with all 8,000 decisions correct,
deterministic receipts and zero model calls. Median gate latency was 0.011750 ms
and p95 was 0.014416 ms. This promotes only the synthetic decision boundary.
Tenant and evidence authenticity remain unproved, and the v1 cartridge still
depends on a separately supplied active tenant ID.

Current next action: add a separately signed tenant envelope and signed
revocation state, then verify cross-cartridge isolation and revoked-key or
revoked-cartridge rejection before any production tenant-bound claim.

### Core SD optimization checkpoint: lossless addressable experts (2026-09-07)

The user explicitly redirected the active programme from the application-level
Business Map dependency back to the universal SD-resident LLM problem. The
tenant-envelope action above remains recorded but is paused; it is not the
current execution target.

A native Metal full-layer probe proved that a genuine SD-mapped layer can be
scanned through a no-copy shared buffer with a 64.37% median create-plus-scan
reduction. Naive custom no-copy expert execution was then falsified: it was
slower than copied execution and did not meet framework-reference exactness.

Four-worker exact CPU materialization reduced an eight-expert microbenchmark by
7.30%, but full generation regressed 5.43%. The experiment nevertheless proved
that 90.07% of the apparent Metal-transfer stage could be moved into explicit
page materialization. Inline pre-materialization is stopped.

The existing layer packs were found to be physically lexicographic rather than
route-aware. A corpus-bound plan reduced weighted pair distance 50.30%, but the
exact full-model ABBA improvement was only 2.71%, below the locked 10% gate.
Layout alone is not promoted.

The promoted candidate stores every tensor as an independently addressable,
lossless Zstandard level-3 frame in the corpus-derived physical order. All
2,560 tensor roundtrips are byte exact. The expert payload fell from
6,039,797,760 to 4,708,753,870 bytes, a 22.04% reduction. In the exact
stage-instrumented eight-token ABBA test, median generation time improved
23.76%, p95 improved 24.11%, and median Metal-transfer attribution fell 90.57%.
Every token and every step logit matched, logical demand was unchanged, and the
three-GiB expert ceiling passed. The mechanism is promoted for replication.

A production-like 24-token run showed a 20.63% median wall-time improvement and
both compressed-candidate trials were exact, but the two ordinary source trials
missed resident-control logits by at most 0.015625. The experiment is preserved
as NOT_PROMOTED because experiment-wide exactness failed.

Current next action: reproduce an exact 24-token source control, then run the
compressed representation across the established four prompt families at
64--256 generated tokens with cold/warm p50 and p95 reporting. Do not claim the
longer throughput gain until every source and candidate step logit is exact.
