"""
📄 entanglement_fusion.py

🔗 Entanglement Fusion Engine for Multi-Agent AION & IGI  
Synchronizes entangled glyph weights, confidence metrics, and knowledge graph nodes across connected agents in real-time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌌 Entanglement Fusion - Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ↔ Bi-Directional Entangled Node Sync Across Agents  
✅ Live KG Confidence/Weight Propagation (WebSocket)  
✅ Gradient Feedback & Drift Weight Merging  
✅ Conflict Resolution via Consensus & Weighted Voting  
✅ Multi-Agent Fusion Bus (Agent IDs + Role Context)  
✅ Supports Collective IQ & Cross-Agent Learning  
✅ Integrated with BrainMapStreamer + PredictionEngine  
✅ Secure Fusion with Agent Identity & Token Validation  
"""

import asyncio
import json
from typing import Dict, List, Any

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphos.symbolic_entangler import get_entangled_for, get_entangled_targets
from backend.modules.knowledge_graph.brain_map_streamer import BrainMapStreamer
from backend.modules.websocket_manager import websocket_manager as broadcast_event
from backend.modules.glyphnet.identity_registry import validate_agent_token # 🔒 Secure auth
from backend.modules.soul.soul_laws import enforce_soul_laws  # 🛡 Ethical checks


class EntanglementFusion:
    def __init__(self):
        self.kg_writer = get_kg_writer()
        self.metrics = CodexMetrics()
        self.brain_streamer = BrainMapStreamer()

        # Live agent sessions: {agent_id: {"ws": websocket, "roles": [...]} }
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.fusion_locks = asyncio.Lock()

    # ──────────────────────────────
    # 🛰 Agent Registration & Identity Validation
    # ──────────────────────────────
    async def register_agent(self, agent_id: str, ws, token: str, roles: List[str]):
        """Register an agent after validating token and roles."""
        if not validate_agent_token(agent_id, token):
            raise PermissionError(f"❌ Unauthorized agent: {agent_id}")
        self.active_agents[agent_id] = {"ws": ws, "roles": roles}
        await self._notify_agent_join(agent_id)

    async def unregister_agent(self, agent_id: str):
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]
            await self._notify_agent_leave(agent_id)

    async def _notify_agent_join(self, agent_id: str):
        await broadcast_event({"type": "fusion_event", "event": "agent_join", "agent_id": agent_id})

    async def _notify_agent_leave(self, agent_id: str):
        await broadcast_event({"type": "fusion_event", "event": "agent_leave", "agent_id": agent_id})

    # ──────────────────────────────
    # ↔ Entangled Node Fusion
    # ──────────────────────────────
    async def fuse_entangled_nodes(self, glyph_id: str, confidence_delta: float, source_agent: str):
        """
        Propagates confidence updates across all entangled nodes for multi-agent KG sync.
        """
        async with self.fusion_locks:
            entangled_nodes = get_entangled_for(glyph_id)

            for node in entangled_nodes:
                # Update KG confidence locally
                self.metrics.adjust_confidence(node, confidence_delta)
                self.kg_writer.store_predictive_node(
                    container_id="fusion",
                    zone="entangled_sync",
                    glyph={"id": node, "entangled_from": glyph_id},
                    metadata={"fusion_confidence_delta": confidence_delta}
                )
                # Stream node update for UI glow refresh
                await self.brain_streamer.stream_node_update(node, status="neutral")

            # 🔗 NEW: Trigger GlyphNet fusion broadcast for multi-agent sync
            fusion_broadcast(
                node_id=glyph_id,
                confidence=self.metrics.get_confidence(glyph_id),
                entropy=self.kg_writer.get_node_metadata(glyph_id).get("entropy", 0.0),
                source_agent=source_agent,
                entangled_nodes=entangled_nodes,
                tags=["↔", "fusion"]
            )

            # Legacy broadcast for agent UI
            await broadcast_event({
                "type": "fusion_confidence_update",
                "glyph_id": glyph_id,
                "entangled_nodes": entangled_nodes,
                "confidence_delta": confidence_delta,
                "source_agent": source_agent,
            })

    # ──────────────────────────────
    # 🌐 Gradient Fusion Propagation
    # ──────────────────────────────
    async def propagate_gradient(self, glyph_id: str, gradient_vector: Dict[str, float], source_agent: str):
        """
        Propagates gradient re-weighting (goal drift correction, failures) across entangled glyph zones.
        """
        async with self.fusion_locks:
            entangled_nodes = get_entangled_for(glyph_id)

            for node in entangled_nodes:
                self.kg_writer.store_predictive_node(
                    container_id="fusion",
                    zone="gradient_sync",
                    glyph={"id": node},
                    metadata={"gradient": gradient_vector, "from_agent": source_agent}
                )
                await self.brain_streamer.stream_node_update(node)

            # 🔗 NEW: Cross-agent gradient sync broadcast
            fusion_broadcast(
                node_id=glyph_id,
                confidence=self.metrics.get_confidence(glyph_id),
                entropy=self.kg_writer.get_node_metadata(glyph_id).get("entropy", 0.0),
                source_agent=source_agent,
                entangled_nodes=entangled_nodes,
                tags=["↔", "gradient"]
            )

            await broadcast_event({
                "type": "fusion_gradient_update",
                "glyph_id": glyph_id,
                "gradient": gradient_vector,
                "entangled_nodes": entangled_nodes,
                "source_agent": source_agent,
            })

    # ──────────────────────────────
    # 🔀 Consensus & Conflict Resolution
    # ──────────────────────────────
    async def resolve_conflict(self, glyph_id: str, agent_updates: List[Dict]):
        """
        Resolve multi-agent conflicts using weighted voting based on confidence contribution.
        """
        weighted_sum = sum(u["confidence"] * u["weight"] for u in agent_updates)
        total_weight = sum(u["weight"] for u in agent_updates) or 1
        consensus_conf = round(weighted_sum / total_weight, 3)

        self.metrics.set_confidence(glyph_id, consensus_conf)
        self.kg_writer.store_predictive_node(
            container_id="fusion",
            zone="consensus_resolution",
            glyph={"id": glyph_id},
            metadata={"final_confidence": consensus_conf, "agents": len(agent_updates)}
        )

        await self.brain_streamer.stream_node_update(glyph_id)

        # 🔗 NEW: Fusion broadcast for consensus update
        fusion_broadcast(
            node_id=glyph_id,
            confidence=consensus_conf,
            entropy=self.kg_writer.get_node_metadata(glyph_id).get("entropy", 0.0),
            source_agent="consensus",
            entangled_nodes=[u["agent_id"] for u in agent_updates],
            tags=["⚖️", "fusion"]
        )

        await broadcast_event({
            "type": "fusion_consensus",
            "glyph_id": glyph_id,
            "confidence": consensus_conf,
            "agents": [u["agent_id"] for u in agent_updates],
        })

    # ──────────────────────────────
    # 🛡 SoulLaw Filtering
    # ──────────────────────────────
    async def enforce_ethics(self, glyph_id: str) -> bool:
        """Ensures glyph fusion updates comply with SoulLaw."""
        violations = enforce_soul_laws(glyph_id)
        if violations:
            await broadcast_event({
                "type": "fusion_violation",
                "glyph_id": glyph_id,
                "violations": violations
            })
            return False
        return True