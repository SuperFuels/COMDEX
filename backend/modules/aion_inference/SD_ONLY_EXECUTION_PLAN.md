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
