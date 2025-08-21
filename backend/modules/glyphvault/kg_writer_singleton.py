# kg_writer_singleton.py

from typing import Optional

_kg_writer_instance = None

def get_kg_writer():
    global _kg_writer_instance
    if _kg_writer_instance is None:
        # 🔁 Delayed import to avoid circular loop
        from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
        _kg_writer_instance = KnowledgeGraphWriter()
    return _kg_writer_instance