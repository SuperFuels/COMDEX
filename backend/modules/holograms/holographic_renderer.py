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

class HolographicRenderer:
    def __init__(self, ghx_packet: Dict[str, Any], observer_id: str = "anon", lazy_mode: bool = True):
        self.ghx = ghx_packet
        self.observer_id = observer_id
        self.observer_hash = hashlib.sha256(observer_id.encode()).hexdigest()[:12]
        self.lazy_mode = lazy_mode
        self.rendered_projection: List[Dict] = []
        self.links: List[Dict] = []

    def render_glyph_field(self) -> List[Dict]:
        """
        Project each glyph into a symbolic 4D light field.
        Apply observer-gated GHX access control and lazy rendering.
        """
        projection = []
        glyphs = self.ghx.get("glyphs") or self.ghx.get("holograms", [])

        for glyph in glyphs:
            if not self._is_visible_to_observer(glyph):
                logger.debug(f"Glyph {glyph.get('id')} hidden from observer {self.observer_id}")
                continue

            if self.lazy_mode and not self._is_in_view(glyph):
                logger.debug(f"Glyph {glyph.get('id')} skipped for lazy mode (out of view)")
                continue

            gid = glyph.get("id")
            symbol = glyph.get("glyph") or glyph.get("symbol")
            label = glyph.get("label", "")
            timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())

            position = self._calc_4d_position(glyph)
            entangled = glyph.get("entangled", []) or get_entangled_links(gid)
            replay = glyph.get("replay", []) or trace_glyph_execution_path(gid)
            cost = glyph.get("cost", 0.0) or calculate_glyph_cost(symbol)

            light_packet = {
                "glyph_id": gid,
                "symbol": symbol,
                "label": label,
                "light_intensity": self._calc_light_intensity(symbol),
                "color": glyph_color_map(symbol),
                "animation": "pulse",
                "position": position,
                "entangled": entangled,
                "trigger_state": "idle",
                "collapse_trace": symbol in ("⧖", "⬁"),
                "replay": replay,
                "cost": cost,
                "timestamp": timestamp,
                "lazy_triggered": not self.lazy_mode
            }
            projection.append(light_packet)

            for eid in entangled:
                self.links.append({
                    "source": gid,
                    "target": eid,
                    "type": "entanglement",
                    "color": "#aa00ff",
                    "animated": True
                })

        self.rendered_projection = projection

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

        # Optional HSX broadcast
        try:
            from backend.modules.hologram.symbolic_hsx_bridge import SymbolicHSXBridge
            SymbolicHSXBridge.broadcast_glyphs(projection, observer=self.observer_id)
        except Exception:
            logger.warning("HSXBridge not available, skipping overlay broadcast.")

        return projection

    def _is_visible_to_observer(self, glyph: Dict[str, Any]) -> bool:
        access = glyph.get("access_control", {})
        allowed = access.get("allowed_observers", [])
        gate = access.get("entropy_gate", "")

        if allowed and self.observer_id in allowed:
            return True
        if gate and self.observer_hash == gate:
            return True
        if not allowed and not gate:
            return True
        return False

    def _is_in_view(self, glyph: Dict[str, Any]) -> bool:
        return False  # Set True manually to test eager expansion

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
            "t": glyph.get("timestamp", "2025-07-25T00:00:00Z")
        }

    def export_projection(self) -> Dict:
        return {
            "rendered_at": datetime.utcnow().isoformat(),
            "projection_id": str(uuid.uuid4()),
            "container_id": self.ghx.get("container_id"),
            "physics": self.ghx.get("physics", "symbolic-quantum"),
            "dimensions": self.ghx.get("dimensions", 4),
            "nodes": self.rendered_projection,
            "links": self.links,
            "metadata": {
                "version": self.ghx.get("ghx_version", "1.0"),
                "replay_enabled": self.ghx.get("replay_enabled", False),
                "lazy_mode": self.lazy_mode
            }
        }

    def export_to_json(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.export_projection(), f, indent=2)