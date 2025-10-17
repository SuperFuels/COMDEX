# ──────────────────────────────────────────────
#  Tessaris • Holographic Renderer (HQCE-Ready)
#  Integrates live GHX rendering + coherence overlay (Stage 4)
# ──────────────────────────────────────────────

import os
import uuid
import math
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from backend.modules.codex.codex_trace import trace_glyph_execution_path
from backend.modules.codex.codex_metrics import calculate_glyph_cost

try:
    from backend.modules.glyphos.symbolic_entangler import get_entangled_links
except Exception:
    def get_entangled_links(*args, **kwargs):
        return []

try:
    from backend.modules.holograms.ghx_encoder import glyph_color_map, glyph_intensity_map
except Exception:
    from .ghx_encoder import glyph_color_map, glyph_intensity_map  # type: ignore

# ✅ CodexLang HUD streaming import
try:
    from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
except Exception:
    def send_codex_ws_event(event_type: str, payload: dict):
        print(f"[Fallback HUD] {event_type} → {json.dumps(payload)}")

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  HQCE Stage 4 — Coherence Overlay Extension
# ──────────────────────────────────────────────
def map_coherence_to_color(value: float) -> str:
    """Map coherence ∈[0,1] → color gradient (blue→white→gold)."""
    if value < 0.5:
        return f"rgb({int(0)}, {int(128 + value * 255)}, {int(255)})"
    else:
        g = int(255 * (1 - abs(value - 1)))
        return f"rgb({int(255)}, {g}, {int(100 + 155 * value)})"


def compute_gradient_map(coherence: float) -> Dict[str, Any]:
    """Optional minor visualization gradient."""
    hue_shift = int(240 * coherence)
    return {
        "start": f"hsl({hue_shift}, 80%, 40%)",
        "end": f"hsl({(hue_shift + 40) % 360}, 90%, 70%)"
    }


# ──────────────────────────────────────────────
#  Core Holographic Renderer
# ──────────────────────────────────────────────
class HolographicRenderer:
    def __init__(self, ghx_packet: Dict[str, Any], observer_id: str = "anon", lazy_mode: bool = True):
        self.ghx = ghx_packet
        self.observer_id = observer_id
        self.observer_hash = hashlib.sha256(observer_id.encode()).hexdigest()[:12]
        self.lazy_mode = lazy_mode
        self.rendered_projection: List[Dict] = []
        self.links: List[Dict] = []
        self.field_coherence_map: Dict[str, float] = {}  # 🧭 HQCE Stage 4 addition
        self.field_coherence_map = {}
        self.coherence_halos = []

    # ────────────────────────────────────────────
    #  Render GHX Projection
    # ────────────────────────────────────────────
    def render_glyph_field(self) -> List[Dict]:
        """
        Project each glyph into a symbolic 4D light field.
        Apply observer-gated GHX access control and lazy rendering.
        Compute dynamic coherence halos (HQCE Stage 4).
        """
        projection = []
        glyphs = self.ghx.get("glyphs") or self.ghx.get("holograms", [])

        for glyph in glyphs:
            if not self._is_visible_to_observer(glyph):
                continue
            if self.lazy_mode and not self._is_in_view(glyph):
                continue

            gid = glyph.get("id")
            symbol = glyph.get("glyph") or glyph.get("symbol")
            label = glyph.get("label", "")
            timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())

            position = self._calc_4d_position(glyph)
            entangled = glyph.get("entangled", []) or get_entangled_links(gid)
            replay = glyph.get("replay", []) or trace_glyph_execution_path(gid)
            cost = glyph.get("cost", 0.0) or calculate_glyph_cost(symbol)

            # ─── HQCE Stage 4: Coherence Computation ───
            goal = glyph.get("goal_alignment_score", 0.5)
            entropy = glyph.get("entropy_score", 0.5)
            coherence = 1.0 - abs(entropy - goal)
            self.field_coherence_map[gid] = coherence
            color = map_coherence_to_color(coherence)

            # Halo packet for HUD rendering
            halo = {
                "radius": 2.0 + 3.0 * coherence,
                "intensity": coherence,
                "color": color,
                "gradient": compute_gradient_map(coherence)
            }

            light_packet = {
                "glyph_id": gid,
                "symbol": symbol,
                "label": label,
                "light_intensity": self._calc_light_intensity(symbol),
                "color": color,
                "animation": "pulse",
                "position": position,
                "halo": halo,
                "entangled": entangled,
                "trigger_state": "idle",
                "collapse_trace": symbol in ("⧖", "⬁"),
                "replay": replay,
                "cost": cost,
                "entropy_score": entropy,
                "goal_alignment_score": goal,
                "coherence": coherence,
                "timestamp": timestamp,
                "lazy_triggered": not self.lazy_mode,
            }
            projection.append(light_packet)

            for eid in entangled:
                self.links.append({
                    "source": gid,
                    "target": eid,
                    "type": "entanglement",
                    "color": "#aa00ff",
                    "animated": True,
                })

        self.rendered_projection = projection

        # ✅ WebSocket broadcast of coherence summary (Codex)
        try:
            coherence_summary = {
                "mean_coherence": round(sum(self.field_coherence_map.values()) / max(1, len(self.field_coherence_map)), 4),
                "glyph_count": len(self.field_coherence_map),
                "timestamp": datetime.utcnow().isoformat()
            }
            send_codex_ws_event("coherence_update", coherence_summary)
        except Exception as e:
            logger.warning(f"[HUD] Coherence update broadcast failed: {e}")

        # ✅ CodexLang HUD stream (after projection render)
        try:
            send_codex_ws_event("hud_ghx_projection", {
                "event": "ghx_projection_ready",
                "observer": self.observer_id,
                "container_id": self.ghx.get("container_id"),
                "glyph_count": len(projection),
                "lazy_mode": self.lazy_mode,
                "ghx_version": self.ghx.get("ghx_version", "1.0"),
                "replay_enabled": self.ghx.get("replay_enabled", False)
            })
        except Exception as e:
            logger.warning(f"[HUD] Failed to stream CodexLang HUD: {e}")

        # ✅ HSX broadcast
        try:
            from backend.modules.holograms.symbolic_hsx_bridge import SymbolicHSXBridge
            SymbolicHSXBridge.broadcast_glyphs(projection, observer=self.observer_id)
        except Exception:
            logger.warning("HSXBridge not available, skipping overlay broadcast.")

        # ✅ NEW: GHX/QFC halo + coherence broadcast (HQCE Stage 4 extension)
        try:
            from backend.modules.websocket.ghx_ws_broadcast import broadcast_ghx_runtime_update
            payload = {
                "type": "halo_update",
                "data": {
                    "halos": [p["halo"] for p in projection],
                    "coherence_map": self.field_coherence_map,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }
            broadcast_ghx_runtime_update(payload)
        except Exception as e:
            logger.warning(f"[HolographicRenderer] GHX halo broadcast failed: {e}")

        return projection

    # ────────────────────────────────────────────
    #  New: Field Coherence Map
    # ────────────────────────────────────────────
    def compute_field_coherence_map(self):
        """
        Build a coherence map for all rendered nodes.
        Coherence = 1 - |entropy - goal_alignment|
        """
        field_map = {}
        for node in self.rendered_projection or []:
            entropy = node.get("entropy", 0.5)
            goal_alignment = node.get("goal_alignment", 0.5)
            coherence = max(0.0, min(1.0, 1 - abs(entropy - goal_alignment)))
            node["coherence"] = coherence
            field_map[node["id"]] = coherence
        self.field_coherence_map = field_map
        return field_map

    # ────────────────────────────────────────────
    #  New: Visual Intensity + Color Update
    # ────────────────────────────────────────────
    def update_visual_intensity(self):
        """
        Adjust color and brightness based on coherence.
        Maps coherence → hue (violet→white) and alpha (transparency).
        """
        if not hasattr(self, "field_coherence_map"):
            self.compute_field_coherence_map()

        for node in self.rendered_projection or []:
            coherence = node.get("coherence", 0.5)
            hue = 270 * (1 - coherence) / 360.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.7, 0.8 + 0.2 * coherence)
            node["color"] = {
                "rgb": [int(r * 255), int(g * 255), int(b * 255)],
                "alpha": round(0.4 + 0.6 * coherence, 2),
            }

    # ────────────────────────────────────────────
    #  New: Coherence Halo Rendering
    # ────────────────────────────────────────────
    def render_coherence_halos(self):
        """
        Adds halo effects (virtual) for high-coherence nodes.
        HUD overlay can later interpret this for glow rendering.
        """
        halos = []
        for node in self.rendered_projection or []:
            c = node.get("coherence", 0.0)
            if c > 0.85:
                halos.append({
                    "node_id": node["id"],
                    "radius": 0.05 + 0.15 * c,
                    "intensity": round(c, 2),
                })
        self.coherence_halos = halos
        return halos

    # ────────────────────────────────────────────
    #  Observer / Visibility Utilities
    # ────────────────────────────────────────────
    def _is_visible_to_observer(self, glyph: Dict[str, Any]) -> bool:
        access = glyph.get("access_control", {})
        allowed = access.get("allowed_observers", [])
        gate = access.get("entropy_gate", "")
        if allowed and self.observer_id in allowed:
            return True
        if gate and self.observer_hash == gate:
            return True
        return not (allowed or gate)

    def _is_in_view(self, glyph: Dict[str, Any]) -> bool:
        """Spatial culling for lazy_mode."""
        return True  # TODO: implement real FoV filter later

    # ────────────────────────────────────────────
    #  Interactive and Utility Methods
    # ────────────────────────────────────────────
    def trigger_projection(self, glyph_id: str, method: str = "gaze") -> Optional[Dict]:
        for glyph in self.rendered_projection:
            if glyph["glyph_id"] == glyph_id:
                glyph["trigger_state"] = f"triggered_by_{method}"
                glyph["activated_at"] = datetime.utcnow().isoformat()
                glyph["lazy_triggered"] = True
                return glyph
        return None

    def get_active_glyphs(self) -> List[str]:
        return [glyph["symbol"] for glyph in self.rendered_projection]

    def _calc_light_intensity(self, symbol: str) -> float:
        return glyph_intensity_map(symbol)

    def _calc_4d_position(self, glyph: Dict) -> Dict:
        gid = glyph.get("id", "")
        seed = uuid.uuid5(uuid.NAMESPACE_DNS, gid)
        return {
            "x": (seed.int % 50) - 25,
            "y": (seed.int % 70) - 35,
            "z": (seed.int % 90) - 45,
            "t": glyph.get("timestamp", "2025-07-25T00:00:00Z"),
        }

    # ────────────────────────────────────────────
    #  Exporters
    # ────────────────────────────────────────────
    def export_projection(self) -> Dict:
        return {
            "rendered_at": datetime.utcnow().isoformat(),
            "projection_id": str(uuid.uuid4()),
            "container_id": self.ghx.get("container_id"),
            "physics": self.ghx.get("physics", "symbolic-quantum"),
            "dimensions": self.ghx.get("dimensions", 4),
            "nodes": self.rendered_projection,
            "links": self.links,
            "field_coherence_map": self.field_coherence_map,
            "metadata": {
                "version": self.ghx.get("ghx_version", "1.0"),
                "replay_enabled": self.ghx.get("replay_enabled", False),
                "lazy_mode": self.lazy_mode,
            },
        }

    def export_to_json(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.export_projection(), f, indent=2)