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

Stage 5 then exposed and repaired a semantic-integrity defect before accepting
multi-prompt evidence. The first four-prompt run was invalidated because two
different public requests compiled to the same generic fallback: the gateway
had bound the source hash but omitted the source text from the model prompt. It
also generated only 202 of 256 requested tokens. The repaired gateway preserves
the complete normalized request, records its prompt hash, and the runner rejects
duplicate compiled inputs or incomplete generations.

The corrected randomized four-family run completed all 256 requested tokens.
Every token ID and generation-step logit matched the full-resident FP16 controls
exactly. Under the existing 3 GiB plan it recorded 54,398 retained hits and
15,148 faults (78.22% hits), 71,480,745,952 logical demand bytes, 0.9015 median
tokens/s and a 0.4351--1.2588 tokens/s range. The fourth request was 2.89 times
the first request's throughput, consistent with persistent-cache warming, but
prompt family and order are confounded, so this is not a causal same-prompt
speedup claim. Filesystem state remained warm uncontrolled and there is one
observation per family.

A hash-bound expert working-set dictionary next tested predictive eviction
protection without speculative reads. Leave-one-observation-out replay predicted
a 4,053,469,816-byte (13.78%) saving and avoided 859 faults across three winning
folds. Live execution did not generalize: it caused 376 additional faults and
1,774,277,824 additional bytes, regressed median time by 6.38%, and regressed
p95 by 5.20%. Exactness passed, but the policy is `NOT_PROMOTED`.

The exact expert storage path now also supports independently addressable
Zstandard frames, reversible two-byte BF16 shuffle, coalesced physical reads,
and bounded parallel decode. The shuffled level-1 representation reduced the
6,039,797,760-byte expert library to 4,134,132,737 bytes (31.55%) with all 2,560
tensor roundtrips exact. In a clean stage-instrumented eight-token ABBA run,
four decode workers improved median generation by 30.46% (96.441 s to 67.066 s)
and preserved every token and step logit. The diagnostic synchronized token
rate rose from 0.0831 to 0.1193 tokens/s; this is not substituted for the
longer-generation throughput measurements. An SD-mount binding now prevents
physical counters from silently targeting the wrong disk. LZ4 was not promoted:
it decoded only 2.22% faster in the mechanism probe while using 23.08% more
compressed bytes than the shuffled Zstandard sample.

The promoted compressed pack is now wired into the sustained storage-first
runner through the same bounded four-worker pool. A first empty-expert-cache
technical-explanation diagnostic generated all 64 requested tokens at 0.6053
tokens/s with exact token IDs and zero step-logit error. TTFT was 53.185 s,
followed by a 0.7395 s median subsequent-token interval. This validates longer
exact execution and clears the declared 0.50-token/s milestone, but is not a
source/candidate speed promotion because the run has one prompt and no matched
storage-first source timing arm.

A route-unaware prompt-slimming probe reduced tokenized input length by
35.41--37.76%. It reduced first-request TTFT by 4.57% and peak MPS allocation by
1.86%, but median time regressed by 16.96%, logical demand increased by
632,322,416 bytes, and one step differed from the full-resident control by
0.015625 logits despite identical token IDs. The probe is
`INVALID_FOR_PROMOTION` and was reverted. Prompt length alone is therefore not
a safe proxy for sparse-MoE expert demand; future Glyph compression must be
route-aware and pass renewed exactness gates.

The next Stage 5 run doubled every prompt to 128 generated tokens without
changing the four-family order, model, SD packs, or 3 GiB controller. It
completed all 512 tokens with exact token and step-logit equivalence. Median
throughput reached 2.6064 tokens/s and the best warm request reached 3.5240
tokens/s; the empty-cache first request achieved 0.7608 tokens/s. The retained
hit rate rose to 80.67%. Relative to the 64-token run, median throughput was
2.89 times higher and logical expert demand per generated token fell by 13.80%.
This confirms that longer generations allow the retained working set to repay
its initial materialization cost. The run remains warm uncontrolled with one
observation per family, so replication and a 256-token condition remain open.

The semantic gateway now also supports exact-signature beam fusion and
cost-aware collapse. Candidate paths may be fused only when their declared
execution signatures are identical; eligible paths are ranked by assurance
before model calls, estimated storage demand, and estimated first-token time.
Unknown model costs remain explicitly unknown rather than being assigned a
favourable invented estimate. A 12-case deterministic SD-backed fixture routed
all cases correctly, immediately completed eight verified calculation or replay
cases without a model call, and correctly deferred four language tasks. All
answers, proof receipts, trace-chain checks, and collapse-policy checks passed.
The observed 66.67% model-call avoidance is a property of this declared fixture,
not an estimate of a real workload, and the deferred tasks were not counted as
completed. Median gateway latency was 147.34 ms and nearest-rank p95 was
318.35 ms. This establishes the governed bypass mechanism; it does not yet show
that beam fusion itself improves end-to-end model throughput.

The first four-prompt 256-token extension was preserved but rejected. It
generated all 1,024 requested tokens and every token ID matched the full-resident
control, while three prompt families also retained exact step logits. The
commercial-risk request reached a maximum step-logit difference of 0.03125, so
the run failed the zero-error integrity gate and is `INVALID_FOR_PROMOTION`.
Observed median throughput was 1.2879 tokens/s and the retained-hit rate was
82.16%, but these figures must not be promoted as an exact-output milestone.
The accepted 128-token run remains the longest fully exact four-prompt result.
The next 256-token work must first localize this numerical divergence under a
bounded reproduction; the integrity threshold must not be relaxed.

The bounded reproduction subsequently ran the commercial-risk family twice in
independent processes. Both 256-token SD-backed generations matched their fresh
full-resident controls at every token and every step logit. They achieved 1.1470
and 1.2199 tokens/s, for a replicated median of 1.1834 tokens/s. Compared with
the exact 128-token run of the same first, empty-cache prompt, throughput
improved by 55.55%; doubling the generated tokens increased total elapsed time
by only 28.70%. Logical expert demand per token fell by 13.12% and retained-hit
rate rose by 2.69 percentage points. Each replication recorded the same 13,347
faults and 53,193 hits. A separate full-resident probe repeated the same
256-token generation three times with exact tokens and logits at a 10.0560
tokens/s median; its complete token hash matched both SD runs. The previous
four-prompt failure remains invalid and differs from this stable sequence after
zero-based step 243. This promotes a replicated exact single-family 256-token
milestone, not a four-family or cold-cache result.

Two fresh four-family 256-token runs then used contrasting prompt orders. Both
runs completed all 1,024 requested tokens with exact token IDs and exact
generation-step logits. Across 2,048 accepted SD-backed tokens, the median of
the two run medians was 1.2972 tokens/s; the individual medians were 1.4102 and
1.1842 tokens/s. Combined retained-hit rate was 82.11%, with 95,208 faults,
437,100 hits and 449,269,795,392 logical demand bytes. Every family remained
exact whether placed early or late. This is the first replicated exact
four-family 256-token milestone. It remains warm uncontrolled, and its median
throughput is 50.23% below the earlier 128-token aggregate median, so it proves
robust sustained correctness rather than a universal longer-is-faster result.

The existing SD-backed Qwen route was revalidated immediately afterwards. All
12 full-context and all 12 selected-context structured answers were correct and
equivalent. Context selection preserved every mandatory policy and reduced
Qwen prompt tokens by 62.77% at the median and at least 62.54% in every case.
This confirms readiness for Stage 6 task routing but is not yet a mixed-workload
completed-task economics result.

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

The compressed Granite prefill working set has now been measured directly.
Across three valid route observations, prefill selected 97.89--98.05% of all
layer/expert pairs, representing 97.88--98.04% of the complete compressed pack.
Cold prefill is therefore an almost-full-library read. Better eviction cannot
avoid weights the router genuinely requested, so cold-prefill prediction is
stopped under the locked pivot rule. Exact reuse remains useful after the
working set exists; otherwise verified model-call avoidance and governed
Qwen/Granite task routing are the next economic levers.

An evidence-bound 110-task economics diagnostic now combines 100 verified
AtomSheet calculations, eight distinct accepted Qwen extraction cases and two
exact-but-quality-failed Granite business tasks. It counted 108 successful
tasks, 100 avoided model calls and 1,041.83 successful tasks/hour over 373.189 s
of projected/measured serial time. The two failed Granite calls consumed 93.50%
of that time. This is not a blinded Stage 7 promotion, but it identifies the
next high-value change: serve the bounded supplier-control information request
from the signed Business Map rather than spending Granite time on an output
that fails its rubric.

That bounded supplier-control route is now implemented. It verifies the signed
SD-resident Business Map, renders all six controls with a proof receipt, grants
no payment authority and made zero model calls in 1,000/1,000 passing trials.
Median latency was 0.305041 ms and p95 was 0.343583 ms. Replacing the prior
169.281 s failed Granite attempt in the unchanged 110-task diagnostic raised
successes from 108 to 109 and successful-task throughput from 1,041.83 to
1,924.39 tasks/hour while reducing total serial time by 45.36%. This is a
synthetic evidence-bound routing result, not a blinded Stage 7 promotion or a
Granite token-generation speedup. The remaining failed Granite task remains a
failure and still consumes 88.11% of revised elapsed time.

The next run exercised the router live rather than recombining timings. A fixed-
seed shuffled evaluator-blind cohort contained 100 promoted calculations, eight
live Qwen extractions, one signed policy answer and the exact Granite contract
already proven to fail its quality rubric. A hash-bound negative-capability gate
sent that exact contract to human review without generalizing the failure to
changed requests. The run completed 109/110 tasks, safely resolved all 110,
avoided 102 model calls and made no Granite call. Actual serial wall time was
25.576 s; task latency was 16.207 ms p50, 0.7502 s p95 and 18.542 s maximum,
with the maximum caused by Qwen's explicit cold start. All receipts, the trace
chain and 72 focused tests passed. This promotes the bounded routing mechanism,
not a family-balanced or real-customer Stage 7 workload.

A subsequent family-balanced gate corrected that arithmetic bias. It used eight
tasks each for calculation, quotation, policy, extraction, short drafting,
planning and coding. A new narrow quotation AtomSheet calculates and inverse-
checks the total but cannot send, approve or take payment. The first two runs
remain preserved as failures (49/56, then 55/56); they exposed an underspecified
drafting contract and a currency-preservation miss. After strengthening the
contracts without relaxing any rubric, v3 completed 56/56 tasks. It measured
33.870 s actual serial time, 5,952.13 successful tasks/hour, 0.3330 s p50 and
0.7811 s p95 latency. It avoided 24 model calls, used 32 bounded Qwen calls and
made no Granite call. Seventy-five focused tests passed. This is a balanced
synthetic mechanism result; unseen holdout paraphrases and adversarial near-
misses remain required before a broader Stage 7 claim.

That separately frozen holdout is now complete. The committed task file and
separate answer key contain four unseen valid tasks and four adversarial near-
misses per family. The first immutable run completed all 28 valid tasks but
failed because two action-bearing policy prompts still reached the read-only
policy renderer. The matcher was narrowed without altering the corpus. V2 then
completed 28/28 valid tasks, rejected verified bypass for 28/28 adversarial
requests, and executed zero adversarial model calls. All seven family gates,
receipts and the trace chain passed. It used 16 Qwen calls, avoided or prohibited
40 calls, and measured 0.3445 s p50 and 1.1347 s p95 valid-task latency. The
failed v1 evidence remains preserved. This promotes a small frozen synthetic
holdout, not production or natural-customer generalization.

Warm Glyph-family batching was then tested with a four-arm ABBA design over the
16 frozen Qwen tasks. Each arm explicitly unloaded and neutrally cold-primed the
same installed model before warm measurement. All 64 task executions passed and
each case's canonical output was identical across arms. Grouping genuinely
shared fixed schema/prompt prefixes and reduced prompt-evaluation time 10.12%,
but total warm workload time improved only 2.17%, below the declared 3% gate.
The strategy is `NOT_PROMOTED` and stopped: serial prefix grouping is real but
too small because generation, not prompt evaluation, now dominates Qwen time.

A compact extraction wire protocol was also stopped. Replacing descriptive JSON
keys with `s`, `i`, and `a` failed 8/12 cases in both candidate arms, increased
generated tokens 3.82%, and improved total warm time only 4.91% against a 10%
gate. Both baseline arms passed 12/12. An `INVALID` sidecar corrects a separate
miscomputed payment-authority field in the report; quality and timing findings
remain valid. The next exact-output economic candidate was a narrow verified
extraction AtomSheet trained from the twelve accepted normalized outcomes, with
a new frozen holdout required before promotion.

That candidate has now passed its independent gate. Twelve verified outcomes
were compiled into a narrow, fail-closed AtomSheet; its derivation gate passed
12,000/12,000 known-valid executions and rejected 4,000/4,000 known attacks.
More importantly, a separately committed and hash-bound 32-case holdout was not
opened until all routing and signed-review observations had completed. It passed
16,000/16,000 unseen valid extractions and reviews, rejected all 16,000
adversarial near-misses, made zero model calls and never granted payment
authority. Valid-route latency was 0.3091 ms p50 and 0.3488 ms p95. This
promotes model-call avoidance for eight explicitly recognized sentence
grammars; it is not open-ended language understanding or a claim that Granite
generates tokens faster.

The promoted route was then integrated into the same fixed-seed 56-task,
seven-family balanced construction used by the earlier v3 result. V4 again
completed 56/56 tasks with valid receipts and trace chain, while extraction
used zero model calls. Total model calls fell from 32 to 24, observed serial
time fell from 33.870 s to 30.283 s, successful-task throughput rose from
5,952.13 to 6,657.27 tasks/hour, and task p50 fell from 0.3330 s to 0.01162 s.
P95 regressed from 0.7811 s to 0.9553 s because the single cold Qwen call was
slower and occurred in a different family. This is a successful integration
observation against historical v3 evidence, not a contemporaneous ABBA causal
speed promotion.

A broader frozen stress diagnostic then tested 24 useful extractions (including
new phrase shapes and harmless surrounding text), eight compound requests and
eight adversarial cases. V1 correctly failed: it refused 62.5% of useful
executions, misread one noisy supplier value and accepted one two-invoice
compound into the verified route. Payment remained impossible. Structural
single-invoice/single-amount guards and a stricter supplier boundary removed
both unsafe interpretations. The unchanged v2 corpus recorded zero wrong
extractions and zero compound/adversarial bypasses, while still refusing 66.67%
of useful forms. The original 32-case exact holdout then repassed 16,000 valid
and 16,000 adversarial executions under the strengthened contract. Safety is
revalidated; broad language coverage is explicitly `NOT_PROMOTED`.

A separately gated Semantic Gateway candidate now canonicalizes eight additional
bounded paraphrase forms plus four whitelisted noise wrappers before invoking
the unchanged verified AtomSheet. Its first derivation run failed only because
four suffix removals left duplicate punctuation; the corrected derivation run
passed 12,000 useful and 8,000 guard executions. A subsequently committed
new-value holdout also passed 12,000/12,000 useful executions and rejected all
8,000 compound/adversarial executions, at 0.337 ms p50 and 0.384 ms p95 for
useful tasks. This is `PROMOTED_FOR_INTEGRATION` only for the declared finite
transformations. The corpus was designed against those transformations, so it
does not establish open-ended paraphrase generalization.

The bounded normalizer is now integrated into `GovernedBusinessRouter`. Its
route receipt binds the original request, canonical request, normalizer
contract and verified-extraction receipt. A 20-case, 500-repeat frozen
end-to-end holdout passed 12,000 exact useful executions and rejected verified
bypass for 8,000 compound/adversarial executions. Every route receipt and the
trace chain verified, payment authority remained false, and useful p50/p95
latency was 0.0541/0.0709 ms. This promotes only the finite declared
transformations; model fallbacks were identified but not executed in this gate.

The first TensorSheet CPU-assistance experiment now has both a real-layer
microbenchmark and complete-model evidence. CPU execution was 48.55% faster
than Metal for an isolated CPU-resident eight-expert fault, but slower when the
weights were already resident in Metal and never bit-exact to Metal. Complete
execution confirmed why: CPU-only moved conversion or wide-prefill computation
onto the slower engine. A phase-aware compressed candidate reduced Metal
transfers 24.21% and observed eight-token time 1.89%, but maximum logit drift was
0.03515625 and the sequential timing missed the 10% gate. It is
`NOT_PROMOTED`. A separate route audit found 16.34% duplicate route sets and
3.256/8 average next-route expert overlap, proving weight reuse but no reusable
expert outputs because activation equality was not recorded.

Exact shared-prefix/KV reuse has also been tested and stopped on the exact
track. Four requests shared an exact 166-token Business Map/policy prefix. A
content-addressed Metal cache reduced full-resident total time 3.94% after its
one-time build, but missed the 10% speed gate, changed one of four token streams
and produced non-identical step logits for every request. The candidate is
`NOT_PROMOTED`: mathematically reusable causal state is not bit-identical to a
one-pass FP16 Metal prefill when kernel partitioning changes. This does not
invalidate prefix caching for an explicitly quality-gated service; it prevents
claiming it as an exact-output optimization on the current stack.

A separate quality-gated candidate has produced a strong real-layer result.
Apple Metal's native weight-only INT8 operation can calculate directly from
packed Granite expert weights. On 200 balanced samples of a verified eight-
expert layer-16 route, the representation was 49.89% smaller, resident
calculation was 28.41% faster, and a refined contiguous Glyph-block fault path
with permanently resident scales was 50.00% faster than FP16. The first naive
packed fault path was 24.01% slower and remains recorded. Maximum layer-output
error was 0.0036621, so this is `ADVANCE_TO_FULL_MODEL_QUALITY_GATE`, not an
exact result or full-model promotion. At approximately 2.82 GiB for all expert
weights, the candidate could make the complete Granite expert library resident
within the existing 3 GiB expert budget.

That candidate has now crossed its first full-model capacity gate. All 1,280
experts were converted into a 2.8186 GiB content-addressed SD library, 49.894%
smaller than the verified source experts. Direct full-resident INT8 execution
kept all 32 short-run token IDs and improved TTFT 10.69%, but improved median
generation only 2.30%; the speed claim is `NOT_PROMOTED`. The decisive result
was storage-first boot: it never materialized FP16 experts, reduced active Metal
allocation 45.67% (6.598 GB to 3.584 GB), cut boot time 52.18% (91.231 s to
43.629 s), retained 8.215 tokens/s within 0.25% of FP16, and matched all 32
short-run tokens. This is `ADVANCE_TO_LONG_QUALITY_GATE`; logits are non-exact
and longer frozen quality validation is mandatory before promotion.

The 64-token extension has now stopped the simple quantizer for long-form use.
All-layer INT8 improved median throughput 2.95% and TTFT 20.32%, but matched
only 64.84% of 256 autoregressive token positions. Retaining the first and last
FP16 layers used 2.9940 GiB and reached 67.19%; retaining the two layers selected
by a real-activation sensitivity audit (29 and 1) reached only 64.06%. All three
are `NOT_PROMOTED`. The layer audit itself is useful: 29, 1, 17, 28 and 24 were
the five most sensitive layers. Further whole-layer-pair guessing is stopped;
the next quality-gated design must use improved quantization or sparse
high-value FP16 retention with frozen calibration and evaluation cohorts.

A sparse FP16 residual shelf was also stopped. Retaining the highest-error 3%
of input columns projected to 2.9925 GiB, but improved maximum layer error only
1.32% while slowing packed calculation 116.90%. This error is too distributed
for sparse column correction. The next diagnostic must compare FP16 and INT8 on
identical teacher-forced histories before deciding whether the observed
autoregressive divergence represents broad degradation or a small number of
cascading greedy choices.

The teacher-forced diagnostic passed. When both models received identical
histories, INT8 preserved FP16's top choice at 247/256 positions (96.48%),
achieved 96.33% mean top-five overlap, mean KL divergence of 0.003455 nats and
only 0.006691 nats additional loss on FP16-selected tokens. This explains much
of the low raw autoregressive match as divergence cascade rather than widespread
probability damage. Status is `ADVANCE_TO_SEMANTIC_TASK_GATE`; exact equivalence
is not claimed, and held-out completed-answer quality remains unproven.

Two frozen semantic gates did not establish absolute task quality because the
FP16 control was weak. Strict JSON produced 2/8 passes for both models. A
twelve-case multiple-choice gate produced 6/12 for FP16 and 7/12 for INT8;
packed answers agreed with FP16 on 11/12 choices and ran 18.31% faster. Both are
`NOT_PROMOTED`. They support relative preservation, not model competence. A
larger choice-likelihood diagnostic and a subsequently unseen holdout are
required before any semantic promotion.

The choice-likelihood diagnostic removed generation and parsing entirely, but
FP16 remained at 6/12. INT8 reached 8/12 and was 18.49% faster in aggregate
forward time, while agreement fell to 10/12 (83.33%). It is
`DIAGNOSTIC_DID_NOT_CLEAR_BASELINE`, report SHA-256
`7caf487aec34af497257f815f02e6e45b3bfba0a029cdd6353a278767117cd49`.
This confirms that formatting was not the main defect. Do not spend an unseen
holdout on this control design; first freeze a larger benchmark and require FP16
to clear its competence floor before running INT8.

Native Metal INT4 was then swept on the real layer-16 eight-expert route. It
reduced logical expert storage by 68.75--73.44% and improved median resident
calculation by 34.83--36.70% versus FP16. However, the best-quality group-32
condition had 0.0159302 maximum layer error, 5.33 times INT8's 0.00299072 and
above the declared four-times ceiling. Larger groups were less accurate. The
result is `STOP_INT4_DIRECT_PATH`, report SHA-256
`1f6a3b60c40fe351e635140c1ce0a31c4ee4854b65c85c206be8184055955b07`.
Naive INT4 must not be scaled; a future candidate requires activation-aware
quantization with frozen calibration/evaluation separation.

Activation-weighted INT4 clipping was tested next on real layer-16 activations,
using two prompt families for calibration and two disjoint families for
evaluation. It retained a 19.46% median one-token layer speed improvement, but
only reduced normalized RMSE from 0.12036 to 0.11881 and worsened maximum error
from 0.222656 to 0.310547. That was 6.91 times the matched INT8 maximum error.
It is `STOP_ACTIVATION_AWARE_INT4_V1`, report SHA-256
`2cb2f415902b2f802f769c215ac8a00f3f420c517166b5ee3fc12f335b4d5e78`.
Simple clipping-ratio tuning is stopped; future INT4 work must use a different
equivalent transformation and explicitly charge any runtime rescaling cost.

Equivalent channel rescaling was also stopped. It preserved the pre-quantized
linear mathematics and improved INT4 normalized RMSE by 5.74%, but worsened
maximum error to 0.246094 (5.48 times matched INT8). Its two charged inverse
scales reduced the median decode-layer gain to 6.93% versus FP16 and made it
12.43% slower than naive INT4. All four gates failed. Result:
`STOP_EQUIVALENT_SCALED_INT4_V1`, report SHA-256
`6f8a13860f37b9c7a749f8b44941aa9e8ae8016e8a3004547cb3025e7b30e7dd`.
The current four-bit branch is closed; INT8 remains the viable packed runtime.

The INT8 runtime then produced a new exact-within-candidate dispatch
breakthrough. Decode selected eight experts per layer but launched both Metal
matrix operations for all 40, including 32 empty experts. Skipping only empty
launches reduced calls from 80 to 16 per layer-token, improved median real-route
layer time 39.13% and p95 20.87%, with bit-identical output. The result is
`ADVANCE_TO_FULL_MODEL_SPARSE_DISPATCH_GATE`, report SHA-256
`0a9244267122b65a627805bac04b51a7659416fbb87b543013f56ed240ebdf11`.
It now requires 64-token storage-first full-model ABBA validation.

The first full-model variant was correctly rejected despite a 13.93% speed gain:
it removed empty concatenation entries and one of twelve repeat comparisons had
non-identical logits. The corrected implementation skips the empty Metal matrix
operations while preserving all 40 concatenation entries. Its full storage-first
64-token ABBA replication improved median throughput from 10.144 to 11.264
tokens/s (11.04%) and p95 generation time 7.88%. All 1,024 generated token IDs
and every step logit were bit-identical, so it is
`PROMOTE_INT8_SPARSE_DISPATCH`. Canonical report SHA-256:
`73a2057a10c8f04f38a41f92bec6ad6a240b8033c958c3ee761bb3570cb43dee`.
Exactness is relative to the packed INT8 model, not FP16; unseen longer
replication remains required.

The larger unseen replication did not extend that promotion boundary. Eight
frozen prompt families and 128 tokens retained a 10.03% median throughput gain
and 7.46% p95 improvement, but one candidate repetition diverged at token 43.
One unchanged baseline repetition also showed logit drift without a token
change, proving that long-run Metal self-repeatability is a separate issue.
Twenty-two of 24 comparisons were bit-identical, but the result remains
`NOT_PROMOTED`, canonical report SHA-256
`989ec69183409a6b3c93c7f5d07c2c5538172d2b35ae2ef88d20bd1f221ac287`.
The 64-token promotion stands; 128-token generalization does not.

Enabling PyTorch deterministic algorithms did not repair the 128-token boundary.
On the two exposed families, all six repeats diverged, including both unchanged
baseline repeats, and maximum logit error reached 43.46875. Throughput dropped
to 7.130 tokens/s for control and 7.706 for sparse dispatch; the candidate gain
fell to 8.08%, below gate. The post-hoc diagnostic is `NOT_PROMOTED`, report
SHA-256 `4e50a445d556b02c167f82c00ac62630625bf7d3a1c875d929f7725d671fcf04`.
Deterministic mode is stopped on this MPS path.

A bounded persistent Metal decode arena was also stopped. It used only 1.25 MiB
projected across 32 layers and remained bit-identical, but explicit buffer copies
made median layer time 2.35% slower and p95 10.06% slower than sparse
concatenation. Result: `STOP_DECODE_ARENA`, report SHA-256
`3fb648e8b208c00daef7eebb5833163b66faa4051fc724d5822ef949f0437b25`.
Default arena capacity is zero; the promoted sparse-concatenation path is
unchanged.

Cached resident weight views were also tested and stopped. They reused only
references to resident packed weights, added no weight bytes, and improved a
1,000-trial real-route layer-16 microbenchmark by 11.31% at p50 and 1.65% at
p95 with bit-identical output (report SHA-256
`f29f2f17583ec86d10f7546cf58abb1051d6ed814d9f2ca9df133ecba16c441d`).
However, the four-family 64-token storage-first ABBA gate was 0.90% slower in
median throughput, 0.05% worse at p95, and failed step-logit bit equivalence
despite matching all token IDs. It is `NOT_PROMOTED` (report SHA-256
`948136d201fd319a36439960410de325df70f201461fdb33d7b33966d8aaa384`).
Do not enable it; sparse dispatch remains the promoted path.

Reusable zero-length Metal views were tested separately because preserving the
40-entry concatenation topology creates 64 empty tensors per layer-token. On
1,000 real-route layer-16 trials, reuse improved p50 by 6.81% with bit-identical
output but regressed p95 by 3.82%, beyond the declared 3% limit. It is
`STOP_CACHED_EMPTY_VIEWS`, report SHA-256
`4d8a5ab1d4ac140740bf8d590f7bb0cda0c42d4a03d73e64589880bd71a947eb`.
It is not enabled or advanced to a full-model run.

Fixed-route graph compilation was also bounded. A real packed-INT8 expert graph
compiled on MPS with bit-identical output in a mechanism probe, but Granite's
data-dependent router prevents one dynamic full graph. Across 16,256 observed
layer-routes from three bound corpora, the most common route covered only 3.05%
at the median layer and the best eight routes only 12.99%. This failed the 50%
coverage gate, so fixed-route graph caching is
`STOP_ROUTE_SPECIALIZED_COMPILE` (report SHA-256
`0f037de61a3efb5e845294820ccaad11a42088fa567ec5092e839e4d050496d7`).
Future compilation work must remove the router's Python `tolist()` boundary or
use a genuinely dynamic fused Metal dispatch kernel.

AION then implemented the dynamic kernel mechanism directly. A runtime-compiled
Metal SIMD matvec accepts eight selected resident INT8 weight buffers and reduces
16 expert matrix launches to two per layer-token, without another weight copy.
On 1,000 real-route layer-16 trials, the complete expert block improved p50 by
20.07% and p95 by 52.57%. Maximum extra error was 0.0000305176, well below the
frozen 0.00075 ceiling. It is
`ADVANCE_FUSED_METAL_MATVEC_TO_MODEL_INTEGRATION`, report SHA-256
`18b1ce06a354cb4b1e5c480bf2bb5f84e34ceceafebac5177b2a1aa2ffb2238f`.
This is a changed-kernel quality-gated track, not bit-exact or full-model
promotion; ordinary packed INT8 remains the fallback until integration gates pass.

The 64-token four-family full-model integration was therefore correctly stopped.
The fused candidate improved median throughput 4.95% (10.9755 to 11.5191
tokens/s) and p95 time 5.40%, but missed its 5% speed floor and changed generated
tokens in two of four families. All closing sparse-INT8 controls remained exact;
maximum candidate step-logit error after autoregressive accumulation was 38.5405.
It is `NOT_PROMOTED`, report SHA-256
`fe7f1f63669671ab02509b7c9187bc0b4d7cf5a12975f1b91781f72abb91346b`.
Fused v1 remains disabled; the promoted sparse INT8 path is unchanged.

Calibration-selected fusion was also stopped. Four frozen calibration families
selected 16 low-sensitivity layers in plan
`941f7224eef566f293937306302b3ad76a0280cb22a314f5798ae1a1ad07085c`.
On four disjoint 64-token holdout families, median throughput improved 4.80%
(11.0729 to 11.6042 tokens/s), but p95 regressed 3.46%, one family changed token
sequences in both candidate repeats, and maximum logit error reached 30.3359.
All closing controls were exact. The result is `NOT_PROMOTED`, report SHA-256
`302f634116f56606e0fa6a9babfe8a863f84b3056fd33f60d8ee9ee97af44386`.
Do not tune smaller subsets against this holdout; kernel arithmetic must improve.

GPU-resident dynamic banking then produced the major speed result. AION keeps
top-eight routes on Metal and addresses one contiguous 40-expert layer bank,
removing Python `tolist()` synchronization. The formal layer gate improved p50
36.71% and p95 25.07%, with maximum error 0.0000610 (report SHA-256
`c093f623b2e5f6fe1b142f001a9775c1939352672b3b364269104bcf30f121b4`).
The SD-native 32-layer bank is 2.8196 GiB with zero runtime duplicate weights;
manifest hash `5ccd5b7d44467bd193e6cb8fc39b95df888a6f285a9d2e68690c685f24e8bb27`.

Full four-family 64-token ABBA generation rose from 11.2886 to 24.4679 tokens/s
(116.75%) and p95 improved 56.43%. All candidate token sequences matched in
both repeats and all closing controls were bit-exact, but maximum step-logit
difference was 2.17969. Status is `ADVANCE_DYNAMIC_BANK_TO_QUALITY_GATES`, not
quality promotion; report SHA-256
`a167b4218c07d1a396093ab65d39ff8c111bad5c69b5af62b29e9372a6e5ece9`.

Quality qualification now promotes the dynamic bank within its measured boundary.
Across 256 identical FP16-forced positions, dynamic top-one agreement was 97.27%
versus 97.66% for native INT8; top-five overlap was 95.86%, KL 0.003687 nats and
NLL delta 0.008386 nats. All gates passed and teacher execution improved 55.76%
(report SHA-256
`50bfc1e9928cfac76236f65f9ba3b432ca8dac4c52aea7e4cd169d2b078a0204`).

The frozen 12-case semantic suite produced 100% answer agreement: both native
and dynamic INT8 scored 7/12, every answer parsed, and dynamic throughput improved
50.46%. Status is `PROMOTE_DYNAMIC_BANK_WITHIN_VALIDATED_BOUNDARY`, report
SHA-256 `225b5fef106cf01f201adaef53df4b56b32b4ad262fcb4149b558083a7ed021a`.
This promotes the execution architecture, not the absolute competence of the
small model. Unseen 128--256-token replication remains required for expansion.

That long-generation expansion now passes. The dynamic bank sustained 24.8073
tokens/s across eight frozen families at 128 tokens and 23.9612 tokens/s on a
disjoint eight-family 256-token holdout, versus native-bank rates of 11.2547 and
10.6228 tokens/s. The candidate lost only 3.41% throughput as length doubled;
p95 generation time improved 55.95% and 59.05%, respectively. Candidate
repeatability was 8/8 at 128 and 7/8 at 256, versus native 6/8 and 7/8.

Because free-running wording differed at long length, an extended FP16 teacher
gate forced identical histories across 2,048 positions. Dynamic top-one agreement
was 98.2422% versus native INT8's 98.1934%; every probability gate passed and
teacher time improved 56.23%. The combined decision is
`PROMOTE_DYNAMIC_BANK_LONG_GENERATION_BOUNDARY`, canonical report SHA-256
`2e772e66d43a28c35cdf6c85b3027a08f29a5e0db1ab6fe39ceac2f3c4569620`.
This remains a quality-gated changed-kernel result, not bit-exact equivalence.
