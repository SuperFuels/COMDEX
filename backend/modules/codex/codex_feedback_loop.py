# 📁 codex_feedback_loop.py

from backend.modules.codex.codex_core import CodexCore
from backend.modules.glyphos.glyph_mutator import mutate_glyph, propose_mutation
from backend.modules.codex.codex_mind_model import CodexMindModel
from backend.modules.hexcore.memory_engine import MEMORY
import time
import logging
logger = logging.getLogger("CodexFeedbackLoop")

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
            if isinstance(result, str) and "error" in result.lower():
                print(f"🚫 Negative feedback, propose fix: {glyph}")
                propose_mutation(glyph, reason="runtime error")
                score = -1
            elif isinstance(result, str) and "success" in result.lower():
                print(f"✅ Reinforced: {glyph}")
                score = 2
            elif isinstance(result, str) and "executed" in result.lower():
                score = 1.5

            # ✅ Store feedback in memory for trace and insight
            MEMORY.store({
                "label": "codex_feedback",
                "content": {  # required field for MEMORY engine
                    "glyph": glyph,
                    "result": result,
                    "metadata": metadata,
                },
                "type": "feedback_trace",
                "score": score,
                "cost": cost,
                "linked_tags": self.mind_model.linked_contexts,
                "timestamp": time.time(),
            })

            # Optional: future enhancements like cumulative scores or blocking bad glyphs

    def initialize(self):
        """
        Compatibility stub for QQC boot sequence.
        Prepares feedback loop (no-op for now).
        """
        print("[CodexFeedbackLoop] Initialized feedback subsystem.")

    @staticmethod
    def rollback_to_last_stable_state(context):
        state = context.get("container_state")
        if state and "last_stable_snapshot" in state:
            state["current"] = state["last_stable_snapshot"]
            logger.info("[QQC] Container rolled back to last stable snapshot")
        else:
            logger.warning("[QQC] No stable snapshot available for rollback")

    from backend.modules.glyphvault.soul_law_validator import verify_transition

    @staticmethod
    def enforce_soul_law(context, codex_program):
        """
        Enforces SoulLaw ethical constraints before executing a Codex program.
        Uses the unified validator in glyphvault.soul_law_validator.
        """
        try:
            # Run SoulLaw transition check
            if not verify_transition(context, codex_program):
                logger.warning(f"[❌ SoulLaw] Vetoed Codex transition: {codex_program}")
                CodexFeedbackLoop.rollback_to_last_stable_state(context)
                return False

            logger.debug("[✅ SoulLaw] Transition passed ethical validation.")
            return True

        except Exception as e:
            logger.error(f"[⚠️ SoulLaw] Enforcement error: {e}")
            # For safety, veto if validator fails
            CodexFeedbackLoop.rollback_to_last_stable_state(context)
            return False