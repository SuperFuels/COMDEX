"""
backend.modules.knowledge_graph
────────────────────────────────────────────
Central entrypoint for Knowledge Graph and Writer singletons.
Ensures the KG and KGWriter are created only once per runtime.
────────────────────────────────────────────
"""

from typing import Optional

_global_kg = None
_global_writer = None


def build_kg():
    """Initialize or reuse a cached Knowledge Graph instance."""
    global _global_kg
    if _global_kg is not None:
        print("[KG] 🧠 Using cached Knowledge Graph instance.")
        return _global_kg

    from backend.modules.knowledge_graph.core import KnowledgeGraph
    try:
        kg = KnowledgeGraph()
        kg.load_boot_nodes()
        _global_kg = kg
        print("[KG] ✅ Knowledge Graph built and cached.")
        return kg
    except Exception as e:
        print(f"[KG] ⚠️ Failed to initialize Knowledge Graph: {e}")
        return None


def get_kg():
    """Safe getter for the global Knowledge Graph instance."""
    global _global_kg
    if _global_kg is None:
        return build_kg()
    return _global_kg


def get_writer():
    """Singleton accessor for the global KnowledgeGraphWriter."""
    global _global_writer
    if _global_writer is not None:
        return _global_writer

    from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
    _global_writer = KnowledgeGraphWriter()
    print("[KGWriter] ✅ Global writer instance created and cached.")
    return _global_writer


# Optional explicit reset (debug/testing only)
def reset_kg_cache():
    global _global_kg, _global_writer
    _global_kg = None
    _global_writer = None
    print("[KG] ♻️ Knowledge Graph cache reset.")