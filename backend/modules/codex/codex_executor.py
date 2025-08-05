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
import logging
from typing import Any, Dict, Optional

# Core imports
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.ops.op_trigger import op_trigger
from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.glyphos.glyph_executor import GlyphExecutor
from backend.modules.tessaris.tessaris_engine import TessarisEngine

# Intelligence & KG
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.knowledge_graph.indexes.introspection_index import add_introspection_event
from backend.modules.knowledge_graph.indexes.prediction_index import PredictionIndex, PredictedGlyph

# Memory & DNA
from backend.modules.consciousness.memory_bridge import MemoryBridge
from backend.modules.hexcore.memory_engine import store_memory
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.dna_chain.mutation_checker import add_dna_mutation

# SQI + Prediction
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.sqi.sqi_trace_logger import SQITraceLogger
from backend.modules.sqi.symbolic_entangler import entangle_glyphs

# GHX & GlyphNet
from backend.modules.glyphnet.glyphnet_ws import broadcast_glyph_event
from backend.modules.scrolls.scroll_builder import build_scroll_from_glyph

# Self-rewrite
from backend.modules.aion.rewrite_engine import RewriteEngine

DNA_SWITCH.register(__file__)

logger = logging.getLogger(__name__)


class CodexExecutor:
    def __init__(self):
        self.metrics = CodexMetrics()
        self.trace = CodexTrace()
        self.glyph_executor = GlyphExecutor()
        self.tessaris = TessarisEngine()
        self.memory_bridge = MemoryBridge()
        self.kg_writer = KnowledgeGraphWriter()
        self.prediction_engine = PredictionEngine()
        self.prediction_index = PredictionIndex()
        self.sqi_trace = SQITraceLogger()

    # ──────────────────────────────
    # 🎯 CodexLang Execution
    # ──────────────────────────────
    def execute_codexlang(self, codex_string: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        instruction_tree = run_codexlang_string(codex_string)
        return self.execute_instruction_tree(instruction_tree, context=context)

    def execute_instruction_tree(self, instruction_tree: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        start_time = time.perf_counter()
        glyph = context.get("glyph", "∅")
        source = context.get("source", "codex")

        try:
            # 🧮 Cost Estimation
            cost = self.metrics.estimate_cost(instruction_tree)
            self.metrics.record_execution_batch(instruction_tree, cost=cost)

            # 🧠 Tessaris Execution
            result = self.tessaris.interpret(instruction_tree, context=context)

            # 🔗 SQI Entanglement (↔)
            entangle_glyphs(glyph, context.get("container_id"))

            # 🌀 Collapse Trace (GHX Replay)
            self.sqi_trace.log_collapse(glyph, cost, entangled=True)

            # 🧬 DNA Mutation Lineage
            add_dna_mutation(label="codex_execution", glyph=glyph, entropy_delta=cost, source_module="CodexExecutor")

            # 📚 KG Logging
            self.kg_writer.log_execution(
                glyph=glyph,
                instruction_tree=instruction_tree,
                cost=cost,
                source=source,
                result=result,
                tags=["codex_execution"]
            )

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

            # 🕵️ Introspection: Blindspot/Confidence Drops
            if cost > 0.85:
                add_introspection_event(
                    description=f"High entropy detected ({cost:.2f}) during glyph execution: {glyph}",
                    source_module="CodexExecutor",
                    tags=["entropy", "alert"],
                    confidence=max(0, 1 - cost),
                    blindspot_trigger="Entropy Spike",
                    glyph_trace_ref=glyph
                )

            if result.get("status") == "contradiction":
                add_introspection_event(
                    description=f"Contradiction detected in glyph {glyph}: {result.get('detail','N/A')}",
                    source_module="CodexExecutor",
                    tags=["contradiction", "self-rewrite"],
                    confidence=0.2,
                    blindspot_trigger="Logic Contradiction"
                )
                self.run_self_rewrite(f"Contradiction: {glyph}", context=context)

            # 🧾 Scroll Builder (GHX Replay)
            scroll = build_scroll_from_glyph(glyph, instruction_tree)

            # 💾 Memory Storage
            store_memory({
                "label": "codex_execution",
                "content": {"glyph": glyph, "instruction_tree": instruction_tree, "result": result, "cost": cost}
            })

            # 🛰️ GHX Replay + WebSocket Broadcast
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
    # 🖋️ Glyph Execution
    # ──────────────────────────────
    def run_glyph(self, glyph: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        result = self.glyph_executor.execute_glyph(glyph, context)
        self.trace.log_event("glyph", {"glyph": glyph, "result": result})

        self.kg_writer.log_execution(glyph=glyph, result=result, source="glyph")
        entangle_glyphs(glyph, context.get("container_id"))
        return result

    # ──────────────────────────────
    # 🔀 Trigger Ops
    # ──────────────────────────────
    def trigger_op(self, context: Dict[str, Any], target: Any = "default_trigger") -> str:
        log = op_trigger(context=context, target=target)
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