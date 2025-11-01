#!/usr/bin/env python3
# ================================================================
# 🌐 Aion Resonance Bridge - LexMemory -> Symatics Field Export
# ================================================================
"""
Converts LexMemory state into a graph suitable for the Symatics Algebra
operators (⊕ superposition, ⟲ resonance, ↔ entanglement).
Each node = concept binding with (ρ, Ī, SQI)
Edges = associative links between shared answers.

Now also emits SCI photon capsules to archive the symbolic field state
(only when not in AION_LITE mode).
"""

import json, logging
from pathlib import Path
from .cee_lex_memory import _load_memory

# ✅ Optional SCI overlay - silent fallback if unavailable
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k): pass

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/telemetry/resonance_graph.json")


def build_graph():
    mem = _load_memory()
    nodes, edges = [], []
    by_answer = {}

    # Build nodes
    for k, v in mem.items():
        nodes.append({
            "id": k,
            "rho": v.get("ρ", 0.0),
            "I": v.get("I", 0.0),
            "SQI": v.get("SQI", 0.0),
            "count": v.get("count", 0)
        })
        ans = k.split("↔")[-1]
        by_answer.setdefault(ans, []).append(k)

    # Build entanglement edges
    for group in by_answer.values():
        if len(group) > 1:
            base = group[0]
            for other in group[1:]:
                edges.append({
                    "source": base,
                    "target": other,
                    "weight": 1.0
                })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    graph = {"nodes": nodes, "edges": edges}
    json.dump(graph, open(OUT_PATH, "w"), indent=2)

    logger.info(f"[AionBridge] Exported {len(nodes)} nodes, {len(edges)} edges -> {OUT_PATH}")

    # 🌟 SCI photon export - symbolic field snapshot
    try:
        sci_emit("resonance_graph",
                 f"Exported resonance field with {len(nodes)} nodes and {len(edges)} entanglements.")
    except Exception:
        pass

    return OUT_PATH


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_graph()