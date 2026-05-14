import uuid
from typing import Dict, List, Optional
from datetime import datetime
from backend.modules.hologram.holographic_renderer import HolographicRenderer
from backend.modules.codex.symbolic_key_deriver import SymbolicKeyDerivation
from backend.modules.glyphos.soul_law_validator import validate_soul_key

class HolographicTriggerController:
    def __init__(self, ghx_packet: Dict, avatar_state: Dict = None):
        self.renderer = HolographicRenderer(ghx_packet)
        self.avatar = avatar_state or {}
        self.light_field = self.renderer.render_glyph_field()

    def evaluate_triggers(self) -> List[Dict]:
        """
        Evaluate all projected glyphs for trigger conditions.
        """
        triggered = []
        for glyph in self.light_field:
            if self._check_observer_gaze(glyph) and self._check_soul_key(glyph):
                triggered_glyph = self.renderer.trigger_projection(
                    glyph_id=glyph["glyph_id"], method="gaze+soul"
                )
                if triggered_glyph:
                    triggered.append(triggered_glyph)
                if triggered:
                    try:
                        from backend.modules.hologram.symbolic_hsx_bridge import SymbolicHSXBridge
                        SymbolicHSXBridge.broadcast_glyphs(triggered, observer=self.avatar.get("id", "unknown"))
                    except Exception:
                        pass
        return triggered

    def _check_observer_gaze(self, glyph: Dict) -> bool:
        """
        Simulate gaze activation (e.g., if avatar position overlaps).
        """
        x, y, z = glyph["position"]["x"], glyph["position"]["y"], glyph["position"]["z"]
        avatar_pos = self.avatar.get("position", {"x": 0, "y": 0, "z": 0})
        return abs(x - avatar_pos["x"]) < 10 and abs(y - avatar_pos["y"]) < 10

    def _check_soul_key(self, glyph: Dict) -> bool:
        """
        Validate if avatar holds required symbolic key (via SoulLaw).
        """
        required_key = glyph.get("required_key")
        if not required_key:
            return True  # No lock present
        derived = SymbolicKeyDerivation().derive_key_from_avatar(self.avatar)
        return validate_soul_key(required_key, derived)

    def export_trigger_log(self) -> Dict:
        """
        Return triggered glyphs with timestamps and methods.
        """
        return {
            "triggered_at": datetime.utcnow().isoformat(),
            "avatar_id": self.avatar.get("id", "unknown"),
            "triggers": [
                g for g in self.light_field if g.get("trigger_state", "").startswith("triggered")
            ]
        }