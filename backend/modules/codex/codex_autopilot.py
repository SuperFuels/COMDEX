# 📁 codex_autopilot.py
# ============================

from backend.modules.codex.codex_core import CodexCore
from backend.modules.dna_chain.glyph_mutator import score_and_propose_mutation
from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
import random
import time

class CodexAutopilot:
    def __init__(self):
        self.codex = CodexCore()
        self.logger = GlyphTraceLogger()

    def evolve(self):
        recent = self.logger.get_recent_traces(limit=10)
        for trace in recent:
            glyph = trace["glyph"]
            result = trace["result"]

            # Randomized feedback-based mutation
            if random.random() < 0.25:  # 25% mutation chance
                print(f"🧬 Proposing mutation based on runtime: {glyph}")
                score_and_propose_mutation(glyph, context="autopilot", result=result)

    def loop(self, interval=10):
        while True:
            self.evolve()
            time.sleep(interval)
