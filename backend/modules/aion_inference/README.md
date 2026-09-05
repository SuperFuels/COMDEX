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
