"""
📄 symbolic_gradient_engine.py

🧠 Symbolic Gradient Engine for AION & IGI Systems  
Handles symbolic backpropagation-like feedback, goal drift correction, and adaptive reasoning over glyph traces.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔮 Symbolic Gradient Engine – Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Backpropagate Failures Across Glyph Traces (⮌)  
✅ ↔ Inject Gradient Feedback into Knowledge Graph & Entangled Links  
✅ Goal Drift Detection & Adaptive Correction (🧭 ➔ 🎯)  
✅ DNA Mutation Suggestions for Failing Glyphs (🧬)  
✅ Codex Metrics Integration (Blindspot & Entropy Events)  
✅ Reinforce Successful Glyph Chains (🏆)  
✅ Multi-Vector Distance & Drift Measurement (Advanced Ready)  
✅ ⚛ Live QGlyph Collapse Feedback → KG Weight Adjustment  
✅ 🔴 Bi-Directional KG Weight Streaming → BrainMap Visualization  
✅ 🌐 Multi-Agent EntanglementFusion Confidence Sync  
"""

from typing import List, Dict, Union
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.symbolic_engine.symbolic_utils import trace_back_causal_chain
from backend.modules.consciousness.memory_bridge import MemoryBridge  # ✅ Fixed path
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.dna_chain.dna_writer import write_gradient_mutation  # ✅ Updated path
from backend.modules.consciousness.gradient_entanglement_adapter import GradientEntanglementAdapter
from backend.modules.knowledge_graph.brain_map_streamer import BrainMapStreamer  # ✅ Live KG updates
from backend.modules.knowledge_graph.entanglement_fusion import EntanglementFusion  # ✅ Multi-agent sync

# 🔧 Local fallback GlyphEvent
class GlyphEvent:
    def __init__(self, glyph_id: str, container_id: str, vector=None, entropy=None, operator=None, metadata=None):
        self.glyph_id = glyph_id
        self.container_id = container_id
        self.vector = vector or []
        self.entropy = entropy
        self.operator = operator
        self.metadata = metadata or {}


class SymbolicGradientEngine:
    def __init__(self, container_id: str = "default-gradient"):
        """
        Initialize Symbolic Gradient Engine tied to a container.
        Args:
            container_id (str): Container context for gradient operations.
        """
        self.container_id = container_id
        self.kg_writer = get_kg_writer()
        self.memory_bridge = MemoryBridge(container_id=self.container_id)  # ✅ FIXED: Pass container_id
        from backend.modules.skills.goal_engine import GoalEngine
        self.goal_engine = GoalEngine()
        self.codex_metrics = CodexMetrics()
        self.entanglement_adapter = GradientEntanglementAdapter()
        self.brain_streamer = BrainMapStreamer()  # ✅ WebSocket KG streaming
        self.entanglement_fusion = EntanglementFusion()  # ✅ Multi-Agent KG sync

    # ──────────────────────────────────────────────
    # ⮌ FAILURE BACKPROPAGATION
    # ──────────────────────────────────────────────
    async def process_failure_trace(self, failed_glyph: GlyphEvent, reason: str, agent_id: str = "local"):
        chain = trace_back_causal_chain(failed_glyph)
        for glyph in reversed(chain):
            self._inject_gradient_feedback(glyph, reason)
            glyph_id = getattr(glyph, "glyph_id", getattr(glyph, "id", "unknown"))
            self.entanglement_adapter.propagate_gradient_feedback(glyph_id, f"Failure trace: {reason}")
            await self.brain_streamer.stream_node_update(glyph_id, status="failure")
            await self.entanglement_fusion.fuse_entangled_nodes(
                glyph_id=glyph_id, confidence_delta=-0.1, source_agent=agent_id
            )

    def _inject_gradient_feedback(self, glyph: Union[GlyphEvent, Dict], reason: str):
        container_id = getattr(glyph, "container_id", glyph.get("container", self.container_id))
        glyph_id = getattr(glyph, "glyph_id", glyph.get("id", "unknown"))
        self.kg_writer.store_predictive_node(
            container_id=container_id,
            zone="failure_gradient",
            glyph=glyph,
            metadata={
                "reason": reason,
                "entropy_delta": getattr(glyph, "entropy", glyph.get("entropy", None)),
            },
        )
        write_gradient_mutation(container_id=container_id, glyph_id=glyph_id, failure_reason=reason)
        self.codex_metrics.record_blindspot_event(glyph)

    # ──────────────────────────────────────────────
    # 🧭 GOAL DRIFT DETECTION
    # ──────────────────────────────────────────────
    async def analyze_goal_drift(self, goal_id: str, glyph_trace: List[GlyphEvent], agent_id: str = "local"):
        """Detect symbolic drift and stream drift-weight feedback to KG + UI + multi-agent sync."""
        original_goal = self.goal_engine.get_goal(goal_id)
        if not original_goal:
            return

        for glyph in glyph_trace:
            if glyph.operator == "🧭":
                distance = self._measure_drift(glyph, original_goal)
                if distance > 0.6:
                    self._inject_gradient_feedback(glyph, f"Goal drift detected: Δ={distance:.2f}")

                    glyph_id = getattr(glyph, "glyph_id", getattr(glyph, "id", "unknown"))
                    self.entanglement_adapter.propagate_gradient_feedback(glyph_id, f"Goal drift Δ={distance:.2f}")

                    # 🔴 Update BrainMap UI
                    await self.brain_streamer.stream_node_update(glyph_id, status="failure")

                    # 🌐 Multi-agent sync
                    await self.entanglement_fusion.propagate_gradient(
                        glyph_id=glyph_id,
                        gradient_data={"drift_delta": -distance, "reason": "Goal drift"},
                        source_agent=agent_id,
                    )

    def _measure_drift(self, glyph: GlyphEvent, goal: Dict) -> float:
        if not hasattr(glyph, "vector") or "vector" not in goal:
            return 0.0
        return abs(sum((a - b) ** 2 for a, b in zip(glyph.vector, goal["vector"]))) ** 0.5

    # ──────────────────────────────────────────────
    # 🏆 SUCCESS REINFORCEMENT
    # ──────────────────────────────────────────────
    async def reinforce_success_trace(self, glyph_trace: List[GlyphEvent], agent_id: str = "local"):
        """Reinforce high-confidence glyphs into KG + BrainMap UI + Multi-Agent Fusion."""
        for glyph in glyph_trace:
            self.kg_writer.store_predictive_node(
                container_id=glyph.container_id,
                zone="success_gradient",
                glyph=glyph,
                metadata={"reinforced": True},
            )

            glyph_id = getattr(glyph, "glyph_id", getattr(glyph, "id", "unknown"))
            self.entanglement_adapter.propagate_gradient_feedback(glyph_id, "Reinforce successful entangled path")

            # 🔴 Update BrainMap UI
            await self.brain_streamer.stream_node_update(glyph_id, status="success")

            # 🌐 Multi-agent sync
            await self.entanglement_fusion.fuse_entangled_nodes(
                glyph_id=glyph_id, confidence_delta=+0.1, source_agent=agent_id
            )

    # ──────────────────────────────────────────────
    # ⚛ QGLYPH COLLAPSE FEEDBACK
    # ──────────────────────────────────────────────
    async def handle_qglyph_collapse(self, collapse_result: Dict, agent_id: str = "local"):
        """Handle QGlyph collapse feedback and propagate to KG, CodexMetrics, BrainMap, and fusion."""
        qglyph_id = collapse_result.get("selected", {}).get("qbit_id", "unknown")
        container_id = collapse_result.get("selected", {}).get("container", "unknown")
        collapsed_value = collapse_result.get("selected", {}).get("collapsed")

        self.kg_writer.store_predictive_node(
            container_id=container_id,
            zone="collapse_feedback",
            glyph={"id": qglyph_id, "collapsed_value": collapsed_value},
            metadata={
                "observer_bias": collapse_result.get("observer_bias"),
                "ranked_paths": collapse_result.get("ranked"),
                "collapse_trace": True,
            },
        )

        self.codex_metrics.record_confidence_event(
            glyph_id=qglyph_id,
            delta=collapse_result.get("observer_bias", {}).get("decision", 0),
        )

        self.entanglement_adapter.propagate_from_collapse(collapse_result)
        await self.brain_streamer.stream_collapse_ripple(collapse_result)
        await self.entanglement_fusion.fuse_entangled_nodes(
            glyph_id=qglyph_id, confidence_delta=+0.05, source_agent=agent_id
        )