from backend.modules.glyphos.glyph_instruction_set import INSTRUCTION_SET, get_instruction
from backend.modules.glyphos.symbolic_hash_engine import symbolic_hash
from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
from backend.modules.glyphos.glyph_mutator import propose_mutation
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ DNA upgrade registration
DNA_SWITCH.register(__file__)

logger = GlyphTraceLogger()

class CodexCore:
    def __init__(self):
        self.known_hashes = set()
        self.execution_log = []
        self.cost_estimator = CodexCostEstimator()

    def execute(self, glyph: str, context: dict = {}):
        from backend.modules.glyphos.codexlang_translator import (
            parse_codexlang_string,
            translate_to_instruction
        )

        glyph = glyph.strip()
        glyph_hash = symbolic_hash(glyph)

        if glyph_hash in self.known_hashes:
            print(f"⚠️ Duplicate glyph skipped: {glyph}")
            return {"status": "duplicate", "glyph": glyph}

        self.known_hashes.add(glyph_hash)

        # 🧠 Parse full CodexLang structure
        parsed = parse_codexlang_string(glyph)
        if not parsed:
            print(f"❌ Failed to parse glyph: {glyph}")
            return {"status": "parse_error", "glyph": glyph}

        try:
            # Translate into symbolic instruction
            memory = context.get("memory")
            result = translate_to_instruction(parsed, memory=memory)

            # Log + store trace
            source = context.get("source", "codex_core")
            logger.log_trace(glyph, result, context=source)
            self.execution_log.append({"glyph": glyph, "result": result})

            # Trigger rewrite mutation if glyph contains symbolic rewrite logic
            action_str = str(parsed.get("action", "")).lower()
            if parsed.get("tag") and "rewrite" in action_str:
                propose_mutation(glyph, reason="CodexCore Rewrite Trigger")

            # Estimate symbolic execution cost
            cost = self.cost_estimator.estimate_glyph_cost(glyph, context or {})
            print(f"[🧮] Estimated glyph cost: {cost.total()} | Breakdown: {vars(cost)}")

            return {
                "status": "executed",
                "glyph": glyph,
                "result": result,
                "cost": {
                    "total": cost.total(),
                    "breakdown": vars(cost)
                }
            }

        except Exception as e:
            print(f"💥 Error during execution of glyph: {glyph}\n{e}")
            return {"status": "execution_error", "glyph": glyph, "error": str(e)}

    def get_log(self, limit=25):
        return self.execution_log[-limit:]

    def reset(self):
        self.known_hashes.clear()
        self.execution_log.clear()