# 📁 codex_memory_triggers.py
# ============================

from backend.modules.memory.memory_engine import retrieve_recent_memories
from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_context_adapter import adapt_codex_context

class CodexMemoryTrigger:
    def __init__(self):
        self.codex = CodexCore()

    def scan_and_trigger(self):
        entries = retrieve_recent_memories(limit=20)
        for entry in entries:
            content = entry.get("content", "")
            if self.is_codexlang_glyph(content):
                print(f"🔁 Triggering glyph from memory: {content}")

                # Use full context adapter
                context = adapt_codex_context(content, source="memory")
                context["memory"] = {
                    "id": entry.get("id"),
                    "timestamp": entry.get("timestamp"),
                    "tags": entry.get("tags", []),
                }

                self.codex.execute(content, context=context)

    def is_codexlang_glyph(self, text):
        # Heuristic for valid CodexLang strings
        return (
            isinstance(text, str)
            and "⟦" in text
            and ("→" in text or "↔" in text or "⊕" in text or "⟲" in text)
            and text.strip().endswith("⟧")
        )