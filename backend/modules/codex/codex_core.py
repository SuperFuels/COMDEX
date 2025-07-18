# 📁 backend/modules/codex/codex_core.py

from backend.modules.glyphos.glyph_instruction_set import INSTRUCTION_SET, get_instruction
from backend.modules.glyphos.symbolic_hash_engine import symbolic_hash
from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
from backend.modules.dna_chain.glyph_mutator import propose_mutation
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator

logger = GlyphTraceLogger()

class CodexCore:
    def __init__(self):
        self.known_hashes = set()
        self.execution_log = []
        self.cost_estimator = CodexCostEstimator()

    def execute(self, glyph: str, context: dict = {}):
        glyph = glyph.strip()
        h = symbolic_hash(glyph)

        if h in self.known_hashes:
            print(f"⚠️ Duplicate glyph skipped: {glyph}")
            return "duplicate"

        self.known_hashes.add(h)

        instruction = self._parse_instruction(glyph)
        if not instruction:
            print(f"❌ Failed to parse glyph: {glyph}")
            return "parse_error"

        op = instruction.get("operator")
        handler = get_instruction(op)

        if not handler:
            print(f"❓ Unknown operator '{op}' in glyph: {glyph}")
            return "unknown_operator"

        try:
            # Execute using instruction wrapper
            result = handler.execute(
                instruction.get("value"),
                instruction.get("action"),
                memory=context.get("memory")
            )

            logger.log_trace(glyph, result, context=context.get("source", "codex_core"))
            self.execution_log.append({"glyph": glyph, "result": result})

            if op == "→" and "rewrite" in str(result).lower():
                propose_mutation(glyph, reason="CodexCore Rewrite Trigger")

            # ✅ Estimate cost
            cost = self.cost_estimator.estimate_glyph_cost(glyph, context or {})
            print(f"[🧮] Estimated glyph cost: {cost.total()} | Breakdown: {vars(cost)}")

            return result
        except Exception as e:
            print(f"💥 Error during execution of glyph: {glyph}\n{e}")
            return "execution_error"

    def _parse_instruction(self, glyph: str):
        try:
            inner = glyph.strip("⟦⟧").strip()
            parts = inner.split("→")
            left = parts[0].strip()
            action = parts[1].strip() if len(parts) > 1 else "Reflect"
            type_tag, value = left.split(":", 1)
            g_type, tag = type_tag.split("|", 1)
            return {
                "type": g_type.strip(),
                "tag": tag.strip(),
                "value": value.strip(),
                "operator": "→",
                "action": action
            }
        except Exception as e:
            print(f"[⚠️] Parse error in CodexCore: {e}")
            return None

    def get_log(self, limit=25):
        return self.execution_log[-limit:]

    def reset(self):
        self.known_hashes.clear()
        self.execution_log.clear()