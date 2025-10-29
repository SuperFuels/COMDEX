"""
🌀 Relevance Scroll Engine (A3)
Merged + Enhanced Version — Part of Spatial Cognition Interface (SCI)

Supports:
- Relevance-based memory scroll loading
- Manual scroll injection into QFC or container
- Scroll execution trace logging
- Integration with KG Writer, QFC Runtime, and Resonant Memory
"""

from __future__ import annotations
import time
from typing import Dict, Optional, Any, List

# ------------------------------------------------------------
# 🔹 Integrations: Memory, Knowledge Graph, Utilities
# ------------------------------------------------------------
try:
    from backend.modules.resonant_memory.resonant_memory_loader import load_scroll_from_memory
except Exception:
    def load_scroll_from_memory(scroll_id: str):
        print(f"[StubMemory] ⚠️ Simulated scroll load for '{scroll_id}'")
        return {"id": scroll_id, "content": f"stub::{scroll_id}", "label": "stub_scroll", "timestamp": time.time()}

try:
    from backend.modules.resonant_memory.resonant_memory_saver import save_scroll_to_memory
except Exception:
    def save_scroll_to_memory(user_id: str, label: str, content: str, metadata: Dict[str, Any]):
        print(f"[StubMemorySaver] 💾 Saved stub scroll '{label}' (user: {user_id})")
        return True

try:
    from backend.modules.utils.cache_utils import simple_cache
except Exception:
    def simple_cache(ttl: int = 60):
        def decorator(fn):
            cache = {}
            def wrapper(*args, **kwargs):
                key = (args, tuple(sorted(kwargs.items())))
                if key in cache:
                    return cache[key]
                res = fn(*args, **kwargs)
                cache[key] = res
                return res
            return wrapper
        return decorator

try:
    from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
except Exception:
    class _StubKGWriter:
        def inject_glyph(self, **kwargs):
            print(f"[StubKG] Glyph injected: {kwargs}")
    kg_writer = _StubKGWriter()

try:
    from backend.modules.container_runtime import get_active_container_id
except Exception:
    def get_active_container_id():
        return "default_container"

# ------------------------------------------------------------
# 🌐 Scroll Engine
# ------------------------------------------------------------

class ScrollEngine:
    """
    Handles scroll retrieval, caching, injection, and persistence.
    Integrated with Resonant Memory + Knowledge Graph systems.
    """

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or "default"
        self.scroll_log: List[Dict[str, Any]] = []
        self.cache: Dict[str, Any] = {}

    # ============================================================
    # 📜 Fetch / Query
    # ============================================================

    @simple_cache(ttl=60)
    def fetch_scroll(self, scroll_id: str) -> Dict[str, Any]:
        """
        Load a scroll by ID. Cached for fast reuse.
        """
        scroll = load_scroll_from_memory(scroll_id)
        if not scroll:
            raise FileNotFoundError(f"Scroll '{scroll_id}' not found for user {self.user_id}")

        self.scroll_log.append({
            "scroll_id": scroll_id,
            "status": "fetched",
            "source": "resonant_memory",
            "timestamp": time.time(),
        })
        return scroll

    @simple_cache(ttl=60)
    def get_relevant_scrolls(self, context_label: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return recent or context-relevant scrolls (sorted by timestamp).
        """
        # This assumes your resonant memory loader supports list fetch
        try:
            scrolls = load_scroll_from_memory("*")  # wildcard pattern
        except Exception:
            scrolls = []

        if context_label:
            scrolls = [s for s in scrolls if context_label.lower() in s.get("label", "").lower()]

        return sorted(scrolls, key=lambda s: s.get("timestamp", 0), reverse=True)

    # ============================================================
    # 🌌 Injection / Persistence
    # ============================================================

    def inject_scroll_to_field(self, scroll: Dict[str, Any], container_id: Optional[str] = None) -> bool:
        """
        Inject a raw scroll dict into the Knowledge Graph + container system.
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
        Fetch a scroll by ID and inject it into the QFC instance.
        """
        scroll_data = self.fetch_scroll(scroll_id)
        qfc_instance.inject_scroll(field_id, scroll_data)
        print(f"🌌 Injected scroll [{scroll_id}] into QFC field [{field_id}]")

    def save_scroll(self, label: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Persist a scroll to Resonant Memory (or stub fallback).
        """
        metadata = metadata or {}
        save_scroll_to_memory(self.user_id, label, content, metadata)
        print(f"💾 Scroll saved for user [{self.user_id}]: {label}")
        return True

    # ============================================================
    # 🧾 Logs / Lifecycle
    # ============================================================

    def list_scroll_history(self) -> List[Dict[str, Any]]:
        return self.scroll_log

    def shutdown(self):
        print(f"[ScrollEngine] Shutdown for user {self.user_id}")
        self.scroll_log.clear()
        self.cache.clear()


# Singleton (for global access)
scroll_engine = ScrollEngine()