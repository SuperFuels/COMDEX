# 📁 codex_memory_triggers.py
# ============================

from backend.modules.memory.memory_engine import retrieve_recent_memories
from backend.modules.codex.codex_core import CodexCore

class CodexMemoryTrigger:
    def __init__(self):
        self.codex = CodexCore()

    def scan_and_trigger(self):
        entries = retrieve_recent_memories(limit=20)
        for entry in entries:
            content = entry.get("content", "")
            if "⟦" in content and "→" in content:
                print(f"🔁 Triggering glyph from memory: {content}")
                self.codex.execute(content, context={"source": "memory"})
