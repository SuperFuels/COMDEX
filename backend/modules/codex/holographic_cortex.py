# backend/modules/codex/holographic_cortex.py

import datetime
import random
from backend.modules.codex.codex_core import CodexCore
from backend.modules.glyphos.codex_trace import CodexTrace

def get_codexcore_projection(container_id: str):
    core_state = CodexCore.get_state(container_id)
    if not core_state:
        return None

    light_field = []
    for i, op in enumerate(core_state['runtime_stack']):
        glyph = op.get("glyph", "?")
        pos = _spiral_position(i)
        light_field.append({
            "glyph_id": f"core_{i}",
            "symbol": glyph,
            "position": {"x": pos[0], "y": pos[1], "z": pos[2], "t": datetime.datetime.utcnow().isoformat()},
            "light_intensity": random.uniform(0.5, 1.2),
            "trigger_state": "active" if i == core_state.get("ip") else "idle",
            "narration": {"text_to_speak": f"CodexCore executing {glyph}"}
        })

    return {
        "projection_id": f"codexcore_{container_id}",
        "rendered_at": datetime.datetime.utcnow().isoformat(),
        "light_field": light_field
    }

def _spiral_position(i: int):
    angle = i * 0.4
    radius = 1.0 + i * 0.1
    height = i * 0.05
    return [
        radius * math.cos(angle),
        height,
        radius * math.sin(angle)
    ]