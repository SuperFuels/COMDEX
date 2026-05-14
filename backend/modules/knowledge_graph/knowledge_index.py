"""
Compatibility shim: keep legacy import path working.

Old:
    from backend.modules.knowledge_graph.knowledge_index import knowledge_index

Real implementation lives at:
    backend/modules/knowledge_graph/indexes/knowledge_index.py
"""
from .indexes.knowledge_index import *  # re-export everything
from .indexes.knowledge_index import knowledge_index, KnowledgeIndex

__all__ = ["knowledge_index", "KnowledgeIndex"]
