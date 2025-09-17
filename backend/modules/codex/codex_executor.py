# 📁 backend/modules/codex/codex_executor.py

"""
⚡ Codex Executor – Ultimate Symbolic Execution Engine
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
from typing import Any, Dict, Optional, List
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
from backend.modules.consciousness.logic_prediction_utils import detect_contradictions
from backend.modules.dna_chain.dna_utils import extract_glyph_diff
from backend.modules.dna_chain.mutation_scorer import score_mutation
from backend.modules.glyphwave.core.beam_logger import log_beam_prediction
from backend.modules.glyphwave.emit_beam import emit_qwave_beam
from backend.modules.creative.innovation_scorer import get_innovation_score
from backend.modules.codex.codex_scroll_builder import build_scroll_from_glyph
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

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

# Use canonical emitter if available; provide a stub otherwise
try:
    from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam as _emit_qwave_beam
except Exception:  # fallback for test/CI
    async def _emit_qwave_beam(**kwargs):
        print(f"[QWaveEmitter] (stub) emit_qwave_beam {kwargs}")

def emit_qwave_beam_ff(**kwargs):
    _spawn_async(_emit_qwave_beam(**kwargs), "QWave emit (codex)")

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
    def __init__(self):
        self.metrics = CodexMetrics()
        self.trace = CodexTrace()
        self.glyph_executor = GlyphExecutor(state_manager=STATE)
        global TessarisEngine
        if TessarisEngine is None:
            from backend.modules.tessaris.tessaris_engine import TessarisEngine
        self.tessaris = TessarisEngine()
        self.kg_writer = get_kg_writer()
        global PredictionEngine
        if PredictionEngine is None:
            from backend.modules.consciousness.prediction_engine import PredictionEngine
        self.prediction_engine = PredictionEngine()
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
        glyph = context.get("glyph", "∅")

        # Make sure 'source' exists before any optional broadcast uses it
        source = context.get("source", "codex")

        # 🌐 WebSocket Broadcast + Pattern Hooks
        try:
            from backend.routes.ws.glyphnet_ws import broadcast_glyph_event
        except Exception:
            def broadcast_glyph_event(*args, **kwargs):
                return None  # no-op fallback

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

            # 🔁 Beam-Based Opcode Execution (QWave)
            if op in ("⧜", "⧝", "↔", "⧠", "⋰", "⋱"):  # or use SymbolicOpCode if available
                try:
                    from backend.codexcore_virtual.virtual_cpu_beam_core import execute_qwave_opcode
                    beam_result = execute_qwave_opcode(instruction_tree, context=context)
                    self.trace.log_event("beam_execution", {
                        "op": op,
                        "glyph": glyph,
                        "result": beam_result,
                        "tags": ["qwave", "symbolic"]
                    })
                    return {"status": "success", "result": beam_result, "cost": 0.0}
                except Exception as beam_exec_err:
                    logger.warning(f"[CodexExecutor] ⚠️ QWave beam opcode execution failed: {beam_exec_err}")

            # ⚡ Use Sycamore-scale collapse kernel if requested
            if op in ("collapse", "join", "combine") and context.get("enable_sycamore_kernel"):
                try:
                    if wave_beams:
                        # 🎯 Use the actual wave beams passed in from test
                        phases = np.array([w["phase"] for w in wave_beams], dtype=np.float32)
                        amplitudes = np.array([w["amplitude"] for w in wave_beams], dtype=np.float32)
                    else:
                        # 🔧 Fallback to random test waves
                        NUM_WAVES = 10000
                        LENGTH = 1
                        phases = np.random.uniform(-np.pi, np.pi, size=(NUM_WAVES, LENGTH)).astype(np.float32)
                        amplitudes = np.random.uniform(0.5, 1.5, size=(NUM_WAVES, LENGTH)).astype(np.float32)

                    wave_result = join_waves_batch(phases, amplitudes)
                    cost = float(wave_result["amplitude"].sum())
                    result = {
                        "phase": wave_result["phase"][:5].tolist(),
                        "amplitude": wave_result["amplitude"][:5].tolist()
                    }

                    self.trace.log_event("collapse_kernel", {
                        "waves": len(phases),
                        "cost": cost,
                        "phase_sample": result["phase"],
                        "amplitude_sample": result["amplitude"]
                    })

                except Exception as kernel_err:
                    logger.warning(f"[CodexExecutor] ⚠️ join_waves_batch failed: {kernel_err}")
                    cost = self.metrics.estimate_cost(instruction_tree)
                    if cost > 0.85:
                        beam_payload = {
                            "event": "high_entropy_execution",
                            "glyph": glyph,
                            "sqi_score": cost,
                            "container_id": context.get("container_id"),
                            "tags": ["sqi_spike", "entropy"]
                        }
                        _spawn_async(
                            _emit_qwave_beam(source="sqi_spike", payload=beam_payload, context=context),
                            label="QWave emit (codex)"
                        )
                    self.metrics.record_execution_batch(instruction_tree, cost=cost)
                    result = self.tessaris.interpret(instruction_tree, context=context)

                    # 🌊 Emit QWave Beam after fallback symbolic mutation
                    beam_payload = {
                        "mutation_type": "symbolic_mutation",
                        "original_glyph": glyph,
                        "mutated_tree": instruction_tree,
                        "container_id": context.get("container_id")
                    }
                    emit_qwave_beam_ff(source="mutation", payload=beam_payload, context=context)

                # 🔄 Plugin Mutation + Synthesis Hooks
                try:
                    from backend.core.plugins.plugin_manager import get_all_plugins
                    for plugin in get_all_plugins():
                        # Mutation hook
                        if hasattr(plugin, "mutate"):
                            logic_str = str(instruction_tree)
                            mutated_logic = plugin.mutate(logic_str)
                            if mutated_logic and mutated_logic != logic_str:
                                logger.debug(f"[Plugin] {plugin.__class__.__name__} mutated logic:\n{mutated_logic}")

                                # 🌊 Emit QWave Beam for plugin mutation
                                beam_payload = {
                                    "mutation_type": "plugin_mutation",
                                    "plugin": plugin.__class__.__name__,
                                    "original_logic": logic_str,
                                    "mutated_logic": mutated_logic,
                                    "container_id": context.get("container_id")
                                }
                                emit_qwave_beam_ff(source="mutation", payload=beam_payload, context=context)

                        # Synthesis hook
                        if hasattr(plugin, "synthesize"):
                            synthesis_goal = context.get("synthesis_goal", "evolve_instruction")
                            synthesized_logic = plugin.synthesize(synthesis_goal)
                            if synthesized_logic:
                                logger.debug(f"[Plugin] {plugin.__class__.__name__} synthesized logic: {synthesized_logic}")
                except Exception as plugin_hook_err:
                    logger.warning(f"[Plugin] mutation/synthesis hook failed: {plugin_hook_err}")

            else:
                # 🧮 Cost Estimation
                cost = self.metrics.estimate_cost(instruction_tree)
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
                to_glyph=glyph,  # dict or str is accepted; will be auto-serialized
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

            # 📡 Plugin QFC Broadcast Hook
            try:
                from backend.core.plugins.plugin_manager import get_all_plugins
                for plugin in get_all_plugins():
                    if hasattr(plugin, "broadcast_qfc_update"):
                        plugin.broadcast_qfc_update()
            except Exception as plugin_broadcast_err:
                logger.warning(f"[Plugin] QFC broadcast hook failed: {plugin_broadcast_err}")

            return result

        except Exception as exc:
            logger.error(f"[CodexExecutor] ❌ Execution failed: {exc}", exc_info=True)
            raise

            # 🔮 Container-level Prediction (SQI Path Selection)
            try:
                cid = context.get("container_id")
                if cid and isinstance(cid, str) and cid.startswith(("dc_", "atom_", "hoberman_", "sec_", "symmetry_", "exotic_", "ucs_", "qfc_")):
                    from backend.modules.consciousness.prediction_engine import PredictionEngine
                    prediction_result = PredictionEngine().run_prediction_on_container(cid)
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
            predictions = self.prediction_engine.analyze(instruction_tree, context=context)
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
                self.run_self_rewrite(f"Contradiction: {glyph}", context=context)

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

    # ──────────────────────────────
    # 🖋️ Glyph Execution
    # ──────────────────────────────
    def run_glyph(self, glyph: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        result = self.glyph_executor.execute_glyph(glyph, context)
        self.trace.log_event("glyph", {"glyph": glyph, "result": result})

        self.kg_writer.log_execution(glyph=glyph, result=result, source="glyph")
        entangle_glyphs(glyph, context.get("container_id"))
        return result

    def run_glyphcell(self, cell: GlyphCell, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GlyphCell's CodexLang logic field.
        """
        context = context or {}
        context["cell_id"] = cell.id
        context["emotion"] = cell.emotion
        context["coord"] = cell.position
        context["linked"] = cell.linked_cells
        context["nested"] = cell.nested_logic
        context["container_id"] = context.get("container_id", "unknown_container")

        # Use logic string as CodexLang source
        logic = cell.logic.strip()
        result = self.execute_codexlang(logic, context=context)

        # Store results back into cell
        cell.result = result.get("result")
        cell.validated = result.get("status") == "success"
        return result

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
        self.trace.reset()
        self.sqi_trace.reset()
        self.tessaris.reset()

# ✅ Singleton instance
codex_executor = CodexExecutor()

# ─────────────────────────────────────────────────────────
# Module-level shims for legacy tests / runners
# (google_benchmark_runner.py expects these symbols)
# ─────────────────────────────────────────────────────────

from typing import Any, Dict, Optional

def execute_codex_instruction_tree(instruction_tree: Dict[str, Any],
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Legacy shim: execute a pre-parsed instruction tree via the singleton executor.
    """
    return codex_executor.execute_instruction_tree(instruction_tree, context=context)

def execute_codexlang(codex_string: str,
                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Legacy shim: execute a CodexLang string via the singleton executor.
    """
    return codex_executor.execute_codexlang(codex_string, context=context)

if __name__ == "__main__":
    import sys, json
    from backend.modules.dna_chain.dc_handler import load_dc_container

    if len(sys.argv) < 2:
        print("Usage: python codex_executor.py <path_to_dc.json> [--save]")
        sys.exit(1)

    path = sys.argv[1]
    autosave = "--save" in sys.argv

    try:
        with open(path) as f:
            container = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load container: {e}")
        sys.exit(1)

    mutated = auto_mutate_container(container, autosave=autosave)

__all__ = [
    "CodexExecutor",
    "codex_executor",
    "execute_codex_instruction_tree",
    "execute_codexlang",
]