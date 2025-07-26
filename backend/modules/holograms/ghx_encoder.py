import json
from datetime import datetime
from typing import Dict, Any, List

from backend.modules.codex.codex_metrics import calculate_glyph_cost
from backend.modules.codex.codex_trace import trace_glyph_execution_path
from backend.modules.glyphos.symbolic_entangler import get_entangled_links

GHX_VERSION = "1.1"


def encode_glyphs_to_ghx(container: Dict[str, Any]) -> Dict[str, Any]:
    container_id = container.get("container_id", "unknown")
    glyphs = container.get("glyphs", [])

    holograms = []
    for glyph in glyphs:
        glyph_id = glyph.get("id")
        symbol = glyph.get("glyph")
        label = glyph.get("label", "")
        timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())

        entangled = glyph.get("entangled", []) or get_entangled_links(glyph_id)
        light_logic = generate_light_logic(symbol)
        position = generate_spatial_coordinates(glyph_id)
        cost = calculate_glyph_cost(symbol)
        replay = trace_glyph_execution_path(glyph_id)
        narration = generate_narration(symbol, label)

        holograms.append({
            "id": glyph_id,
            "symbol": symbol,
            "label": label,
            "timestamp": timestamp,
            "entangled": entangled,
            "light_logic": light_logic,
            "position": position,
            "cost": cost,
            "replay": replay,
            "narration": narration,
            "tts_ready": True,
        })

    return {
        "ghx_version": GHX_VERSION,
        "container_id": container_id,
        "generated": datetime.utcnow().isoformat(),
        "physics": container.get("physics", "symbolic-quantum"),
        "dimensions": 4,
        "holographic": True,
        "replay_enabled": True,
        "holograms": holograms
    }


def generate_light_logic(symbol: str) -> Dict[str, Any]:
    return {
        "color": glyph_color_map(symbol),
        "intensity": glyph_intensity_map(symbol),
        "animation": "pulse",
        "collapse_trace": symbol in ("⧖", "⬁")
    }


def generate_spatial_coordinates(glyph_id: str) -> Dict[str, float]:
    index = int(glyph_id[1:]) if glyph_id.startswith("g") and glyph_id[1:].isdigit() else 0
    return {
        "x": index * 2.0,
        "y": (index % 3) * 1.0,
        "z": (index // 3) * 1.5
    }


def glyph_color_map(symbol: str) -> str:
    return {
        "⊕": "#ffcc00",
        "↔": "#aa00ff",
        "⧖": "#00ffff",
        "🧠": "#00ff66",
        "⬁": "#ff6666",
        "→": "#66ccff"
    }.get(symbol, "#ffffff")


def glyph_intensity_map(symbol: str) -> float:
    return {
        "⊕": 0.9,
        "↔": 1.0,
        "⧖": 0.7,
        "🧠": 0.6,
        "⬁": 1.2,
        "→": 0.8
    }.get(symbol, 0.5)


def generate_narration(symbol: str, label: str) -> Dict[str, Any]:
    description_map = {
        "⊕": "Combine logic",
        "↔": "Entangled reasoning",
        "⧖": "Collapsed moment",
        "🧠": "Cognitive glyph",
        "⬁": "Mutation trigger",
        "→": "Directional execution"
    }
    spoken = description_map.get(symbol, f"Glyph {symbol}")
    return {
        "text_to_speak": f"{spoken}. {label}" if label else spoken,
        "voice": "default",  # Optional: allow user-defined voice
        "language": "en-US"
    }


def export_ghx(container: Dict[str, Any], output_path: str):
    ghx_data = encode_glyphs_to_ghx(container)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ghx_data, f, indent=2)