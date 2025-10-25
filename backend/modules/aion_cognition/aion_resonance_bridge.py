# ================================================================
# 🌐 Aion Resonance Bridge — LexMemory → Symatics Field Export
# ================================================================
"""
Converts LexMemory state into a graph suitable for the Symatics Algebra
operators (⊕ superposition, ⟲ resonance, ↔ entanglement).
Each node = concept binding with (ρ, Ī, SQI)
Edges = associative links between shared answers.
"""

import json, logging
from pathlib import Path
from .cee_lex_memory import _load_memory

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
                edges.append({"source": base, "target": other, "weight": 1.0})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"nodes": nodes, "edges": edges}, open(OUT_PATH, "w"), indent=2)
    logger.info(f"[AionBridge] Exported {len(nodes)} nodes, {len(edges)} edges → {OUT_PATH}")
    return OUT_PATH

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_graph()