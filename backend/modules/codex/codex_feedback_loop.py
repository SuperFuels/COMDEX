# 📁 codex_feedback_loop.py

from backend.modules.codex.codex_core import CodexCore
from backend.modules.glyphos.glyph_mutator import mutate_glyph, propose_mutation
from backend.modules.codex.codex_mind_model import CodexMindModel
from backend.modules.hexcore.memory_engine import MEMORY

class CodexFeedbackLoop:
    def __init__(self):
        self.codex = CodexCore()
        # ✅ Lazy import of GlyphTraceLogger to break circular dependency
        from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
        self.logger = GlyphTraceLogger()
        self.mind_model = CodexMindModel()

    def reinforce_or_mutate(self):
        traces = self.logger.get_recent_traces()

        for trace in traces:
            glyph = trace.get("glyph")
            result = trace.get("result", "")
            cost = trace.get("cost", None)
            metadata = trace.get("metadata", {})

            # Update prediction model with glyph usage
            self.mind_model.observe(glyph)

            # Basic scoring
            score = 1
            if "error" in result.lower():
                print(f"🚫 Negative feedback, propose fix: {glyph}")
                propose_mutation(glyph, reason="runtime error")
                score = -1
            elif "success" in result.lower():
                print(f"✅ Reinforced: {glyph}")
                score = 2
            elif "executed" in result.lower():
                score = 1.5

            # Store feedback in memory for trace and insight
            MEMORY.store({
                "label": "codex_feedback",
                "type": "feedback_trace",
                "glyph": glyph,
                "score": score,
                "result": result,
                "cost": cost,
                "linked_tags": self.mind_model.linked_contexts,
            })

            # Optional future: accumulate scores or block failing glyphs