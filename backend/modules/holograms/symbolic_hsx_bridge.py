# ──────────────────────────────────────────────
#  Tessaris • Symbolic HSX Bridge (HQCE Stage 5)
#  Connects symbolic cognition layer → GHX field overlays
#  Computes semantic κ (gravity wells) and broadcasts overlay maps
# ──────────────────────────────────────────────
import uuid
import math
import logging
from datetime import datetime
from typing import Dict, List, Optional

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.identity.avatar_registry import get_avatar_identity
from backend.modules.holograms.ghx_packet_validator import GHXPacketValidator
from backend.modules.glyphnet.glyphnet_ws import broadcast_ghx_overlay
from backend.modules.holograms.morphic_ledger import morphic_ledger

# ✅ WebSocket HUD import
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:
    def send_codex_ws_event(event_type: str, payload: dict):
        print(f"[Fallback HUD] {event_type} → {payload}")

logger = logging.getLogger(__name__)


class SymbolicHSXBridge:
    """Bridges symbolic cognition metrics into holographic overlays."""

    def __init__(self, avatar_id: str, ghx_packet: Dict[str, any]):
        self.avatar_id = avatar_id
        self.ghx_packet = ghx_packet
        self.identity = get_avatar_identity(avatar_id)
        self.validator = GHXPacketValidator(ghx_packet)

    # ──────────────────────────────────────────────
    #  Inject symbolic identity / trail metadata
    # ──────────────────────────────────────────────
    def inject_identity_trails(self) -> Dict:
        """Append symbolic identity trail into GHX nodes."""
        valid, _, _ = self.validator.validate()
        if not valid:
            raise ValueError("Invalid GHX packet")

        for node in self.ghx_packet.get("nodes", []):
            node.setdefault("symbolic_trail", []).append({
                "by": self.identity.get("name", "unknown"),
                "avatar_id": self.avatar_id,
                "timestamp": datetime.utcnow().isoformat(),
                "signature": self.identity.get("signature", str(uuid.uuid4()))
            })

        logger.debug(
            f"[SymbolicHSXBridge] Injected identity trails for "
            f"{len(self.ghx_packet.get('nodes', []))} nodes."
        )
        return self.ghx_packet

    # ──────────────────────────────────────────────
    #  Symbolic scoring and semantic κ computation
    # ──────────────────────────────────────────────
    def score_overlay_paths(self) -> List[Dict]:
        """
        Score GHX nodes for symbolic weight and goal alignment,
        and compute semantic curvature κₛ (semantic gravity).
        """
        results = []
        weights, entropies = [], []

        for node in self.ghx_packet.get("nodes", []):
            symbol = node.get("symbol")
            entropy = float(node.get("entropy", 0.0))
            cost = float(node.get("cost", 0.0))

            scores = CodexMetrics.score_symbol(symbol)
            w = scores.get("symbolic_weight", 0.0)
            a = scores.get("goal_match_score", 0.0)

            node.update({
                "goal_alignment_score": a,
                "symbolic_weight": w,
                "semantic_kappa": None,  # placeholder until computed
            })

            weights.append(w)
            entropies.append(entropy)
            results.append({
                "glyph_id": node.get("glyph_id"),
                "symbol": symbol,
                "alignment": a,
                "weight": w,
                "entropy": entropy,
                "cost": cost,
            })

        # Compute semantic curvature κₛ
        if weights:
            mean_w = sum(weights) / len(weights)
            var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)
            mean_entropy = sum(entropies) / len(entropies) if entropies else 0.0
            κs = math.tanh(mean_w / (1.0 + 10.0 * var_w + mean_entropy))

            for node in self.ghx_packet.get("nodes", []):
                node["semantic_kappa"] = κs

            logger.info(f"[SymbolicHSXBridge] Computed semantic κₛ={κs:.4f}")
        else:
            κs = 0.0
            var_w, mean_w, mean_entropy = 0.0, 0.0, 0.0
            logger.warning(
                "[SymbolicHSXBridge] No weights available for semantic curvature computation."
            )

        # Write summary into Morphic Ledger
        morphic_ledger.append({
            "psi": mean_entropy,
            "kappa": κs,
            "T": 1.0,
            "coherence": mean_w,
            "gradient": var_w ** 0.5,
            "stability": mean_w / (1.0 + var_w),
            "metadata": {"origin": "SymbolicHSXBridge"},
        }, observer=self.avatar_id)

        # 🧠 Compute semantic gravity map and broadcast
        gravity_map = self.compute_semantic_gravity()
        try:
            send_codex_ws_event("semantic_gravity_update", gravity_map)
        except Exception as e:
            logger.warning(f"[SymbolicHSXBridge] WS gravity broadcast failed: {e}")

        return results

    # ──────────────────────────────────────────────
    #  Semantic Gravity Computation (HQCE Stage 5)
    # ──────────────────────────────────────────────
    def compute_semantic_gravity(self) -> Dict[str, any]:
        """
        Compute local semantic gravity wells for visualization.
        Returns dict: { 'clusters': [...], 'field_strength': float }
        """
        nodes = self.ghx_packet.get("nodes", [])
        if not nodes:
            return {"clusters": [], "field_strength": 0.0}

        clusters = []
        for node in nodes:
            κs = node.get("semantic_kappa", 0.0)
            w = node.get("symbolic_weight", 0.0)
            entropy = node.get("entropy", 0.0)
            cluster_strength = (w * (1 - entropy)) * (1 + κs)
            clusters.append({
                "glyph_id": node.get("glyph_id"),
                "symbol": node.get("symbol"),
                "gravity_strength": round(cluster_strength, 4),
                "semantic_kappa": κs,
                "weight": w,
                "entropy": entropy,
            })

        # Normalize gravity strengths
        total_strength = sum(c["gravity_strength"] for c in clusters)
        for c in clusters:
            c["gravity_strength"] = c["gravity_strength"] / max(total_strength, 1e-9)

        field_strength = round(sum(c["gravity_strength"] for c in clusters) / len(clusters), 5)
        gravity_map = {
            "timestamp": datetime.utcnow().isoformat(),
            "avatar": self.avatar_id,
            "clusters": clusters,
            "field_strength": field_strength,
        }

        logger.debug(
            f"[SymbolicHSXBridge] Semantic gravity computed for {len(clusters)} nodes "
            f"(field_strength={field_strength:.4f})"
        )
        return gravity_map

    # ──────────────────────────────────────────────
    #  Broadcast to GHX overlay clients
    # ──────────────────────────────────────────────
    def broadcast_overlay(self):
        """Send GHX overlay packet to connected clients."""
        payload = {
            "type": "ghx_overlay",
            "avatar": self.identity,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": self.ghx_packet.get("nodes", []),
            "projection_id": self.ghx_packet.get("projection_id"),
        }
        try:
            broadcast_ghx_overlay(payload)
            logger.debug("[SymbolicHSXBridge] GHX overlay broadcast successful.")
        except Exception as e:
            logger.error(f"[SymbolicHSXBridge] Broadcast failed: {e}")