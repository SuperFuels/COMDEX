# ================================================================
# 🎬 CEE Exercise Playback Engine — Phase 45G.10 Integration
# ================================================================
"""
Plays back CEE-generated exercises in either:
  • simulate mode → automatic answers (with LexMemory recall)
  • interactive mode → user answers via console input

Expanded with advanced exercise generators:
  - Flash Card (definition recall)
  - Find Match (synonym/antonym)
  - Spin Wheel (creative challenge)

Now includes LexMemory reinforcement:
  - recall_from_memory(prompt) before answering
  - update_lex_memory(prompt, answer, resonance) after correct answers
"""

import json, time, random, logging
from pathlib import Path
from backend.modules.aion_cognition.cee_lexicore_bridge import LexiCoreBridge
from backend.modules.aion_cognition.language_habit_engine import update_habit_metrics
from backend.modules.aion_cognition.cee_lex_memory import (
    recall_from_memory,
    update_lex_memory,
)
from backend.modules.aion_cognition.cee_language_templates import (
    generate_matchup,
    generate_anagram,
    generate_unjumble,
    generate_flashcard,
    generate_find_match,
    generate_spin_wheel,
)
from backend.modules.aion_cognition.cee_language_cloze import (
    generate_cloze,
    generate_group_sort,
)

logger = logging.getLogger(__name__)
OUT_PATH = Path("data/sessions/playback_log.qdata.json")


# ================================================================
# 🧩 Playback Engine
# ================================================================
class CEEPlayback:
    def __init__(self, mode="simulate"):
        self.mode = mode
        self.session_id = f"PLAY-{int(time.time())}"
        self.session = []
        self.bridge = LexiCoreBridge()
        logger.info(f"[CEE-Playback] Session {self.session_id} started in {mode} mode")

    # ------------------------------------------------------------
    def play_exercise(self, ex):
        ex_type = ex.get("type", "unknown")
        prompt = ex.get("prompt", "")
        options = ex.get("options", [])
        answer = ex.get("answer", None)
        resonance = ex.get("resonance", {"ρ": 0, "I": 0, "SQI": 0})

        print(f"\n▶ {ex_type} — {prompt}")
        if options:
            print(f"Options: {', '.join(options)}")

        # --------------------------------------------------------
        # 🧠 LexMemory Recall Integration
        memory_hit = recall_from_memory(prompt)
        if memory_hit:
            guess = memory_hit["answer"]
            logger.info(f"[CEE-Playback] 🧠 Recall → {prompt} → {guess}")
        else:
            # Input phase: interactive or simulate
            if self.mode == "interactive":
                guess = input("Your answer: ").strip()
            else:
                guess = random.choice(options) if options else None

        # --------------------------------------------------------
        correct = (guess == answer)
        if correct:
            logger.info(f"[CEE-Playback] ✅ Correct: {guess}")
            update_lex_memory(prompt, answer, resonance)
        else:
            logger.info(f"[CEE-Playback] ❌ Wrong (expected {answer}): {guess}")

        # Log the attempt
        self.session.append({
            "type": ex_type,
            "prompt": prompt,
            "guess": guess,
            "answer": answer,
            "correct": correct,
            "resonance": resonance,
            "timestamp": time.time(),
        })

    # ------------------------------------------------------------
    def run(self, n=6):
        """Run multiple randomized exercises."""
        gens = [
            generate_matchup,
            generate_anagram,
            generate_unjumble,
            generate_flashcard,
            generate_find_match,
            generate_spin_wheel,
            generate_cloze,
            generate_group_sort,
        ]

        for _ in range(n):
            gen = random.choice(gens)
            try:
                if gen.__name__ == "generate_cloze":
                    sentence = random.choice([
                        "The sun rises in the ____.",
                        "She plays the ____ beautifully.",
                        "Water freezes at zero ____.",
                    ])
                    missing_word = "east"
                    ex = gen(sentence, missing_word)
                elif gen.__name__ == "generate_group_sort":
                    groups = {"Fruits": ["apple", "banana"], "Animals": ["dog", "cat"]}
                    ex = gen(groups)
                else:
                    ex = gen()

                if not isinstance(ex, dict):
                    ex = ex.to_dict()

                self.play_exercise(ex)

            except Exception as e:
                logger.warning(f"[CEE-Playback] Error running {gen.__name__}: {e}")

        return self.finalize()

    # ------------------------------------------------------------
    def finalize(self):
        """Compute metrics and export session summary."""
        if not self.session:
            logger.warning("[CEE-Playback] No exercises played.")
            return None

        corrects = [e["correct"] for e in self.session]
        perf = round(sum(corrects) / len(corrects), 3)
        avg_SQI = round(
            sum(e["resonance"].get("SQI", 0) for e in self.session) / len(self.session),
            3,
        )

        summary = {
            "timestamp": time.time(),
            "session": self.session_id,
            "mode": self.mode,
            "entries": len(self.session),
            "performance": perf,
            "avg_SQI": avg_SQI,
            "schema": "CEEPlayback.v1",
        }

        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        json.dump(summary, open(OUT_PATH, "w"), indent=2)
        logger.info(f"[CEE-Playback] Exported playback log → {OUT_PATH}")

        update_habit_metrics(avg_SQI)
        print(json.dumps(summary, indent=2))
        return summary


# ================================================================
# 🚀 Entry Point
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mode = input("Enter mode [simulate/interactive]: ").strip().lower()
    if mode not in ["simulate", "interactive"]:
        mode = "simulate"

    player = CEEPlayback(mode=mode)
    player.run(6)