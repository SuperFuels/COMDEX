# File: backend/modules/consciousness/memory_bridge.py

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.dna_chain.glyph_trigger_logger import log_trigger_trace


class MemoryBridge:
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.memory = MemoryEngine(container_id)

    def trace_trigger(self, glyph: str, context: dict):
        """Log a glyph trigger trace entry with optional metadata."""
        trace_entry = {
            "glyph": glyph,
            "context": context,
            "memory_links": self.memory.search_links(glyph),
            "origin": context.get("origin", "unknown"),
            "role": context.get("role", "unspecified"),
        }
        log_trigger_trace(trace_entry, self.container_id)

    def store_trace(self, glyph: str, reason: str):
        """Store a readable log note into memory about glyph trigger reason."""
        note = f"🧠 Glyph '{glyph}' triggered — Reason: {reason}"
        self.memory.store(role="trigger_log", content=note)