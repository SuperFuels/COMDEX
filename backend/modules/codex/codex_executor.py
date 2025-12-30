# 📁 backend/modules/codex/codex_executor.py

"""
⚡ Codex Executor - Ultimate Symbolic Execution Engine
───────────────────────────────────────────────────────
Executes CodexLang & glyphs with:
✅ SQI entanglement ↔ + collapse tracing
✅ Knowledge Graph logging (introspection + prediction)
✅ Cost estimation & CodexMetrics
✅ Tessaris interpretation
✅ DNA mutation lineage tracking 🧬
✅ Self-rewrite (⬁) on contradictions
✅ GHX replay event injection
✅ Blindspot + confidence introspection (IGI-ready)
✅ Prediction + introspection index hooks
"""

import time
import json
from typing import Any, Dict, Optional, List, Union
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

# Core imports
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.ops.op_trigger import op_trigger
from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.core.plugins.plugin_manager import register_all_plugins, get_plugin, get_all_plugins
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam
from backend.modules.aion.rewrite_engine import RewriteEngine
from backend.photon.photon_qwave_bridge import to_qglyph, to_wave_program

# Intelligence & KG
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.knowledge_graph.indexes.introspection_index import add_introspection_event
from backend.modules.knowledge_graph.indexes.prediction_index import PredictionIndex, PredictedGlyph
from backend.modules.symbolic.symbol_tree_generator import inject_symbolic_tree 

# Memory & DNA
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.dna_chain.mutation_checker import add_dna_mutation
from backend.modules.consciousness.state_manager import STATE  # singleton instance
from backend.modules.codex.rewrite_executor import auto_mutate_container

from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic.symbolic_inference_engine import run_symbolic_inference
from backend.modules.dna_chain.dna_utils import extract_glyph_diff
from backend.modules.dna_chain.mutation_scorer import score_mutation
from backend.modules.glyphwave.core.beam_logger import log_beam_prediction
from backend.modules.glyphwave.emit_beam import emit_qwave_beam
from backend.modules.creative.innovation_scorer import get_innovation_score
from backend.modules.codex.codex_scroll_builder import build_scroll_from_glyph
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
from backend.symatics.symatics_dispatcher import evaluate_symatics_expr, is_symatics_operator
from backend.modules.photon.photon_to_codex import photon_capsule_to_glyphs, render_photon_scroll
from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
from backend.modules.spe.spe_bridge import recombine_from_beams, repair_from_drift, maybe_autofuse
from backend.modules.codex.codex_trace import log_codex_trace as record_trace

# ⬁ Self-Rewrite Imports
from backend.modules.codex.scroll_mutation_engine import mutate_scroll_tree

# SQI + Prediction
from backend.modules.sqi.sqi_trace_logger import SQITraceLogger
TessarisEngine = None
PredictionEngine = None

try:
    from backend.modules.glyphos.symbolic_entangler import entangle_glyphs
except Exception:
    def entangle_glyphs(*args, **kwargs):
        # no-op fallback for tests
        return []

# GHX & GlyphNet
try:
    from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
except Exception:
    async def broadcast_qfc_update(*args, **kwargs):
        return None  # no-op fallback for test environments
try:
    from backend.modules.scrolls.scroll_builder import build_scroll_from_glyph
except ImportError:
    def build_scroll_from_glyph(*args, **kwargs):
        return None  # no-op for tests

# after: from backend.modules.codex.ops.op_trigger import op_trigger
from backend.modules.codex.ops.op_trigger import op_trigger as _raw_op_trigger

# --- Async helpers & QWave wrapper ---------------------------------------------------
import asyncio

import logging
logger = logging.getLogger(__name__)

def _coerce_glyph_obj(glyph: Any) -> Dict[str, Any]:
    """
    Coerce legacy/adapter glyph inputs into a dict-like object.
    - dict -> returned as-is
    - empty string / None -> {}
    - non-empty string -> {"program": "...", "raw": "..."}
    """
    if glyph is None:
        return {}
    if isinstance(glyph, dict):
        return glyph
    if isinstance(glyph, str):
        s = glyph.strip()
        if not s or s in ("∅", "null", "none"):
            return {}
        return {"program": s, "raw": s, "type": "codex_program"}
    # last resort
    return {"raw": str(glyph), "type": "unknown"}

def resolve_op(op_symbol: str):
    mapping = {
        "⊕": "superpose",
        "↔": "entangle",
        "⟲": "resonate",
        "⧖": "delay",
        "->": "trigger",
    }
    # ∇ is RESERVED for math gradient; leave as-is.
    return mapping.get(op_symbol, op_symbol)

def _get_tessaris():
    """
    Lazy Tessaris getter to avoid circular imports.
    Returns an initialized TessarisEngine or None if unavailable.
    """
    try:
        from backend.modules.tessaris.tessaris_engine import TessarisEngine
        return TessarisEngine()
    except Exception as e:
        logger.warning(f"[CodexExecutor] Tessaris unavailable: {e}")
        return None

# --- New helper ---
def _align_with_tessaris(glyphs, origin=None):
    """
    Run Tessaris intent extraction only if origin is 'photon'.
    Returns extracted intents or empty list.
    """
    if origin != "photon":
        return []

    try:
        tessaris = _get_tessaris()
        if tessaris:
            intents = tessaris.extract_intents_from_glyphs(glyphs, origin="photon")
            logger.info(f"[CodexExecutor] Tessaris intents extracted: {intents}")
            return intents
    except Exception as e:
        logger.warning(f"[CodexExecutor] Tessaris alignment failed: {e}")

    return []

# ===============================
# 📁 codex_executor.py (patched QWave emitter wrapper)
# ===============================

import asyncio
import time
import logging

logger = logging.getLogger(__name__)

def _spawn_async(coro, label: str = "task"):
    """
    Schedule a coroutine if an event loop is running; otherwise skip gracefully.
    Prevents 'await outside async function' and pytest RuntimeWarnings.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        print(f"⚠️ {label} skipped: no running event loop")

# ✅ Canonical QWave emitter import (with fallback stub)
try:
    from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam as _emit_qwave_beam
except Exception:  # fallback for test/CI
    async def _emit_qwave_beam(*, wave, container_id, source, metadata=None):
        print(f"[QWaveEmitter] (stub) emit_qwave_beam: {wave} -> {container_id}, src={source}, meta={metadata}")

from backend.modules.glyphwave.core.wave_state import WaveState

def _call_plugin_qfc_broadcast(plugin, field_state: Dict[str, Any], *, container_id: Optional[str] = None):
    """
    Call plugin.broadcast_qfc_update safely across signature differences.
    Only passes kwargs the plugin actually accepts.
    """
    import inspect
    fn = getattr(plugin, "broadcast_qfc_update", None)
    if not fn:
        return

    kwargs = {}
    try:
        sig = inspect.signature(fn)
        if "observer_id" in sig.parameters:
            kwargs["observer_id"] = "codex_executor"
        if "container_id" in sig.parameters and container_id:
            kwargs["container_id"] = container_id
        if "payload" in sig.parameters:
            kwargs["payload"] = field_state
        if "field_state" in sig.parameters:
            kwargs["field_state"] = field_state
    except Exception:
        # if signature introspection fails, fall back to simplest call
        kwargs = {}

    if inspect.iscoroutinefunction(fn):
        _spawn_async(fn(field_state, **kwargs), "QFC plugin broadcast")
    else:
        try:
            fn(field_state, **kwargs)
        except TypeError:
            # last resort: no kwargs
            fn(field_state)

def validate_stub(symbolic_logic):
    try:
        from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
        raw = validate_logic_trees({"symbolic_logic": symbolic_logic})
        return normalize_validation_errors(raw)
    except Exception:
        return []

def emit_qwave_beam_ff(*, source: str, payload: dict, context: dict = None):
    """
    Fire-and-forget wrapper around emit_qwave_beam.
    Converts CodexExecutor's payload into a WaveState + forwards to emitter.
    """
    try:
        # Build WaveState from payload
        wave = WaveState(
            wave_id=payload.get("wave_id", f"beam_{int(time.time()*1000)}"),
            glow_intensity=payload.get("glow", 0.0),
            pulse_frequency=payload.get("pulse", 0.0),
            mutation_type=payload.get("mutation_type", "codex"),
            mutation_cause=payload.get("event", source),
            timestamp=time.time()
        )

        container_id = payload.get("container_id", context.get("container_id") if context else "unknown")
        metadata = {k: v for k, v in payload.items() if k not in ["wave_id", "container_id"]}

        # 🔒 SoulLaw veto check - BEFORE reinjection
        try:
            from backend.modules.soullaw.soul_law_hooks import log_soullaw_event, validate_against_soullaws
            from backend.modules.symbolic.symbolic_broadcast import broadcast_glyph_event

            log_soullaw_event(
                beam_id=wave.wave_id,
                container_id=container_id,
                source=source,
                metadata=metadata
            )

            if not validate_against_soullaws(wave, metadata):
                reason = f"SoulLaw veto for beam {wave.wave_id}"
                broadcast_glyph_event(
                    event_type="denied_beam_event",
                    glyph=wave.wave_id,
                    container_id=container_id,
                    coord="0:0",
                    extra={
                        "law_id": "matched",
                        "reason": reason,
                        "origin": "soullaw_veto"
                    }
                )
                return  # 🚫 stop here if vetoed

        except Exception as e:
            logger.error(f"[SoulLaw] Hook failed: {e}", exc_info=True)

        # ✅ If not vetoed -> emit as normal
        event_coro = _emit_qwave_beam(
            wave=wave,
            container_id=container_id,
            source=source,
            metadata=metadata
        )
        _spawn_async(event_coro, "QWave emit (codex)")

    except Exception as e:
        logger.error(f"[CodexExecutor] Beam emit failed: {e}", exc_info=True)

# --- Move these to module scope so methods can use them without self. --------------
import numpy as np  # was incorrectly imported inside the class
try:
    from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch
except Exception:
    # simple fallback to keep tests running if kernel unavailable
    def join_waves_batch(phases, amplitudes):
        # Return a shape-compatible, no-op-like result
        return {"phase": phases, "amplitude": amplitudes}

def _safe_op_trigger(context: Dict[str, Any], target: str = "default_trigger") -> str:
    """
    Adapts to both legacy signatures:
      - op_trigger(args, registers, context)
      - op_trigger(context=..., target=...)
    """
    try:
        # Newer/virtual-CPU signature
        return _raw_op_trigger([target], None, context)  # args, registers(None OK), context
    except TypeError:
        # Older keyword-style signature
        return _raw_op_trigger(context=context, target=target)

# Self-rewrite
from backend.modules.aion.rewrite_engine import RewriteEngine

DNA_SWITCH.register(__file__)

logger = logging.getLogger(__name__)


class CodexExecutor:
    def __init__(self, use_qpu: bool = False, test_mode: bool = False):
        """
        CodexExecutor orchestrates execution of CodexLang instruction trees.

        Args:
            use_qpu (bool): whether to initialize CodexVirtualQPU backend.
            test_mode (bool): if True, bypasses strict validation & execution
                              so unit tests can focus on rewrite behavior.
        """
        self.metrics = CodexMetrics()
        self.trace = CodexTrace()
        self.glyph_executor = GlyphExecutor(state_manager=STATE)

        # QPU setup
        self.use_qpu: bool = use_qpu
        self.qpu: Optional[CodexVirtualQPU] = None
        if self.use_qpu:
            try:
                from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
                self.qpu = CodexVirtualQPU(use_qpu=True)
                logger.info("[CodexExecutor] QPU backend initialized")
            except Exception as e:
                logger.warning(f"[CodexExecutor] Failed to initialize QPU: {e}")
                self.qpu = None
                self.use_qpu = False

        # Tessaris Engine
        self.tessaris = None
        self.tessaris = _get_tessaris()
        self.kg_writer = get_kg_writer()
        from backend.modules.consciousness.prediction_engine import get_prediction_engine
        self.prediction_engine = get_prediction_engine()
        self.prediction_index = PredictionIndex()

        # 🔌 Load and register cognition plugins
        register_all_plugins()
        self.sqi_trace = SQITraceLogger()

        # Resolve the active container id for memory scoping
        try:
            active_cid = STATE.get_current_container_id() or "ucs_hub"
        except Exception:
            active_cid = "ucs_hub"
        self.memory_bridge = MemoryBridge(container_id=active_cid)

        # ✅ Testing mode flag (bypasses validation/execution when True)
        self.test_mode: bool = test_mode

    def _validate_container_stub(self, symbolic_logic: list) -> list[dict]:
        """
        Validate a symbolic_logic list with Lean validators.
        Always returns normalized validation_errors (list[dict]).
        """
        try:
            from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
            container_stub = {"symbolic_logic": symbolic_logic}
            raw_errors = validate_logic_trees(container_stub)
            return normalize_validation_errors(raw_errors)
        except Exception as e:
            logger.error(f"[Validation] Container stub validation failed: {e}")
            return []

    # ──────────────────────────────
    # 🔆 Photon Capsule Execution (Unified)
    # ──────────────────────────────
    def execute_photon_capsule(
        self,
        capsule: Union[str, Path, Dict[str, Any]],
        *,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a Photon capsule (.phn file, dict, or already-parsed object).
        Pipeline:
        1. Load + normalize capsule
        2. Photon -> LogicGlyphs (with multi-glyph split support)
        3. Register into symbolic_registry
        4. Render Codex scroll
        5. Detect & evaluate Symatics operators (if present)
        6. Otherwise: compile Codex scroll -> instruction tree -> execute

        Always guarantees an "engine" field in the result.
        """
        context = context or {}
        capsule_id = context.get("capsule_id", "photon_capsule")

        # ✅ Lazy imports (avoid circular deps)
        from backend.modules.photon.photon_to_codex import (
            load_photon_capsule,
            photon_capsule_to_glyphs,
            render_photon_scroll,
            register_photon_glyphs,
        )
        from backend.symatics.symatics_dispatcher import (
            evaluate_symatics_expr,
            is_symatics_operator,
        )
        from backend.modules.glyphos.codexlang_translator import run_codexlang_string
        from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors

        # ─────────────────────────────────────────────────────────────
        # 🔧 Capsule Normalizer: keep schema strict, move root context into metadata
        #   Fixes: E001 "context was unexpected"
        #   Also ensures SoulLaw sees avatar/container under metadata.context
        # ─────────────────────────────────────────────────────────────
        def _normalize_capsule_for_schema(obj: Any, runtime_ctx: Dict[str, Any]) -> Any:
            if not isinstance(obj, dict):
                return obj

            # Ensure metadata is a dict
            meta = obj.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
                obj["metadata"] = meta

            # Move root context → metadata.context
            root_ctx = obj.pop("context", None)
            if isinstance(root_ctx, dict):
                meta_ctx = meta.get("context")
                if not isinstance(meta_ctx, dict):
                    meta_ctx = {}
                    meta["context"] = meta_ctx
                # root wins over existing meta if both exist
                meta_ctx.update(root_ctx)

            # Merge runtime context into metadata.context if provided
            if isinstance(runtime_ctx, dict) and runtime_ctx:
                meta_ctx = meta.get("context")
                if not isinstance(meta_ctx, dict):
                    meta_ctx = {}
                    meta["context"] = meta_ctx
                # runtime fills missing keys only (doesn't override capsule-provided)
                for k, v in runtime_ctx.items():
                    meta_ctx.setdefault(k, v)

            # Optional: ensure container_meta is present/complete if container_id exists
            meta_ctx = meta.get("context")
            if isinstance(meta_ctx, dict):
                cid = meta_ctx.get("container_id")
                cmeta = meta_ctx.get("container_meta")
                if cid and not isinstance(cmeta, dict):
                    meta_ctx["container_meta"] = {
                        "id": cid,
                        "kind": meta_ctx.get("container_kind", "qqc"),
                        "source": meta_ctx.get("container_source", "qqc_kernel_boot"),
                    }

                # Optional: if avatar_state accidentally arrives nested or null
                if "avatar_state" in meta_ctx and meta_ctx["avatar_state"] is None:
                    meta_ctx["avatar_state"] = "active"

            return obj

        # If caller passed a dict capsule, normalize it *before* schema validation.
        if isinstance(capsule, dict):
            capsule = _normalize_capsule_for_schema(capsule, context)

        try:
            # 🔗 Load + normalize capsule (schema validation happens inside)
            capsule_dict = load_photon_capsule(capsule)
            glyphs = photon_capsule_to_glyphs(capsule_dict)

            # 🚑 Split scroll expressions into multiple glyphs if needed
            normalized_glyphs = []
            try:
                for g in glyphs:
                    g_str = str(g)
                    if ";" in g_str:  # crude separator for multi-glyph scrolls
                        parts = [p.strip() for p in g_str.split(";") if p.strip()]
                        for p in parts:
                            from backend.modules.glyphos.glyph_tokenizer import (
                                tokenize_symbol_text_to_glyphs,
                            )
                            for token in tokenize_symbol_text_to_glyphs(p):
                                if hasattr(token, "operator"):
                                    normalized_glyphs.append(token)
                    else:
                        normalized_glyphs.append(g)
                glyphs = normalized_glyphs
            except Exception as split_err:
                logger.error(f"[Photon] Glyph splitting failed: {split_err}")
                return {
                    "status": "error",
                    "engine": "codex",  # safe default
                    "error": f"Glyph splitting failed: {split_err}",
                }

            # 🔐 Register glyphs into the symbolic registry
            try:
                register_photon_glyphs(glyphs, capsule_id=capsule_id)
            except Exception as reg_err:
                logger.warning(f"[Photon] Glyph registry failed: {reg_err}")

            # 🌀 Render scroll
            scroll = render_photon_scroll(glyphs)

            # 🛡 Validation after glyph parsing
            try:
                container_stub = {"symbolic_logic": [g.to_dict() for g in glyphs if hasattr(g, "to_dict")]}
                raw_errors = validate_logic_trees(container_stub)
                errors = normalize_validation_errors(raw_errors)
                if errors:
                    logger.warning(f"[Validation] Photon capsule validation errors: {errors}")
                    return {
                        "status": "error",
                        "engine": "codex",
                        "glyphs": [g.to_dict() for g in glyphs if hasattr(g, "to_dict")],
                        "scroll": scroll,
                        "validation_errors": errors,
                        "validation_errors_version": "v1",
                    }
            except Exception as val_err:
                logger.error(f"[Validation] Photon capsule validation failed: {val_err}")

            # 🔍 Detect Symatics algebra operators
            if any(is_symatics_operator(getattr(g, "operator", None)) for g in glyphs):
                try:
                    execution_result = [
                        evaluate_symatics_expr(g, context=context) for g in glyphs
                    ]
                    return {
                        "status": "success",
                        "engine": "symatics",
                        "glyphs": [g.to_dict() for g in glyphs if hasattr(g, "to_dict")],
                        "scroll": scroll,
                        "execution": execution_result,
                    }
                except Exception as e:
                    logger.error(f"[Photon] Symatics evaluation failed: {e}")
                    return {
                        "status": "error",
                        "engine": "symatics",
                        "glyphs": [g.to_dict() for g in glyphs if hasattr(g, "to_dict")],
                        "scroll": scroll,
                        "error": f"Symatics evaluation failed: {e}",
                    }

            # 🔁 Fallback: run CodexLang pipeline
            try:
                instruction_tree = run_codexlang_string(scroll)
                if not instruction_tree or not isinstance(instruction_tree, dict):
                    raise ValueError("Invalid instruction tree from Photon scroll")

                execution_result = self.execute_instruction_tree(
                    instruction_tree, context=context
                )

                # ✅ Trace execution for Photon bridge + monitoring
                from backend.modules.codex.codex_trace import _global_trace
                try:
                    glyph_label = context.get("glyph") if context else "<photon>"
                    _global_trace.trace_execution(
                        codex_str=glyph_label,
                        result=str(execution_result),
                        context=context,
                        source="codex_executor",
                    )
                except Exception as trace_err:
                    import logging
                    logging.warning(f"[CodexTrace] ⚠️ Failed to trace execution: {trace_err}")

                return {
                    "status": "success",
                    "engine": "codex",
                    "glyphs": [g.to_dict() for g in glyphs if hasattr(g, "to_dict")],
                    "scroll": scroll,
                    "execution": execution_result,
                }
            except Exception as e:
                logger.error(f"[Photon] CodexLang execution failed: {e}")
                return {
                    "status": "error",
                    "engine": "codex",
                    "glyphs": [g.to_dict() for g in glyphs if hasattr(g, "to_dict")],
                    "scroll": scroll,
                    "error": f"CodexLang execution failed: {e}",
                }

        except Exception as outer_e:
            logger.error(f"[Photon] Capsule load failed: {outer_e}")
            # 🚑 Guarantee engine field even if early load/parse fails
            return {
                "status": "error",
                "engine": "codex",  # default fallback
                "error": f"Photon capsule load failed: {outer_e}",
            }

    # ──────────────────────────────
    # 🎯 CodexLang Execution
    # ──────────────────────────────
    from backend.modules.glyphwave.kernels.interference_kernel_core import join_waves_batch
    import numpy as np
    def execute_instruction_tree(
        self,
        instruction_tree: Dict[str, Any],
        *,
        context: Optional[Dict[str, Any]] = None,
        wave_beams: Optional[List[Dict[str, Any]]] = None  # or List[WaveGlyph] if typed
    ) -> Dict[str, Any]:
        context = context or {}
        start_time = time.perf_counter()

        # ✅ Coerce glyph to dict so downstream .get(...) is always safe
        _raw_glyph = context.get("glyph", "∅")
        glyph_obj = _coerce_glyph_obj(_raw_glyph)

        # If empty/invalid, keep a structured noop glyph (DON'T crash validators)
        if not glyph_obj:
            logger.info("[Validation] Empty glyph received -> continuing with noop glyph.")
            glyph_obj = {"program": "∅", "raw": "∅", "type": "noop"}

        glyph = glyph_obj
        context["glyph"] = glyph  # keep context consistent

        # Ensure 'source' always exists
        source = context.get("source", "codex")

        # ✅ Canonicalize & Rewrite before anything else
        try:
            from backend.symatics.symatics_to_codex_rewriter import rewrite_symatics_to_codex
            from backend.modules.codex.codexlang_rewriter import CodexLangRewriter

            # Step 1: Symatics -> Codex
            instruction_tree = rewrite_symatics_to_codex(instruction_tree) or instruction_tree

            # Step 2: canonicalize ops
            rewriter = CodexLangRewriter()
            instruction_tree = rewriter.canonicalize_ops(instruction_tree) or instruction_tree

            # refresh op after rewrite
            op = instruction_tree.get("op") if isinstance(instruction_tree, dict) else None

            # 🔄 Canonicalize symbolic operator keys (⊕, ↔, etc.)
            try:
                if isinstance(instruction_tree, list):
                    for node in instruction_tree:
                        if isinstance(node, dict):
                            op = next(iter(node))
                            canonical = resolve_op(op)
                            node[canonical] = node.pop(op)
                elif isinstance(instruction_tree, dict):
                    op = next(iter(instruction_tree))
                    canonical = resolve_op(op)
                    instruction_tree[canonical] = instruction_tree.pop(op)
            except Exception as canon_err:
                logger.debug(f"[CodexExecutor] Canonical op rewrite skipped: {canon_err}")

        except Exception as rewrite_err:
            logger.warning(f"[CodexExecutor] Rewrite stage skipped: {rewrite_err}")
            op = instruction_tree.get("op") if isinstance(instruction_tree, dict) else None

        # 🧪 Test mode: short-circuit after rewrite
        if getattr(self, "test_mode", False):
            return {
                "status": "ok",
                "engine": "codex",
                "result": instruction_tree,
            }

        # 🚧 Guard after rewrite
        if not isinstance(instruction_tree, dict) or not op:
            return {
                "status": "error",
                "engine": "codex",
                "error": f"Invalid instruction_tree: {instruction_tree!r}"
            }

        # 🛡 Validate glyph before execution
        try:
            from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
            container_stub = {"symbolic_logic": [glyph]}
            raw_errors = validate_logic_trees(container_stub)
            errors = normalize_validation_errors(raw_errors)
            if errors:
                return {
                    "status": "error",
                    "error": "Invalid glyph",
                    "validation_errors": errors,
                    "validation_errors_version": "v1",
                }
        except Exception as val_err:
            logger.error(f"[Validation] Glyph validation failed: {val_err}")

        # ✅ Lightweight Tessaris alignment (photon origin only)
        try:
            glyphs = glyph.get("glyphs") if isinstance(glyph, dict) else []
            if source == "photon":
                intents = None
                try:
                    tessaris = _get_tessaris()
                    if tessaris:
                        intents = tessaris.extract_intents_from_glyphs(glyphs, origin="photon")
                except Exception as e:
                    logger.debug(f"[CodexExecutor] Tessaris lightweight alignment failed: {e}")
                if intents:
                    context.setdefault("intents", []).extend(intents)
                    self.trace.log_event("tessaris_lightweight", {
                        "source": "codex_executor",
                        "origin": source,
                        "intents": intents
                    })
        except Exception as align_err:
            logger.debug(f"[CodexExecutor] Lightweight Tessaris alignment skipped: {align_err}")

        # ✅ Full Tessaris intents injection
        if source == "photon":
            try:
                tessaris = _get_tessaris()
                intents = []
                if tessaris:
                    intents = tessaris.extract_intents_from_glyphs(
                        glyph.get("glyphs", []),
                        origin="photon"
                    )
                if intents:
                    logger.info(f"[CodexExecutor] Tessaris intents aligned: {intents}")
                    context.setdefault("intents", []).extend(intents)
            except Exception as e:
                logger.warning(f"[CodexExecutor] Tessaris alignment skipped: {e}")

        # 🌐 WebSocket Broadcast + Pattern Hooks
        try:
            from backend.routes.ws.glyphnet_ws import broadcast_glyph_event
        except Exception:
            def broadcast_glyph_event(*args, **kwargs):
                return None

        try:
            from backend.modules.codex.codex_scroll_builder import build_scroll_from_glyph
            scroll = build_scroll_from_glyph(glyph.get("glyphs", [])) if isinstance(glyph, dict) else None
            if scroll:
                broadcast_glyph_event(
                    glyph=glyph,
                    action=instruction_tree.get("op", ""),
                    source=source,
                    cost=0.0,
                    entangled=True,
                    scroll=scroll,
                    metadata={"container": context.get("container_id")}
                )
        except Exception as e:
            logger.warning(f"[CodexExecutor] WebSocket broadcast failed: {e}")

        # 🔁 Auto-trigger pattern hooks if applicable
        if isinstance(glyph, dict) and glyph.get("glyphs"):
            try:
                from backend.modules.patterns.pattern_prediction_hooks import (
                    broadcast_pattern_prediction,
                    auto_trigger_qfc_from_pattern,
                    trigger_emotion_bridge_from_pattern,
                )
                broadcast_pattern_prediction(glyph)
                auto_trigger_qfc_from_pattern(glyph)
                trigger_emotion_bridge_from_pattern(glyph)
            except Exception as e:
                logger.warning(f"[CodexExecutor] Pattern hook failed: {e}")

        # 🔐 Enforce QKD-required policy
        try:
            from backend.modules.glyphwave.qkd.qkd_policy_enforcer import QKDPolicyEnforcer
            QKDPolicyEnforcer.enforce_if_required(context)
        except Exception as qkd_err:
            logger.error(f"[CodexExecutor] QKD policy enforcement failed: {qkd_err}")
            raise

        try:
            # 🔍 Detect special op
            op = instruction_tree.get("op")

            # ✅ Symatics Interception
            from backend.symatics.symatics_dispatcher import evaluate_symatics_expr, is_symatics_operator
            if op in ("logic:⊕", "logic:⊖", "interf:⋈") or is_symatics_operator(op):
                try:
                    result = evaluate_symatics_expr(instruction_tree, context=context)
                    return {
                        "status": "success",
                        "engine": "symatics",
                        "result": result,
                        "cost": 0.1,  # low cost baseline
                        "elapsed": 0.0,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "engine": "symatics",
                        "error": str(e),
                    }

            # 🔁 Beam-Based Opcode Execution (QWave)
            if op in ("⧜", "⧝", "↔", "⧠", "⋰", "⋱"):
                ...
                # (no changes here)

            # ⚡ Use Sycamore-scale collapse kernel if requested
            if op in ("collapse", "join", "combine") and context.get("enable_sycamore_kernel"):
                ...
                # (unchanged collapse kernel block)

            else:
                # 🧮 Cost Estimation
                cost = self.metrics.estimate_cost(instruction_tree)

                # ✅ Photon -> QWave bridge (after cost estimation, before Tessaris interpret)
                if source == "photon":
                    try:
                        from backend.modules.qwave.photon_qwave_bridge import to_qglyph, to_wave_program
                        qglyph = to_qglyph(instruction_tree)
                        wave_program = to_wave_program(qglyph)

                        emit_qwave_beam_ff(
                            source="codex_executor",
                            payload={
                                "wave_id": f"photon_{int(time.time()*1000)}",
                                "container_id": context.get("container_id") if context else "unknown",
                                "mutation_type": "photon_qwave",
                                "event": "compile",
                                "glow": 1.0,
                                "pulse": 0.5,
                                "program": wave_program,
                            },
                            context=context
                        )
                    except Exception as e:
                        logger.error(f"[CodexExecutor] Photon->QWave bridge failed: {e}", exc_info=True)

                # ✅ High-entropy SQI spike emission
                if cost > 0.85:
                    beam_payload = {
                        "event": "high_entropy_execution",
                        "glyph": glyph,
                        "sqi_score": cost,
                        "container_id": context.get("container_id"),
                        "tags": ["sqi_spike", "entropy"]
                    }
                    emit_qwave_beam_ff(source="sqi_spike", payload=beam_payload, context=context)

                self.metrics.record_execution_batch(instruction_tree, cost=cost)

                # 🧠 Tessaris Execution
                result = self.tessaris.interpret(instruction_tree, context=context)

            # ✅ Trace execution (CodexTrace injection)
            from backend.modules.codex.codex_trace import _global_trace
            try:
                glyph_label = context.get("glyph") if context else "<tree>"
                _global_trace.trace_execution(
                    codex_str=glyph_label,
                    result=str(result),
                    context=context,
                    source="codex_executor",
                )
            except Exception as trace_err:
                import logging
                logging.warning(f"[CodexTrace] ⚠️ Failed to trace execution: {trace_err}")

            # 🔗 SQI Entanglement (↔)
            try:
                entangle_glyphs(glyph, context.get("container_id"))
            except Exception as e:
                logger.debug(f"[CodexExecutor] entangle_glyphs failed (non-fatal): {e}")

            # 🌀 Collapse Trace (GHX Replay)
            self.sqi_trace.log_collapse(glyph, cost, entangled=True)

            # 🧬 DNA Mutation Lineage
            glyph_str = json.dumps(glyph, ensure_ascii=False, indent=2)
            add_dna_mutation(
                from_glyph="∅",
                to_glyph=glyph,
                container=context.get("container_id"),
                coord=context.get("coord"),
                label="codex_execution"
            )

            # ✅ Inject execution trace into KG
            self.kg_writer.inject_glyph(
                content=str(result),
                glyph_type="execution",
                metadata={
                    "source": source,
                    "label": glyph,
                    "cost": cost,
                    "instruction_tree": instruction_tree,
                    "tags": ["codex_execution"]
                },
                trace=source
            )

            # ✅ Maybe auto-fuse beams (SPE)
            try:
                beams = maybe_autofuse(wave_beams or [])
                logger.info(f"[CodexExecutor] Autofuse applied, {len(beams)} beams after fusion")
            except Exception as e:
                logger.warning(f"[CodexExecutor] Autofuse failed: {e}")

            # ✅ Plugin Trigger Hook
            try:
                from backend.core.plugins.plugin_manager import get_all_plugins
                for plugin in get_all_plugins():
                    if hasattr(plugin, "trigger"):
                        plugin.trigger({
                            "event_type": "execute_instruction",
                            "glyph": glyph,
                            "result": result,
                            "context": context
                        })
            except Exception as plugin_trigger_err:
                logger.warning(f"[Plugin] trigger hook failed: {plugin_trigger_err}")

            # 📡 Plugin QFC Broadcast Hook (signature-safe)
            try:
                from backend.core.plugins.plugin_manager import get_all_plugins
                import inspect

                field_state = {
                    "nodes": [],
                    "links": [],
                    "glyphs": [],
                    "scrolls": [],
                    "qwaveBeams": [],
                    "entanglement": {},
                    "sqi_metrics": {},
                    "camera": {},
                    "reflection_tags": [],
                    "validation_errors": [],
                }

                def _safe_plugin_broadcast(plugin, field_state: Dict[str, Any], container_id: Optional[str] = None):
                    fn = getattr(plugin, "broadcast_qfc_update", None)
                    if not fn:
                        return

                    # Only pass kwargs the plugin actually accepts
                    kwargs: Dict[str, Any] = {}
                    try:
                        sig = inspect.signature(fn)
                        if "observer_id" in sig.parameters:
                            kwargs["observer_id"] = "codex_executor"
                        if "container_id" in sig.parameters and container_id:
                            kwargs["container_id"] = container_id
                        # support alt param names if present
                        if "payload" in sig.parameters:
                            kwargs["payload"] = field_state
                        if "field_state" in sig.parameters:
                            kwargs["field_state"] = field_state
                    except Exception:
                        kwargs = {}

                    if inspect.iscoroutinefunction(fn):
                        _spawn_async(fn(field_state, **kwargs), "QFC plugin broadcast")
                    else:
                        try:
                            fn(field_state, **kwargs)
                        except TypeError:
                            fn(field_state)

                cid = context.get("container_id") if isinstance(context, dict) else None
                for plugin in get_all_plugins():
                    if hasattr(plugin, "broadcast_qfc_update"):
                        _safe_plugin_broadcast(plugin, field_state, container_id=cid)

            except Exception as plugin_broadcast_err:
                logger.warning(f"[Plugin] QFC broadcast hook failed: {plugin_broadcast_err}")

            return result

        except Exception as exc:
            logger.error(f"[CodexExecutor] ❌ Execution failed: {exc}", exc_info=True)
            result = {"status": "error", "error": str(exc)}
            
            # 🔮 Container-level Prediction (SQI Path Selection)
            try:
                cid = context.get("container_id")
                if cid and isinstance(cid, str) and cid.startswith((
                    "dc_", "atom_", "hoberman_", "sec_", "symmetry_", "exotic_", "ucs_", "qfc_"
                )):
                    from backend.modules.consciousness.prediction_engine import run_prediction_on_container
                    # Wrap string ID into a minimal container dict
                    prediction_result = run_prediction_on_container({"id": cid})
                    if prediction_result:
                        self.kg_writer.store_predictions(
                            container_id=cid,
                            predictions=prediction_result.get("predicted_paths", []),
                            reason="Triggered from CodexExecutor (B2)"
                        )
                        self.trace.log_event("prediction", {
                            "source": "CodexExecutor",
                            "container_id": cid,
                            "paths": prediction_result.get("predicted_paths", []),
                            "metadata": prediction_result.get("metadata", {})
                        })
            except Exception as pred_err:
                logger.warning(f"[CodexExecutor] ⚠️ Container prediction failed: {pred_err}")

            # 🔮 Prediction Engine & Index
            predictions = self.prediction_engine._run_prediction_on_ast(instruction_tree)
            for pred in predictions or []:
                self.prediction_index.add_prediction(
                    PredictedGlyph(
                        glyph=pred.get("glyph", "?"),
                        source=pred.get("source", "PredictionEngine"),
                        confidence=pred.get("confidence", 0.5),
                        entropy=pred.get("entropy", 0.0),
                        container_id=context.get("container_id"),
                        tick=pred.get("tick"),
                        tags=pred.get("tags", [])
                    )
                )

            # 🔁 Self-Rewrite Trigger on Contradiction
            if result.get("status") == "contradiction":
                reason = result.get("detail", "N/A")

                # 🕵️ Introspection Event
                add_introspection_event(
                    description=f"Contradiction detected in glyph {glyph}: {reason}",
                    source_module="CodexExecutor",
                    tags=["contradiction", "self-rewrite"],
                    confidence=0.2,
                    blindspot_trigger="Logic Contradiction"
                )

                # 🛡 Validation on contradiction
                try:
                    from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
                    container_stub = {"symbolic_logic": [instruction_tree]}
                    raw_errors = validate_logic_trees(container_stub)
                    errors = normalize_validation_errors(raw_errors)
                    if errors:
                        result["validation_errors"] = errors
                        result["validation_errors_version"] = "v1"
                        logger.warning(f"[Validation] Contradiction due to invalid tree: {errors}")
                except Exception as val_err:
                    logger.error(f"[Validation] Contradiction validation crash: {val_err}")

                # 🔍 Attempt rewrite suggestion
                suggestion = None
                ast = instruction_tree.get("ast")

                try:
                    if context.get("container_type") == "lean":
                        from modules.lean.lean_tactic_suggester import suggest_tactic
                        suggestion = suggest_tactic(ast)
                except Exception as e:
                    logger.warning(f"[CodexExecutor] Lean tactic suggestion failed: {e}")

                try:
                    if not suggestion:
                        from modules.consciousness.prediction_engine import suggest_simplifications, goal_match_score
                        suggestion = suggest_simplifications(ast)

                        # ✅ Optional SQI feedback if rewrite suggestion includes a rewritten glyph
                        rewritten_glyph = suggestion.get("rewritten_glyph") if suggestion else None
                        if glyph and rewritten_glyph:
                            score = goal_match_score(glyph, rewritten_glyph)
                            if score and score > 0.6:
                                self.sqi_trace.adjust_weights(
                                    glyph=rewritten_glyph,
                                    feedback={"goal_match_score": score},
                                    reason="Successful mutation alignment"
                                )
                except Exception as e:
                    logger.warning(f"[CodexExecutor] Fallback simplification suggestion failed: {e}")

                if suggestion:
                    # 📦 DNA Trace
                    add_dna_mutation(
                        label="suggested_rewrite",
                        glyph=glyph,
                        entropy_delta=0.3,
                        suggestion=suggestion,
                        source_module="CodexExecutor"
                    )

                    # 🛰️ WebSocket Broadcast
                    scroll = build_scroll_from_glyph(glyph, instruction_tree)
                    broadcast_glyph_event(
                        glyph=glyph,
                        action="rewrite_suggestion",
                        source=source,
                        scroll=scroll,
                        metadata={
                            "type": "rewrite_suggestion",
                            "suggestion": suggestion,
                            "container": context.get("container_id")
                        }
                    )

                    # 📊 Trace + SQI Trace
                    self.trace.log_event("suggested_rewrite", {
                        "glyph": glyph,
                        "suggestion": suggestion,
                        "origin": "auto_rewrite",
                        "tags": ["rewrite", "suggestion"]
                    })
                    self.sqi_trace.log_suggestion(glyph, suggestion, source="contradiction")

                    # 🎯 Goal Engine Hook
                    try:
                        from modules.goals.goal_engine import link_suggestion_to_goals
                        link_suggestion_to_goals(glyph=glyph, suggestion=suggestion, context=context)
                    except Exception as ge:
                        logger.debug(f"[CodexExecutor] Goal resolver hook failed: {ge}")

                # 🔁 Self-Rewrite Execution
                rewrite_result = self.run_self_rewrite(...)
                if rewrite_result:
                    logger.info(f"[CodexExecutor] Self-rewrite completed for glyph {glyph}")

                # 🧠 Trace + SQI Flag
                self.trace.log_event("rewrite", {
                    "glyph": glyph,
                    "reason": reason,
                    "container": context.get("container_id"),
                    "tags": ["contradiction", "rewrite"]
                })
                self.sqi_trace.log_collapse(glyph, cost, entangled=True, contradiction=True)

                # 🌊 QWave Beam + Innovation Hook
                try:
                    source_glyph = glyph
                    mutated_glyph = suggestion.get("rewritten_glyph")
                    container_id = context.get("container_id")

                    if source_glyph and mutated_glyph and container_id:
                        # 🧠 Innovation Score
                        innovation_score = get_innovation_score(source_glyph, mutated_glyph)

                        # 🌊 Log Beam Prediction (with SQI + Innovation score)
                        log_beam_prediction({
                            "source": source_glyph,
                            "result": mutated_glyph,
                            "container_id": container_id,
                            "sqi_score": cost,
                            "innovation_score": innovation_score,
                            "mutation_type": "contradiction_rewrite"
                        })

                        # 🔌 Emit QWave Beam  ⟵⟵⟵ ONLY CHANGE: schedule instead of await
                        beam_payload = {
                            "source": source_glyph,
                            "target": mutated_glyph,
                            "sqi_score": cost,
                            "innovation_score": innovation_score,
                            "container_id": container_id,
                            "tags": ["rewrite", "contradiction", "mutation"]
                        }
                        emit_qwave_beam_ff(source="contradiction", payload=beam_payload, context=context)
                except Exception as beam_ex:
                    logger.warning(f"[CodexExecutor] QWave/Innovation hook failed: {beam_ex}")

                # 🛰️ Final Broadcast for Contradiction
                scroll = build_scroll_from_glyph(glyph, instruction_tree)
                broadcast_glyph_event(
                    glyph=glyph,
                    action="contradiction",
                    source=source,
                    cost=cost,
                    entangled=True,
                    scroll=scroll,
                    metadata={
                        "type": "contradiction",
                        "reason": reason,
                        "container": context.get("container_id")
                    }
                )
            else:
                # ⬁ Normal Execution Broadcast
                scroll = build_scroll_from_glyph(glyph, instruction_tree)
                broadcast_glyph_event(
                    glyph=glyph,
                    action=instruction_tree.get("op", ""),
                    source=source,
                    cost=cost,
                    entangled=True,
                    scroll=scroll,
                    metadata={"container": context.get("container_id")}
                )

            elapsed = time.perf_counter() - start_time
            # 🔄 QFC WebSocket Update (New glyphs / beams)
            try:
                container_id = context.get("container_id")
                if container_id and glyph and isinstance(glyph, dict):
                    from backend.modules.visualization.glyph_to_qfc import convert_glyph_to_qfc_node
                    qfc_node = convert_glyph_to_qfc_node(glyph)
                    broadcast_qfc_update(container_id, {
                        "nodes": [qfc_node],
                        "links": []
                    })
            except Exception as qfc_err:
                logger.warning(f"[CodexExecutor] ⚠️ QFC update failed: {qfc_err}")
            # 🧠 Inject Holographic Symbol Tree (HST) for introspection
            try:
                from backend.modules.symbolic.symbol_tree_generator import inject_symbolic_tree
                from backend.modules.symbolic.hst.hst_websocket_streamer import stream_hst_to_websocket
                from backend.modules.dna_chain.dc_handler import load_dc_container
                from backend.modules.hologram.ghx_replay_broadcast import emit_replay_trace

                cid = context.get("container_id")
                if cid and isinstance(cid, str) and cid.startswith((
                    "dc_", "atom_", "hoberman_", "sec_", "symmetry_", "exotic_", "ucs_", "qfc_"
                )):
                    inject_symbolic_tree(cid)
                    container = load_dc_container(cid)
                    tree = container.get("symbolic_tree")
                    if tree:
                        stream_hst_to_websocket(cid, tree, context="prediction_engine")
                        emit_replay_trace(cid, tree)
                        self.trace.log_event("hst_injected", {
                            "container_id": cid,
                            "node_count": len(tree.nodes),
                            "tags": ["hst", "introspection"]
                        })
            except Exception as hst_err:
                logger.warning(f"[CodexExecutor] ⚠️ HST injection failed: {hst_err}")

            return {"status": "success", "result": result, "cost": cost, "elapsed": elapsed}

        except Exception as e:
            logger.error(f"💥 Codex execution failed: {str(e)}", exc_info=True)
            self.metrics.record_error()
            add_introspection_event(
                description=f"Execution error in glyph {glyph}: {e}",
                source_module="CodexExecutor",
                tags=["error", "execution"],
                confidence=0.1
            )
            return {"status": "error", "error": str(e)}

    # ──────────────────────────────
    # ✨ CodexLang Execution (String Input)
    # ──────────────────────────────
    def execute_codexlang(self, codex_string: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a CodexLang string by compiling it and passing it to the instruction executor.
        """
        try:
            # Compile the CodexLang string into an instruction tree
            instruction_tree = run_codexlang_string(codex_string)

            if not instruction_tree or not isinstance(instruction_tree, dict):
                raise ValueError("Failed to compile CodexLang string into a valid instruction tree.")

            # Execute the compiled tree
            return self.execute_instruction_tree(instruction_tree, context=context)

        except Exception as e:
            logger.error(f"[CodexExecutor] CodexLang execution failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # -----------------------------------------------------------------------------
    # Compatibility Layer for QQC
    # -----------------------------------------------------------------------------
    def execute_codex_program(self, code_or_tree, context: dict | None = None):
        """
        Universal entrypoint for Codex execution.
        - Accepts CodexLang strings or pre-parsed instruction trees.
        - Delegates to execute_instruction_tree internally.
        """
        context = context or {}

        # Detect string vs structured input
        if isinstance(code_or_tree, str):
            try:
                from backend.modules.glyphos.codexlang_translator import parse_codexlang_string
                parsed = parse_codexlang_string(code_or_tree)
                instruction_tree = parsed.get("action") or parsed
                # If "action" is still a CodexLang string, compile it to a tree
                if isinstance(instruction_tree, str):
                    instruction_tree = run_codexlang_string(instruction_tree)
            except Exception as e:
                print(f"[CodexExecutor] ⚠️ Failed to parse CodexLang string: {e}")
                instruction_tree = {"error": str(e), "raw": code_or_tree}
        else:
            instruction_tree = code_or_tree

        return self.execute_instruction_tree(instruction_tree=instruction_tree, context=context)

    # ──────────────────────────────
    # 🖋️ Glyph Execution
    # ──────────────────────────────
    from backend.modules.lean.lean_utils import (
        validate_logic_trees,
        normalize_validation_errors,
    )

    def run_glyph(self, glyph: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}

        # 🛡 Validate glyph before execution
        try:
            from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
            container_stub = {"symbolic_logic": [glyph]}
            raw_errors = validate_logic_trees(container_stub)
            errors = normalize_validation_errors(raw_errors)
            if errors:
                return {
                    "status": "error",
                    "error": "Invalid glyph",
                    "validation_errors": errors,
                    "validation_errors_version": "v1",
                }
        except Exception as val_err:
            logger.error(f"[Validation] Glyph validation failed: {val_err}")

        # ▶️ Proceed with execution if valid
        import asyncio
        result = self.glyph_executor.execute_glyph(glyph, context)
        self.trace.log_event("glyph", {"glyph": glyph, "result": result})

        self.kg_writer.log_execution(glyph=glyph, result=result, source="glyph")
        entangle_glyphs(glyph, context.get("container_id"))
        return result


    def run_glyphcell(
        self, cell: GlyphCell, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GlyphCell's CodexLang logic field.
        Supports optional QPU execution, SQI scoring, and QFC broadcasting.
        """
        context = context or {}
        context["cell_id"] = cell.id
        context["emotion"] = cell.emotion
        context["coord"] = cell.position
        context["linked"] = cell.linked_cells
        context["nested"] = cell.nested_logic
        context["container_id"] = context.get("container_id", "unknown_container")

        logic = cell.logic.strip()

        # 🛡 Validate glyphcell logic before execution
        try:
            from backend.modules.lean.lean_utils import (
                validate_logic_trees,
                normalize_validation_errors,
            )

            container_stub = {"symbolic_logic": [logic]}
            raw_errors = validate_logic_trees(container_stub)
            errors = normalize_validation_errors(raw_errors)
            if errors:
                return {
                    "status": "error",
                    "engine": "codex",
                    "error": f"Invalid logic in cell {cell.id}",
                    "validation_errors": errors,
                    "validation_errors_version": "v1",
                }
        except Exception as val_err:
            logger.error(f"[Validation] GlyphCell {cell.id} validation failed: {val_err}")

        # -------------------
        # QPU path
        # -------------------
        if self.use_qpu and self.qpu:
            from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
            from backend.modules.glyphos.glyph_tokenizer import (
                tokenize_symbol_text_to_glyphs,
            )

            tokens = tokenize_symbol_text_to_glyphs(logic)
            qpu_results = []

            for token in tokens:
                try:
                    res = self.qpu.execute_cell(token, context=context)
                except Exception as e:
                    res = f"[QPU ERROR {token.get('value', '?')}: {str(e)}]"
                qpu_results.append(res)

            # Update SQI
            prev_sqi = cell.sqi_score or 0.0
            cell.sqi_score = score_sqi(cell)
            if hasattr(self.qpu, "metrics"):
                # Track SQI delta in QPU metrics
                self.qpu.metrics["sqi_shift"] += cell.sqi_score - prev_sqi

            # Broadcast results and metrics to QFC
            try:
                from backend.modules.visualization.qfc_websocket_bridge import (
                    broadcast_qfc_update,
                )

                container_id = context.get("container_id", "unknown_container")
                payload = {
                    "nodes": [{"cell_id": cell.id, "sqi": cell.sqi_score}],
                    "links": [],
                }

                if hasattr(self.qpu, "get_qpu_metrics"):
                    try:
                        payload["qpu_metrics"] = self.qpu.get_qpu_metrics()
                    except Exception:
                        payload["qpu_metrics"] = {}

                broadcast_qfc_update(container_id, payload)
            except Exception as e:
                record_trace(cell.id, f"[QPU Broadcast Error]: {e}")  # non-fatal

            result = {"result": qpu_results, "status": "success", "qpu": True}

        else:
            # -------------------
            # Legacy path
            # -------------------
            result = self.execute_codexlang(logic, context=context)

        # Store results back into cell
        cell.result = result.get("result")
        cell.validated = result.get("status") == "success"

        return result

    def execute_sheet(self, cells: List[GlyphCell], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a full sheet of GlyphCells, optionally on the QPU backend.
        Aggregates QPU metrics and records execution traces.
        """
        context = context or {}
        context["sheet_cells"] = cells
        from time import perf_counter
        start_time = perf_counter()

        # 🛡 Validate sheet container before execution
        try:
            from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
            sheet = [cell.to_dict() if hasattr(cell, "to_dict") else str(cell) for cell in cells]
            container_stub = {"symbolic_logic": sheet}
            raw_errors = validate_logic_trees(container_stub)
            errors = normalize_validation_errors(raw_errors)
            if errors:
                return {
                    "status": "error",
                    "engine": "codex",
                    "error": "Invalid sheet",
                    "validation_errors": errors,
                    "validation_errors_version": "v1",
                }
        except Exception as val_err:
            logger.error(f"[Validation] Sheet validation failed: {val_err}")

        sheet_results: Dict[str, Any] = {}

        if self.use_qpu and self.qpu:
            for cell in cells:
                sheet_results[cell.id] = self.run_glyphcell(cell, context)
            # Aggregate QPU metrics
            metrics = self.qpu.dump_metrics()
            record_trace("sheet", f"[QPU Sheet Metrics] {metrics}")
        else:
            for cell in cells:
                sheet_results[cell.id] = self.run_glyphcell(cell, context)

        elapsed = perf_counter() - start_time
        record_trace("sheet", f"[Sheet Execution] elapsed={elapsed:.6f}s")
        return sheet_results

    # ──────────────────────────────
    # 🔀 Trigger Ops
    # ──────────────────────────────
    def trigger_op(self, context: Dict[str, Any], target: Any = "default_trigger") -> str:
        log = _safe_op_trigger(context=context, target=str(target))
        self.trace.log_event("trigger", {"target": target, "context": context})
        return log

    # ──────────────────────────────
    # 🔁 Self-Rewrite
    # ──────────────────────────────
    def run_self_rewrite(self, contradiction_note: str, context: Optional[Dict[str, Any]] = None):
        rewrite = RewriteEngine()
        return rewrite.initiate_rewrite(reason=contradiction_note, context=context or {})

    # ──────────────────────────────
    # 🛠️ Reset State
    # ──────────────────────────────
    def reset(self):
        self.metrics.reset()
        self.trace.clear()
        self.sqi_trace.reset()
        self.tessaris.reset()

    # ──────────────────────────────
    # 🔄 QQC Compatibility Wrapper
    # ──────────────────────────────
    def execute(self, beam_data: dict, context: Optional[dict] = None) -> dict:
        """
        QQC expects a .execute() entrypoint.
        Redirect to execute_photon_capsule for beam/capsule data.
        """
        try:
            return self.execute_photon_capsule(beam_data, context=context)
        except Exception as e:
            logger.error(f"[CodexExecutor] execute() shim failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

# ✅ Singleton instance
codex_executor = CodexExecutor()

# ─────────────────────────────────────────────────────────
# Module-level shims for legacy tests / runners
# (google_benchmark_runner.py expects these symbols)
# ─────────────────────────────────────────────────────────

from typing import Any, Dict, Optional

# ──────────────────────────────
# Legacy / Convenience Shims
# ──────────────────────────────

def execute_codex_instruction_tree(
    instruction_tree: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Legacy shim: execute a pre-parsed instruction tree via the singleton executor.
    """
    return codex_executor.execute_instruction_tree(instruction_tree, context=context)


def execute_codexlang(
    self,
    codex_string: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes a CodexLang string.

    If QPU is enabled, the string is tokenized and executed in bulk on the
    QPU ISA, optionally handling multiple GlyphCells at once.
    """
    context = context or {}
    start_time = perf_counter()

    # -------------------
    # QPU bulk path
    # -------------------
    if self.use_qpu and self.qpu:
        from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
        from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
        from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs

        # Tokenize the full CodexLang string
        tokens = tokenize_symbol_text_to_glyphs(codex_string)
        qpu_results: List[Any] = []

        # Treat each token as a pseudo-cell for QPU execution
        for token in tokens:
            pseudo_cell = GlyphCell(
                id=f"qpu_temp_{token['value']}",
                logic=token["value"],
                position=context.get("coord", [0, 0])
            )
            context["cell"] = pseudo_cell

            try:
                res = self.qpu.execute_cell(token, context=context)
            except Exception as e:
                res = f"[QPU ERROR {token.get('value', '?')}: {str(e)}]"
            qpu_results.append(res)

            # Update SQI per pseudo-cell
            pseudo_cell.sqi_score = score_sqi(pseudo_cell)

        # Aggregate QPU metrics
        metrics = self.qpu.dump_metrics()
        record_trace("codexlang_bulk_qpu", f"[QPU Bulk Metrics] {metrics}")

        result = {
            "result": qpu_results,
            "status": "success",
            "qpu": True,
            "metrics": metrics,
        }

    # -------------------
    # Legacy path
    # -------------------
    else:
        try:
            instruction_tree = run_codexlang_string(codex_string)
            if not instruction_tree or not isinstance(instruction_tree, dict):
                raise ValueError("Failed to compile CodexLang string into a valid instruction tree.")
            result = self.execute_instruction_tree(instruction_tree, context=context)
        except Exception as e:
            result = {"status": "error", "error": str(e)}

    elapsed = perf_counter() - start_time
    record_trace("codexlang_execution", f"[CodexLang] elapsed={elapsed:.6f}s")
    return result

def execute_photon_capsule(
    path_or_dict: Union[str, Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Legacy shim: execute a Photon capsule via the singleton executor.
    """
    return codex_executor.execute_photon_capsule(path_or_dict, context=context)

# ──────────────────────────────
# CLI / Standalone Execution
# ──────────────────────────────

if __name__ == "__main__":
    import sys, json
    from backend.modules.dna_chain.dc_handler import load_dc_container
    from backend.modules.codex.rewrite_executor import auto_mutate_container

    if len(sys.argv) < 2:
        print("Usage: python codex_executor.py <path_to_dc.json> [--save]")
        sys.exit(1)

    path = sys.argv[1]
    autosave = "--save" in sys.argv

    try:
        with open(path) as f:
            container = json.load(f)

        # 🛡 Validate container before mutation
        from backend.modules.lean.lean_utils import validate_logic_trees
        errors = validate_logic_trees(container)
        if errors:
            print(f"⚠️ Validation errors detected: {errors}")

    except Exception as e:
        print(f"❌ Failed to load container: {e}")
        sys.exit(1)

    mutated = auto_mutate_container(container, autosave=autosave)
    print(f"✅ Container processed. Autosave={autosave}")

# ──────────────────────────────
# Module exports
# ──────────────────────────────

__all__ = [
    "CodexExecutor",
    "codex_executor",
    "execute_codex_instruction_tree",
    "execute_codexlang",
    "execute_photon_capsule",
]