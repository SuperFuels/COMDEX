from typing import Optional, Dict
from backend.modules.dna_chain.container_index_writer import add_to_index

def add_inferred_skill(
    title: str,
    tag: str,
    inferred_from: str,
    confidence: float = 0.85,
    plugin: str = "curiosity_engine"
):
    entry = {
        "id": None,
        "type": "inferred_skill",
        "content": title,
        "timestamp": None,
        "metadata": {
            "tags": [tag],
            "inferred_from": inferred_from,
            "confidence": confidence,
        },
        "plugin": plugin,
    }
    add_to_index("curiosity_index", entry)
    return entry