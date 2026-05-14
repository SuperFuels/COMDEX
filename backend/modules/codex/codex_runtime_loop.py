# 📁 codex_runtime_loop.py

"""
Codex Runtime Loop

Executes CodexLang glyphs from a queue or schedule at runtime.
Supports real-time symbolic execution, mutation triggering, and memory feedback.
"""

import time
from typing import List, Dict

from backend.modules.glyphos.codexlang_translator import run_codexlang_string
from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.codex.codex_mind_model import CodexMindModel

class CodexRuntimeLoop:
    def __init__(self):
        self.queue: List[str] = []  # Glyph strings to run
        self.delay = 1.0  # Seconds between executions
        self.running = False
        self.codex = CodexCore()
        self.metrics = CodexMetrics()
        self.mind_model = CodexMindModel()
        self.retry_limit = 2

    def add_glyph(self, glyph_str: str):
        self.queue.append(glyph_str)

    def run_once(self):
        if not self.queue:
            return None

        glyph = self.queue.pop(0)
        context = {
            "source": "codex_runtime_loop",
            "memory": MEMORY.get_recent(limit=5)  # Runtime context memory
        }

        for attempt in range(1, self.retry_limit + 1):
            try:
                result = run_codexlang_string(glyph, context=context)
                self.metrics.record_execution()
                self.mind_model.observe(glyph)

                MEMORY.store({
                    "label": "codex_loop",
                    "type": "glyph_execution",
                    "glyph": glyph,
                    "result": result,
                    "attempt": attempt,
                })

                print(f"[Codex Loop ✅] Executed: {glyph} -> {result}")
                return result
            except Exception as e:
                self.metrics.record_error()
                print(f"[Codex Loop ⚠️] Error on attempt {attempt} for {glyph}: {e}")

        print(f"[Codex Loop ⛔] Failed to execute: {glyph} after {self.retry_limit} attempts")
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

    def suggest_operator(self) -> str:
        return self.mind_model.suggest_next_operator()

    def status(self) -> Dict:
        return {
            "queued_glyphs": len(self.queue),
            "is_running": self.running,
            "suggested_operator": self.suggest_operator(),
            "metrics": self.metrics.dump()
        }


# Optional test execution block
if __name__ == "__main__":
    loop = CodexRuntimeLoop()
    loop.load_schedule([
        "⟦ Logic | Reflect: Self -> ⟲(Dream) ⟧",
        "⟦ Memory | Save: Truth -> ⊕(Store, Recall) ⟧"
    ])
    loop.run_forever()