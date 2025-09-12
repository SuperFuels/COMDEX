"""
🌀 Relevance Scroll Engine (A3)
Merged + Enhanced Version — Part of Spatial Cognition Interface (SCI)

Supports:
- Relevance-based memory scroll loading
- Manual scroll injection into QFC or container
- Scroll execution trace logging
- Integration with KG Writer, QFC Runtime, and Memory
"""

import time
from typing import Dict, Optional, Any, List

from backend.modules.memory.memory_loader import load_scroll_from_memory
from backend.modules.memory.memory_saver import save_scroll_to_memory
from backend.modules.utils.cache_utils import simple_cache
from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
from backend.modules.container_runtime import get_active_container_id


class ScrollEngine:
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or "default"
        self.scroll_log: List[Dict[str, Any]] = []
        self.cache = {}

    @simple_cache(ttl=60)
    def fetch_scroll(self, scroll_id: str) -> Dict[str, Any]:
        """
        Load a scroll by ID. Caches result for fast reuse.
        """
        scroll = load_scroll_from_memory(self.user_id, scroll_id)
        if not scroll:
            raise FileNotFoundError(f"Scroll '{scroll_id}' not found for user {self.user_id}")
        
        self.scroll_log.append({
            "scroll_id": scroll_id,
            "status": "fetched",
            "source": "memory",
        })
        return scroll

    @simple_cache(ttl=60)
    def get_relevant_scrolls(self, context_label: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return recent or context-relevant scrolls (sorted by timestamp).
        """
        scrolls = load_scroll_from_memory(self.user_id)
        if context_label:
            scrolls = [s for s in scrolls if context_label.lower() in s.get("label", "").lower()]
        
        return sorted(scrolls, key=lambda s: s.get("timestamp", 0), reverse=True)

    def inject_scroll_to_field(self, scroll: Dict[str, Any], container_id: Optional[str] = None) -> bool:
        """
        Injects a raw scroll dict into the KG + container.
        """
        container_id = container_id or get_active_container_id()
        content = scroll.get("content", "")
        label = scroll.get("label", "injected_scroll")
        timestamp = scroll.get("timestamp", time.time())

        kg_writer.inject_glyph(
            content=content,
            glyph_type="scroll",
            metadata={"label": label, "timestamp": timestamp},
            region="scroll_engine",
            plugin="ScrollEngine",
            container_id=container_id,
        )

        print(f"📜 Injected scroll [{label}] into container [{container_id}]")
        return True

    def inject_scroll_into_qfc(self, qfc_instance, field_id: str, scroll_id: str):
        """
        Fetch a scroll by ID and inject into QFC instance.
        """
        scroll_data = self.fetch_scroll(scroll_id)
        qfc_instance.inject_scroll(field_id, scroll_data)
        print(f"🌌 Injected scroll [{scroll_id}] into QFC field [{field_id}]")

    def save_scroll(self, label: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save scroll to memory.
        """
        metadata = metadata or {}
        save_scroll_to_memory(self.user_id, label, content, metadata)
        print(f"💾 Scroll saved for user [{self.user_id}]: {label}")
        return True

    def list_scroll_history(self) -> List[Dict[str, Any]]:
        return self.scroll_log

    def shutdown(self):
        self.scroll_log.clear()
        self.cache.clear()


# Singleton (for default usage)
scroll_engine = ScrollEngine()