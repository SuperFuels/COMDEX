# 📁 codex_feedback_loop.py

from backend.modules.codex.codex_core import CodexCore
from backend.modules.dna_chain.glyph_mutator import propose_mutation
from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger

class CodexFeedbackLoop:
    def __init__(self):
        self.codex = CodexCore()
        self.logger = GlyphTraceLogger()

    def reinforce_or_mutate(self):
        traces = self.logger.get_recent_traces()
        for trace in traces:
            glyph = trace["glyph"]
            result = trace["result"]

            if "error" in result.lower():
                print(f"🚫 Negative feedback, propose fix: {glyph}")
                propose_mutation(glyph, reason="runtime error")
            elif "success" in result.lower():
                print(f"✅ Reinforced: {glyph}")