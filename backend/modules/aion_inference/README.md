# AION adaptive inference baseline

This package is Phase 0 of the Glyph-Addressed Adaptive Inference Runtime. It
creates a reproducible control measurement before the Semantic Gateway,
AtomSheet bypass, Glyph context compression, or layer streaming is enabled.

The runner records runtime-supplied token and timing values, response hashes,
deterministic quality checks, machine inventory, model-store provenance, and an
optional bounded storage probe. Measurements unavailable from the selected
runtime are stored as `unavailable`; they are never replaced by estimates.

Example with an Ollama model store on external storage:

```bash
export AION_INFERENCE_STORAGE_ROOT="/Volumes/EXTERNAL/AION-Inference"
export OLLAMA_MODELS="$AION_INFERENCE_STORAGE_ROOT/models"
export OLLAMA_HOST="127.0.0.1:11435"
ollama serve
```

In a second terminal:

```bash
python backend/scripts/run_aion_inference_baseline.py \
  --model qwen3:1.7b \
  --base-url http://127.0.0.1:11435 \
  --storage-root "$AION_INFERENCE_STORAGE_ROOT" \
  --model-store "$OLLAMA_MODELS" \
  --probe-storage \
  --output "$AION_INFERENCE_STORAGE_ROOT/baselines/qwen3-1.7b.json"
```

The benchmark manifest covers arithmetic, business calculation,
classification, document interpretation, planning, tool selection, novel
reasoning, longer policy context, and a repeated task variation.

This phase does not claim AirLLM compatibility, sparse model execution, model
weight compression, or GPU-memory savings. Those require separate measured
experiments against this control.

## First Semantic Gateway route

`SemanticGateway` compiles a profit request into a content-addressed meaning
capsule, scores the verified AtomSheet and model routes, and executes the sheet
only when revenue, materials, labour, currency consistency, ambiguity, and
numeric validity gates pass. Incomplete or ambiguous requests return a compact
fallback prompt and require a model call. Policy constraints are retained in
that prompt.

```python
from backend.modules.aion_inference import SemanticGateway

result = SemanticGateway().route(
    "Profit with revenue EUR 4000, materials EUR 1700 and labour EUR 900?"
)
assert result.route == "verified_atomsheet"
assert result.model_call_required is False
```

Use `backend/scripts/run_aion_semantic_gateway_comparison.py` to compare this
route with a recorded Phase 0 case. The comparison refuses to report a bypass
unless the AtomSheet gate and independent inverse verification both pass.

The COMDEX API exposes:

- `GET /api/aion/inference/capabilities`
- `POST /api/aion/inference/route`

The route supports verified profit, percentage, rectangular area, rectangular
volume, and length-conversion AtomSheets. Results are written to a verified
replay store and an append-only execution receipt log. The runtime uses
`AION_INFERENCE_STORAGE_ROOT` when set; otherwise it uses a single mounted
`*/AION-Inference` directory when one is present, falling back to
`data/aion_inference` only when no unambiguous external store exists.

Requests containing a second action, multiple calculations, missing values,
invalid dimensions, mixed profit currencies, or unresolved ambiguity cannot
take the deterministic bypass.

## AION Semantic Gateway and SQI route beams

The public adaptive route now executes the complete bounded gateway sequence:

```text
Public Intent Gateway
        ↓
Semantic Transformer
        ↓
Glyph Meaning Compiler
        ↓
SQI Candidate Beams
        ↓
Route Collapse
        ↓
Replay / AtomSheet / bounded CodexCore operator / Model
```

Profit, calculation, learned-AtomSheet, workflow, and model-fallback candidates
are evaluated as independent deterministic beams. Collapse selects the
highest-scoring eligible beam; ineligible or unsafe beams remain in the proof
receipt with their rejection reasons. Candidate and collapse events are also
published through the existing `BeamEventBus`.

These are parallel symbolic route candidates, not token-sampling beams,
physical light measurements, or quantum computation. Their event metadata
explicitly records that boundary. Workflow lookup is discovery-only until a
governed executor is explicitly bound, so a matching workflow cannot silently
gain execution authority. Model-route prediction chooses a fallback class and
an expert-prefetch profile. `expert_prefetch.py` now converts that prediction
into a deterministic per-layer Granite shard plan using measured domain-router
counts. Every result records all
ten gateway stages, candidate scores, collapse evidence, workflow catalog hash,
model-route prediction, selected context, minimal prompt, trace, and proof
receipt.

Run the SD-backed acceptance experiment with a fresh run ID:

```bash
PYTHONPATH=. python backend/scripts/run_aion_sqi_gateway_experiment.py \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --run-id sqi-semantic-gateway-v2
```

Run the real SD-backed Glyph-to-MoE bridge experiment with a fresh run ID:

```bash
PYTHONPATH=. python backend/scripts/run_aion_glyph_moe_prefetch_experiment.py \
  --model-path "/Volumes/EXTERNAL/AION-Inference/hf-models/granite-3.1-3b-a800m-instruct" \
  --profile "/Volumes/EXTERNAL/AION-Inference/experiments/real-moe-expert-profile-v1.json" \
  --shard-manifest "/Volumes/EXTERNAL/AION-Inference/expert-shards/granite-3.1-3b-a800m-instruct/manifest.json" \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --run-id glyph-moe-prefetch-v1
```

The first four-profile run bound arithmetic/business, policy, coding and general
Gateway predictions to real 32-layer expert plans and reproduced every
unrestricted output token exactly. Targeted prefetch reduced median generation
time from 77.68 s to 26.33 s and loaded 15.21% fewer speculative bytes than the
broad plan. Its 51.29 s prefetch cost consumed essentially the entire gain:
median total time was 77.62 s versus 77.69 s with no prefetch. All three methods
ultimately requested the same 23,679,058,832 logical bytes because each complete
request touched about 1,253--1,255 of the model's 1,280 experts. The
prediction-to-loader bridge therefore works, but this profile is not selective
enough to deliver a meaningful end-to-end speed or request-peak-memory gain.
Physical SD reads were not isolated from the macOS file cache.

The follow-up changes the memory lifecycle rather than widening the preload.
`run_aion_layer_scoped_moe_experiment.py` compares immediate layer eviction,
static one-layer-ahead top-eight prefetch, and bounded retention of the eight
experts selected by the live router for the final prompt token:

```bash
PYTHONPATH=. python backend/scripts/run_aion_layer_scoped_moe_experiment.py \
  --model-path "/Volumes/EXTERNAL/AION-Inference/hf-models/granite-3.1-3b-a800m-instruct" \
  --profile "/Volumes/EXTERNAL/AION-Inference/experiments/real-moe-expert-profile-v1.json" \
  --shard-manifest "/Volumes/EXTERNAL/AION-Inference/expert-shards/granite-3.1-3b-a800m-instruct/manifest.json" \
  --request-scope-reference "/Volumes/EXTERNAL/AION-Inference/experiments/glyph-moe-prefetch-v1.json" \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --run-id layer-scoped-moe-v2-live-router
```

On the two tested prompts, pure layer eviction reduced peak Metal allocation
from 6.60 GB to 0.78 GB but raised median generation from 79.99 s to 92.38 s.
Static layer-ahead prediction added 9.54% I/O and did not improve speed. Bounded
live-router retention was the best tradeoff: 2.06 GB peak allocation (68.77%
below request-wide retention) and 84.88 s median generation. It recovered 8.12%
against pure eviction and was only 6.11% slower than the request-wide reference.
All outputs remained exact. This is a two-prompt, warm-file-cache result, not a
production throughput claim.

The longer-generation experiment compares request-wide retention with a
one-route cache and an LRU union of the two most recent live token routes under
one model load:

```bash
PYTHONPATH=. python backend/scripts/run_aion_live_router_lru_experiment.py \
  --model-path "/Volumes/EXTERNAL/AION-Inference/hf-models/granite-3.1-3b-a800m-instruct" \
  --profile "/Volumes/EXTERNAL/AION-Inference/experiments/real-moe-expert-profile-v1.json" \
  --shard-manifest "/Volumes/EXTERNAL/AION-Inference/expert-shards/granite-3.1-3b-a800m-instruct/manifest.json" \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --run-id live-router-lru-long-v1
```

For exact 8-token and 16-token generations, the two-route LRU was 17.72% faster
and issued 18.09% fewer logical shard bytes than one-route retention. Its
decode-only retained-hit rate was 61.34%, versus 42.96% for one route. Peak
Metal allocation was 2.89 GB, 56.38% below the same-run request-wide control,
but median generation remained 80.51% slower than that high-memory control.
The two-route LRU is therefore the current memory-saving mode, not the default
throughput mode. All token IDs and every step's logits matched exactly.

### Packed and reuse-aware expert caches

The expert layout now also supports one verified Safetensors pack per MoE
layer. Packing all 1,280 experts into 32 files cut median storage-open
operations by 81.83% in a same-model ABBA comparison, but improved median time
by only 1.36%. This rejects file-open count as the dominant remaining cost;
expert transfer and repeated cache misses matter more.

On a 16-token packed run, increasing live-route depth from two to eight cut
generation time by 37.45% and logical demand bytes by 32.38%, while raising
peak Metal allocation from 2.89 GB to 4.31 GB. A bounded LFU policy then found
a better operating point: 16 retained experts per layer came within 2.30% of
depth-eight time while using 25.30% less peak Metal memory. A 24-expert policy
was 7.49% faster than depth eight at 1.84% more peak memory. Every token ID and
every generation-step logit remained exact. These are single-prompt warm-cache
results and require corpus-scale and controlled-storage replication.

The cache now has a deterministic global-budget planner. It replays measured
route batches without loading tensors, evaluates every capacity from zero to
40 for each layer, and uses dynamic programming to minimize predicted demand
bytes under an exact global expert-slot budget. In the first transfer test it
learned a non-uniform 512-slot allocation from one policy prompt and was tested
against uniform 16-per-layer retention on held-out arithmetic and coding
prompts. The learned plan reduced held-out median time by 7.54% and demand bytes
by 0.96%, with a 1.75% peak-Metal increase. It improved time on both held-out
cases and preserved every token and generation-step logit exactly. This is the
current reference cache controller, subject to larger-corpus replication.

Passing controller evidence can be promoted into an immutable external-storage
plan. Promotion requires intact canonical evidence, exact outputs, held-out
latency and demand-byte improvements, and an unchanged capacity budget. The
artifact binds the model configuration, routing profile, shard manifest, pack
manifest, and source evidence hashes. `verify_promoted_expert_cache_plan`
rejects content mutation, invalid capacities, failed gates, and model or
manifest substitution before the runtime accepts the per-layer capacities.

A broader four-prompt, 16-token replication preserved exact outputs and reduced
logical demand bytes by 1.43%. The promoted plan was faster in three of four
paired cases and the median paired change favoured it by 1.43%, but the raw
aggregate median was 9.83% slower because one promoted-first pass was 20.55%
slower. A focused ABBA rerun of that anomaly reversed the result: the promoted
plan was 7.75% faster and used 0.96% fewer demand bytes. This exposes substantial
run-order/cache variance. The plan remains the promising experimental reference,
but a population latency claim is explicitly disallowed until repeated,
randomized, cache-controlled testing is complete.

`ExpertRouteCorpus` now provides the next learning boundary. It stores only
content-addressed router batches, Glyph addresses, model-input hashes and model
or manifest bindings; public prompt text and model output are excluded. Exact
duplicate observations deduplicate automatically, mutation fails hash
verification, and observations with different model bindings cannot be mixed.
Multiple verified observations can be combined into one global cache-budget
optimization, enabling the next controller to learn from a corpus rather than
one prompt.

The first live three-prompt capture was invalidated after audit found that two
observations contained empty layer histories: cache reset had cleared the route
lists before offsets were applied. The original report is preserved with an
external `INVALID` sidecar. Both the runner and corpus now reject any empty
layer. The corrected SD-backed run recorded 16 batches for every one of 32
layers in each of three prompt-private observations. Its distinct 512-slot plan
reduced held-out logical demand bytes by 1.226%, versus 0.963% for the original
single-prompt plan on the same routes, and improved same-run median time by
2.26% with 0.29% peak-Metal overhead. Every token and step logit was exact. The
plan is promoted only as a corpus candidate pending direct broader comparison.

That direct comparison now exists. On four new 24-token prompts, the corpus
candidate used 372,787,096 fewer logical SD bytes (0.619%), incurred 79 fewer
faults, retained 79 more hits, and reduced peak Metal allocation by 1.44%
against the prior promoted plan at the same exact 512-slot budget. Median time
fell by 7.61%, with the candidate faster on three of four prompts. One prompt
was 3.93% slower and another used slightly more demand bytes, so the advantage
is aggregate rather than universal. Every token ID and every step logit matched
the unrestricted controls exactly. The candidate is now the better measured
controller for this model, pending broader randomized and cache-controlled
replication before any population claim.

The controller now also accepts an explicit retained-expert byte ceiling rather
than assuming a fixed slot count. It charges each slot conservatively at the
largest expert artifact in its layer and uses an exact non-dominated dynamic
program to minimize replayed demand without crossing the ceiling. On the three
verified corpus observations, leave-one-out plans at 1, 2 and 3 GiB reduced
held-out logical demand by 3.20%, 2.24% and 3.87% respectively versus the best
equal per-layer capacity that fit the same ceiling. The learned allocation won
all nine folds/budget comparisons. This is exact offline route replay, not a
timed model run; live Metal memory, latency and output equivalence remain gates
for the next execution experiment.

### Measured SD/Metal latency attribution

Stage 1 now instruments the exact SD-backed MoE critical path rather than
inferring its bottleneck from aggregate generation time.  A 24-token run using
the corpus-trained 3 GiB controller assigned 98.50% of measured wall time to
named stages.  Host-to-Metal expert materialisation calls accounted for 70.58%,
SD/Safetensors reads for 20.78%, router and route capture for 4.45%, expert
compute and combination for 1.69%, and every other named stage for less than
1%.  A prior immutable 24-token run measured the same two dominant stages at
67.98% and 21.67%, respectively.  Both runs reproduced every control token and
generation-step logit exactly; the corrected v2 also proved its conservative
3,218,237,968-byte expert allocation remained below the declared 3 GiB ceiling.
The filesystem cache was warm but not controlled, physical disk counters were
system-wide, and the inserted synchronization barriers perturb latency.  These
results select Metal materialisation—not file opens or cache-policy overhead—as
the next bounded optimization target; they are not production throughput data.

The first single-change probe requested non-blocking copies for each expert
tensor while retaining the layer synchronization barrier.  It was rejected
immediately: the 24-token output diverged, maximum step-logit error reached
25.59375, and instrumented time increased by 2.04% relative to the corrected
blocking reference.  Its report and `INVALID` sidecar remain on the SD evidence
volume.  No ABBA replication is warranted because exactness failed; subsequent
Metal work must use an explicitly synchronized batch or arena design.

A second probe fused each expert's input and output matrices into one owned CPU
buffer, then made one blocking Metal transfer whose two device views remain
independently evictable as a single expert.  It preserved exact tokens and
logits, halved transfer operations from 4,922 to 2,461, reduced attributed Metal
materialisation time by 11.52%, and reduced total instrumented time by 6.92%
against the corrected v2 reference (135.010 s to 125.663 s).  However, it was
5.14% slower than the earlier immutable v1 reference.  It therefore remains an
unpromoted candidate below the 10% live-time gate pending balanced ABBA
replication; no general speedup is claimed.

The required same-model-load blocking/fused/blocking/fused comparison then
resolved that uncertainty.  Blocking median time was 124.670 s and fused median
time was 126.170 s, making fusion 1.20% slower.  Median attributed Metal time
improved by only 0.33% despite halving the number of transfer operations.  Both
conditions requested exactly 23,226,051,728 logical bytes across their two
runs; fused p95 and peak Metal allocation were slightly lower, all four runs
assigned more than 98% of wall time, and every token and logit was exact.  The
10% promotion gate failed, so per-expert fusion is retired and preserved with a
`NOT_PROMOTED` sidecar.  This falsifies transfer-call count as the dominant
Metal cost and advances the programme to a bounded persistent transfer-arena
design.

The bounded per-layer Metal arena was then tested in a same-load
dynamic/arena/arena/dynamic comparison at the corpus-selected 3 GiB ceiling.
It remained numerically exact and preserved identical logical SD demand, but
failed performance promotion decisively: median generation time increased by
30.71%, median attributed Metal transfer time increased by 43.97%, p95
regressed, and observed peak MPS allocation increased by 83.86%.  The fixed
arena itself occupied 2.997 GiB; current-layer experts outside each layer's
retained capacity remained transient.  The result falsifies MPS slice-copy
reuse as a useful implementation on this backend and is preserved with a
`NOT_PROMOTED` sidecar.  The next Metal optimization must avoid a full-size
persistent arena and target transfer representation or execution fusion.

Stage 3 then compiled prompt-private routes into a hash-bound sparse transition
capsule.  A top-1 predictor used the current token's route in layer L to predict
one missing expert in layer L+1 only when learned confidence was at least 0.80.
Across four balanced 24-token prompts it achieved 147 useful and 55 wasted
prefetches, removed 147 demand faults, preserved exact tokens/logits, and added
no peak Metal memory.  Nevertheless, Python-threaded SD/safetensors overlap
made median time 15.29% slower and regressed p95 from 122.33 s to 159.56 s.
The predictor capsule remains a verified research artifact, but this threaded
I/O mechanism is `NOT_PROMOTED`; future use requires a non-contending read path.

A subsequent CPU-streaming feasibility study adapted the useful systems idea
from `kimi-k3-in-c`: pack weights once in their execution representation and
compute without a Metal transfer.  Four immutable one-token probes separated
runtime conversion, native BF16 CPU arithmetic, lazy memory-mapped FP16, and
explicitly materialized FP16.  Every probe reproduced the control token and
logits exactly.  The first FP16 pack was correctly invalidated because some
BF16 values do not round-trip through FP16; the corrected 6,040,073,472-byte
pack instead proves exact equivalence to the existing FP16 execution
conversion across all 32 layers and 1,280 experts.

The decisive materialized-FP16 run reduced expert arithmetic to 1.010 s, but
loading and materializing 5,917,405,296 logical expert bytes took 77.897 s.
Total streamed time was 79.423 s for one token, versus 2.221 s for the
full-resident CPU control.  The apparently faster lazy-mapped run was diagnosed
as deferred page faults inside the measured compute stage, not faster I/O.
Execution-format repacking therefore moves the bottleneck but does not remove
it and is `NOT_PROMOTED`.  The external implementation's central advantage is
low-bit packed arithmetic that reduces bytes read; that lossy method is outside
this programme's exact-FP16 gate unless evaluated later as a separately
authorized quality track.

Stage 4 then replaced temporary full-checkpoint startup with a true
storage-first construction path.  The model was created as an unallocated meta
skeleton, 226 shared/router checkpoint tensors were loaded to Metal, and all 64
combined expert tensors were skipped.  Verified SD pack addresses were bound to
the governed layer cache instead.  A first attempt failed closed because the
deterministic RoPE buffer had also been placed on meta; its failure record is
preserved.  The corrected build left no meta parameter or buffer at execution.

In the bounded warm-uncontrolled feasibility run, full-checkpoint construction
took 93.295 s and allocated 6,597,587,456 Metal bytes.  Storage-first
construction took 6.549 s and peaked at 557,789,184 Metal bytes: 14.25 times
faster construction and 91.55% lower startup Metal allocation.  All 1,280
experts remained addressable.  First and subsequent inference reproduced every
control token and logit exactly.  The first request took 78.563 s; the second
took 40.199 s with 682 retained hits across both requests.  This passes the
Stage 4 construction proof, but it is not yet a cold-start, multi-prompt, or
throughput promotion result.

The corrected FP16 execution-format packs were also tested on the live Metal
path rather than only in the rejected CPU-streaming design.  A same-load
BF16/FP16/FP16/BF16 24-token comparison showed that preconversion reduced
median attributed Metal-transfer time by 13.71%, but total instrumented time by
only 5.79%.  A second production-like ABBA run removed attribution-only stage
barriers.  Its median improved by only 2.07% (121.981 s to 119.459 s, or
0.1977 to 0.2009 tokens/s), while p95 improved from 130.257 s to 120.502 s.
Every token and logit was exact, logical demand and peak Metal memory were
identical, and the three-GiB controller gate passed.  Two controlled results
therefore miss the 10% median gate; execution-format repacking is retained as a
valid composable artifact but is `NOT_PROMOTED` as an independent strategy.

The first Stage 5 sustained-generation milestone extended storage-first
execution to two sequential 64-token inferences.  The empty-start run completed
in 143.715 s (0.4453 tokens/s); the subsequent retained-cache run completed in
98.408 s (0.6504 tokens/s), a 31.53% time reduction.  Across both inferences the
controller recorded 27,031 retained hits and 7,731 faults, a 77.76% retained-hit
rate.  All 128 generated tokens and all 128 corresponding step-logit tensors
matched the full-resident FP16 control exactly.  The strong 0.50 tokens/s warm
SD milestone is therefore exceeded for this prompt.  The filesystem state was
warm uncontrolled and only one prompt was tested, so randomized multi-prompt,
cold/warm, p95, 128-token, and 256-token validation remain open.

```bash
PYTHONPATH=. python backend/scripts/run_aion_moe_latency_attribution.py \
  --model-path "/Volumes/EXTERNAL/AION-Inference/hf-models/granite-3.1-3b-a800m-instruct" \
  --shard-manifest "/Volumes/EXTERNAL/AION-Inference/expert-shards/granite-3.1-3b-a800m-instruct/manifest.json" \
  --pack-manifest "/Volumes/EXTERNAL/AION-Inference/expert-layer-packs/granite-3.1-3b-a800m-v1/manifest.json" \
  --route-corpus "/Volumes/EXTERNAL/AION-Inference/route-corpora/adaptive-cache-corpus3-v2" \
  --memory-budget-gib 3 --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --device disk6 --run-id UNIQUE-RUN-ID --generated-tokens 24
```

## Learned AtomSheets and Glyph context

`LearnedAtomSheetStore` is the first quarantined promotion pipeline. It accepts
model outcomes only through a trusted internal verifier boundary. A model
response is never treated as proof. Automatic promotion requires at least six
distinct verified input sets, two verifier identities, a unique exact match in
the audited operator-template library, and a two-observation holdout pass.
Promoted contracts are content hashed, written to the external evidence root,
and cannot be silently replaced by a different contract. Later verified
outcomes monitor the existing contract. Unknown intents, mismatched inputs,
numeric boundary failures, and inverse-check failures return the full-model
route.

There is deliberately no public learning-ingestion endpoint yet. The API
publishes learning status and can execute an already promoted structured route:

- `GET /api/aion/inference/learning/status`
- `POST /api/aion/inference/route-structured`

`GlyphContextDictionary` gives repeated policy and evidence passages stable
content addresses and small session slots. The first packet carries hash-checked
definitions; later packets carry slot references. Decoding rejects tampering,
unknown slots, dictionary mismatches, and any discrepancy between declared and
decoded policy slots.

`AddressedShardExperiment` measures full versus selected content-addressed
storage reads. Its current fixture is synthetic and proves only byte-addressing
and hash verification. It does not claim real MoE routing, neural output
equivalence, or token-throughput improvement.

The first promoted family is connected to the normal text route. Requests such
as `What is 225 with a 16% markup?` compile to the promoted inputs, execute
without a model call, and replay across equivalent supported wording. Ambiguous
phrasing and compound follow-on actions still fail closed.

Run the combined SD-backed experiment while the isolated Ollama model store is
available:

```bash
PYTHONPATH=. python backend/scripts/run_aion_learning_context_shard_experiments.py \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --base-url http://127.0.0.1:11435 \
  --model qwen3:1.7b
```

The multi-family falsification harness extends promotion to markup, discount,
tax, and hourly labour while keeping formulas out of the prompts. It preserves
incorrect model answers as rejected evidence, challenges each promoted sheet
on 25 unseen inputs, and attacks the boundary with negative, zero, oversized,
out-of-range percentage, mismatched-field, unknown-intent, ambiguous-language,
and compound-action cases. Use a fresh run ID for every cohort:

```bash
PYTHONPATH=. python backend/scripts/run_aion_multifamily_falsification.py \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --run-id multifamily-v4-domain-bounds \
  --base-url http://127.0.0.1:11435 \
  --model qwen3:1.7b \
  --structured-output
```

The recorded v4 SD-backed cohort promoted all four expected operators, passed
100 of 100 unseen calculations without model calls, and rejected all 983
adversarial cases from the learned fast path. Earlier failed tax cohorts remain
on the evidence volume; they show that promotion safely remains quarantined
when the small model does not supply enough correct outcomes.

All four promoted families now have bounded ordinary-English routing. The
separate text experiment covers 100 valid variants and 450 invalid, ambiguous,
mixed-family, or compound-action prompts. Its acceptance gate requires exact
answers for every valid variant and zero invalid fast-path executions:

```bash
PYTHONPATH=. python backend/scripts/run_aion_multifamily_text_routing_experiment.py \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --run-id multifamily-v4-domain-bounds
```

To measure whether context selection reduces tokens actually consumed by the
local model, run the paired full-versus-selected experiment against the
isolated SD-backed Ollama endpoint:

```bash
PYTHONPATH=. python backend/scripts/run_aion_selected_context_model_experiment.py \
  --storage-root "/Volumes/EXTERNAL/AION-Inference" \
  --base-url http://127.0.0.1:11435 \
  --model qwen3:1.7b
```

The first 12-case run preserved all three mandatory policies and produced
identical correct structured answers in both arms. Selected context reduced
Qwen's measured prompt-token count by 62.77% at the median and by at least
62.54% in every case. This is prompt-token evidence; it is not a claim of
Glyph-native model vocabulary, KV-cache compression, or weight compression.
