# ──────────────────────────────────────────────
#  Tessaris * Symbolic HSX Bridge (HQCE Stage 5)
#  Connects symbolic cognition layer -> GHX field overlays
#  Computes semantic κ (gravity wells) and broadcasts overlay maps
# ──────────────────────────────────────────────
from __future__ import annotations

import asyncio
import logging
import math
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.holograms.morphic_ledger import morphic_ledger
from backend.modules.identity.avatar_registry import get_avatar_identity

# IMPORTANT: broadcast_event is async in backend.modules.websocket_manager
from backend.modules.websocket_manager import broadcast_event

logger = logging.getLogger(__name__)
QUIET = os.getenv("AION_QUIET_MODE", "0") == "1"

# ✅ WebSocket HUD interface (safe fallback)
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:

    async def send_codex_ws_event(event_type: str, payload: dict):
        if not QUIET:
            print(f"[Fallback HUD] {event_type} -> {payload}")


# Optional hard kill-switch for perf tests
DISABLE_HSX_WS = os.getenv("AION_DISABLE_HSX_WS", "0") == "1"

# Throttles (avoid flooding event loop / slowing core workloads)
HSX_MIN_BROADCAST_INTERVAL_S = float(os.getenv("AION_HSX_MIN_BROADCAST_INTERVAL_S", "0.25"))
HSX_GRAVITY_MIN_BROADCAST_INTERVAL_S = float(os.getenv("AION_HSX_GRAVITY_MIN_BROADCAST_INTERVAL_S", "0.5"))

# If you *want* sync callers to still work without awaiting (back-compat),
# we schedule the async sends.
def _fire_and_forget(coro) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # no running loop: best effort, but never crash caller
        try:
            asyncio.run(coro)
        except Exception:
            pass


async def _broadcast(tag: str, payload: Dict[str, Any]) -> None:
    """Guarded async broadcast."""
    if DISABLE_HSX_WS:
        return
    try:
        await broadcast_event(tag, payload)
    except Exception:
        # broadcasting must never affect core compute
        pass


class SymbolicHSXBridge:
    """Bridges symbolic cognition metrics into holographic overlays (Stage 5)."""

    def __init__(self, avatar_id: str, ghx_packet: Dict[str, Any]):
        self.avatar_id = avatar_id
        self.ghx_packet = ghx_packet or {}
        self.identity = get_avatar_identity(avatar_id)

        # per-instance throttles (prevents HSX from dominating hot loops)
        self._last_overlay_broadcast_ts = 0.0
        self._last_gravity_broadcast_ts = 0.0

    # ──────────────────────────────────────────────
    #  Inject symbolic identity / trail metadata
    # ──────────────────────────────────────────────
    def inject_identity_trails(self) -> Dict[str, Any]:
        """Append symbolic identity trail into GHX nodes."""
        nodes = self.ghx_packet.get("nodes", []) or []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node.setdefault("symbolic_trail", []).append(
                {
                    "by": self.identity.get("name", "unknown"),
                    "avatar_id": self.avatar_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "signature": self.identity.get("signature", str(uuid.uuid4())),
                }
            )

        logger.debug(f"[SymbolicHSXBridge] Injected identity trails into {len(nodes)} nodes.")
        return self.ghx_packet

    # ──────────────────────────────────────────────
    #  Symbolic scoring + semantic κ computation
    # ──────────────────────────────────────────────
    def score_overlay_paths(self) -> List[Dict[str, Any]]:
        """
        Score GHX nodes for symbolic weight and goal alignment,
        then compute semantic curvature κs (semantic gravity factor).

        Returns a compact list of scored nodes for callers that want a summary.
        """
        nodes = self.ghx_packet.get("nodes", []) or []
        if not nodes:
            return []

        results: List[Dict[str, Any]] = []
        weights: List[float] = []
        entropies: List[float] = []

        for node in nodes:
            if not isinstance(node, dict):
                continue

            symbol = node.get("symbol")
            entropy = float(node.get("entropy", 0.0) or 0.0)
            cost = float(node.get("cost", 0.0) or 0.0)

            scores = CodexMetrics.score_symbol(symbol)
            w = float(scores.get("symbolic_weight", 0.0) or 0.0)
            a = float(scores.get("goal_match_score", 0.0) or 0.0)

            node.update(
                {
                    "goal_alignment_score": a,
                    "symbolic_weight": w,
                    # semantic_kappa set after aggregation
                }
            )

            weights.append(w)
            entropies.append(entropy)

            results.append(
                {
                    "glyph_id": node.get("glyph_id"),
                    "symbol": symbol,
                    "alignment": a,
                    "weight": w,
                    "entropy": entropy,
                    "cost": cost,
                }
            )

        # Compute semantic curvature κs
        if weights:
            mean_w = sum(weights) / len(weights)
            var_w = sum((w - mean_w) ** 2 for w in weights) / len(weights)
            mean_entropy = sum(entropies) / len(entropies) if entropies else 0.0
            kappa = math.tanh(mean_w / (1.0 + 10.0 * var_w + mean_entropy))

            for node in nodes:
                if isinstance(node, dict):
                    node["semantic_kappa"] = kappa

            logger.info(f"[SymbolicHSXBridge] Computed semantic κs={kappa:.4f}")
        else:
            kappa, mean_w, mean_entropy, var_w = 0.0, 0.0, 0.0, 0.0
            logger.warning("[SymbolicHSXBridge] No symbolic weights found for κ computation.")

        # 🧾 Persist summary in Morphic Ledger (best effort)
        try:
            morphic_ledger.append(
                {
                    "psi": mean_entropy,
                    "kappa": kappa,
                    "T": 1.0,
                    "coherence": mean_w,
                    "gradient": var_w**0.5,
                    "stability": (mean_w / (1.0 + var_w)) if (1.0 + var_w) else 0.0,
                    "metadata": {"origin": "SymbolicHSXBridge"},
                },
                observer=self.avatar_id,
            )
        except Exception:
            pass

        # 🧠 Compute semantic gravity + broadcast (async, throttled)
        gravity_map = self.compute_semantic_gravity()
        now = datetime.utcnow().timestamp()
        if (now - self._last_gravity_broadcast_ts) >= HSX_GRAVITY_MIN_BROADCAST_INTERVAL_S:
            self._last_gravity_broadcast_ts = now
            _fire_and_forget(_broadcast("semantic_gravity_update", gravity_map))

        return results

    # ──────────────────────────────────────────────
    #  Semantic Gravity Computation (HQCE Stage 5)
    # ──────────────────────────────────────────────
    def compute_semantic_gravity(self) -> Dict[str, Any]:
        """
        Compute local semantic gravity wells for visualization.
        Returns dict: { 'clusters': [...], 'field_strength': float }.
        """
        nodes = self.ghx_packet.get("nodes", []) or []
        if not nodes:
            return {"clusters": [], "field_strength": 0.0}

        clusters: List[Dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue

            kappa = float(node.get("semantic_kappa", 0.0) or 0.0)
            w = float(node.get("symbolic_weight", 0.0) or 0.0)
            entropy = float(node.get("entropy", 0.0) or 0.0)

            strength = (w * (1.0 - entropy)) * (1.0 + kappa)
            clusters.append(
                {
                    "glyph_id": node.get("glyph_id"),
                    "symbol": node.get("symbol"),
                    "gravity_strength": float(strength),
                    "semantic_kappa": kappa,
                    "weight": w,
                    "entropy": entropy,
                }
            )

        total = sum(c["gravity_strength"] for c in clusters) or 0.0
        for c in clusters:
            c["gravity_strength"] = round(c["gravity_strength"] / max(total, 1e-9), 6)

        field_strength = round(sum(c["gravity_strength"] for c in clusters) / max(len(clusters), 1), 6)

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
    #  GHX Overlay Broadcast
    # ──────────────────────────────────────────────
    async def broadcast_overlay_async(self) -> None:
        """Async GHX overlay broadcast (preferred)."""
        if DISABLE_HSX_WS:
            return

        payload = {
            "type": "ghx_overlay",
            "avatar": self.identity,
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": self.ghx_packet.get("nodes", []) or [],
            "projection_id": self.ghx_packet.get("projection_id"),
        }

        # throttle
        now = time.time()
        if (now - self._last_overlay_broadcast_ts) < HSX_MIN_BROADCAST_INTERVAL_S:
            return
        self._last_overlay_broadcast_ts = now

        await _broadcast("ghx_overlay_update", payload)

        # Optional HUD event mirror (best effort)
        try:
            await send_codex_ws_event("ghx_overlay_update", payload)
        except Exception:
            pass

    def broadcast_overlay(self) -> None:
        """
        Back-compat: callable from sync contexts without blocking.
        Schedules the async broadcast safely.
        """
        _fire_and_forget(self.broadcast_overlay_async())