from backend.modules.glyphos.glyph_instruction_set import INSTRUCTION_SET, get_instruction
from backend.modules.glyphos.symbolic_hash_engine import symbolic_hash
from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
from backend.modules.glyphos.glyph_mutator import propose_mutation
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator

logger = GlyphTraceLogger()

class CodexCore:
    def __init__(self):
        self.known_hashes = set()
        self.execution_log = []
        self.cost_estimator = CodexCostEstimator()

    def execute(self, glyph: str, context: dict = {}):
        from backend.modules.glyphos.codexlang_translator import (  # ⬅ Delayed import
            parse_codexlang_string,
            translate_to_instruction
        )

        glyph = glyph.strip()
        h = symbolic_hash(glyph)

        if h in self.known_hashes:
            print(f"⚠️ Duplicate glyph skipped: {glyph}")
            return "duplicate"

        self.known_hashes.add(h)

        # 🧠 Parse full CodexLang structure
        parsed = parse_codexlang_string(glyph)
        if not parsed:
            print(f"❌ Failed to parse glyph: {glyph}")
            return "parse_error"

        try:
            # 🧠 Translate into executable instruction
            memory = context.get("memory")
            result = translate_to_instruction(parsed, memory=memory)

            # 🧾 Log and trace
            logger.log_trace(glyph, result, context=context.get("source", "codex_core"))
            self.execution_log.append({"glyph": glyph, "result": result})

            # 🧬 Auto-propose rewrite mutation if triggered
            action_str = str(parsed.get("action"))
            if parsed.get("tag") and "rewrite" in action_str.lower():
                propose_mutation(glyph, reason="CodexCore Rewrite Trigger")

            # 💰 Cost estimation
            cost = self.cost_estimator.estimate_glyph_cost(glyph, context or {})
            print(f"[🧮] Estimated glyph cost: {cost.total()} | Breakdown: {vars(cost)}")

            return result
        except Exception as e:
            print(f"💥 Error during execution of glyph: {glyph}\n{e}")
            return "execution_error"

    def get_log(self, limit=25):
        return self.execution_log[-limit:]

    def reset(self):
        self.known_hashes.clear()
        self.execution_log.clear()