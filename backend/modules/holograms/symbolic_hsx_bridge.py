import uuid
from datetime import datetime
from typing import Dict, List, Optional

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.identity.avatar_registry import get_avatar_identity
from backend.modules.hologram.ghx_packet_validator import GHXPacketValidator
from backend.modules.glyphnet.glyphnet_ws import broadcast_ghx_overlay

class SymbolicHSXBridge:
    def __init__(self, avatar_id: str, ghx_packet: Dict):
        self.avatar_id = avatar_id
        self.ghx_packet = ghx_packet
        self.identity = get_avatar_identity(avatar_id)
        self.validator = GHXPacketValidator(ghx_packet)

    def inject_identity_trails(self) -> Dict:
        """
        Append symbolic identity trail into GHX nodes.
        """
        valid, _, _ = self.validator.validate()
        if not valid:
            raise ValueError("Invalid GHX packet")

        for node in self.ghx_packet.get("nodes", []):
            if "symbolic_trail" not in node:
                node["symbolic_trail"] = []
            node["symbolic_trail"].append({
                "by": self.identity.get("name", "unknown"),
                "avatar_id": self.avatar_id,
                "timestamp": datetime.utcnow().isoformat(),
                "signature": self.identity.get("signature", str(uuid.uuid4()))
            })

        return self.ghx_packet

    def score_overlay_paths(self) -> List[Dict]:
        """
        Score GHX nodes for symbolic weight and goal alignment.
        """
        results = []
        for node in self.ghx_packet.get("nodes", []):
            symbol = node.get("symbol")
            cost = node.get("cost", 0)
            entropy = node.get("entropy", 0.0)

            scores = CodexMetrics.score_symbol(symbol)
            node["goal_alignment_score"] = scores.get("goal_match_score")
            node["symbolic_weight"] = scores.get("symbolic_weight")

            results.append({
                "glyph_id": node["glyph_id"],
                "symbol": symbol,
                "alignment": node["goal_alignment_score"],
                "weight": node["symbolic_weight"],
                "entropy": entropy,
                "cost": cost,
            })

        return results

    def broadcast_overlay(self):
        """
        Send GHX overlay packet to connected clients.
        """
        payload = {
            "type": "ghx_overlay",
            "avatar": self.identity,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": self.ghx_packet.get("nodes", []),
            "projection_id": self.ghx_packet.get("projection_id"),
        }
        broadcast_ghx_overlay(payload)