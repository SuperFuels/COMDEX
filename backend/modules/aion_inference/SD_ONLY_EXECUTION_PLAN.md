# AION SD-Only Execution Plan

Latest operational state (2026-09-12): C4 training collection restarted in
`results/aion_gptoss_c4_full_layer_training_queue_20260912_retry02`, up to 24
training-only prompts across all 36 layers. Both earlier roots are interrupted
and preserved, not verified evidence. Restart free space approximately 19 GiB;
3 GiB during-capture reserve remains mandatory. No additional L2 allocated.
Queue/economics checks passed 13/13 again. No new certification or speed claim.
Do not start competing full-model inference while this queue is running.

Ranked correction compiler preparation: future counterfactual teacher jobs
also save hash-bound gated E2/E3 targets without extra neural work. The first
active retry02 arithmetic job loaded the older E4-only code; do not count it
as E2/E3 coverage. Follow-up jobs load the extension. Corrections for the last
selected contribution on 2/3-expert calls require their own gate/activation/
reduction-order and downstream validation; no inference shortcut is enabled.

Incremental local gate worker is active (2026-09-12), watching retry02 verified
completions and writing `results/aion_ranked_correction_incremental_local_gates_20260912`.
It probes layer 12 using different completed TRAINING prompt families for
fit/development, ranks 2/3/4 when targets exist. Fixed ridge .001, minimum four
fit observations, max32, cosine .80, local error <=.02 and improvement over
drop. These are exploratory training/development probes, never certificates.
Selection/holdouts remain unused. At most one BLAS thread; no SD/model compute.
No automatic neural injection or full-generation promotion. Inspect report
support, error, payload and coverage before downstream integration.

First retry02 arithmetic teacher is COMPLETE_VERIFIED: 1332 observations,
teacher canonical 2c685a371d367016291d20f366bafe98d98ae592b28c44366f73a35bb77940a7,
completion f6ff83bd0c5e2b97c6215f7b68b3151ca9e5dfb22b7a9c856764923345f32a25.
Continuation E4 calls 576, not certified traffic. A prefill-to-continuation
same-prompt sanity probe at layers2/13/18 rejected all6 test positions at the
frozen .80 support screen (max cosine .5985). This is a coverage miss, not an
accuracy failure or speed gain. Independent family business capture active;
incremental continuation-to-continuation probes remain the next gate.

Status: LOCKED for execution until faster storage or additional hardware is available.

Subsequent operational update: business01 COMPLETE_VERIFIED, 1188 observations
and 1188 hash-bound targets of each rank E2/E3/E4; teacher canonical
a9a6faf2c267279d5bedec8532bfa804ba4e9a4b10d9587b3c6db3332ef23047,
seal 790ed2d994de3aed6b482e83fea7430cdbb064f595e01ab56d1bda07ae044d8a.
Arithmetic-to-business layer12 E64 probe: four fit calls, one supported dev
call, cosine .8910833, omission error .06939687, correction error .03246070,
149764 resident bytes. Fixed .02 gate fails; NOT_CERTIFIED. No supported
local passing calls among 16 development E4 calls. E2/E3 fitting unavailable
in older arithmetic job. Explanation01 teacher now active, enabling subsequent
new-target cross-family probes. Two verified prompts supply 1152 continuation
E4 calls; none meet >=8-call/two-family identity support yet. Certified share
remains unavailable and no speed result changes.

Ranked correction reduction audit (2026-09-12): native 1+C2, 2+C3 and
3+C4 integrations matched the corresponding diagnostic 2/3/4-expert outputs
bit-for-bit when supplied the real gated final contribution. Zero differing
elements in all three cases, one CPU thread, existing read-only verified local
L2 components, zero SD expert reads. Evidence canonical
0d21ecacfd752304361670515b0470c733fee5089aaff8765608e0ed46655f72.
This validates addition order only: no learned accuracy, quality certificate,
timing improvement or full-model substitution is inferred. Existing exact ABI
and existing top3+C4 path remain unchanged.

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

### Evaluator-blind governed-router result (2026-09-07)

The first shuffled end-to-end router cohort has now completed. The router saw
request text only; case kind and expected answers were withheld until the
post-route evaluator. A fixed-seed order commitment bound 100 promoted
AtomSheet calculations, eight live Qwen supplier extractions, one signed
Business Map policy request and the exact previously failed removable-model
integrity contract.

All route receipts and the append-only trace chain verified. AION completed
109/110 tasks (99.09%), sent the remaining task to human review, avoided 102
model calls and made eight Qwen calls with no Granite call. Serial wall time was
25.576 s, yielding 15,342.75 completed tasks/hour for this highly arithmetic
synthetic mix. End-to-end task latency was 16.207 ms p50, 0.7502 s p95 and
18.542 s maximum. The maximum was Qwen's explicit cold start; Qwen warm p50 was
0.7460 s and warm p95 was 0.8729 s.

This promotes the bounded routing mechanism and the negative-capability gate,
not general Stage 7 economics. The cohort is synthetic and dominated by 100
fast calculations; it does not yet include accepted quotation, drafting,
planning and coding rubrics. Qwen supplies no step logits, and the human-review
decision is a safe resolution but not a completed task. Current next action:
build a family-balanced blinded cohort with explicit success rubrics for those
missing business categories, measure per-family p50/p95 and preserve the same
no-failed-task-counted-as-complete rule.

### Family-balanced Stage 7 synthetic gate (2026-09-07)

A narrow verified quotation AtomSheet now calculates an EUR base-plus-markup
total, inverse-checks it, emits a deterministic draft and permanently denies
sending, approval and payment authority. It requires human approval and fails
closed outside its exact grammar and numeric bounds.

The first equal-weight run preserved a genuine failure: 49/56 tasks completed,
with drafting at 2/8 and extraction at 7/8. The drafting requests had not made
the customer name a literal output requirement, and one extraction dropped a
currency code. A second immutable run tightened the drafting contract without
weakening its rubric; drafting reached 8/8 but extraction remained 7/8. The
third run restored the exact extraction instruction previously verified twice.

The final fixed-seed evaluator-blind cohort passed all 56 tasks: eight each for
calculation, quotation, policy, extraction, short drafting, planning and coding.
All route receipts and the trace chain verified. Twenty-four model calls were
avoided; 32 bounded Qwen calls completed the four language families and no
Granite call was made. Actual serial wall time was 33.870 s, or 5,952.13
successful tasks/hour. End-to-end p50 was 0.3330 s, p95 was 0.7811 s and the
16.430 s maximum was Qwen's explicit cold start; warm Qwen p50/p95 were
0.5909/0.7791 s.

This passes the balanced synthetic Stage 7 mechanism gate, not production
economics. The tasks are constructed, deterministic and only eight deep per
family; supplier evidence is synthetic and Qwen step logits are unavailable.
Current next action: freeze these contracts, generate unseen paraphrases and
adversarial near-misses before execution, then run a separately committed
holdout manifest. Any family regression must fail the whole cohort.

### Frozen unseen/adversarial holdout result (2026-09-07)

The next corpus was committed before runner adaptation and installed unchanged,
read-only, on the SD volume. Its task manifest and separately opened answer key
have SHA-256 values `f49a3cd894568ae31a503e1bf3ce4fcb55bdabf47001f5fd22f8e9f2878b6481`
and `8e6b767af902082e6a655a411ff54b4a1c34cb4363dfc425c5d01a05aa954a66`.
It contains four unseen valid requests and four adversarial near-misses for each
of the seven families. Every request was routed before the evaluator opened the
answer key; adversarial requests were prohibited from model execution.

Version 1 completed all 28 unseen valid tasks but failed promotion because two
adversarial policy requests still reached the read-only signed policy renderer.
No payment action was possible, but a verified bypass was still incorrect. The
immutable failed result remains on the SD. The matcher had recognized `approve
payment` but not `approve the supplier payment`; it was narrowed to reject an
action verb within the surrounding payment phrase.

The unchanged v2 holdout passed every gate: 28/28 unseen valid tasks completed,
28/28 adversarial near-misses rejected verified bypass, zero adversarial model
calls, all seven families passed, and every receipt and the trace chain
verified. Sixteen valid Qwen calls ran; 40 calls were avoided or prohibited.
Total wall time including all adversarial route checks was 28.837 s, yielding
3,495.53 successful valid tasks/hour. Valid-task latency was 0.3445 s p50,
1.1347 s p95 and 19.624 s maximum; the maximum was the explicit cold Qwen call.
Warm Qwen p50/p95 were 0.5982/1.1328 s. Granite was not needed.

This promotes the frozen synthetic holdout gate, not production deployment.
Four cases per disposition and family remain small, and the language tasks are
contract-shaped. Current next action: scale the frozen holdout with generated-
then-manually-frozen paraphrases, cross-family compounds and irrelevant-noise
injections; separately measure false refusal as well as false bypass.

### Stopped warm Glyph-family batching strategy (2026-09-07)

The sixteen frozen valid Qwen tasks were executed in an ABBA comparison of
deterministically shuffled order versus grouping by bounded executor family.
Every arm explicitly unloaded Qwen, performed a neutral cold prime and then
measured only warm calls. Grouped requests genuinely shared the same schema and
fixed prompt prefix. All 64 task executions passed and every case produced an
identical canonical response across all four arms.

Grouping reduced median total prompt-evaluation time from 0.81935 s to 0.73646
s (10.12%), but median total warm workload time fell only from 9.78512 s to
9.57284 s (2.17%). This misses the predeclared 3% promotion threshold and is
`NOT_PROMOTED`. The result localizes the remaining Qwen cost: common-prefix
evaluation is a small share, while response generation dominates. Do not spend
more cycles on serial family grouping for this workload. Current next action:
use recorded per-family generated-token and generation-time evidence to target
the largest output family with a separately quality-gated minimal-response
contract or verified AtomSheet promotion.

### Stopped compact extraction wire protocol (2026-09-07)

Extraction was the largest measured Qwen family, so a separately quality-gated
ABBA test replaced the full JSON keys with Glyph-compiled `s`, `i`, and `a`
keys, then expanded them back into the identical Business Map fields. Twelve
cases ran through baseline/compact/compact/baseline arms after an explicit
unload and neutral cold prime for each arm.

The compact candidate failed 8/12 cases identically in both candidate arms,
while both baseline arms passed 12/12. It increased generated tokens from 445
to 462 (3.82%), increased median generation time from 5.7663 s to 5.9710 s, and
improved total warm time only 4.91%, below the 10% gate. It is stopped and
`NOT_PROMOTED`; short field names are not a useful token code for this model.

The first report also incorrectly calculated its
`payment_execution_never_allowed` field from task success rather than recorded
authority. A hash-bound `INVALID` sidecar invalidates only that field; it does
not change the failed quality, token, timing or promotion conclusions. The
runner now records authority directly. The resulting verified extraction
AtomSheet and its separately frozen holdout are recorded below.

### Promoted verified supplier-extraction AtomSheet (2026-09-07)

The twelve previously accepted normalized supplier outcomes were compiled into
eight strict sentence grammars with bounded invoice, currency and amount rules.
The route fails closed on ambiguity, action language and cross-tenant language;
fallback remains available, but the verified route can neither approve nor
execute payment. Its derivation gate passed 12,000/12,000 valid executions and
rejected 4,000/4,000 known attacks.

A separate 32-case task manifest and answer key were committed before execution
and copied unchanged to the SD evidence volume. Their SHA-256 values are
`b6f38c0d77f90e93d3eaf9d50214a8b21a6443ad821f3df9ff21b7460b3794c1`
and `eb2b1b460f1996f4d79b484b838416a72b46fab84f809cd37730d20e9db59b34`.
The evaluator routed and reviewed every shuffled request before opening the
answer key. Across 1,000 repetitions it passed 16,000/16,000 unseen valid
extractions with exact fields and signed review, rejected all 16,000 adversarial
near-misses, produced deterministic receipts, made zero model calls and never
granted payment authority. Valid latency was 0.3091 ms p50 and 0.3488 ms p95.

This is a serious completed-task-throughput promotion, not a model token-speed
claim: requests within a verified grammar no longer need token generation at
all. The boundary remains deliberately narrow and synthetic. New phrase shapes,
ambiguous requests and action-bearing requests must fall back or fail closed.
Next action: integrate this promoted route into a newly measured balanced
workload, then freeze a broader phrase/noise/compound holdout before expanding
the grammar or automatically compiling additional verified outcomes.

### Balanced integration of verified extraction (2026-09-07)

The promoted extraction route was integrated into the same fixed-seed 56-task,
seven-family construction as the prior v3 balanced gate. V4 completed all
56 tasks, all families, receipts and the trace chain. Extraction completed 8/8
with zero model calls; total model calls fell from 32 to 24 and avoided calls
rose from 24 to 32. Observed serial time fell 10.59% from 33.870 s to 30.283 s,
and successful-task throughput rose 11.85% from 5,952.13 to 6,657.27 tasks/hour.
Overall task p50 fell from 0.3330 s to 0.01162 s; extraction p50/p95 were
0.503/1.041 ms.

The p95 comparison regressed 22.30%, from 0.7811 s to 0.9553 s, because the
single cold Qwen start was slower and occurred in a different family. The v3
and v4 runs were separated in time rather than contemporaneous ABBA arms.
Therefore this promotes functional integration and call avoidance, not a causal
11.85% speed claim. Current next action: freeze the broader phrase/noise/compound
corpus, including false-refusal accounting, before expanding parser coverage.

### Frozen extraction stress diagnostic and safety repair (2026-09-07)

A committed 40-case corpus expanded beyond the eight learned sentence shapes:
24 useful extraction requests, eight cross-family compounds and eight
adversarial inputs. Its task and separate answer-key SHA-256 values are
`d5ab58a7d5dda8c9be364332422bff18d3556de78bba30ed440150d7a3b3b5f9`
and `df9c5a66c3c646b5edffa75522309d2d28b7087c54fe5d7451241ff04fec4bb4`.

The immutable v1 run failed. Across 500 repetitions it refused 7,500 of 12,000
useful executions (62.5%), produced 500 wrong extractions from one noisy case,
and produced 500 false verified bypasses from one two-invoice compound. No
payment authority existed. The defects came from allowing a sentence period
inside a supplier span and not enforcing global single-invoice/single-amount
cardinality.

The contract was strengthened with both structural guards and hash-bound to the
new rules. On the unchanged v2 corpus, wrong extractions fell to zero and all
8,000 compound/adversarial executions were rejected. Coverage remained a
failure: 8,000/12,000 useful executions were refused (66.67%). The original
independent holdout was then rerun under the strengthened contract and again
passed 16,000/16,000 valid and 16,000/16,000 adversarial executions exactly.

This promotes the safety repair but not broader parser coverage. Do not add all
stress-corpus wording directly and call it generalization. Next action: design a
narrow canonical-intent normalizer with an explicit ambiguity/compound gate,
then evaluate it only on a newly frozen corpus; otherwise send unsupported
forms to the governed Qwen fallback.

### Bounded Semantic Gateway candidate (2026-09-07)

A separate normalizer candidate was built rather than widening the production
parser directly. It requires unique invoice and amount entities, rejects
compound/action language, and canonicalizes eight additional explicit
paraphrase forms plus four whitelisted harmless prefix/suffix forms into the
already verified grammar. It is not yet called by the governed router.

On the stress derivation corpus, v1 reduced false refusals from 66.67% to 16.67%
with zero wrong extraction or guard bypass; four suffix cases exposed a duplicate
punctuation defect. V2 corrected that mechanical defect and passed 12,000 useful
and 8,000 guard executions. A separate new-value holdout was then committed with
task/answer hashes `35f43a2fc1c89c644d50c7993db530ee1202eae99814b4ce872b0d55760b61f2`
and `4a36559cb6d1cc9b1b61d3910df13f10f41c207236cc1d3c287f15e9178c88b1`.
It passed 12,000/12,000 exact useful executions and rejected 8,000/8,000
compound/adversarial executions. Useful latency was 0.337 ms p50 and 0.384 ms
p95, with zero model calls and no payment authority.

This is `PROMOTED_FOR_INTEGRATION` for the finite declared transformations, not
general paraphrase understanding. The holdout used new values and requests but
was intentionally constructed from the supported transformation families.
Before router promotion, bind original and canonical request hashes into one
proof receipt and run a fresh end-to-end governed-router holdout.

### Governed-router normalizer integration gate (2026-09-07)

The bounded supplier-intent normalizer is now connected to the production
governed router. Every accepted route seals the original public-request hash,
the canonical-request hash, the normalizer-contract hash and the downstream
verified-extraction receipt into one route receipt. The transformation grants
no approval or payment authority; rejected compound and adversarial requests
continue through the exact fallback path without verified bypass.

The separately frozen 20-case new-value holdout was executed 500 times through
the complete governed router before its answer key was opened. All 12,000
useful executions completed with exact fields, all 8,000 guard executions
avoided the verified route, every receipt and the append-only trace chain
verified, and payment execution remained impossible. Useful-route latency was
0.0541 ms p50 and 0.0709 ms nearest-rank p95; guarded fallback-decision latency
was 1.155 ms p50 and 1.607 ms p95. The canonical report SHA-256 is
`4e804342f8c3f8fca35dd732cf286714209201c031c0162a53a15295596b632e`;
the evidence-file SHA-256 is
`60eef85eaf4b7a4e7e38269568b0cd46a126c1d0df36961ef644cb5b9b425e9a`.

This promotes the finite normalizer transformations into governed routing. It
does not establish open-ended language understanding or production traffic
performance, and fallback model calls were declared but deliberately not
executed in this gate. Current next action: rerun a family-balanced blinded
cohort containing these newly accepted phrasings and measure contemporaneous
model-call avoidance and end-to-end p50/p95 rather than projecting the gain.

### TensorSheet CPU-assistance and neural-repetition diagnostic (2026-09-07)

A real layer-16 decode route was decomposed into eight independently scheduled
expert calculations using 37,750,592 verified SD-backed logical weight bytes.
Across 200 balanced samples, resident Metal remained fastest at 1.159 ms p50;
resident CPU, two-CPU-expert hybrid and four-CPU-expert hybrid were respectively
107.56%, 22.55% and 48.47% slower. When the same weights began CPU-resident as
a simulated cache fault, CPU-only execution avoided weight placement and was
48.55% faster than placing all eight experts into Metal. However, every
CPU-assisted result differed numerically from Metal, with maximum absolute
layer-output error (3.0518\times10^{-5}). It cannot enter the exact track.

Full-model tests explained the boundary. On the uncompressed pack, moving
faulted experts into Metal consumed 63.856 s of an 86.463 s two-token control.
Sending all experts to CPU did not remove the cost: BF16-to-FP16 conversion
moved 60.680 s into CPU materialization and the run slowed to 93.701 s. A
preconverted FP16 pack removed conversion but made the wide 163-token prefill
CPU-bound; expert calculation and combination consumed 78.091 s and total time
rose to 101.198 s. Both CPU arms preserved token IDs but failed exact logits,
with maximum error 0.2265625.

A phase-aware candidate therefore retained Metal for prefill and resident
experts while sending only new one-token faults to CPU. Against a separately
executed matched compressed four-decoder Metal arm, it reduced Metal transfer
operations 24.21% (3,312 to 2,510) and observed time from 68.762 s to 67.461 s
(1.89%). All eight token IDs matched, but maximum logit drift was 0.03515625.
The runs were sequential rather than ABBA, and the timing change is below the
10% promotion gate. Phase-aware CPU fault execution is therefore
`NOT_PROMOTED`; do not spend an exact-track cycle attempting to make CPU and
Metal kernels bit-identical. It remains available only as a separately
quality-gated research path.

The accompanying repetition audit examined three content-addressed route
observations: 5,696 layer-route instances contained 931 duplicates (16.34%),
and consecutive routes shared 3.256 of eight experts on average. This validates
weight retention. Only 45 of 5,664 consecutive pairs were identical (0.794%),
and the privacy-preserving corpus contains no activation vectors, so zero
expert-output calculations are proven reusable. Exact output reuse requires
matching activation, weight and numerical-contract hashes. The next repetition
target is exact shared-prefix/KV reuse across requests, where identical causal
prefix state is genuinely reusable, rather than memoizing outputs from merely
similar expert routes.

### Exact shared-prefix/KV reuse falsification (2026-09-08)

A full-resident Metal mechanism test used four synthetic business requests with
a genuinely identical 166-token policy and Business Map prefix. The cache key
bound the exact prefix tokens, all model artifacts, FP16 datatype and MPS
backend. Model and evidence remained on the mounted SD volume; prompt text and
logits were not persisted. The control performed each 181--193-token prefill in
one pass. The candidate calculated the 166-token prefix once, branched its KV
state without copying the underlying Metal tensors, and processed only the
15--27 unique suffix tokens per request.

An initial engineering attempt was rejected before evidence creation because
PyTorch refuses to deep-copy non-leaf cache tensors. The corrected,
position-bound run avoided tensor copying and recorded canonical evidence. It
reduced total measured time from 4.8451 s to 4.6543 s including the shared-cache
build, an observed 3.94% improvement. This missed the declared 10% speed gate.
More importantly, only three of four token streams matched and no request had
bit-identical step logits; the largest observed step-logit deviation after
divergence was 36.0342.

The candidate is `NOT_PROMOTED` and stopped on the exact track. Splitting a
Metal prefill changes the floating-point execution shape even when causal token
state is mathematically reusable, so it cannot reproduce the one-pass control's
bit pattern on this stack. Do not repeat this implementation under the exact
gate. Prefix/KV reuse may be reconsidered only in a separately declared
quality-gated track, or if a backend can prove bit-identical chunked and
one-pass prefill. The next exact optimization must avoid changing neural kernel
partitioning; governed replay, verified AtomSheets and finite Semantic Gateway
routes remain the proven way to eliminate repeated neural calculation exactly.

### Native INT8 Glyph-block breakthrough candidate (2026-09-08)

The quality-gated track identified a native Apple Metal weight-only INT8 matrix
operation that consumes packed expert weights directly. Unlike earlier storage
compression, the weights do not need to be reconstructed as full FP16 tensors
before matrix calculation. A real layer-16 decode route containing eight
verified Granite experts was tested for 200 balanced samples.

Symmetric per-output-channel INT8 weights plus FP16 scales reduced the route's
weight representation from 37,748,736 to 18,915,328 bytes (49.89%). Once
resident, native packed execution was 28.41% faster at p50 than FP16. The first
fault implementation was correctly rejected because separate weight and scale
placements made it 24.01% slower. The refined layout retained the small scales
on Metal and joined each expert's two matrices into one contiguous,
Glyph-addressed block. That fault path was 50.00% faster at p50 than FP16.

This is `ADVANCE_TO_FULL_MODEL_QUALITY_GATE`, not promotion. Maximum and mean
layer-output errors were respectively 0.0036621 and 0.00036268, so the candidate
is explicitly non-exact. The approximate complete expert representation is
3.03 GB decimal (about 2.82 GiB), potentially placing all 1,280 Granite experts
inside the existing 3 GiB expert budget and eliminating expert eviction after
initialization. The next locked action is to build content-addressed INT8 Glyph
blocks on the SD volume, integrate the native operation across all 32 layers,
and run frozen prompt-quality, token-agreement, throughput, TTFT and memory
gates against FP16 and the promoted exact compressed streaming control.

### Full-model native INT8 and storage-first packed boot (2026-09-08)

The complete derived library contains all 1,280 experts across 32 layers. Its
logical size is 3,026,452,480 bytes (2.8186 GiB), a measured 49.894% reduction
from 6,040,094,720 verified source bytes. Every source and output object is
content-addressed, all indexes are hash-bound, and the atomic manifest canonical
SHA-256 is
`62b7768bd2062d668a2c2aefbf765137829ac34390e8cb1421532c61dc3c3d5b`.

The first full-resident four-prompt, eight-token mechanism run installed all 32
native INT8 layers. All 32 generated token identifiers matched FP16, and median
time to first token improved 10.69%. Median generation increased only from
8.235 to 8.425 tokens/s (2.30%), below the declared 10% speed gate, while logits
were non-exact. Direct full-resident speed is therefore `NOT_PROMOTED`. Active
Metal allocation nevertheless fell from 6,597,587,456 to 3,591,071,232 bytes.

The subsequent storage-first implementation constructed the model skeleton,
loaded 226 shared tensors and deliberately skipped all 64 combined FP16 expert
tensors. It then loaded the content-addressed INT8 Glyph library directly; FP16
experts were never materialized. Ready-state active Metal allocation was
3,584,241,664 bytes, 45.67% below the FP16 control. Boot fell from 91.2310 to
43.6290 seconds (52.18%), median throughput was 8.215 tokens/s (only 0.25%
below FP16), and all 32 token identifiers again matched. Every declared gate
passed, so the result is `ADVANCE_TO_LONG_QUALITY_GATE`, not production
promotion. The evidence canonical SHA-256 is
`adb6e1e6deb9826c818bd4c1253bc298ba7b98d1360bc969fcc4f53c4df8a9e5`.

This establishes a new capability boundary on the existing M3 Pro: a fully
resident, functioning Granite model with roughly half the expert storage,
45.67% less active Metal memory and 52.18% faster boot, without sacrificing
short-run tokens or throughput. It does not yet establish 64--256-token output
quality, randomized prompt robustness, task accuracy or equivalence. The next
stage must preserve the FP16 baseline, run longer frozen multi-family cohorts,
measure divergence and semantic task quality, and separately compare the packed
resident runtime against the 0.6053-token/s exact SD-streaming track.

### Sixty-four-token packed-quality and mixed-precision gates (2026-09-08)

The unchanged four prompt families were extended to 64 generated tokens each.
All-layer INT8 produced finite logits, improved median throughput from 9.921 to
10.213 tokens/s (2.95%) and reduced median TTFT 20.32%. Token agreement fell to
166/256 (64.84%), below the declared 75% gate, and speed remained below the 10%
gate. It is `NOT_PROMOTED`; report canonical SHA-256:
`a7c8bf2e0a4ba3d169561766103620803884fdb8460b1386b8e6424e75129b00`.

The 3 GiB ceiling leaves room for two complete FP16 expert layers. A first/last
layer heuristic used 2.9940 GiB and improved median throughput 10.50% and TTFT
24.44%, but reached only 67.19% token agreement. It failed quality. A subsequent
real-activation TensorSheet audit measured each layer independently across all
four prompt families. It ranked layers 29 and 1 as most sensitive, followed by
17, 28 and 24; audit canonical SHA-256:
`190345280c86024d7f72ab693eb535ed9ac5924e4da4a0376381404ac7aeba93`.
Replacing the guessed endpoints with layers 29 and 1 retained the same 2.9940
GiB budget but achieved only 64.06% token agreement. It is also `NOT_PROMOTED`.

Whole-layer mixed precision is therefore stopped under this budget: measured
sensitivity did not translate into sufficient autoregressive agreement. The
storage-first eight-token capacity result remains valid, but long-form quality
is not promoted. The next quality candidate must change the quantizer itself or
retain a sparse set of high-value expert weights, rather than guessing more
whole-layer pairs. Any next candidate requires a frozen calibration/evaluation
split, teacher-forced quality diagnostics to separate cascade effects, and a
semantic task gate in addition to raw autoregressive token agreement.

A 3% outlier-residual shelf was then tested on the real layer-16 route. It kept
the projected full expert library within 2.9925 GiB, but reduced maximum layer
error only 1.32% and made native INT8 calculation 116.90% slower through extra
indexing and FP16 correction kernels. The candidate is `NOT_PROMOTED` and
stopped; canonical report SHA-256:
`ca2604039afc04d5daf28611df89c8c96312d6c4a55e9cbf2223194e2ffd668a`.
The quantization error is not sufficiently concentrated in a small set of input
columns for this residual form. Do not scale or repeat it. The next diagnostic
is teacher-forced FP16-versus-INT8 scoring on identical histories, followed by a
separate semantic task gate if probability/top-choice preservation is strong.

That teacher-forced diagnostic has now passed all declared gates. On the same
256 FP16-generated positions and identical histories, all-layer INT8 preserved
the FP16 top-1 choice at 247 positions (96.48%) and achieved 96.33% mean top-five
overlap. Mean KL divergence was 0.003455 nats, and mean additional negative log
likelihood on FP16-chosen tokens was only 0.006691 nats. The nine disagreements
occurred at low FP16 decision margins on average within each family. Canonical
report SHA-256:
`1c732ec78c27f73e769275c314caeaa08c637282fafab937110ad51f48ba3930`.

This is `ADVANCE_TO_SEMANTIC_TASK_GATE`, not promotion. It establishes that raw
autoregressive positional agreement substantially overstated underlying model
damage: a small number of alternative greedy choices changed later histories,
while the packed model closely preserved FP16 probabilities on equal histories.
The next frozen gate must score completed answers on held-out semantic tasks and
must still report unconstrained generation divergence, latency, throughput and
memory. Exact-track claims remain prohibited because logits differ.

Two separately frozen semantic microtask gates were then executed. The first
strict-JSON cohort was unsuitable: FP16 and INT8 each passed only 2/8 tasks,
although seven parsed outputs were identical and INT8 ran 6.26% faster. The
second cohort removed JSON-formatting ambiguity with twelve multiple-choice
tasks. FP16 passed only 6/12, below its required 10/12 competence floor; INT8
passed 7/12, agreed with FP16 on 11/12 decisions (91.67%) and ran 18.31% faster.
Both gates are `NOT_PROMOTED` because a weak baseline cannot establish absolute
semantic quality. The multiple-choice canonical report SHA-256 is
`4105f6fa4203073525639bf0b6cf7aca042f0f179bbb0582e2c3047551a00ba1`.

These results provide additional relative non-inferiority evidence but no broad
capability claim. The next semantic design must first prove FP16 competence on a
larger frozen cohort, preferably by direct choice-token likelihood rather than
free-generation formatting. Any method refined using these failures is a
diagnostic and requires a new unseen holdout before promotion.

The direct choice-token likelihood diagnostic has now been executed on that
already-observed twelve-case cohort. It combined the probability mass of each
valid bare and space-prefixed one-token answer spelling, eliminating generation
length and parser behavior. FP16 still passed only 6/12. INT8 passed 8/12, but
the models agreed on only 10/12 choices (83.33%). Candidate forward time was
3.3656 seconds versus 4.1288 seconds for FP16 (18.49% lower), but timing was not
a promotion gate for this post-hoc diagnostic. The result is
`DIAGNOSTIC_DID_NOT_CLEAR_BASELINE`; canonical report SHA-256:
`7caf487aec34af497257f815f02e6e45b3bfba0a029cdd6353a278767117cd49`.

This falsifies formatting as the main cause of the weak FP16 score on this
cohort. No unseen holdout will be spent against this inadequate control design.
The packed representation remains a proven capacity and boot breakthrough with
strong teacher-forced relative preservation, but it has not passed absolute
semantic quality. The next quality gate must use a larger independently sourced
or deterministically constructed frozen benchmark on which FP16 first clears a
declared competence threshold; INT8 evaluation may begin only after that control
condition is met.

### Native Metal INT4 direct-path sweep (2026-09-08)

A native Metal INT4 sweep tested group sizes 32, 64 and 128 on the same real
layer-16 eight-expert route used by the successful INT8 mechanism gate. Against
FP16, the three representations reduced logical expert bytes by 68.75%, 71.875%
and 73.4375%, while improving median resident expert calculation by 34.83%,
36.04% and 36.70%. The group-32 condition was the best-quality INT4 result, but
its maximum layer-output error was 0.0159302 versus 0.00299072 for INT8: 5.33
times larger and above the predeclared four-times-INT8 ceiling. Group 64 and 128
were worse at 0.0227661 and 0.0281067.

The result is `STOP_INT4_DIRECT_PATH`; canonical report SHA-256:
`1f6a3b60c40fe351e635140c1ce0a31c4ee4854b65c85c206be8184055955b07`.
This is a real storage and calculation opportunity, but naive affine INT4 did
not earn a full-model build. Do not relax the quality gate or repeat the direct
group-size sweep. Any further four-bit candidate must be activation-aware, use
separate calibration and evaluation activations, and beat this recorded group-32
quality/speed frontier before it can scale.

The first activation-aware INT4 candidate used real Granite layer-16
activations, with commercial-risk and technical-explanation prompts reserved for
calibration and business-planning and cache-diagnosis prompts used only for
evaluation. Calibration selected a 0.98 clipping ratio for 79/80 expert matrices
and 0.95 for one. On the disjoint evaluation activations, normalized RMSE
improved only from 0.12036 to 0.11881 and mean absolute error improved 1.62%,
while maximum error worsened from 0.222656 to 0.310547. Matched INT8 maximum
error was 0.0449219, making activation-aware INT4 6.91 times worse. Median
one-token layer time remained useful at 19.46% faster than FP16, but both quality
requirements failed. The result is `STOP_ACTIVATION_AWARE_INT4_V1`; canonical
report SHA-256:
`2cb2f415902b2f802f769c215ac8a00f3f420c517166b5ee3fc12f335b4d5e78`.

Simple activation-weighted clipping is therefore stopped. It found the same
mild clip almost everywhere, did not materially reduce distributed four-bit
error, and increased the worst error. Do not repeat ratio tuning. Any later
four-bit work must change the transformation itself---for example equivalent
activation/weight rescaling with its runtime cost explicitly charged---and must
first win a new narrow gate before full-model construction.

Equivalent activation/weight rescaling was then tested as a different INT4
transformation. Before quantization, each stored weight channel was multiplied
by a bounded calibration-derived scale and each live activation was divided by
the same scale, preserving the underlying linear calculation. The runtime cost
of both inverse scaling operations and 3.31 MiB of FP16 scale vectors per layer
were charged. The resulting layer representation remained 68.66% smaller than
FP16. Calibration selected the balanced alpha 0.5 for 73/80 matrices.

On the disjoint real evaluation activations, normalized RMSE improved 5.74%
(0.12036 to 0.11346) and mean absolute error improved 5.64%, but maximum error
worsened from 0.222656 to 0.246094, 5.48 times the matched INT8 error. Median
one-token speed improved only 6.93% versus FP16 after charging rescaling, versus
17.22% for naive INT4, and was 12.43% slower than naive INT4. All four declared
gates failed. The result is `STOP_EQUIVALENT_SCALED_INT4_V1`; canonical report
SHA-256:
`6f8a13860f37b9c7a749f8b44941aa9e8ae8016e8a3004547cb3025e7b30e7dd`.

This stops the current INT4 branch: direct affine packing, activation-weighted
clipping and equivalent channel scaling all failed their quality/speed gates.
Do not build a full four-bit library from these methods. Native INT8 remains the
only packed full-model candidate that has crossed its mechanism, capacity, boot
and teacher-forced probability gates. Work returns to optimizing the proven
INT8 runtime and to establishing an adequate absolute semantic benchmark.

### INT8 sparse expert dispatch breakthrough (2026-09-08)

Inspection of the packed INT8 runtime found that one-token MoE decoding routed
tokens to eight experts per layer but still invoked both Metal matrix operations
for all 40 experts. Thirty-two zero-token experts therefore caused 64 empty
Metal calls per layer and 2,048 avoidable calls across 32 layers for every
generated token. A sparse-dispatch candidate omitted only those empty calls;
all selected experts, weights, activations and operation order remained
unchanged.

On 500 balanced trials of the real layer-16 eight-expert route, Metal matrix
calls fell from 80 to 16 per layer-token (80%). Median time fell from 0.900542 ms
to 0.548188 ms, a 39.13% improvement, and nearest-rank p95 fell from 1.97037 ms
to 1.55921 ms, a 20.87% improvement. Candidate and control INT8 layer outputs
were bit-identical with maximum error zero. Every narrow gate passed, producing
`ADVANCE_TO_FULL_MODEL_SPARSE_DISPATCH_GATE`; canonical report SHA-256:
`0a9244267122b65a627805bac04b51a7659416fbb87b543013f56ed240ebdf11`.

This establishes a genuine kernel-dispatch optimization, not a quality trade.
It does not yet establish end-to-end tokens/s because attention, routing, shared
weights and generation orchestration remain unchanged. The next gate must use
the storage-first full model, 64-token multi-family ABBA execution, and require
bit-identical INT8 token identifiers and step logits before promotion.

The first full-model implementation removed empty results from the concatenation
list as well as skipping their Metal calls. In a storage-first four-family,
64-token ABBA run it improved median throughput 13.93% (10.254 to 11.682
tokens/s) and p95 generation time 12.53%, with every token identifier unchanged.
However, one of twelve repeat comparisons produced non-identical step logits
with maximum error 1.17578125; the other eleven comparisons, including the
second candidate run for the same family, were bit-identical. This implementation
is `NOT_PROMOTED`; canonical report SHA-256:
`1facb2f8687be315f6cfb6ba1e4ba94ea2977ce959bce317d0ec62985f041d2b`.

The correction continued to skip all zero-token matrix operations but restored
the original 40-entry empty/non-empty concatenation topology. Its repeated
layer gate remained bit-identical and improved p50 31.43% and p95 15.67%; layer
report SHA-256:
`f93eb681e4167d9f74c3ce9e37ac87bd286247e24472412d525f5f448f416015`.
The unchanged full-model ABBA method was then rerun without prompt-specific
warm-up. Across 1,024 measured generated tokens, control median throughput was
10.144 tokens/s and candidate throughput was 11.264 tokens/s, an 11.04%
improvement. P95 generation time improved 7.88%, from 6.7465 to 6.2150 seconds.
All token identifiers and all step logits were bit-identical in all twelve
comparisons; maximum logit error was zero. Storage-first boot again skipped all
64 FP16 expert tensors. Every gate passed and the result is
`PROMOTE_INT8_SPARSE_DISPATCH`; canonical report SHA-256:
`73a2057a10c8f04f38a41f92bec6ad6a240b8033c958c3ee761bb3570cb43dee`.

Sparse dispatch is now the default promoted packed-INT8 execution path. The
claim remains bounded to the four fixed prompt families and 64-token ABBA
cohort, and exactness is relative to the existing lossy INT8 candidate rather
than FP16. The next validation must replicate on a larger unseen prompt cohort
and longer generation lengths while preserving the same bit-exact INT8 gate.

An eight-family prompt cohort was then frozen in commit `0853d69f` before either
condition ran. The storage-first ABBA replication doubled generation length to
128 tokens and measured 4,096 tokens across 32 runs. Sparse dispatch retained a
10.03% median throughput improvement (10.2175 to 11.2427 tokens/s) and improved
p95 generation time 7.46%. It did not pass integrity. One of 16 candidate runs
first diverged in token identifier at generation step 43 and reached maximum
step-logit error 37.7129; the other candidate repeat for that family was exact.
Separately, one unchanged all-40 baseline repeat retained every token identifier
but had maximum logit error 0.634766. The remaining 22/24 repeat comparisons
were bit-identical. The result is `NOT_PROMOTED`; canonical report SHA-256:
`989ec69183409a6b3c93c7f5d07c2c5538172d2b35ae2ef88d20bd1f221ac287`.

The promoted 64-token four-family boundary remains valid, but exact sparse
dispatch is not established at 128 tokens across the larger cohort. The control
self-drift also proves that Metal repeatability must be separated from
candidate-specific drift. Do not weaken the exact gate or claim the 128-token
result. The next diagnostic is deterministic-mode repetition of the two exposed
families; a successful diagnostic would still require a new full frozen
replication before extending promotion.

PyTorch deterministic algorithms were then enabled for a post-hoc 128-token
ABBA diagnostic restricted to the two exposed families. The setting was
accepted by the runtime but did not make Metal repeatable: all six repeat
comparisons had non-identical tokens and logits, including both closing all-40
baseline runs. Maximum step-logit error was 43.46875. Deterministic control
throughput fell to 7.130 tokens/s from 10.217 in the ordinary eight-family run,
and candidate throughput fell to 7.706 from 11.243. Sparse dispatch improved
median throughput only 8.08%, below its 10% gate, although p95 time improved
14.22%. The diagnostic is `NOT_PROMOTED`; canonical report SHA-256:
`4e50a445d556b02c167f82c00ac62630625bf7d3a1c875d929f7725d671fcf04`.

Stop deterministic-algorithm mode on this MPS stack: it neither provides the
required repeatability nor preserves the promoted performance gain. The
64-token sparse-dispatch promotion remains the exact-within-INT8 boundary.
Longer quality-gated work must report control self-repeatability separately and
must not relabel tolerance or token agreement as bit-exactness.

### Bounded persistent INT8 decode arena (2026-09-08)

The promoted sparse dispatcher still created two concatenation buffers per
layer-token. A bounded candidate preallocated input and output Metal arenas for
eight routed decode assignments and reused them, while all larger prefill
batches fell back to sparse concatenation. The projected 32-layer arena was only
1,310,720 bytes (1.25 MiB), and output remained bit-identical.

The arena did not improve performance. On 500 balanced real-route trials,
median layer time increased from 0.602104 to 0.616250 ms (2.35% slower), while
p95 increased from 1.48804 to 1.63779 ms (10.06% slower). Explicit slice-copy
commands cost more than the allocator/concatenation work they replaced. The
result is `STOP_DECODE_ARENA`; canonical report SHA-256:
`3fb648e8b208c00daef7eebb5833163b66faa4051fc724d5822ef949f0437b25`.

Do not scale or enable the persistent arena. Production defaults allocate no
arena capacity. Sparse concatenation remains the promoted INT8 dispatch path.

### Cached resident weight-view boundary (2026-09-08)

The next candidate retained lightweight references to each expert's already
resident packed-weight and scale views, avoiding repeated attribute lookup,
slicing and reshaping. It duplicated no weight storage and changed no matrix
operation. On 1,000 balanced real-route layer-16 trials it improved median
dispatch time 11.31% (0.607209 to 0.538562 ms) and p95 1.65%, with bit-identical
layer output. The narrow result advanced to the full-model gate; canonical
report SHA-256:
`f29f2f17583ec86d10f7546cf58abb1051d6ed814d9f2ca9df133ecba16c441d`.

The storage-first four-family, 64-token ABBA gate did not reproduce that gain.
With promoted sparse dispatch active in both conditions, median throughput fell
from 10.9462 to 10.8475 tokens/s (0.90% slower), while p95 generation time was
0.05% worse. All token identifiers matched, but the required step-logit
bit-equivalence gate failed with maximum error 0.46875. The result is
`NOT_PROMOTED`; canonical report SHA-256:
`948136d201fd319a36439960410de325df70f201461fdb33d7b33966d8aaa384`.

Stop cached weight views as a production optimization. The layer saving is
swallowed by full-model work and ordinary Metal variation, and neither speed nor
integrity crossed its gate. The promoted sparse dispatcher remains unchanged.

### Reusable empty-view boundary (2026-09-08)

Sparse dispatch preserves 40 concatenation entries for exactness and therefore
still created 64 zero-length tensors per layer-token, or a projected 2,048 per
32-layer model token. A bounded candidate reused two zero-length Metal views
instead. It added no weight bytes and retained the exact concatenation topology.

Across 1,000 balanced real-route layer-16 trials, median time improved 6.81%
(0.609751 to 0.568229 ms) and output was bit-identical. Tail latency failed the
predeclared gate: nearest-rank p95 increased 3.82%, from 1.50133 to 1.55867 ms,
exceeding the allowed 3% regression. The decision is
`STOP_CACHED_EMPTY_VIEWS`; canonical report SHA-256:
`4d8a5ab1d4ac140740bf8d590f7bb0cda0c42d4a03d73e64589880bd71a947eb`.

Do not scale the candidate to the full model or enable it by default. Reducing
Python tensor-object churn can improve the median, but this implementation did
not provide stable tail latency. Sparse dispatch remains unchanged.

### Route-specialized graph-compilation boundary (2026-09-08)

A real packed-INT8 eight-expert block successfully compiled on the local MPS
stack with bit-identical output in a mechanism probe. Granite's production
router cannot compile as one full graph because it converts data-dependent
expert counts to a Python list. The bounded alternative was therefore a small
dictionary of fixed-route compiled graphs with eager fallback.

Three hash-bound route observations supplied 16,256 layer-route samples. They
contained 6,889 unique route sets when counted independently by layer. Although
aggregate exact-repeat fraction was 57.62%, repetition was spread across many
patterns: the single most common graph covered only 3.05% at the median layer,
and the best eight graphs per layer covered only 12.99%. This failed the
predeclared 50% coverage gate. The decision is
`STOP_ROUTE_SPECIALIZED_COMPILE`; canonical report SHA-256:
`0f037de61a3efb5e845294820ccaad11a42088fa567ec5092e839e4d050496d7`.

Do not construct a fixed-route graph cache. Compilation remains promising only
if routing and dispatch can stay dynamic inside one graph, or if a fused Metal
router/expert kernel can consume expert indices directly without Python
`tolist()` and split specialization.

### Fused eight-expert Metal matvec advance (2026-09-08)

The native packed-INT8 operation accepts only two-dimensional inputs and cannot
batch eight selected weights. AION therefore compiled a local Metal SIMD kernel
that receives the eight already-selected expert buffers dynamically and performs
all eight one-token matrix-vector products in one launch. Applied to both expert
projections, it reduced per-layer expert matrix launches from 16 to two (87.5%)
without duplicating weights.

On 1,000 balanced trials of a real layer-16 eight-expert route, the complete
input-projection, SiLU/gate and output-projection block improved from 0.412355 to
0.329604 ms at p50 (20.07%). Nearest-rank p95 improved from 1.35450 to 0.642416
ms (52.57%). Maximum additional error relative to the packed-INT8 control was
0.0000305176 and RMSE was 0.000000307926, below the frozen 0.00075 ceiling. All
gates passed, producing `ADVANCE_FUSED_METAL_MATVEC_TO_MODEL_INTEGRATION`;
canonical report SHA-256:
`18b1ce06a354cb4b1e5c480bf2bb5f84e34ceceafebac5177b2a1aa2ffb2238f`.

This is a major kernel mechanism advance, not yet a full-model speed or quality
claim. Because reduction order differs, it is explicitly outside the bit-exact
track. Next, integrate it only for one-token eight-unique-expert decode, retain
the promoted packed-INT8 path as fallback, and run frozen full-model probability,
token, latency, memory and semantic gates before promotion.

The subsequent storage-first four-family, 64-token ABBA integration did not
pass. Fused execution improved median throughput from 10.9755 to 11.5191
tokens/s (4.95%) and p95 generation time by 5.40%, but missed the frozen 5%
throughput threshold by 0.05 percentage points. More importantly, only two of
four prompt families retained identical token sequences. Both candidate repeats
diverged for technical explanation and business planning, while every closing
sparse-INT8 control repeat remained exact. Maximum accumulated step-logit error
was 38.5405. The result is `NOT_PROMOTED`; canonical report SHA-256:
`fe7f1f63669671ab02509b7c9187bc0b4d7cf5a12975f1b91781f72abb91346b`.

Stop fused Metal matvec v1 at the full-model boundary and keep it disabled by
default. Its narrow numerical error is small, but recurrent autoregressive
execution amplifies changed reduction order. Do not relabel the measured speed
gain as a promotion. A future fused kernel must materially reduce accumulated
error under a new frozen narrow gate before another model-scale run.

### Calibration-selected fused-layer boundary (2026-09-08)

A final bounded attempt tested whether fusion could be restricted to layers that
least amplify its changed reduction order. Four frozen calibration families
measured every layer independently for one decode step. The 16 lowest-sensitivity
layers were frozen as 0, 2--9, 12--14, 17, 22--23 and 29 in a cryptographically
bound plan. Plan SHA-256:
`941f7224eef566f293937306302b3ad76a0280cb22a314f5798ae1a1ad07085c`.

Four disjoint frozen holdout families then ran 64-token ABBA generation. The
candidate improved median throughput 4.80%, from 11.0729 to 11.6042 tokens/s,
but p95 generation time regressed 3.46%. Logistics-planning tokens diverged in
both candidate repeats; the other three families retained token identity but
exceeded the 0.05 logit ceiling. Every closing sparse-INT8 control was exact.
Maximum step-logit error was 30.3359. The result is `NOT_PROMOTED`; canonical
report SHA-256:
`302f634116f56606e0fa6a9babfe8a863f84b3056fd33f60d8ee9ee97af44386`.

Stop sensitivity-selected fusion. Layer selection did not prevent recurrent
error accumulation or tail regression. Do not attempt progressively smaller
post-hoc layer subsets on this holdout. Future fused work must improve arithmetic
agreement at the kernel itself under a new calibration and evaluation design.

### GPU-resident dynamic expert-bank breakthrough (2026-09-08)

The next architecture removed the deeper synchronization boundary rather than
tuning the stopped per-expert fusion. Granite formerly converted GPU expert
counts to a Python list in every layer. AION instead retained top-eight indices
and gates on Metal, addressed one contiguous 40-expert layer bank, executed two
SIMD kernels, and reduced expert outputs on-device.

A formal 1,000-trial real layer-16 gate improved p50 from 1.87092 to 1.18408 ms
(36.71%) and p95 from 2.96121 to 2.21871 ms (25.07%). Maximum additional output
error was 0.0000610352, below the 0.00075 ceiling. Logical bank weight bytes
equalled the source representation. The result advanced to storage layout;
report SHA-256:
`c093f623b2e5f6fe1b142f001a9775c1939352672b3b364269104bcf30f121b4`.

The SD-native build wrote 32 independently hashed banks containing 3,026,452,480
logical bytes (2.8196 GiB) and declares zero runtime duplicate weight bytes.
Manifest canonical SHA-256:
`5ccd5b7d44467bd193e6cb8fc39b95df888a6f285a9d2e68690c685f24e8bb27`.

On the storage-first four-family 64-token ABBA gate, bank-native INT8 achieved
11.2886 tokens/s and dynamic-bank execution achieved 24.4679 tokens/s: a
116.75% median throughput improvement. P95 generation time improved 56.43%,
from 6.0314 to 2.62775 seconds. All four families and both dynamic repeats kept
identical token sequences; all closing native controls were bit-exact. Maximum
step-logit difference was 2.17969, so quality is not yet promoted. All mechanism,
capacity and storage gates passed, producing
`ADVANCE_DYNAMIC_BANK_TO_QUALITY_GATES`; report SHA-256:
`a167b4218c07d1a396093ab65d39ff8c111bad5c69b5af62b29e9372a6e5ece9`.

This is the first model-scale result near the 30-token/s target on the ordinary
18 GB Mac. It is a genuine speed breakthrough but remains a changed-kernel
quality-gated candidate. Direct FP16 teacher-forced probability and frozen
semantic validation are required before runtime promotion.

Those quality gates now pass. Incremental teacher forcing compared FP16,
bank-native INT8 and dynamic-bank INT8 on the same 256 frozen positions. Native
INT8 retained 97.66% FP16 top-one agreement; dynamic banking retained 97.27%,
within 0.4 percentage points. Dynamic top-five overlap was 95.86%, mean KL was
0.003687 nats and additional FP16-token NLL was 0.008386 nats. All relative
quality gates passed, while dynamic execution reduced incremental teacher time
55.76%. Decision: `ADVANCE_DYNAMIC_BANK_TO_FROZEN_SEMANTIC_GATE`; report SHA-256:
`50bfc1e9928cfac76236f65f9ba3b432ca8dac4c52aea7e4cd169d2b078a0204`.

On the previously frozen twelve-case semantic suite, bank-native and dynamic
banking produced identical answers in all 12 cases and both achieved 7/12
correct. Every answer was parseable. Dynamic throughput improved from 6.2627 to
9.4227 generated tokens/s (50.46%) on these short tasks. Every declared gate
passed, producing `PROMOTE_DYNAMIC_BANK_WITHIN_VALIDATED_BOUNDARY`; canonical
report SHA-256:
`225b5fef106cf01f201adaef53df4b56b32b4ad262fcb4149b558083a7ed021a`.

The promoted claim is bounded: AION has demonstrated a 2.8196 GiB SD-native
Granite expert bank running at 24.47 tokens/s on four 64-token families, with
unchanged token sequences, strong FP16-relative probability preservation and
complete answer preservation on the frozen semantic suite. The suite's absolute
7/12 score also proves that this small Granite model is not universally capable;
promotion concerns execution architecture and relative preservation, not a claim
of frontier-model intelligence. Next validation should use unseen longer prompts,
128--256 tokens, repeatability and broader competent-model tasks.

The long-generation expansion gate has now passed. On the previously frozen
eight-family cohort, 128-token ABBA execution measured 4,096 generated tokens.
Dynamic banking sustained 24.8073 tokens/s versus 11.2547 for the native bank
(+120.42%), improved p95 time 55.95%, and repeated exactly on 8/8 families
versus 6/8 for native. Canonical report SHA-256:
`6a9e929ffd2d527437ee1204a382a42655ebb554068452f48d3ef470b87a8933`.

A disjoint eight-domain, 256-token holdout was frozen before execution in commit
`7113f1ad` (manifest SHA-256
`68bad763a3d70ba735779d4d6168114a11a4609183245d9c5c83b627221ac385`).
Across 8,192 generated tokens, dynamic banking sustained 23.9612 tokens/s versus
10.6228 native (+125.56%) and improved p95 time 59.05%. Candidate throughput
dropped only 3.41% from 128 to 256 tokens. Both candidate and native repeated
exactly on 7/8 families. Report SHA-256:
`cfb5823bb2aa58c273769a8430296db3eb40ffd1a61b9a30b212de3773a916b9`.

Only 1/8 opening native and dynamic 256-token free-running sequences was wholly
identical, so exact wording is not claimed. Instead, an extended FP16 teacher
gate forced identical native histories over 2,048 positions. Dynamic FP16
top-one agreement was 98.2422%, slightly above native INT8's 98.1934%; top-five
overlap was 96.7969%, KL 0.002552 nats, NLL delta -0.002641 nats, and teacher
time improved 56.23%. All fixed quality gates passed; report SHA-256:
`bd4e56118cec96351c3ee4db5d0a762590826668b9e5de57a072e1cad08601f4`.

The combined hash-bound result is
`PROMOTE_DYNAMIC_BANK_LONG_GENERATION_BOUNDARY`, canonical SHA-256
`2e772e66d43a28c35cdf6c85b3027a08f29a5e0db1ab6fe39ceac2f3c4569620`.
This promotes sustained approximately 24-token/s quality-gated execution through
256 tokens on this model and Mac. It does not promote bit-exact logits, identical
free-running wording, arbitrary larger models, or direct continuous SD streaming
at the resident-bank rate. The next optimisation target must be selected from a
fresh profile of the 256-token dynamic path; no speed claim should be inferred
before measuring its largest remaining component.

### GPT-OSS 120B complete execution breakthrough (2026-09-09)

The verified 64 GB compressed SD warehouse has advanced beyond isolated expert
tests. A complete layer-0 position-zero block executed RMS-normalised attention,
real Q/K/V and sinks, residuals, the real 128-way router, its selected four
MXFP4 experts and the final residual. Two executions produced identical output
bytes. The route was `[18, 96, 49, 9]`; the report canonical SHA-256 is
`d5d6f3b76ffec3b390f6eaf843904f5c9b46e5c06a68cf4811de9cd9061c1344`.

The next gate reconstructed the model-declared BOS embedding (token 199998),
chained all 36 real attention/MoE layers, applied the final norm and evaluated
all 201,088 vocabulary logits. Two independent executions selected identical
routes at all 36 layers, produced bit-identical final hidden states and logits,
and generated the same argmax token ID 2167. The 256 MiB expert cache faulted
144 layer-addressed experts under bounded memory; the largest native arena was
768 MiB for the vocabulary projection. The canonical report SHA-256 is
`9c286d588d9976a6436204f43ffe02f873cc7070bde322219172ce8f3079b954`.

This promotes feasibility, not speed or quality. Vocabulary staging took 9.469
seconds. The two subsequent layer-chain/vocabulary passes took 36.675 and
34.388 seconds, approximately 0.028 token/s after staging; the first complete
cold path was approximately 46.1 seconds. Expert retrieval accounted for about
20.2 seconds per pass and shared-weight retrieval about 9.1 seconds. The input
was BOS-only and the gate has not yet validated text tokenisation, KV-cache
generation, prompt quality or steady-state throughput. The next work must first
reduce repeated physical weight traffic, then add a real prompt and multi-token
KV cache without weakening repeatability or memory ceilings.

The bounded resident replay gate then staged invariant shared tensors once and
retained the complete observed 144-expert route set under a 3 GiB ceiling. The
first cold-expert pass took 28.328 seconds. The exact replay produced 144/144
expert hits, zero new expert SD reads, and took 11.864 seconds, 65.50% below the
34.388-second non-resident replay. Hidden bytes, logits and token ID remained
exact. Canonical report SHA-256:
`7d840512519f85f87bc3451c15c84d39e0d9dff598c31a4747720e0e20fa8814`.
This is an upper-bound reuse result, not a multi-token speed claim. Proceed to
token-two KV history and measure genuine per-layer route overlap.

That corrected NeoX-rotary K/V gate now passes. The BOS-conditioned sequence was
`199998 -> 2167 -> 679`; two complete executions reproduced all routes, hidden
states, logits and tokens. Token two reused 30/144 experts (20.83%). Opening-run
latency fell from 28.723 to 24.829 seconds and expert retrieval from 20.108 to
16.292 seconds. Canonical SHA-256:
`30b8a1a4a643d01b805e85cd60fb5270e377b27d38e5e94e1764fe651903102a`.
The earlier normal-RoPE diagnostic is preserved as INVALID. Cache-only scaling
is insufficient because 114/144 token-two experts were new. Prioritise overlap
of verified expert I/O with computation and persistent shared tensor arenas.

Four-token cache variants were then tested and stopped. Scan-resistant
compressed caching cut repeat SD traffic from 5.581 GB to 2.371 GB and achieved
389/576 hits, but wall time remained about 108.2 seconds because cached frames
still required decode, verification and rematerialisation. A raw-per-layer plus
compressed-history tier improved the fourth repeat token 13.8%, but regressed
aggregate repeat time 3.57% and opening time materially. Both are
`NOT_PROMOTED`; report hashes are respectively
`76fde04c87cca31eb6c0d225b8aac2a3f62a280e29ca71445d95b40a6790a9cc` and
`e352a3ce69fe59c1badbf316e33f66c48ce65b173ae171ab78a6f28ffdb87ed3`.
Stop cache representation tuning. Build one persistent native arena that
accepts verified frames directly and removes temporary-file and per-layer
process/allocation boundaries before testing longer generation.

That persistent-arena gate now passes for position-zero execution. Profiling
showed that the former exact warm path spent 7.363 seconds writing already
resident expert buffers back to temporary files. A direct read-only native
weight view removed the redundant 1,908,541,440-byte expert restage, and a
single-copy persistent attention/router arena removed the equivalent shared
weight process boundary. Across one opening plus five warm complete 36-layer
passes per variant, every route, hidden byte, logit byte and token remained
exact. Warm median fell from 4.204 to 2.436 seconds (42.05%); p95 fell from
4.380 to 3.345 seconds (23.63%). The final report canonical SHA-256 is
`a0efa41e27578e4ebb4e5c7d91d18d876afbb83778f48dbadbac02ffc4627368`.

Promote this only for exact position-zero/resident replay. It is not a
steady-state generation-rate result. Extend the persistent attention interface
to per-layer K/V state, retain the 3 GiB expert ceiling, and rerun genuine
multi-token sequences with cold/warm separation. The candidate must preserve
every token and step-logit hash while reporting route turnover, physical SD
bytes, median and p95 token latency. Do not extrapolate the approximately
0.411 position-zero evaluations/s median to normal text generation.

The persistent K/V extension also passes on genuine token-two route turnover.
The exact sequence remains `199998 -> 2167 -> 679` across two full runs, with
all routes, hidden arrays and logit arrays repeated exactly. Opening token-two
latency fell from 24.829 to 19.433 seconds (21.73%), raising validated
later-token throughput from about 0.0403 to 0.0515 token/s. Canonical SHA-256:
`38f8e1f62b7d38c8c789735f3c21f97c9b4a67284b98854201dc98bab1611e97`.

The new profile is decisive: token two spends 16.405 of 19.433 seconds
(84.42%) retrieving experts, while only 30/144 expert addresses overlap token
one. Stop attention-only tuning. Measure longer raw-cache working-set growth
and route-transition predictability, then test only a bounded strategy that can
avoid or overlap physical expert reads. Keep exact routing/cache work separate
from any quality-gated reduced-traffic model architecture.

Eight-token exact validation stops the raw-cache convergence hypothesis. The
cumulative route reached 661 layer/expert pairs (about 8.76 GB raw), opening
average throughput was 0.0322 token/s, and 10.198 GB of compressed expert bytes
were read. Preserve the exact report with its LIMITATION sidecar; canonical
SHA-256:
`d99a00851fc1fa332a3e1e9537932efd1970aa297acf51d9a24dabdd8ac20884`.
Do not increase the cache above the locked 3 GiB ceiling or claim that longer
generation naturally becomes resident.

The direct packed Metal probe is also stopped for single-token experts. Metal
supports the MXFP4 graph, but its 0.514 ms warm median was 2.31 times the
0.223 ms CPU median, and its output was not bitwise equal (relative L2
0.006230). The argmax agreed, so only a future fused or multi-token batched
quality-gated experiment remains justified. Canonical SHA-256:
`9db1e300d30d571fcea9e5915fc2b81e2084465b637f0859108ba068cc75674f`.

That batched Metal follow-up has a real crossover. One resident real expert
remained slower on Metal through batch eight, but batch 16 was 1.85x faster
than CPU and batch 32 was 3.06x faster. Metal reached 27,993 expert-activation
calculations/s at batch 32; relative L2 stayed about 0.00623 and the compared
argmax agreed. Decision: `ADVANCE_BATCHED_METAL`; canonical SHA-256:
`53fc40a6a12c8eb7fb4a80f2a6f45874fbf8c68770832fca9ba5d8d92c5314dc`.

Next build a real-route grouped batch gate, not a repeated-expert benchmark.
Use an already-installed small model only as a draft source, group 120B
candidate activations by layer/expert, and measure unique expert SD reads,
Metal batch occupancy, accepted draft tokens, end-to-end latency and quality.
Stop if real route diversity prevents batches large enough to cross the Metal
threshold. Do not report expert activations/s as generated tokens/s.

The real-route feasibility gate stops that unconstrained batch integration
before expensive implementation. Across eight exact tokens, 1,152 routed
activations occupy 661 unique layer/expert pairs (mean batch 1.743, maximum
eight); no real group reaches the batch-16 Metal crossover. Perfect grouping
would save 42.64% of compressed bytes. A first-four-token dictionary with six
experts per layer fits in 2.863 GB but covers only 30.90% of the final four
tokens. Fixed dictionaries of 8--16 experts exceed 3 GiB and still cover less
than half. Decision: `STOP_UNCONSTRAINED_BATCHED_METAL` and stop the naive
fixed dictionary. Canonical SHA-256:
`7b365998ba18e978346692254cd09351e858db0147ced625fad9cfe5d555c766`.

The next permitted mechanism gate is a separately labelled changed-model
study of shared expert structure or route concentration. First measure
cross-expert functional redundancy on real packed weights using bounded random
projections; do not train or inject new weights. Advance only if a compact
basis predicts held-out expert responses at a predeclared error while reducing
resident/SD bytes by at least one order of magnitude. Any later trained
subnetwork requires explicit authorization and frozen semantic evaluation.

The bounded cross-expert functional-basis gate has now falsified that final
no-training compression hypothesis. On all 128 real layer-zero experts, rank
12 met the nominal 10.67x representation target but produced 0.5890 held-out
relative L2 error against a maximum of 0.05. Even rank 64 retained 0.4001 error
for only 2x reduction. Decision: `STOP_SHARED_EXPERT_BASIS`; canonical SHA-256:
`57f565c6b77228ee642f7e0980321949e4ccb9bcd0338489290aabbb8061ae43`.

Do not repeat exact cache growth, naive route batching, fixed dictionaries,
single-token Metal, or untrained shared-basis work. The unrestricted 120B path
remains an exact selective depth/verification tier at 0.0515 genuine token/s.
The next stage is the heterogeneous completed-task architecture: use the
promoted resident small-model path for interactive generation, escalate only
ambiguous or policy-critical cases to 120B, and measure end-to-end successful
tasks/hour, user latency, escalation rate and frozen quality. Keep the
approximately 24 token/s promoted resident result separate from the roughly
40 token/s bounded hybrid evidence and from the 120B rate.

The missing real-text bridge is now promoted. Header-only sparse GGUF shells
gave the installed tokenizer access to the complete 201,088-token vocabulary
using 13,025,280 physical bytes instead of reconstructing 62,841,713,344
logical model bytes. `Hello from AION` tokenized as `[13225, 591, 355, 2044]`;
all four tokens were teacher-forced through the custom 36-layer engine twice
with KV history. Routes, hidden states and logits repeated exactly, and token
5913 decoded as `etwork`. The passes took 79.819 s and 88.744 s and read 5.723
GB and 5.331 GB of compressed experts respectively. This is
`PROMOTE_PROMPT_BRIDGE`, not a quality or speed promotion. Receipt canonical
SHA-256:
`ec16405dd2641eb352798baaac2c5aa82723d2e6e30928730a21c7c1f8e3bc99`.

Next apply the model-declared Harmony chat template using the same sparse
vocabulary shell, execute the smallest meaningful user message, and decode a
short response. Retain exact repeated routes/logits, the 3 GiB ceiling and
separate prompt-prefill versus continuation timing. Do not route business work
to 120B until this functional quality gate passes.

The minimal Harmony gate now passes. The seven-token model-declared template
for `Hi` was teacher-forced through all 36 layers, after which the engine
autonomously generated `[200005, 35644, 200008]`, decoded as
`<|channel|>analysis<|message|>`. Both complete nine-position passes had exact
response tokens, routes, hidden arrays and logits. Passes took 241.381 s and
412.017 s, reading 9.605 GB and 9.161 GB of compressed experts; the latter
contains a 232.228 s pressure outlier and is not throughput evidence. Status:
`PROMOTE_HARMONY_RESPONSE_HEADER`; receipt canonical SHA-256:
`f2a39370083fa15a91fbab48f238b73eee27618605fb533b7fa844540760cc9e`.

Next generate the first ordinary-language token after this exact Harmony
header, then the shortest terminated response that can be evaluated for basic
coherence. Keep the response structure and quality claim separate from speed.
Once usable text passes, integrate 120B only as a selective depth tier in the
heterogeneous completed-task gate.

### Exact 120B route-cartridge falsification and quality-track pivot (2026-09-10)

The proposed 6--10 GiB exact resident route cartridge was tested before full
integration against three independent, bitwise-repeatable GPT-OSS 120B route
families. Each family used its first half as the only permitted training prefix
and its remaining tokens as held-out expert demand. Separate leave-one-family-
out measurements tested cross-family transfer. The calculation used the exact
raw and compressed byte lengths from the `COMPLETE_VERIFIED` SD warehouse.

The predeclared gate required at least 90% held-out route coverage for every
family, which is the minimum needed for a tenfold reduction in expert faults.
It failed. Within-family coverage ranged from 30.2083% to 66.1111%; the best
minimum coverage across 6, 8 and 10 GiB was 30.2083%. Cross-family minimum
coverage remained below 47%. More capacity did not repair prefix holdout because
the additional required experts had never occurred in the observed prefix.
Decision: `STOP_EXACT_ROUTE_CARTRIDGE`. Canonical report SHA-256:
`295232993424e95c44cac975933210dd5bbc3883dbc39cee30099ec21711df4c`.
The identical report is preserved on the mounted SD evidence volume; stored-file
SHA-256: `d76d9ab5d5d43539b494516ced869427f3c58008916670da0c2e47e9e690b99d`.

Do not integrate a family-prefix exact cartridge or enlarge its cache. The exact
120B control remains 0.0515 genuine token/s. The only remaining route to the
tens-of-tokens/s target on this hardware is a separately labelled changed-model
track: constrain each layer to a bounded pool of original resident GPT-OSS
experts, retain the original attention/backbone and router scoring, and select
the top four only within that pool. Freeze the evaluation set and baseline before
testing it. Report semantic quality, probability divergence, memory, TTFT and
genuine generation speed; never describe the constrained subnetwork as exact
full-model execution. In parallel, move the now-resident shared attention path
to a persistent Metal implementation, because the existing approximately
2.4-second resident evaluation boundary cannot reach 30 token/s even after SD
faults are removed.

### Adaptive 120B quality-track working set and persistent-output result (2026-09-10)

Uniform 16- and 20-expert-per-layer changed-model pools eliminated continuation
faults but damaged Harmony response structure and are `NOT_PROMOTED`. A
variable-width 10 GiB pool was then built by retaining every expert required by
the complete seven-token prompt prefix and using remaining capacity for the
highest observed value-per-byte entries. It contains 810 layer/expert entries,
10,735,545,600 raw resident bytes, and 15--46 experts per layer. One-time SD
activation took about 114 seconds. Timed continuation then recorded zero faults,
zero evictions and zero compressed SD bytes read.

A persistent 768 MiB vocabulary-output arena removed repeated process creation
and approximately 615 MB weight access per position. An unrestricted BOS gate
preserved final hidden bytes, logits and token bit-for-bit. Within the adaptive
candidate, every token and logit hash also remained unchanged. The initial
17-position candidate reached 2.8363 and 4.3807 token/s versus matched
unrestricted control rates of 0.07679 and 0.07754 token/s: 36.934x and 56.496x
faster respectively.

Six-thread tuning was subsequently replicated over four 24-position passes.
All routes, hidden states, logits and tokens repeated exactly within the
candidate. After the first warm-up pass, continuation rates were 4.9671,
5.1954 and 5.3528 token/s; median 5.1954 token/s. This is a real later-token
result for a GPT-OSS 120B-derived constrained subnetwork using only original
weights. It is not bit-exact unrestricted GPT-OSS 120B and semantic quality has
not passed a broad frozen corpus. Decision: `ADVANCE_BROADER_QUALITY_GATE`.

Four-way concurrent expert calculation passed an isolated exact BOS gate but
regressed sustained continuation to 1.7735 and 2.2655 token/s because of CPU and
memory-bandwidth contention. Decision: `STOP_SUSTAINED_PARALLEL_EXPERTS`.

Compact evidence canonical SHA-256:
`4b9cce1d391c1bf09b415202cf390a2f13c9ba68b43b7675dbb6614cc514de09`.
Identical local/SD file SHA-256:
`5f7da76b3cdd33fd04fdc82f7e747fcc8e6b32cf43ffe6ad01fe1006d5947004`.
Next freeze and execute representative blinded prompts against the unrestricted
reference. Do not promote the pool on the minimal `Hi` prompt. If quality holds,
attack the now-dominant native MoE stage with fused packed kernels; otherwise
revise pool construction under the same capacity and quality gates.

### Exact-prefill / bounded-continuation breakthrough (2026-09-10)

The first frozen held-out arithmetic gate falsified constraining prompt and
response together: the universal pool changed `23` to `2?` and did not reach
the correct answer within 33 generated positions. The full 15-position prompt
itself touched 1,005 layer/expert addresses (12.405 GiB raw), exceeding the
10 GiB resident budget. Preserve this failure; do not claim the universal pool
as quality-promoted.

The runtime was changed so prompt positions retain unrestricted exact 120B
routing, followed by a prompt/response-boundary rehydration of a request-derived
10 GiB original-weight pool. On `What is 17 multiplied by 23?`, both 15-position
prompt passes matched unrestricted token IDs, hidden arrays and logits
bit-for-bit. Both candidate continuations repeated exactly and produced
`17*23 = 391`. The 33-position response phases reached 3.0707 and 2.7253 token/s
versus 0.07213 and 0.07207 token/s for the matched unrestricted reference:
42.571x and 37.813x faster. Post-rehydration expert loading across each whole
response was only 12.6 ms and 19.1 ms.

Status: `PASSED_NARROW_ARITHMETIC`, not general quality promotion. Initial pool
activation remained 113.6 seconds and boundary repair remained 61.6 seconds,
reading 5.58 GB compressed per repair. The next target is TTFT: overlap
request-pool construction/rehydration with exact prompt computation, then run
the already-frozen explanation, extraction and business-diagnosis families.
Do not trade away exact prompt semantics to improve TTFT.

Canonical summary SHA-256:
`ca807decf327196d3fd1ece56012fc5fc3fc3c1a26701b4c5dd94885084cccdc`.
Identical local/SD file SHA-256:
`799e66834c4a724ac26f9ab49bf706cbda2dd7d25c27133c1ef14012793329e6`.

### Protected response workbench and 8 GiB quality frontier (2026-09-10)

The 61.6-second post-prompt repair was eliminated by pinning the response pool
and making exact-prefill misses transient. Exact prompt experts are still read,
verified and calculated, but cannot evict response experts. The boundary fell
to 0.315--0.575 ms with zero faults, reads or evictions and the complete correct
candidate remained bit-for-bit unchanged. Continuation reached 3.8144 and
3.1990 token/s. Promote the protected-workbench mechanism.

Incremental admission retained pool experts while exact prefill naturally
requested them and reduced the first boundary fill to 26 experts / 330 MB /
4.16 seconds. Cold first-response readiness remained 161.6 seconds because the
same unique SD bytes still had to arrive. Retain it for warm-request study but
do not claim a cold-TTFT win.

The protected capacity sweep established a narrow quality frontier. Six GiB
reached 7.3975/7.7451 token/s and seven GiB reached 6.4707/7.8199 token/s, but
neither produced 391 in the unchanged 33-position gate. A longer six-GiB
diagnostic also failed. Eight GiB produced `17*23 = 391` at 5.7792 and 7.5425
token/s, 80.12x and 104.65x faster than paired unrestricted response rates.
Ten GiB remained correct but slower at 3.8144/3.1990 token/s. Decision:
`PROMOTE_NARROW_8G_FRONTIER`; do not generalize it beyond this arithmetic task.

Capacity-frontier canonical SHA-256:
`51bfd50c3a419aff439831b51964404d6a71d1e5efd3ec5d8107aeef82bcc4d8`.
Identical local/SD file SHA-256:
`e79acafb405462858bb842caa5b2adb5ef807b84cafbd418bf4234a3e904f059`.

Next execute the frozen extraction, explanation and business-diagnosis families
using exact prefill and protected request-specific pools. In parallel, isolate
why resident MXFP4 route compute is 8--10x slower under a large pool than in the
hot microgate; test fused four-expert Metal/CPU kernels only against exact
candidate outputs and measured memory pressure. The primary product metric is
time to correct answer, with response token/s and TTFT reported separately.

### Exact protected core and adaptive exception halo (2026-09-10)

The frozen extraction family falsified static constrained-pool generalisation.
Eight- and ten-GiB candidates were internally bitwise repeatable and fast, but
both corrupted `EUR 287.50` and repeated partial text. Decisions:
`STOP_STATIC_EXTRACTION_POOL_8G` and `STOP_STATIC_EXTRACTION_POOL_10G`.

The router was therefore restored to unrestricted top-four selection at every
position. A hash-bound resident core is protected, while winners outside the
core are fetched exactly from the verified SD warehouse. With an eight-GiB
core and no exception space, only 45/792 response layer-routes were completely
resident and response speed improved only from 0.07103--0.07106 to
0.07980--0.08027 token/s.

Adding a separate two-GiB ordinary LRU exception halo reduced faults to
2,465--2,506 and produced 0.10064--0.10090 token/s, a paired 41.63--42.05%
improvement. Rebalancing the same ten-GiB total budget to a six-GiB protected
core plus four-GiB halo produced 0.10282--0.10345 token/s, a paired
44.70--45.64% improvement. Every route, token, hidden-state hash and logit hash
matched the separately frozen unrestricted 48-position control on both passes.
Decision: `PROMOTE_EXACT_CORE_HALO_MECHANISM`. The 6+4 split is only a marginal
frontier over 8+2, not a separate order-of-magnitude result.

Canonical summary SHA-256:
`f8dd3ed93e6132fe8159d5422007aeda170d30771ee445154832cd2cf0026d7e`.
Identical local/SD file SHA-256:
`193af2360b9d36c51e20610267a0cae2106adaf88f5567d484dab0189fae42e3`.
The two immutable halo receipts inherited inaccurate transient-only wording.
Correction sidecar local/SD SHA-256:
`ac2b804b3496c45681964059258ebef8d5d5c4faee74616a0cfd256551c34fe9`.
The correction changes claim text only, not measured evidence.

Next stop global core/halo ratio sweeps. Derive per-layer miss and reuse-distance
profiles from the exact traces, allocate the halo per layer under the same
total ceiling, and scale only if exact fault count and response time improve.
In parallel, implement a fused four-expert MXFP4 route kernel against real
resident pool weights; the naive isolated single-expert Metal probe remains
stopped. Continue to separate TTFT from response speed and do not describe
0.103 token/s as approaching the 30-token/s target.

Offline per-layer halo analysis found only a modest same-trace ceiling. Under
the 6+4 GiB split, uniform per-layer quotas predicted 2,555 faults / 32.423 GB
compressed traffic, while a trace-fitted optimum predicted 2,468 faults /
31.317 GB: only 3.4% fewer bytes and 87 fewer faults. Do not spend a full long
runtime gate on this fitted allocation yet. Prioritize fused real four-expert
MXFP4 execution; revisit per-layer quotas only with a held-out allocation rule.
Analysis canonical SHA-256:
`61b38d7c794ae7ee05fa191193ed37ac4a9a591039ae02fb1cb5262b70743bd3`.
Identical local/SD file SHA-256:
`e9ad17df819676f81b36cf1339e1dc477045e52f354aade43cfd61de2faca75f`.

### Native compute and host-flow gates (2026-09-10)

A real four-expert GPT-OSS route was evaluated as one fused GGML Metal graph.
It was not a win: CPU p50 was 0.6928 ms and warm Metal p50 was 1.9372 ms,
so Metal was 2.80x slower. Relative L2 error was 0.00749 and the output was
not bitwise equal. Decision: `NOT_PROMOTED`; do not integrate this single-token
Metal graph or repeat it without a materially different packed kernel.

Reusing the exact CPU GGML graph metadata preserved bitwise output but improved
median wall time by only 1.71% (0.7116 to 0.6996 ms), below the 10% gate.
Decision: `NOT_PROMOTED`; graph construction is not the material resident cost.

Removing the remaining per-layer host-file writes and reads was material. On a
paired, exact BOS position-zero resident replay, warm wall time fell from
0.40756 s to 0.06531 s, a 6.240x speedup. The selected experts, final hidden
state, logits and token 2167 matched exactly. Decision:
`PROMOTE_EXACT_RESIDENT_FLOW`. This is a resident position-zero execution rate,
not sustained generation throughput.

The required genuine two-token KV check also passed repeatability and produced
tokens 2167 and 679, but its warm second token still took 16.080 s under the
3 GiB cache. The in-memory change therefore removes host orchestration overhead
when weights are resident but does not solve SD expert faults. Apply it to the
exact 6+4 GiB core/halo runner next, while retaining the measured conclusion
that expert movement remains the primary path to higher unrestricted 120B
generation speed.

Bound-summary canonical SHA-256:
`25768d87a531e5c803a6869a52f7be6c626af498fa4a00d42f513e4d7cdd0e3`.
Identical local/SD file SHA-256:
`62b33c5b82114372c1e9d289e41761a3af38ac8bd61e550f0236c22de7c1552e`.

The full 48-position scale gate then combined the in-memory flow with the exact
6 GiB core + 4 GiB halo. It matched the frozen unrestricted control at every
position, route, token, hidden-state hash and logit hash on both passes. It did
not improve SD-bound generation: response rates were 0.10313 and 0.10181
token/s, versus 0.10282 and 0.10345 token/s for the file-flow candidate. Paired
changes were +0.30% and -1.59%. Decision:
`NOT_PROMOTED_FOR_SD_BOUND_GENERATION`. Retain in-memory flow for resident
execution but stop expecting host-file removal to improve the exact core/halo
path. The identical fault/byte counts and opposite timing movement confirm
that SD traffic dominates this cohort.

Scale-summary canonical SHA-256:
`2ae716234c238aca912dd6bbba766975bcf008521968959c35a54c4c5cb4b78e`.
Identical local/SD file SHA-256:
`371f6ac87cc8de68653a4c003e1e6d2eb386e9b859246fd7dd53728511f2b653`.

### Route-local physical-layout microgate (2026-09-10)

A bounded, lossless 402,624,694-byte layer-0 micropack placed each selected
expert's six already-compressed components contiguously. The 32 experts were
selected from a frozen trace and supported 15 complete four-expert routes.
macOS `F_NOCACHE` was enabled and the order was balanced. The candidate reduced
read calls per route from 24 to 4, and every decoded raw component remained
hash-exact. It did not reduce elapsed time: scattered p50/p95 were
106.530/113.041 ms, versus 109.198/115.183 ms route-local. Median speedup was
0.976x. Decision: `NOT_PROMOTED`. On this SD and frame size, six-component seek
count is not the dominant cost; do not build a full duplicate route-local bank.

Gate canonical SHA-256:
`6536c8a70c6d5b20a8ba11bb4b9c10faf15755c6b26849eaae73b68e076c71ba`.
Identical local/SD gate file SHA-256:
`80728464f191e288ddffdf023e40656fb14c5bb5d5261ac332af1dc66b30ccef`.
The bounded pack and manifest remain immutable SD evidence. Next isolate
compressed read time, source/target copies, hashing and zstd decode; advance
only a direct reusable decode-buffer candidate that wins a narrow real-frame
gate before attempting runtime integration.

The direct reusable decode-buffer gate was exact but missed its declared 10%
speed threshold. On one real six-component expert, the current copied decode
path measured 22.871 ms p50; removing the encoded-source copy measured
21.761 ms; additionally reusing all six output buffers measured 20.996 ms.
The final gain was 8.93%, with all raw hashes exact. Decision:
`NOT_PROMOTED`. Do not add buffer-lifetime complexity to the full runtime for
an effect below the narrow gate, especially while SD traffic dominates.
Canonical SHA-256:
`3c2fa7ecf29f4cd902efbce220d7bd67f3bffab78e2ff8f18a84d2f03ef69000`.
Identical local/SD file SHA-256:
`1f5c7746846f076880df60ed486661f469e947b565b02dffcdcfbd52303dc86e`.

Exact-track micro-optimisation has now exhausted three adjacent mechanisms:
host-file flow, route-local layout, and reusable decode buffers. The resident
host-flow win does not transfer under SD faults; layout and decode fail their
narrow gates. Further orders-of-magnitude work must be separately quality-
gated and reduce the number of expert bytes mathematically required per token,
or use exact verified multi-token/task avoidance. It must not be presented as
an exact full-model speedup unless the 120B token/logit sequence is preserved.

### Real-activation expert-omission gate (2026-09-10)

The changed-arithmetic track captured 16 genuine activation/route pairs from
two KV-linked token positions across layers 0, 5, 10, 15, 20, 25, 30 and 35.
The source two-token run remained route-, hidden- and logit-repeatable. Each
captured route was recalculated with four, three, two and one expert, using
both original retained gates and renormalized gates.

No candidate passed. With original gates, top-3 reduced expert bytes only
1.33x yet had p95 layer-output relative L2 error 0.0847 and p95 expert-
contribution error 0.3757. Top-2 offered 2x theoretical byte reduction but
errors rose to 0.1606 and 0.5771. Top-1 offered 4x but errors were 0.2573 and
0.7881. Renormalization did not repair the result. Decision:
`STOP_TOPK_EXPERT_OMISSION`. All four routed experts make material numerical
contributions on real states; do not scale naive expert dropping to a semantic
run.

Canonical SHA-256:
`7ec161947c242517d44c9da5323f39ef8031862627f276fbd441b1d88a9f9488`.
Identical local/SD result file SHA-256:
`f72ca17418f852a7222598fbe2c38141bc54c91c7026a401ff7eded1cfd53423`.
Next test structured activation/weight-block omission only as a quality-gated
mechanism. Because gate mass is distributed and all experts matter, confidence
cannot be inferred from expert rank alone. Any later learned surrogate or
residual expert requires separate explicit training authorization.

The real-activation internal-block gate also failed. Keeping the highest-energy
75% of individual activation values retained a median 99.30% of activation
energy, but could reduce total expert weight traffic by only 1.20x and still
produced p95 layer-output relative L2 error 0.0225. The required 2x traffic
candidate retained 25% of values and produced p95 output/contribution errors
of 0.1963/0.6565. Storage-addressable 32-value blocks were worse: the 2x
candidate retained only 35.87% median activation energy and errors reached
0.4085/1.3675. Decision: `STOP_ACTIVATION_BLOCK_OMISSION`. Do not build a
block-addressable full warehouse for this mechanism.

Canonical SHA-256:
`e8b7b8250ddc550d36dd7676ce0044a184bf76860fe35eee2c65428a28635eec`.
Identical local/SD file SHA-256:
`bfc58e4e5e06d02ba9e8a54c59ef85c78269001c70472e389da5462837c4bfaf`.
Next measure intrinsic MXFP4 zero/repetition structure before proposing any
sparse exact representation. If real packed blocks are not strongly sparse,
stop storage-level sparsification and require a separately authorized learned
surrogate for any further order-of-magnitude model-traffic reduction.

The governed next architecture is specified in
`AION_GLYPH_SHADOW_EXPERT_PROTOCOL.md`. It predicts the combined four-expert
residual from the already-resident layer activation, unrestricted route and
gates, then either accepts under a calibrated error bound or falls back to the
unchanged exact warehouse. It is explicitly a changed-arithmetic quality track
and cannot be called exact GPT-OSS 120B. Its mechanism gate requires at least
10x projected traffic reduction, sub-1 ms p50 calculation, held-out residual
relative L2 at most 0.02 p95, and detection of at least 99.9% of violations.
No personal/customer data may be collected. The protocol, capture schema,
split and evaluator may be built now; training or injecting a derived cartridge
requires separate explicit user authorization.

The dataset split builder is now operational. It hash-verified the existing 16
real numerical activation captures and correctly returned
`INSUFFICIENT_FAMILY_COVERAGE`: there is only one family, versus the locked
minimum of four disjoint train/calibration/numerical-holdout/semantic-holdout
families. No training is authorized and no holdout claim may use this seed
corpus alone. Manifest canonical SHA-256:
`d9896a4188b9a8d4ca1ff1af84cbd7904a5775acb562f26fdc5520d35f2768a8`.
Identical local/SD file SHA-256:
`51332ef74510ebe10873bbf6df0398a210f191d5d60cb48eeb021b9f112a4fa2`.

An exact draft/verify upper bound was also completed before implementation.
The captured eight-token route allows at most 42.64% perfect grouping byte
reduction. Even assuming 100% draft acceptance, zero draft/scheduling cost,
perfect grouping and zero non-I/O work, applying that reduction to the best
exact 0.10345 token/s rate yields only 0.18034 token/s. Decision:
`STOP_EXACT_DRAFT_AS_BREAKTHROUGH_PATH`. It may offer an incremental throughput
improvement in another product context, but cannot reach even 1 token/s here
and must not consume the breakthrough programme.

Upper-bound canonical SHA-256:
`778585165210d14bbc92f20118f3f054e028c8b6872054b0ad1006bc3c5d7c34`.
Identical local/SD file SHA-256:
`0cdd982fcec9141aeacc03682b5c4de7fe9e8b34cf037db6186e5d4be3825e84`.

The intrinsic MXFP4 structure gate then sampled 16 routed layer/expert
addresses and all three packed matrices. Median signed-zero code content was
12.19% (range 11.36--18.63%), no sampled 32-value block was entirely zero, and
the unique-block fraction was 1.0 throughout. Median packed-value entropy was
3.864 of 4 bits. Decision: `STOP_EXACT_MXFP4_SPARSIFICATION`. The real expert
weights are dense, high-entropy and non-repetitive; lossless sparse or
dictionary storage cannot provide the required multiple-times traffic
reduction.

Canonical SHA-256:
`cc90b6456b0ff5549691331d3cd383418b50e80297f125ebad11f2cc2459a692`.
Identical local/SD file SHA-256:
`da3819abf1925cfb112bb77f320d728d73d4c8df513b8e59638b5e3bd9bab061`.
This closes naive whole-expert omission, activation-block omission and exact
packed-weight sparsification. The next order-of-magnitude model path requires
a learned/distilled representation or another changed architecture and may not
start without explicit authorization to train or inject derived weights.

### Shadow target capture and exact-fallback evaluator readiness (2026-09-10)

The governed readiness path now records a complete hash-bound target row from
the live 120B runner: post-attention FFN input, router input, unrestricted route
and gates, complete layer output, and the F32 observable combined four-expert
residual. Metadata binds the warehouse manifest, both verified source-model
shards, implementation and precision. Prompt text and personal/customer data
are explicitly excluded.

The manifest builder now requires every row to carry a verified residual target
in addition to four family-disjoint splits. A frozen evaluator verifies target,
prediction and confidence-receipt hashes, measures held-out relative L2 error,
applies a predeclared confidence rejection threshold and models fallback to the
unchanged exact SD route. A focused synthetic readiness test passed and confirms
that two perfect holdout predictions still fail the 10x traffic gate; a tiny
oracle corpus therefore cannot be promoted. The existing 16-row v1 corpus was
re-audited as `INSUFFICIENT_FAMILY_COVERAGE` with zero target-bearing rows.
Readiness canonical SHA-256:
`423eeb80778e8762e7db8d0c9543bc23154f29c14d034a54d5116efd7e115403`.
Local result file SHA-256:
`a8cd38dda08cb49aa5f3ebd83e71fb661f4bef6b948e0919a7468fdda0109a2e`.
No Shadow Expert weights have been trained or injected; explicit authorization
remains required before that boundary.

The v2 capture was then validated on the real 120B execution path. One BOS
family traversed all 36 layers twice; routes, final hidden state and logits were
bitwise repeatable. Layers 0, 12, 24 and 35 yielded 4/4 hash-verified target
rows, each with the complete F32 layer output and combined residual. The
capture-run canonical SHA-256 is
`cf3aebf7fc00f6cd3e6b6e724923802e676f8ea04191c0390db00f17eeb1205a`;
identical local/SD file SHA-256 is
`5f1f8e097d522c04cf77b6f8e71286e3a606a450a8e29ee559f1caadd9282789`.
The target-manifest canonical SHA-256 is
`da0cfd31c517b1269f5f15487c6cfa0f7e01fadd6ca69052bc3522bd76285a54`;
identical local/SD file SHA-256 is
`bc7ccb7700370cbcf6babcabc3aea0582d5eec139ce778271938f9b1458fccfe`.
Its status remains `INSUFFICIENT_FAMILY_COVERAGE`: this proves the capture
plumbing against genuine 120B arithmetic but makes no learning or quality claim.

Three further synthetic token families then traversed the complete 36-layer
runtime twice each. All three were route-, hidden-state- and logit-bitwise
repeatable. The combined frozen manifest has four family-disjoint groups,
16/16 verified target rows, no cross-family activation-hash collision, and is
`READY_FOR_AUTHORIZED_TRAINING` with `training_authorized: false`. Manifest
canonical SHA-256:
`6564bc3fef79e40528046a7c05af104791eb24a0663b14e0349d9785d49b9b27`.
Identical local/SD file SHA-256:
`fd0279e8f3eb9887470205e266183a8531bd116f1c89f2a5f21054606010394b`.

The frozen evaluator was exercised with non-trained deterministic controls.
An oracle candidate achieved zero error but remained `MECHANISM_GATE_FAILED`:
eight holdout observations prove only an 8x conservative traffic bound, below
the locked 10x minimum. A false-high-confidence zero candidate produced 1.0
relative L2 error, eight violations and zero violation capture, and also failed.
Oracle/zero evaluation canonicals are respectively
`a4216d7064eed72f5c8a6ef057645adc62bc3a0ec2dc429794851a142da57aa6`
and `1521922cf33b7988583eab72df605f03a202ef54b67edc0e1f22707387920b7b`.
Identical local/SD file hashes are respectively
`1fe5eccd38a51f2c1599705715981e2e40aa748223da293923a03d02dc121387`
and `a6025a95d163db85343afbf542ce469ad4428422bf6f0df4b427afa5a2d4c404`.
This validates refusal logic, not model quality. No learning occurred.

The evidence-volume readiness gate was then closed without training. All four
families were recaptured at 12 distributed layers, producing 48/48 verified
targets and 24 holdout observations. Two complete passes per family remained
route-, final-hidden- and logit-bitwise repeatable. The expanded manifest has no
cross-family activation collision. Canonical SHA-256:
`f91d9c8c1e9f4db2ffae76e2dcecf2b2500e6668ec8ecd38d79f75d0d35b37e3`.
Identical local/SD file SHA-256:
`688192f92c0c18d9a19070d38976c48e3f58b6c31364cd11cb74d2173fabc07f`.

The evaluator now requires at least ten holdout observations, emits precise
failure reasons, and labels deterministic controls so they cannot be confused
with deployable candidates. The 24-row oracle achieved zero error and passed
only `CONTROL_GATE_PASSED`, demonstrating a conservative 24x bound. The zero
control failed with relative L2 1.0 at p50/p95/max, 24 violations and zero
capture. Oracle/zero canonical SHA-256 values are
`896bbb66c468505498b4d89e119c3be67345370aa87f60cec9dc70c7335e1c02`
and `9a91c59077fe705fe32cf2e9339b14c9ff050d7230e2da6bc9e2c5b805468999`;
identical local/SD files are
`b2221d5d4dcc3fa77c08c6ab344429539c8c967d826ca6c262c691ed19ac29f6`
and `588bd891127afb46c6531e9ddb6cd91022c0d4ed798674bb9fb0e61b04443632`.
This completes the authorized readiness scope. Training/injection remains a
separate explicit user decision.

### Authorized staged Shadow Expert search (2026-09-10)

The user explicitly authorized local training from the frozen model-generated
numerical corpus, still excluding prompt text and personal/customer data. The
10x traffic target remains the breakthrough rung, but verified intermediate
wins may now advance as explicitly experimental: greater than 1.10x, at least
2x, then at least 10x. Numerical accuracy, confidence violation capture, exact
fallback and honest changed-arithmetic labelling were not relaxed.

The first authorized candidate was a 2,860-byte per-layer affine/polynomial
cartridge. It calculated in 0.0182 ms p50 and 0.0186 ms p95, proving computation
and cartridge size would be negligible. Accuracy decisively failed: no layer
passed calibration, numerical/semantic holdout p95 relative L2 errors were
20.02/21.41, and traffic reduction remained 1.0x. Decision:
`STOP_AFFINE_BASELINE`. Report canonical SHA-256:
`c7ff59cb0b96bdb3ae3eeea67d5536f5c08f251113a9c81b8dbf5aaee0c1ee32`.
Identical local/SD file SHA-256:
`e443ba15b37dbfd273c0801ccb43b3314339de7e161dcf5f4659e51a6423aea5`.
The next justified candidate is nonlinear and low-rank, after collecting enough
additional training trajectories; repeating affine variants is stopped.

### Nonlinear and route-aware Shadow Expert results (2026-09-10)

Calibration and both holdout families were frozen while four new first-token
families and two genuine eight-token KV trajectories were added only to
training. Each long capture repeated routes, final hidden state and logits
bitwise. The explicit manifest now binds 288 targets and 21 training states per
captured layer. Canonical/file SHA-256:
`a2dfe446585f12466dba6decd210e195974759872410516e48f2240c960d5f3a` /
`03b9384eafebd632bb7bb784454db2444918af8d28e1864d97b4736923e1a1e8`.

Nonlinear RBF/multikernel models reduced worst holdout p95 from 21.41 to 0.918,
but no layer met the locked error gate. An impossible holdout-target oracle
projection established a lower bound for residual dictionaries: overall
numerical/semantic p95 errors remained 0.663/0.808 even when the oracle chose
the best combination in the full training span. Layers 6 and 9 were exceptions,
with individual oracle errors near 0.015--0.017. Global decision:
`STOP_RESIDUAL_DICTIONARY_SUBSPACE`. Canonical/file SHA-256:
`f997d884eb821774e63004735b761734dd2a49df3f63cdd000f18507e7a53b28` /
`7ffe73a807b4a507b2cadb2707ad257d25e5f0e386af2a64e221a89ea0633c87`.

Encoding unrestricted expert IDs and gates as a route Glyph created the first
narrow near-signal. Layer 6 reached 0.0192 calibration relative L2 and
0.0282/0.0312 on the two frozen holdouts. Candidate calculation was 0.0850 ms
p50 and 0.1070 ms p95. However, held-out p95 still missed 0.02 and skipping one
of twelve measured layer fetches projects only 1.0909x traffic reduction, below
the unchanged >1.10x experimental rung. Decision: `STOP_KERNEL_BASELINE`, not
promoted. Canonical/file SHA-256:
`9f1b12cf4ca4660d9031abd51b2f1124c2b362a16ac7cbc142f0293ac9d153fb` /
`ef31a56cfac110d2fefabbdf1a8fe7e137e47cff26b8fa0a123e3238b37dcfa8`.

Formal route coverage shows why: median closest-route overlap is 2/4, one of 24
holdout rows has zero overlap, and only 8/24 have all four experts seen anywhere
in training. Route-coverage canonical/file SHA-256:
`6f0d2b505b88b3bcb6dff2012d9f253cabc115f1251775edc44233ccca38028c` /
`89b00377375d69e6efbb384fc721fd6d8052ae35e11710eb4e9459727e5cd37a`.
Next collect for missing layer/expert coverage and focus layers 6 and 9; random
corpus expansion and global residual dictionaries are stopped.

### GHX route memory result (2026-09-10)

A bounded GHX-inspired test represented the unrestricted layer-6 route as a
compact gated expert crystal. Two new post-freeze validation token families
were captured; both complete 120B executions repeated routes, final hidden
state and logits bitwise. The candidate was computationally negligible at
0.0190 ms p50, but fresh relative L2 errors were 0.0560 and 0.0736. Its one-layer
traffic projection was only 1.0909x. Decision: `STOP_GHX_ROUTE_CRYSTAL`.
Canonical/file SHA-256:
`562ed9cad0fb2c9a3f6fd6bbc0a7531c6a4a4d9e01efca532dc19c8a8ac43b87` /
`207cdb9f1059ed517798a2fc4f0245ba2bdb2411f0d952dc24e2d07df303ea0b`.

The numerical substitute is stopped. The 0.02--0.03 ms prototype-matching
primitive is retained only as a governed selector for a future per-expert
calculator and exact fallback. GHX is not treated as lossless neural-weight
compression. Continue with targeted route coverage and structured low-rank
per-expert modelling at layers 6 and 9.

### Structured per-expert low-rank closure (2026-09-10)

The per-expert candidate used separate gated feature blocks for all 128 experts
and a low-rank output basis, with configuration selected solely by grouped
training cross-validation. It calculated in 0.0305 ms p50 but produced 0.1922
and 0.3463 calibration relative L2 at layers 6 and 9. No layer was accepted;
traffic remained 1.0x. Decision: `STOP_PER_EXPERT_LOW_RANK`. Canonical/file
SHA-256: `4c61233adde48fd804371073e798c818f40f46805200aa0e7a8c05088445a262` /
`246c18e1e558b70d9f5c4f8d725fb72d3428a8b5abb01650b527d0e521a4a2e6`.

This closes small-data additive expert factorization. Preserve the fast GHX
selector, but do not fit another low-capacity residual form to the same corpus.
The next exact-track test is layer-major multi-token verification: draft a
short block with an already-resident small model, then group the exact 120B
positions by layer and expert so each fetched expert serves multiple positions.

### Exact eight-position layer block result (2026-09-10)

Existing exact traces predicted 1.8611x--1.9136x fewer expert loads when eight
positions are processed layer-major. The real SD-backed layer-12 implementation
exceeded that conservative aggregate bound locally: two independent cases cut
32 expert faults to 13 and 16, reduced compressed traffic by 2.4616x and
2.0001x, and improved wall time by 2.4784x and 2.2137x. All 16 outputs were
bitwise identical to their exact captured targets. Peak live expert storage was
212,060,160 bytes. Decision: `ADVANCE_EXACT_BLOCK_RUNTIME`.

Runtime canonical/file SHA-256:
`e22f692a633aa269a4d0280e4db004d95f6466fbc4fb2c26c8f7351558e963f1` /
`af978a55c128973beb5253f507fa2a7f1b615b37aaafb62389515ad891cb2f3e`.
This remains a layer microgate. Build complete causal block attention plus
layer-major MoE, then measure draft acceptance and end-to-end exact generated
tokens per second before making a full-model speed claim.

### Full causal block closure and adaptive active-expert frontier (2026-09-10)

The layer-major candidate was extended through all 36 causal attention/MoE
layers and the complete 201,088-logit output head. Frozen teacher traces supplied
two, four and eight known positions. Every run retained unrestricted routing and
original weights; every hidden-state and logit hash matched bit-for-bit.

The exact mechanism did not transfer its logical-traffic gain to wall time.
Two positions reduced compressed traffic 1.1754x but improved median wall time
only 1.0265x. Four positions reduced traffic 1.3683x but improved wall time only
1.0222x. The exploratory eight-position run reduced traffic 1.8617x but improved
wall time only 1.0383x. macOS page caching already served repeated logical reads
without equivalent physical SD traffic. Decision:
`STOP_EXACT_BLOCK_AS_PRIMARY_SPEED_STRATEGY`. Preserve it as supporting
infrastructure, but do not report the earlier 2.35x layer microgate as a
full-model token-rate gain.

A separately labelled quality track tested fewer original experts only during
continuation after exact unrestricted prefill into the protected 8 GiB request
workbench. Fixed top two reached 10.8786/5.9082 token/s but failed to emit 391
in the frozen window. Fixed top three emitted 391 but repeated the calculation.
A gate-mass-adaptive candidate preserved the original four-expert gate values
instead of renormalizing after omission. At a 0.75 cumulative-mass threshold it
used 1,087 three-expert and 101 two-expert layer decisions per 33-position
response, produced coherent text containing 391, and repeated routes, hidden
states, logits and tokens bitwise. Its four-pass rates were 5.2649, 5.7622,
3.2772 and 8.3831 token/s; post-warmup median was 5.7622 token/s. This does not
beat the promoted narrow four-expert 8 GiB arithmetic control median of 6.6608
token/s, so it is retained for broader quality research but not promoted for
speed.

A 7.5 GiB workbench was structurally impossible because the required frozen
seven-token route prefix alone occupies 7.8505 GiB. A valid 7.9 GiB pool retained
640 layer/expert entries and still emitted 391, but reached only 4.8776 and
3.5381 token/s. Retain the 8 GiB control as the narrow arithmetic frontier.

Compact canonical SHA-256:
`74f4d7ec92b946939a941334ca99a7997a4c17a7dbbd21d10c60569fadb2d806`.
Identical local/SD stored-file SHA-256:
`ce6bde87c72a71020d0e015d583547ffae5b117795cf35ecbfb44d0225288644`.

The immediate frozen extraction gate then stopped semantic generalization. On
`Invoice A-104, total EUR 287.50`, the preserved-mass adaptive candidate was
internally bitwise repeatable and reached 5.1222/5.3437 token/s with only
16.6/24.1 ms total response expert lookup. It retained `A-104` but corrupted
the amount into an incomplete `EUR 287...`; therefore semantic acceptance
failed. Decision: `STOP_ADAPTIVE_075_FOR_EXTRACTION`. Do not lower thresholds
or describe arithmetic correctness as general quality. Runtime/receipt local
and SD hashes are respectively
`a55965c9b935f7d24b30e62018beb3b23ea6106857803d1a9f63dab56eaa7b21` and
`363655c525cf7c327ba82df9db2e93eaf81af97e6d6113c7cd81f782c4aac550`.

The unrestricted extraction trace shows why a simple confidence escape is not
an orders-of-magnitude repair: only 45/792 response layer-routes were wholly in
the pool, median missing unrestricted gate mass was 0.595, and 62.9% of routes
still had at least 0.5 missing mass. A safe exact escape would therefore restore
most SD faults. The next speed work must target resident packed-kernel execution
and a genuinely broader learned/request-family pool, not another lower top-k
threshold on this static extraction workbench.

### Exact L2 access and reusable-route-arena frontier (2026-09-10)

Direct process-lifetime mapping produced a 17.10x exact real-layer microgate
win but regressed complete arithmetic generation to 0.66837 token/s because
page faults moved into native compute. MADV_WILLNEED (0.37269 token/s) and
explicit parallel page touching (0.70108 token/s) also lost. Stop mapped L2 as
a full-model path on this Mac; retain the evidence and diagnostic support.

Bulk sequential reads with one verification epoch per process transferred.
The exact arithmetic warm rate rose from 1.06950 to 1.45591 token/s and the
settled extraction median reached 1.41036 token/s. Every tested token, route,
layer output, hidden state and logit remained exact, with zero settled SD
fallbacks.

A four-slot 50.56 MiB reusable route arena then removed the second Python
component copy while retaining page-resident bulk reads. The zero-fallback real
layer improved 2.610x. At an equal 20 GiB internal-disk L2 ceiling, its settled
arithmetic median was 1.59411 token/s versus 1.38184 for verified bulk copy, a
15.36% arena gain. Against the prior 17 GiB exact control this is a combined
49.05% improvement. Promote for the frozen task-aligned arithmetic session.

Do not generalize this rate to rapid mixed-family switching. Following the
arithmetic run, extraction still incurred 690/230/51 SD fallbacks across three
passes at 20 GiB and its third pass reached 1.22879 token/s. The combined
cross-family working set exceeds this local tier. Next test signed per-family
cartridges or admission forecasting; report cartridge-switch fill time and do
not label an unsettled family as warm.

### Exact demand-admitted family cartridges (2026-09-10)

The signed family-cartridge branch passed its paired live gate. Offline
analysis used two real semantic traces plus six explicitly labelled synthetic
stress traces and selected a 20 GiB layout: 10 GiB shared core, an active
family segment and a 2 GiB exact exception halo. Observed replay coverage was
100%, but this is not an unseen-family claim.

Eager family staging was rejected because arithmetic/extraction switches would
read 14.01/14.45 GiB compressed from SD including their RAM pools. The runtime
instead protects planned L2 frames only after genuine unrestricted demand.
Arithmetic and extraction hostile switches each fetched 311 experts (about
3.67 GiB compressed), after which both settled passes had zero SD fallbacks.
Every token, route, layer output, hidden state and logit remained exact.

Settled continuation medians were 1.62106 token/s arithmetic and 1.59706
token/s extraction. Extraction improved 86.33% over the prior thrashing
mixed-family reusable-arena settled median and 13.24% over its stable bulk-copy
control. Promote the mechanism for exact two-family cache stability. Do not
claim 30--50 token/s or general unseen-family coverage. Next profile stable
internal-L2 delivery versus native compute and advance only the largest real
cost.

The immediate 1.5 GiB durable-L1 hotset extension was then stopped. It admitted
exactly 121 measured hot experts and reduced settled L2 delivery by 28.67%, but
raised resident expert memory from 7.90 to 9.39 GiB. Native expert calculation
slowed enough that settled arithmetic fell from 1.62106 to 1.31965 token/s, an
18.59% regression, despite exact outputs. Do not retry larger RAM expert halos
on this 18 GB host. Preserve the promoted demand-admitted disk cartridge and
seek a fused/lower-copy path that does not increase the resident footprint.

### Exact adaptive L2-read/compute overlap (2026-09-11)

The lower-copy branch passed.  Sixteen real SD-backed layer routes first proved
that independent expert delivery can overlap exact per-expert MXFP4 arithmetic.
An isolated eight-thread gate reduced median route time from 5.1670 to 4.8970
ms (5.51%), with exact outputs on 16/16 routes.  Concurrent exploratory
four/eight-thread timings were invalidated and are not evidence.

The full integration is adaptive: it preserves the ordinary fused four-expert
call when fewer than two experts are missing from the RAM workbench, and uses
read/compute overlap only for two to four pending experts.  A five-pass
in-process protocol used warm-up then control/candidate/candidate/control.  All
five runs retained exact unrestricted routes, token IDs, final hidden states
and step logits.  Settled L2 delivery was identical at 45,129,243,480 bytes per
pass with zero SD fallbacks.

For 33 genuine continuation positions, median control time was 20.744085 s and
median overlap time was 19.135475 s: an exact 8.4064% end-to-end improvement.
Median throughput rose from 1.59081 to 1.72455 token/s.  Overlap was selected
for 937/1,188 continuation-layer evaluations (78.87%).  Decision:
`PROMOTE_EXACT_ADAPTIVE_L2_READ_COMPUTE_OVERLAP` for the frozen arithmetic
family.  This is not 30--50 token/s and not yet a cross-family claim.  Replicate
on blinded extraction/reasoning and 128--256-token gates before broadening it.

Balanced runtime canonical/file SHA-256:
`c000c889c84025a510552e31341831bfb12c7b8878b60f008ea06961a95faa52` /
`392b30f3b60749d10488ddd7ce2e3bd053b5ede615d102c843dfb6575f87afe8`.

The frozen invoice-extraction replication then passed more strongly.  After
one hostile arithmetic-to-extraction switch/warm-up, balanced settled passes
had identical 42,531,495,544-byte L2 delivery and zero SD fallbacks.  Median
22-token response time fell from 14.456209 to 12.031206 s (20.1559%), raising
throughput from 1.52184 to 1.82858 token/s.  Overlap applied to 616/792 response
layer evaluations.  Routes, tokens, final hidden states and step logits were
exact across all five passes.  This promotes the mechanism as a measured exact
two-family result, not merely arithmetic-specific.  Extraction canonical/file
SHA-256:
`180d4ec6595450dd4da79ee6c6ec3ad6381e54b1e380d6242f9fac42032dddc6` /
`2ca647e49f037a91a9ca1dec7b0d440b992c03670d92651d302aa2c05afb779f`.

### Exact response reuse frontier and sub-GiB memory cliff (2026-09-11)

Response-only analysis after removing the existing exact RAM pools found a
hard first-touch floor.  Arithmetic delivered 36.1665 GiB across 33 response
positions, but 14.6394 GiB was unique first-touch demand; eliminating 50% would
require 4.7029 GiB of extra resident experts.  Extraction delivered 23.2675
GiB, with a 12.6891 GiB first-touch floor, so even unlimited within-response
retention could remove only 45.46%.  Weighted p50/p95 reuse distances were
3.22/10.81 GiB arithmetic and 2.06/8.61 GiB extraction.

Six-component retention was materially identical to whole-expert retention:
its advantage was about 0.10 percentage points at 0.5 GiB and below 0.004
points at 4 GiB.  Stop component-granularity caching.

The live 0.5 GiB hotset plus overlap test admitted exactly 40 experts and cut
settled L2 delivery 12.51%, from 45,129,243,480 to 39,483,117,864 bytes.  It
remained fully exact with zero settled SD fallbacks, but median throughput fell
from 1.72455 to 1.50127 token/s, a 12.95% regression.  Stop the unrun 1.0 GiB
candidate and all additional RAM expert hotsets on this 18 GB Mac.  The next
exact architecture must reduce transient delivery or consume a lossless packed
representation with bounded scratch space; it cannot enlarge durable expert
residency.

Offline frontier canonical/file SHA-256:
`8c2821c48a7acd28c5327eefdbd0832923ee8daa3f941479ec2e6cbf90046401` /
`5f4f404074a9735cbae82b4345ca44a96295f4870f71d071f4ac8dcf30719045`.
Live boundary canonical/file SHA-256:
`b476d87e10a10f35c2f7591ea3a3c126fb0a9ece24071d01fb896967cfcb553d` /
`f89a2936c38998359ededd0534aae4adc39a3bcf4abb4f581cdc522389f22a2d`.

The dependency-staged packed-I/O branch was then stopped at its real-route
microgate.  Splitting gate/up from down arithmetic was bitwise exact and added
only 4.55% resident compute overhead, but process-verified partial L2 reads
raised median four-expert route time from 4.9073 to 7.3853 ms.  The second read,
second native graph and synchronization boundary overwhelmed the tiny overlap
window.  All 96 compared outputs were exact.  Do not integrate this path into
full generation.  Canonical/file SHA-256:
`f10a46617ed6ef1129b4f3919837981836d34d040b34bcca6c3981447bc9559d` /
`33fe30fe9bb7fb54f9ab29d503dad0d36b4a2772656a51053fba929de55e3c4b`.

### Current C4 refinement and continuous coverage phase (2026-09-12)

The target remains unrestricted GPT-OSS 120B and a separately labelled,
quality-gated compact fourth-expert correction. Do not substitute a smaller
resident model or claim that approximate continuation is exact unrestricted
inference. Existing exact short-window frontiers remain 1.72455/1.82858 t/s;
the correct reasoning quality controller remains approximately 7 t/s in its
tested operating region. No new speed result has been promoted here.

The initial C4 integration added its contribution after residual addition.
Real exact-E4 audits exposed 838/883 differing elements. The corrected native
three-expert-plus-correction reducer appends C4 before residual addition and
matches all original quartet output elements exactly on both audits. This
isolates addition-order error, not approximation error, and does not prove
that all earlier downstream drift came from integration rounding.

A frozen two-anchor affine secant for layer 12/expert 22 occupies 46,080 bytes
of response/secant payload and 69,288 loaded cartridge-array bytes including
anchors/metadata. The previous extraction development activation is now
explicitly fitting data. On the next unused training-split extraction
trajectory, one of 39 E4 calls passed the unchanged joint cosine 0.80 and
interpolation-support mask. Local output error was 0.774095%, versus 1.577208%
for the constant correction on the same activation. Two other identity
matches were rejected. A paired warm narrow median-cost probe, including
similarity/support/prediction, measured 7.73% of resident real-E4 cost under
concurrent diagnostic load; this is not a full-runtime performance gate.

The prospective single-position downstream test substituted only position
27/layer 12, retaining true E4 everywhere else. Both passes were repeatable and
all 42 next-token/second-choice IDs matched control, but only 15 positions were
at or after substitution. There were 28 ordered-route changes, 15 expert-set
changes and one top-expert change. Maximum chosen-logit drift was 0.526638;
worst recorded top-two perturbation/teacher-margin ratio was 11.4143%.
Classification: TOKEN_STABLE_DOWNSTREAM_DRIFT, not a certified correction.
Differences from the older trajectory are not a matched causal ablation.
Downstream analysis canonical SHA-256:
`b5a2bd616c94d8ecae643f902e6aab756652ba8c8c6703a6d88c611cb3211def`.

Continuous collection of all 24 frozen **training** prompts is now running at
`results/aion_gptoss_c4_full_layer_training_queue_20260912`, balanced across
six families and capturing all 36 layers. Do not launch a competing full-model
job while this queue is active: the shared inference lock prevents accidental
overcommit. Each capture uses six threads, a declared 8 GiB expert cache and
the watchdog-bounded curriculum-yield lease. Selection and holdout trajectories
remain unused. Evidence is local, not SD-backed; the mounted SD remains the
verified model source. Approximately 9 GiB local free space precluded a new
20 GiB disk cache. The queue checks a 3 GiB reserve before each job.

Count only completed `COMPLETE_VERIFIED.json` sidecars. They bind the corpus,
exact-repeatability receipt, complete position/layer grid and all capture file
hashes. New targets include the exact gated native-F32 E4 contribution and
full vocabulary logits (201,088 F32 values) without another neural evaluation.
Interrupted or invalid jobs are preserved and stop the queue; partial files,
planned observations and queued jobs are never successful evidence.

Next: inspect completed training coverage by layer/expert/activation region;
fit corrections only where authentic support warrants it; freeze before
selection and sealed holdout evaluation. Preserve local <2% error and <25%
charged correction-cost requirements, original-E4 fallback and downstream
route/logit/token/semantic checks. The next promotion is a transferable region
and eventually enough certified traffic to improve balanced completed-answer
generation, not another isolated tiny calculator or a relaxed threshold.
<!-- 2026-09-12 disk-guarded C4 restart: the initial queue was interrupted
without completed evidence. Preserve it. Active retry root:
results/aion_gptoss_c4_full_layer_training_queue_20260912_retry01.
The queue polls a 3 GiB local free-space reserve during captures every 5 s.
Up to 24 training-only captures, no extra L2 allocation; 13 focused tests
passed. No new speed/certification claim. See
GPT_OSS_120B_C4_CAPTURE_RESTART_APPEND_2026-09-12.tex. -->
