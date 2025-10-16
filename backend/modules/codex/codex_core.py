from backend.modules.glyphos.glyph_instruction_set import INSTRUCTION_SET, get_instruction
from backend.modules.glyphos.symbolic_hash_engine import symbolic_hash
from backend.modules.glyphos.glyph_mutator import propose_mutation
from backend.modules.codex.codex_cost_estimator import CodexCostEstimator
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ DNA upgrade registration
DNA_SWITCH.register(__file__)

# ✅ Lazy GlyphTraceLogger
_glyph_trace_logger = None


class CodexCore:
    """
    Core symbolic execution engine.
    - Executes CodexLang glyphs or photon capsules
    - Handles symbolic hashing, mutation triggers, and cost estimation
    - Fully compatible with QQC → SQI → Codex pipeline
    """

    def __init__(self):
        self.known_hashes = set()
        self.execution_log = []
        self.cost_estimator = CodexCostEstimator()

    def _get_logger(self):
        """Lazy-load GlyphTraceLogger only when needed to break circular imports."""
        global _glyph_trace_logger
        if _glyph_trace_logger is None:
            from backend.modules.glyphos.glyph_trace_logger import GlyphTraceLogger
            _glyph_trace_logger = GlyphTraceLogger()
        return _glyph_trace_logger

    # ──────────────────────────────────────────────
    #  Main Execution Entry
    # ──────────────────────────────────────────────
    def execute(self, data, context: dict = None):
        """
        Execute symbolic glyph(s) or a photon capsule (dict-based beam payload).
        Accepts:
          - str  → single glyph string
          - dict → capsule or beam_data with "glyphs" key
          - list → direct list of glyphs
        """
        from backend.modules.glyphos.codexlang_translator import (
            parse_codexlang_string,
            translate_to_instruction
        )

        context = context or {}

        # 🧩 Normalize input into glyph list
        if isinstance(data, str):
            glyphs = [data]
        elif isinstance(data, dict):
            glyphs = data.get("glyphs") or data.get("steps") or [str(data)]
        elif isinstance(data, list):
            glyphs = data
        else:
            raise TypeError(f"Unsupported glyph input type: {type(data)}")

        results = []

        # ──────────────────────────────────────────────
        #  Execute each glyph sequentially
        # ──────────────────────────────────────────────
        for glyph in glyphs:
            if isinstance(glyph, str):
                glyph = glyph.strip()
            elif isinstance(glyph, dict):
                # Extract logic/operator representation
                glyph = glyph.get("logic") or glyph.get("operator") or str(glyph)
            else:
                glyph = str(glyph)

            glyph_hash = symbolic_hash(glyph)
            if glyph_hash in self.known_hashes:
                print(f"⚠️ Duplicate glyph skipped: {glyph}")
                continue

            self.known_hashes.add(glyph_hash)

            # 🧠 Parse CodexLang structure
            parsed = parse_codexlang_string(glyph)
            if not parsed:
                print(f"❌ Failed to parse glyph: {glyph}")
                results.append({"status": "parse_error", "glyph": glyph})
                continue

            try:
                # 🔁 Execute symbolic logic
                memory = context.get("memory")
                result = translate_to_instruction(parsed, memory=memory)

                # 🧾 Trace logging
                source = context.get("source", "codex_core")
                self._get_logger().log_trace(glyph, result, context=source)
                self.execution_log.append({"glyph": glyph, "result": result})

                # 🧬 Auto-mutation triggers
                action_str = str(parsed.get("action", "")).lower()
                if parsed.get("tag") and "rewrite" in action_str:
                    propose_mutation(glyph, reason="CodexCore Rewrite Trigger")

                # 💰 Cost estimation
                cost = self.cost_estimator.estimate_glyph_cost(glyph, context)
                print(f"[🧮] Estimated glyph cost: {cost.total()} | Breakdown: {vars(cost)}")

                results.append({
                    "status": "executed",
                    "glyph": glyph,
                    "result": result,
                    "cost": {
                        "total": cost.total(),
                        "breakdown": vars(cost),
                    },
                })

            except Exception as e:
                print(f"💥 Error during execution of glyph: {glyph}\n{e}")
                results.append({
                    "status": "execution_error",
                    "glyph": glyph,
                    "error": str(e),
                })

        # Return single result or aggregated batch
        if len(results) == 1:
            return results[0]
        return {"status": "batch_executed", "results": results}

    # ──────────────────────────────────────────────
    #  Utilities
    # ──────────────────────────────────────────────
    def get_log(self, limit=25):
        return self.execution_log[-limit:]

    def reset(self):
        self.known_hashes.clear()
        self.execution_log.clear()