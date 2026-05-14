# File: backend/modules/teleport/symbolic_teleport_trail.py

from typing import List, Optional, Dict, Any
from uuid import uuid4
from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree, SymbolicTreeNode
from backend.modules.knowledge_graph.kg_writer_singleton import inject_symbolic_trace
from backend.modules.codex.codex_metric import CodexMetrics
from backend.modules.teleport.portal_manager import TeleportPacket

class SymbolicTeleportTrail:
    """
    Captures the symbolic intention and meaning path during teleportation
    across containers. Attaches introspectable trails to each packet.
    """

    def __init__(self):
        self.trails: Dict[str, Dict[str, Any]] = {}

    def register_teleport_event(
        self,
        packet: TeleportPacket,
        origin_tree: Optional[SymbolicMeaningTree],
        reason: str,
        target_container_id: str,
    ) -> str:
        trail_id = str(uuid4())

        self.trails[trail_id] = {
            "packet_id": packet.packet_id,
            "origin_container": packet.origin_container_id,
            "target_container": target_container_id,
            "reason": reason,
            "symbol_tree_snapshot": origin_tree.to_dict() if origin_tree else None,
            "glyph_focus": packet.payload.get("focused_glyph"),
            "goal_state": packet.payload.get("goal_id"),
            "trail_id": trail_id,
        }

        # Inject into knowledge graph
        inject_symbolic_trace(
            container_id=target_container_id,
            trace_type="teleport_trail",
            metadata=self.trails[trail_id],
        )

        return trail_id

    def get_trail(self, trail_id: str) -> Optional[Dict[str, Any]]:
        return self.trails.get(trail_id)

    def all_trails(self) -> List[Dict[str, Any]]:
        return list(self.trails.values())

    def attach_to_packet(self, packet: TeleportPacket, trail_id: str):
        if trail_id in self.trails:
            packet.payload["symbolic_trail_id"] = trail_id


# Singleton instance
symbolic_teleport_trail = SymbolicTeleportTrail()