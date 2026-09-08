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
