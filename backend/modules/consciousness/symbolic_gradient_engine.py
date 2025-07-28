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
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.symbolic.glyph_types import GlyphEvent
from backend.modules.symbolic.symbolic_utils import trace_back_causal_chain
from backend.modules.memory_engine import MemoryBridge
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.goals.goal_engine import GoalEngine
from backend.modules.dna.dna_writer import write_gradient_mutation
from backend.modules.consciousness.gradient_entanglement_adapter import GradientEntanglementAdapter
from backend.modules.knowledge_graph.brain_map_streamer import BrainMapStreamer  # ✅ Live KG updates
from backend.modules.knowledge_graph.entanglement_fusion import EntanglementFusion  # ✅ NEW for multi-agent sync

class SymbolicGradientEngine:
    def __init__(self):
        self.kg_writer = KnowledgeGraphWriter()
        self.memory_bridge = MemoryBridge()
        self.goal_engine = GoalEngine()
        self.codex_metrics = CodexMetrics()
        self.entanglement_adapter = GradientEntanglementAdapter()
        self.brain_streamer = BrainMapStreamer()  # ✅ Live WebSocket KG weight streaming
        self.entanglement_fusion = EntanglementFusion()  # ✅ Multi-Agent KG fusion

    # ──────────────────────────────────────────────
    # ⮌ BACKPROPAGATION: FAILURE TRACE
    # ──────────────────────────────────────────────
    async def process_failure_trace(self, failed_glyph: GlyphEvent, reason: str, agent_id: str = "local"):
        """Backpropagate symbolic trace after failure or contradiction."""
        chain = trace_back_causal_chain(failed_glyph)
        for glyph in reversed(chain):
            self._inject_gradient_feedback(glyph, reason)

            glyph_id = getattr(glyph, 'glyph_id', None) or getattr(glyph, 'id', 'unknown')
            self.entanglement_adapter.propagate_gradient_feedback(glyph_id, f"Failure trace: {reason}")

            # 🔴 Stream failure node update to BrainMap UI
            await self.brain_streamer.stream_node_update(glyph_id, status="failure")

            # 🌐 Sync entangled feedback across agents
            await self.entanglement_fusion.fuse_entangled_nodes(
                glyph_id=glyph_id, confidence_delta=-0.1, source_agent=agent_id
            )

    def _inject_gradient_feedback(self, glyph: Union[GlyphEvent, Dict], reason: str):
        """Store symbolic feedback in KG and DNA mutation suggestions."""
        container_id = getattr(glyph, 'container_id', glyph.get('container', 'unknown'))
        glyph_id = getattr(glyph, 'glyph_id', glyph.get('id', 'unknown'))

        # KG injection
        self.kg_writer.store_predictive_node(
            container_id=container_id,
            zone='failure_gradient',
            glyph=glyph,
            metadata={
                'reason': reason,
                'entropy_delta': getattr(glyph, 'entropy', glyph.get('entropy', None)),
            }
        )

        # DNA mutation suggestion
        write_gradient_mutation(container_id=container_id, glyph_id=glyph_id, failure_reason=reason)

        # Blindspot metric logging
        self.codex_metrics.record_blindspot_event(glyph)

    # ──────────────────────────────────────────────
    # 🧭 GOAL DRIFT DETECTION
    # ──────────────────────────────────────────────
    async def analyze_goal_drift(self, goal_id: str, glyph_trace: List[GlyphEvent], agent_id: str = "local"):
        """Detects symbolic drift and streams drift-weight feedback to KG + UI + multi-agent sync."""
        original_goal = self.goal_engine.get_goal(goal_id)
        if not original_goal:
            return

        for glyph in glyph_trace:
            if glyph.operator == '🧭':
                distance = self._measure_drift(glyph, original_goal)
                if distance > 0.6:
                    self._inject_gradient_feedback(glyph, f"Goal drift detected: Δ={distance:.2f}")

                    glyph_id = getattr(glyph, 'glyph_id', None) or getattr(glyph, 'id', 'unknown')
                    self.entanglement_adapter.propagate_gradient_feedback(glyph_id, f"Goal drift Δ={distance:.2f}")

                    # 🔴 Stream drift to BrainMap UI
                    await self.brain_streamer.stream_node_update(glyph_id, status="failure")

                    # 🌐 Sync drift across agents
                    await self.entanglement_fusion.propagate_gradient(
                        glyph_id=glyph_id,
                        gradient_data={"drift_delta": -distance, "reason": "Goal drift"},
                        source_agent=agent_id
                    )

    def _measure_drift(self, glyph: GlyphEvent, goal: Dict) -> float:
        if not hasattr(glyph, 'vector') or 'vector' not in goal:
            return 0.0
        return abs(sum((a - b) ** 2 for a, b in zip(glyph.vector, goal['vector']))) ** 0.5

    # ──────────────────────────────────────────────
    # 🏆 SUCCESS TRACE REINFORCEMENT
    # ──────────────────────────────────────────────
    async def reinforce_success_trace(self, glyph_trace: List[GlyphEvent], agent_id: str = "local"):
        """Reinforce high-confidence glyphs into KG + BrainMap UI + Multi-Agent Fusion."""
        for glyph in glyph_trace:
            self.kg_writer.store_predictive_node(
                container_id=glyph.container_id,
                zone='success_gradient',
                glyph=glyph,
                metadata={'reinforced': True}
            )

            glyph_id = getattr(glyph, 'glyph_id', None) or getattr(glyph, 'id', 'unknown')
            self.entanglement_adapter.propagate_gradient_feedback(glyph_id, "Reinforce successful entangled path")

            # 🔴 Stream success highlight to BrainMap UI
            await self.brain_streamer.stream_node_update(glyph_id, status="success")

            # 🌐 Sync reinforcement across agents
            await self.entanglement_fusion.fuse_entangled_nodes(
                glyph_id=glyph_id, confidence_delta=+0.1, source_agent=agent_id
            )

    # ──────────────────────────────────────────────
    # ⚛ QGLYPH COLLAPSE FEEDBACK → KG WEIGHTING
    # ──────────────────────────────────────────────
    async def handle_qglyph_collapse(self, collapse_result: Dict, agent_id: str = "local"):
        """
        Accepts QGlyph collapse and updates:
        • KG predictive nodes  
        • CodexMetrics weights  
        • Entangled ancestry confidence  
        • BrainMap ripple visualization 🌌  
        • Multi-Agent fusion via EntanglementFusion
        """
        qglyph_id = collapse_result.get("selected", {}).get("qbit_id", "unknown")
        container_id = collapse_result.get("selected", {}).get("container", "unknown")
        collapsed_value = collapse_result.get("selected", {}).get("collapsed")

        # Store collapse feedback in KG
        self.kg_writer.store_predictive_node(
            container_id=container_id,
            zone='collapse_feedback',
            glyph={
                'id': qglyph_id,
                'collapsed_value': collapsed_value,
                'coord': collapse_result.get("selected", {}).get("coord"),
            },
            metadata={
                'observer_bias': collapse_result.get("observer_bias"),
                'ranked_paths': collapse_result.get("ranked"),
                'collapse_trace': True
            }
        )

        # Update CodexMetrics
        self.codex_metrics.record_confidence_event(
            glyph_id=qglyph_id,
            delta=collapse_result.get("observer_bias", {}).get("decision", 0)
        )

        # ↔ Propagate entangled collapse weighting
        self.entanglement_adapter.propagate_from_collapse(collapse_result)

        # 🌌 Stream collapse ripple to BrainMap UI
        await self.brain_streamer.stream_collapse_ripple(collapse_result)

        # 🌐 Sync collapse confidence weighting across agents
        await self.entanglement_fusion.fuse_entangled_nodes(
            glyph_id=qglyph_id,
            confidence_delta=+0.05,
            source_agent=agent_id
        )