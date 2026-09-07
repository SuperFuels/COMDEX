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

### 2026-09-07 exact compressed-pipeline promotion and codec pivot

The expert execution representation now uses route-aware physical ordering,
independently addressable lossless Zstandard frames, reversible two-byte BF16
shuffle, coalesced physical reads, and a bounded four-worker decoder. The full
expert library is 4,134,132,737 bytes rather than 6,039,797,760 bytes (31.55%
smaller). A stage-instrumented, one-prompt, eight-token ABBA run bound to the
mounted SD's verified `disk6` counter improved median time from 96.441 s to
67.066 s (30.46%). All token IDs and every generation-step logit were exact;
the 3 GiB expert-cache plan passed. Physical read counts fell from
20,369--30,419 to 531--577 in the two samples. This is promoted as an exact
short-run mechanism result, not as a universal production throughput claim.

The previous eight-worker evidence remains valid for timing, exactness, logical
demand and memory, but its physical counters were not bound to the mounted SD;
correction sidecars invalidate only those physical-I/O fields. All affected
measurement scripts now fail closed on a counter/storage-root mismatch.

A real-frame LZ4 alternative was stopped before full-pack construction. It was
only 2.22% faster for median in-memory decode but used 457,768,168 bytes versus
371,922,093 bytes for Zstandard on the same 542,638,080 raw sampled bytes. The
SD-byte penalty dominates the small decode gain, so LZ4 is `NOT_PROMOTED`.

The next exact-output candidates, in measured priority order, are longer and
multi-family replication of the four-worker compressed pipeline, a same-total-
memory two-tier compressed/Metal cache, Glyph-family request batching for
completed-task throughput, and a longer-corpus replacement for the previously
failed predictive-eviction dictionary. Lossy quantization, pruning and reduced
expert count remain a separate quality-gated track.

The first integration gate for the promoted pack then completed one
technical-explanation request for the full 64-token ceiling. From an empty
expert cache it achieved 0.6053 tokens/s, 53.185 s time to first token, and a
0.7395 s median subsequent-token interval. It recorded 4,393 faults, 12,994
retained hits (74.73%), and 20,729,793,832 logical expert bytes. All 64 token IDs
and all 64 step logits matched the full-resident control exactly. This passes
the programme's 0.50-token/s strong-result milestone and validates that the
compressed decoder is connected to storage-first execution. It is retained as
a valid diagnostic rather than a performance promotion because it has one
prompt, warm-uncontrolled filesystem state, and no matched storage-first source
arm. Its 53.185 s cold-cache TTFT makes initial working-set construction the
largest immediate user-visible cost.

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

### Cold-prefill lower bound and locked pivot (2026-09-07)

The promoted four-worker representation subsequently passed an exact 64-token
storage-first integration gate at 0.6053 tokens/s, with 53.185 s TTFT and zero
token or step-logit error. A route-bound audit then localized that TTFT. Across
all three valid corpus observations, the first prompt pass selected
97.8906--98.0469% of the 1,280 layer/expert pairs and required
97.8791--98.0352% of the complete 4,134,132,737-byte compressed library.

This falsifies eviction-only cold-TTFT optimisation: almost every expert is
genuine first-pass demand, not a cache mistake. A reversible BF16 bit-plane
exploratory transform was also worse than the promoted byte shuffle on a real
3,145,728-byte tensor (25.43% versus 30.87% compression) and is stopped.

Locked pivot: do not spend further exact-track cycles predicting cold-prefill
experts for these prompt lengths. Preserve the promoted compressed format for
Granite, use exact reuse only when a prefix or working set is already verified
and resident, and continue Stage 6/7 routing: AtomSheet/replay first, bounded
warm Qwen for accepted low-cost tasks, and Granite for depth or policy
requirements. Semantic prompt shortening, quantization and reduced-expert
execution remain separately quality-gated because they change input or
numerical execution.

### Evidence-bound Stage 7 economics diagnostic (2026-09-07)

An immutable cross-artifact projection combined 100 previously verified
AtomSheet calculations, one measured call for each of eight distinct accepted
Qwen extraction cases, and the two exact-but-quality-failed Granite business
tasks. It attempted 110 tasks and counted 108 as successful (98.18%). One
hundred model calls were avoided. Using the measured AtomSheet median for its
projected total and individual Qwen/Granite wall times, the cohort occupied
373.189 s and yielded 1,041.83 successful tasks/hour.

The critical result is allocation of time, not the headline projection:
AtomSheets consumed 0.0028%, Qwen 6.4949%, and the two failed Granite attempts
93.5023% of the cohort time. Granite's token/logit exactness did not cause those
tasks to pass their output rubrics, so both remain failures. This proves that
task-level gating is economically dominant: a slow strong-model call must not
be made merely because a request sounds complex when a verified cartridge or
better task contract can handle it. The result is diagnostic, not Stage 7
promotion, because it combines separate synthetic runs and is not a blinded
live mixed-workload execution.

Current action: route the bounded supplier-control information task through the
already signed Business Map cartridge and remeasure it without granting payment
authority. Keep the removable-model-integrity task uncompleted until a verified
contract or quality-passing model route exists.

### Verified Business Map policy-route result (2026-09-07)

The signed supplier-control cartridge now has a deterministic, read-only answer
route. It verifies the cartridge and trust anchor fail closed, renders all six
controls with both the risk prevented and required human evidence, emits a
content-addressed proof receipt, makes no model call, and cannot execute a
payment. Across 1,000 SD-backed trials the answer and receipt were identical;
median latency was 0.305041 ms and nearest-rank p95 was 0.343583 ms.

Substituting this verified route for the prior 169.281 s failed Granite attempt
in the same evidence-bound 110-task scenario increased successful tasks from
108 to 109, reduced serial time from 373.189 s to 203.908 s (45.36%), and raised
diagnostic successful-task throughput from 1,041.83 to 1,924.39 tasks/hour
(84.71%). Model calls fell from 10 to 9. The remaining failed Granite
removable-integrity task is still counted as a failure and consumes 88.11% of
the revised scenario time.

This is a genuine routing and task-economics advance, not a claim that Granite
itself generates tokens faster. It remains diagnostic rather than Stage 7
promotion because it combines immutable synthetic runs instead of executing a
blinded live mixed workload. Current next action: define a verified workflow or
explicit unsupported/human-review outcome for removable-model integrity, then
run the complete router on a blinded task set with end-to-end p50/p95 latency.
