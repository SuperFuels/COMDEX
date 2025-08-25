# ✅ backend/modules/knowledge_graph/crdt_registry_singleton.py

from backend.modules.knowledge_graph.crdt.crdt_registry import CRDTRegistry

_crdt_registry = CRDTRegistry()

def get_crdt_registry() -> CRDTRegistry:
    return _crdt_registry