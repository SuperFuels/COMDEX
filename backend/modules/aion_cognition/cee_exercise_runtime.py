# ================================================================
# 🎯 CEE Lexical Exercise Runtime - Phase 45G.10 Integration
# ================================================================
"""
Runs live lexical training sessions using the Cognitive Exercise Engine (CEE).

Each exercise is dynamically generated via CEE templates and evaluated for
symbolic accuracy and resonance coherence.

Integrates:
  - cee_language_templates (Match-Up, Anagram, Unjumble)
  - cee_language_cloze (Cloze, Group Sort)
  - LexiCoreBridge (semantic data)
  - LanguageHabitEngine (habit reinforcement feedback)
  - LexMemory (persistent symbolic reinforcement)

Outputs:
    data/sessions/lexsession_v1.qdata.json
"""

import json, time, random, logging
from pathlib import Path
from statistics import mean
from dataclasses import asdict

from backend.modules.aion_cognition.cee_language_templates import (
    generate_matchup,
    generate_anagram,
    generate_unjumble,
)
from backend.modules.aion_cognition.cee_language_cloze import (
    generate_cloze,
    generate_group_sort,
)
from backend.modules.aion_cognition.cee_lexicore_bridge import LexiCoreBridge
from backend.modules.aion_cognition.language_habit_engine import update_habit_metrics
from backend.modules.aion_cognition.cee_lex_memory import (
    recall_from_memory,
    update_lex_memory,
)
from backend.modules.aion_cognition.cee_math_schema import MathExercise

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/sessions/lexsession_v1.qdata.json")


# ================================================================
# 🧩 Core Runtime
# ================================================================
class CEEExerciseRuntime:
    """Handles execution of lexical and symbolic training sessions."""

    def __init__(self):
        self.session_id = f"LEX-{int(time.time())}"
        self.session = []
        self.bridge = LexiCoreBridge()
        logger.info(f"[CEE-Runtime] Session {self.session_id} initialized")

    # ------------------------------------------------------------------
    def run_exercise(self, ex):
        """Run a single exercise - handles different CEE types safely."""
        ex_type = ex.get("type", "unknown")
        prompt = ex.get("prompt", "")
        options = ex.get("options", [])

        # Some exercises (like group_sort) use 'items' instead of 'options'
        if not options and "items" in ex:
            options = ex["items"]

        logger.info(f"[CEE-Runtime] Exercise -> {ex_type}: {prompt}")

        if not options:
            logger.warning(f"[CEE-Runtime] Skipping {ex_type} (no options).")
            return None

        # ------------------------------------------------------------
        # 🧠 Memory Recall Integration
        memory_hit = recall_from_memory(prompt)
        if memory_hit:
            guess = memory_hit["answer"]
            logger.info(f"[CEE-Runtime] 🧠 Recall -> {prompt} -> {guess}")
        else:
            guess = random.choice(options)

        # ------------------------------------------------------------
        correct = ex.get("answer", None)
        correct_flag = (guess == correct)
        resonance = ex.get("resonance", {"ρ": 0.0, "I": 0.0, "SQI": 0.0})
        perf = 1.0 if correct_flag else 0.0

        # ------------------------------------------------------------
        # 🧩 Reinforcement
        if correct_flag:
            update_lex_memory(prompt, correct, resonance)
            logger.info(f"[CEE-Runtime] ✅ Correct -> {guess}")
        else:
            logger.info(f"[CEE-Runtime] ❌ Wrong -> {guess} (expected {correct})")

        # Log entry
        self.session.append({
            "type": ex_type,
            "prompt": prompt,
            "guess": guess,
            "answer": correct,
            "correct": correct_flag,
            "resonance": resonance,
            "perf": perf,
            "timestamp": time.time(),
        })

    # ------------------------------------------------------------------
    def run_session(self, n: int = 8):
        """Run a full lexical training session."""
        generators = [
            generate_matchup,
            generate_anagram,
            generate_unjumble,
            generate_cloze,
            generate_group_sort,
        ]

        for _ in range(n):
            gen = random.choice(generators)

            # --- handle cloze ---
            if gen.__name__ == "generate_cloze":
                sentence = random.choice([
                    "The sun rises in the ____.",
                    "She plays the ____ beautifully.",
                    "Water freezes at zero ____.",
                    "He is reading a ____ book.",
                ])
                missing_word = "east" if "sun" in sentence else (
                    "piano" if "plays" in sentence else
                    "degrees" if "freezes" in sentence else
                    "interesting"
                )
                ex = gen(sentence, missing_word)

            # --- handle group_sort ---
            elif gen.__name__ == "generate_group_sort":
                groups = {"Fruits": ["apple", "banana"], "Animals": ["dog", "cat"]}
                ex = gen(groups)

            # --- handle unjumble ---
            elif gen.__name__ == "generate_unjumble":
                word = random.choice(["resonance", "quantum", "wave", "field", "light"])
                ex = gen(word)

            else:
                ex = gen()

            # Ensure dataclass compatibility
            if isinstance(ex, dict):
                if hasattr(ex, "__dataclass_fields__"):
                    ex = asdict(ex)
            self.run_exercise(ex)

        return self.finalize()

    # ------------------------------------------------------------------
    def finalize(self):
        """Aggregate metrics and export session summary."""
        if not self.session:
            logger.warning("[CEE-Runtime] No exercises completed.")
            return None

        ρ_vals = [e["resonance"]["ρ"] for e in self.session if "ρ" in e["resonance"]]
        I_vals = [e["resonance"]["I"] for e in self.session if "I" in e["resonance"]]
        SQI_vals = [e["resonance"]["SQI"] for e in self.session if "SQI" in e["resonance"]]
        perf_vals = [e["perf"] for e in self.session]

        summary = {
            "timestamp": time.time(),
            "session": self.session_id,
            "entries": len(self.session),
            "averages": {
                "ρ̄": round(mean(ρ_vals), 3) if ρ_vals else 0.0,
                "Ī": round(mean(I_vals), 3) if I_vals else 0.0,
                "SQĪ": round(mean(SQI_vals), 3) if SQI_vals else 0.0,
                "performance": round(mean(perf_vals), 3) if perf_vals else 0.0,
            },
            "schema": "LexSession.v1",
        }

        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(summary, open(OUT_PATH, "w"), indent=2)
        logger.info(f"[CEE-Runtime] Exported session summary -> {OUT_PATH}")

        # Habit update feedback
        update_habit_metrics(summary["averages"])
        print(json.dumps(summary, indent=2))
        return summary


# ================================================================
# 🚀 Entry Point
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runtime = CEEExerciseRuntime()
    runtime.run_session(10)