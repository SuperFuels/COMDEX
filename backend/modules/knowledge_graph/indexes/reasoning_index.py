# backend/modules/knowledge_graph/indexes/reasoning_index.glyph

"""
🌀 Reasoning Index
Stores "Why I chose this..." reflection chains tied to glyph nodes in the Knowledge Graph.
Auto-populated from CodexExecutor + KnowledgeGraphWriter.
"""

from typing import Dict, List
import time

reasoning_index: List[Dict] = []

def add_reasoning_entry(glyph_id: str, reasoning: str, context: Dict):
    entry = {
        "glyph_id": glyph_id,
        "reasoning": reasoning,
        "context": context,
        "timestamp": time.time(),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    reasoning_index.append(entry)
    return entry

def get_reasoning_for_glyph(glyph_id: str) -> List[Dict]:
    return [e for e in reasoning_index if e["glyph_id"] == glyph_id]