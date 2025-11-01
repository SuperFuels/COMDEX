# ================================================================
# 🪐 CEE FieldViz - Resonant Concept Glyph Mapper
# ================================================================
"""
Visualizes the active resonance field by grouping LexMemory keys into
semantic clusters (phonetics, semantics, syntax, etc.).
Each node's bubble size reflects its SQI magnitude.
"""

import matplotlib.pyplot as plt
from pathlib import Path
import random, json, re
from .cee_lex_memory import _load_memory

OUT_PATH = Path("data/telemetry/field_glyph_map.png")
logger_name = "backend.modules.aion_cognition.cee_field_viz"

def _cluster_for_prompt(prompt: str) -> str:
    p = prompt.lower()
    if re.search(r"phon|sound", p): return "phonetics"
    if re.search(r"semant|meaning", p): return "semantics"
    if re.search(r"syntax|sentence|structure", p): return "syntax"
    if re.search(r"morph|word", p): return "morphology"
    return "other"

def generate_field_map():
    mem = _load_memory()
    clusters = {"phonetics": [], "semantics": [], "syntax": [], "morphology": [], "other": []}
    for k, v in mem.items():
        base = k.split("↔")[0]
        c = _cluster_for_prompt(base)
        clusters[c].append(v.get("SQI", 0.1))

    plt.figure(figsize=(9,6))
    y_positions = list(range(len(clusters)))
    for i, (cluster, sqis) in enumerate(clusters.items()):
        xs = [random.uniform(0, 1) for _ in sqis]
        ys = [i + random.uniform(-0.15, 0.15) for _ in sqis]
        sizes = [max(50, s * 2000) for s in sqis]
        plt.scatter(xs, ys, s=sizes, alpha=0.4, label=f"{cluster} ({len(sqis)})")
    plt.legend()
    plt.title("LexMemory Resonance Field (SQI-weighted)")
    plt.yticks(y_positions, list(clusters.keys()))
    plt.axis("off")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150)
    print(json.dumps({"output": str(OUT_PATH), "clusters": {k: len(v) for k, v in clusters.items()}}, indent=2))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    generate_field_map()