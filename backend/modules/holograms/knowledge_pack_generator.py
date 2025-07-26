import uuid
from datetime import datetime
from typing import List, Dict, Any

from backend.modules.codex.codex_trace import trace_glyph_execution_path
from backend.modules.symbolic_entangler import get_entangled_links
from backend.modules.codex.codex_metrics import calculate_glyph_cost
from backend.modules.hologram.ghx_encoder import glyph_color_map, glyph_intensity_map

def generate_knowledge_pack(glyph_tree: List[Dict[str, Any]], container_id: str) -> Dict:
    """
    Bundle a recursive logic tree into a portable GHX hologram pack.
    """
    projection = []
    links = []

    for glyph in glyph_tree:
        gid = glyph.get("id", str(uuid.uuid4()))
        symbol = glyph["symbol"]
        label = glyph.get("label", "")
        timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())
        entangled = glyph.get("entangled", []) or get_entangled_links(gid)
        replay = trace_glyph_execution_path(gid)
        cost = calculate_glyph_cost(symbol)

        projection.append({
            "glyph_id": gid,
            "symbol": symbol,
            "label": label,
            "color": glyph_color_map(symbol),
            "light_intensity": glyph_intensity_map(symbol),
            "trigger_state": "idle",
            "animation": "pulse",
            "collapse_trace": symbol in ("⧖", "⬁"),
            "entangled": entangled,
            "replay": replay,
            "cost": cost,
            "timestamp": timestamp
        })

        for target in entangled:
            links.append({
                "source": gid,
                "target": target,
                "type": "entanglement",
                "color": "#aa00ff",
                "animated": True
            })

    return {
        "projection_id": str(uuid.uuid4()),
        "rendered_at": datetime.utcnow().isoformat(),
        "container_id": container_id,
        "physics": "symbolic-quantum",
        "dimensions": 4,
        "nodes": projection,
        "links": links,
        "metadata": {
            "ghx_version": "1.0",
            "replay_enabled": True,
            "recursive_pack": True
        }
    }