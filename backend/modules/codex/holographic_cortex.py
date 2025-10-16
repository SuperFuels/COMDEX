# ============================================================
# 📁 backend/modules/codex/holographic_cortex.py
# ============================================================

"""
HolographicCortex — symbolic projection and light-field synthesis layer.
Provides visual–symbolic mappings for CodexCore state projections.
"""

import datetime
import random
import math

from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_trace import CodexTrace


# ──────────────────────────────────────────────
#  Utility: Spiral Projection Geometry
# ──────────────────────────────────────────────
def _spiral_position(i: int):
    angle = i * 0.4
    radius = 1.0 + i * 0.1
    height = i * 0.05
    return [
        radius * math.cos(angle),
        height,
        radius * math.sin(angle)
    ]


def get_codexcore_projection(container_id: str):
    """Generate static projection of CodexCore state."""
    core_state = CodexCore.get_state(container_id)
    if not core_state:
        return None

    light_field = []
    for i, op in enumerate(core_state.get("runtime_stack", [])):
        glyph = op.get("glyph", "?")
        pos = _spiral_position(i)
        light_field.append({
            "glyph_id": f"core_{i}",
            "symbol": glyph,
            "position": {
                "x": pos[0],
                "y": pos[1],
                "z": pos[2],
                "t": datetime.datetime.utcnow().isoformat(),
            },
            "light_intensity": random.uniform(0.5, 1.2),
            "trigger_state": "active" if i == core_state.get("ip") else "idle",
            "narration": {"text_to_speak": f"CodexCore executing {glyph}"},
        })

    return {
        "projection_id": f"codexcore_{container_id}",
        "rendered_at": datetime.datetime.utcnow().isoformat(),
        "light_field": light_field,
    }


# ──────────────────────────────────────────────
#  Class Wrapper for QQC Integration
# ──────────────────────────────────────────────
class HolographicCortex:
    """Holographic light-field manager used by QQC and Codex subsystems."""

    def __init__(self):
        self.active_projections = {}
        self.initialized = False

    async def initialize(self):
        """Prepare holographic field memory and sync state."""
        self.initialized = True
        print("[🧠] HolographicCortex initialized.")

    async def teardown(self):
        """Gracefully shutdown the holographic field."""
        self.active_projections.clear()
        self.initialized = False
        print("[🧠] HolographicCortex shutdown complete.")

    def render_projection(self, container_id: str):
        """Generate and store a projection for a given container."""
        proj = get_codexcore_projection(container_id)
        if proj:
            self.active_projections[container_id] = proj
        return proj

    def get_projection(self, container_id: str):
        """Retrieve a previously rendered projection."""
        return self.active_projections.get(container_id)

    def list_active(self):
        """List all active projections."""
        return list(self.active_projections.keys())


__all__ = ["HolographicCortex", "get_codexcore_projection"]