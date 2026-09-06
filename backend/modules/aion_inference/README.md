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
