# pattern_crdt_sync.py

from backend.modules.patterns.pattern_registry import PatternRegistry
from backend.modules.collab.crdt_handler import CRDTDocument
from backend.modules.collab.sync_broadcast import broadcast_crdt_update

class PatternCRDTSync:
    """
    Enables collaborative editing of patterns across agents using CRDT sync.
    """

    def __init__(self):
        self.registry = PatternRegistry()
        self.crdt_docs: dict = {}  # pattern_id → CRDTDocument

    def load_or_create_doc(self, pattern_id: str) -> CRDTDocument:
        if pattern_id not in self.crdt_docs:
            pattern = self.registry.get(pattern_id)
            if pattern:
                doc = CRDTDocument(doc_id=pattern_id, initial=pattern.to_dict())
                self.crdt_docs[pattern_id] = doc
        return self.crdt_docs[pattern_id]

    def apply_update(self, pattern_id: str, update: dict) -> dict:
        doc = self.load_or_create_doc(pattern_id)
        doc.apply_update(update)
        broadcast_crdt_update(pattern_id, update)
        updated_data = doc.to_data()
        updated_pattern = pattern_registry.get(pattern_id)
        updated_pattern.metadata = updated_data.get("metadata", {})
        updated_pattern.glyphs = updated_data.get("glyphs", [])
        self.registry.register(updated_pattern)
        return updated_data

    def get_latest(self, pattern_id: str) -> dict:
        doc = self.load_or_create_doc(pattern_id)
        return doc.to_data()