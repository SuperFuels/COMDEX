# backend/modules/codex/codex_runtime_loop.py

"""
Codex Runtime Loop

Executes CodexLang glyphs from a queue or schedule at runtime.
Supports real-time symbolic execution, mutation triggering, and memory feedback.
"""

import time
from typing import List, Dict

from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.codex.codex_core import CodexCore


class CodexRuntimeLoop:
    def __init__(self):
        self.queue: List[str] = []  # Glyph strings to run
        self.delay = 1.0  # Seconds between executions
        self.running = False
        self.codex = CodexCore()

    def add_glyph(self, glyph_str: str):
        self.queue.append(glyph_str)

    def run_once(self):
        if self.queue:
            glyph = self.queue.pop(0)
            context = {"source": "codex_runtime_loop"}
            result = run_codexlang_string(glyph, context=context)
            print(f"[Codex Loop] Executed: {glyph} → {result}")
            return result
        return None

    def run_forever(self):
        self.running = True
        print("🔁 Codex Runtime Loop Started")
        while self.running:
            self.run_once()
            time.sleep(self.delay)

    def stop(self):
        self.running = False
        print("⏹️ Codex Runtime Loop Stopped")

    def load_schedule(self, glyph_list: List[str]):
        self.queue.extend(glyph_list)

    def status(self) -> Dict:
        return {
            "queued_glyphs": len(self.queue),
            "is_running": self.running
        }


# Example usage (remove if importing elsewhere)
if __name__ == "__main__":
    loop = CodexRuntimeLoop()
    loop.load_schedule([
        "⟦ Logic | Reflect: Self → ⟲(Dream) ⟧",
        "⟦ Memory | Save: Truth → ⊕(Store, Recall) ⟧"
    ])
    loop.run_forever()