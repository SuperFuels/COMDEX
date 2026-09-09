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
