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
from backend.modules.aion_cognition.cee_resonance_analytics import snapshot_memory
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
from backend.modules.aion_cognition.cee_language_cloze import generate_cloze, generate_group_sort
from backend.modules.aion_cognition.cee_wordwall_importer import wordwall_to_exercise
from backend.modules.aion_cognition.cee_llm_exercise_generator import generate_llm_exercise_batch

from backend.modules.aion_cognition.cee_grammar_templates import (
    grammar_fix_sentence,
    grammar_agreement_mcq,
    grammar_punctuation_insert,
    grammar_word_order,
)

import os
from openai import OpenAIError

# --- OpenAI API key validation ---
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    logger.error(
        "[CEE-Playback] Missing OPENAI_API_KEY environment variable. "
        "LLM feed will be unavailable."
    )
    # You may choose to disable LLM feed or fallback to local generators
    _llm_client = None
else:
    from backend.modules.aion_cognition.cee_llm_exercise_generator import client as _llm_client

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
    # ------------------------------------------------------------
    def play_exercise(self, ex):
        """Safely play a single CEE exercise with full fallback handling."""
        ex_type = ex.get("type", "unknown")

        # --- Safe prompt normalization ---
        prompt = ex.get("prompt")
        if not isinstance(prompt, str):
            prompt = str(prompt or "").strip()
        safe_prompt = prompt if prompt else "[no prompt provided]"

        options = ex.get("options", [])
        answer = ex.get("answer")
        resonance = ex.get("resonance", {"ρ": 0, "I": 0, "SQI": 0})

        # --- Display the exercise ---
        print(f"\n▶ {ex_type} — {safe_prompt}")
        if options:
            print(f"Options: {', '.join(str(o) for o in options if o)}")

        # --------------------------------------------------------
        # 🧠 LexMemory Recall Integration
        memory_hit = recall_from_memory(prompt)
        if memory_hit and memory_hit.get("answer"):
            guess = memory_hit["answer"]
            logger.info(f"[CEE-Playback] 🧠 Recall → {prompt} → {guess}")

            # ⚠ Recall mismatch diagnostic
            if guess and answer and guess != answer:
                logger.warning(
                    f"[LexMemory] ⚠ Recall mismatch for '{prompt}': "
                    f"recalled '{guess}', expected '{answer}'"
                )
        else:
            # Input phase: interactive or simulate
            if self.mode == "interactive":
                try:
                    guess = input("Your answer: ").strip()
                except Exception:
                    guess = ""
            else:
                guess = random.choice(options) if options else ""

        # --------------------------------------------------------
        # Safe normalize both guess and answer
        guess = (guess or "").strip() if isinstance(guess, str) else str(guess or "")
        answer = (answer or "").strip() if isinstance(answer, str) else str(answer or "")

        # --------------------------------------------------------
        # Evaluate correctness or handle missing answer
        if not answer:
            logger.info(f"[CEE-Playback] ⚠ No answer provided for {ex_type} — skipping scoring.")
            correct = None
        else:
            correct = (guess == answer)
            if correct:
                logger.info(f"[CEE-Playback] ✅ Correct: {guess}")
                update_lex_memory(prompt, answer, resonance)
            else:
                logger.info(f"[CEE-Playback] ❌ Wrong (expected {answer}): {guess}")

                # 🧩 Auto-correct memory drift when recall was wrong
                if memory_hit and answer:
                    update_lex_memory(prompt, answer, resonance)
                    logger.info(f"[LexMemory] 🔧 Auto-corrected memory for '{prompt}' → {answer}")

        # --------------------------------------------------------
        # Log attempt safely
        self.session.append({
            "type": ex_type,
            "prompt": safe_prompt,
            "guess": guess,
            "answer": answer,
            "correct": correct,
            "resonance": resonance,
            "timestamp": time.time(),
        })

    # ------------------------------------------------------------
    from backend.modules.aion_cognition.cee_wordwall_importer import wordwall_to_exercise
    from backend.modules.aion_cognition.cee_llm_exercise_generator import generate_llm_exercise_batch

    def run(self, n=6, feed="hybrid"):
        """
        Run multiple randomized exercises from selected feed.

        feed:
            - "local"   → run built-in randomized generators
            - "wordwall" → import from Wordwall URLs
            - "llm"      → generate batch via LLM
            - "hybrid"   → combine both Wordwall + LLM
        """
        exercises = []

        # -------------------------------
        # 1. Feed: Wordwall
        # -------------------------------
        if feed == "wordwall":
            urls = [
                "https://wordwall.net/resource/39252",
                # Add more Wordwall resource links here
            ]
            for u in urls:
                ex = wordwall_to_exercise(u)
                if ex:
                    exercises.append(ex)

        # -------------------------------
        # 2. Feed: LLM
        # -------------------------------
        elif feed == "llm":
            try:
                batch = generate_llm_exercise_batch(topic="symbolic cognition", count=n)
                exercises.extend(batch)
            except NameError as e:
                logger.error(f"[CEE-Playback] LLM feed requested but function not available: {e}")
                # fallback to local generators
                feed = "local"

        # -------------------------------
        # 3. Feed: Hybrid (mix both)
        # -------------------------------
        elif feed == "hybrid":
            llm_batch = generate_llm_exercise_batch(topic="linguistics", count=n // 2)
            wordwall_items = [wordwall_to_exercise("https://wordwall.net/resource/39252")]
            exercises = [e for e in wordwall_items if e] + llm_batch

        # -------------------------------
        # 4. Feed: Local Generators
        # -------------------------------
        else:
            gens = [
                generate_matchup,
                generate_anagram,
                generate_unjumble,
                generate_flashcard,
                generate_find_match,
                generate_spin_wheel,
                generate_cloze,
                generate_group_sort,
                grammar_fix_sentence,
                grammar_agreement_mcq,
                grammar_punctuation_insert,
                grammar_word_order,
            ]

            for _ in range(n):
                gen = random.choice(gens)
                try:
                    # --- Handle Cloze contextual mapping ---
                    if gen.__name__ == "generate_cloze":
                        sentence = random.choice([
                            "The sun rises in the ____.",
                            "She plays the ____ beautifully.",
                            "Water freezes at zero ____.",
                            "He is reading a ____ book."
                        ])
                        # Map sentence → required missing word
                        if "sun rises" in sentence:
                            missing_word = "east"
                        elif "plays the" in sentence:
                            missing_word = "piano"
                        elif "freezes" in sentence:
                            missing_word = "degrees"
                        else:
                            missing_word = "interesting"
                        ex = gen(sentence, missing_word)

                    # --- Handle Group Sort ---
                    elif gen.__name__ == "generate_group_sort":
                        groups = {"Fruits": ["apple", "banana"], "Animals": ["dog", "cat"]}
                        ex = gen(groups)

                    else:
                        ex = gen()

                    if not isinstance(ex, dict):
                        ex = ex.to_dict()

                    exercises.append(ex)

                except Exception as e:
                    logger.warning(f"[CEE-Playback] Error running {gen.__name__}: {e}")

        # -------------------------------
        # 5. Playback + Finalize
        # -------------------------------
        for ex in exercises:
            try:
                self.play_exercise(ex)
            except Exception as e:
                logger.warning(f"[CEE-Playback] Error playing exercise: {e}")

        return self.finalize()

    # ------------------------------------------------------------
    # ------------------------------------------------------------
    def finalize(self):
        """Compute metrics and export session summary safely."""
        if not self.session:
            logger.warning("[CEE-Playback] No exercises played.")
            return None

        # Only include exercises with valid correctness values
        valid_corrects = [e["correct"] for e in self.session if isinstance(e["correct"], bool)]

        if valid_corrects:
            perf = round(sum(valid_corrects) / len(valid_corrects), 3)
        else:
            perf = 0.0  # fallback when all items had no answer

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

        # Pass proper dict to habit engine
        update_habit_metrics({"ρ̄": 0.0, "Ī": 0.0, "SQĪ": avg_SQI})
        print(json.dumps(summary, indent=2))
        # --------------------------------------------------------
        # 🧭 Resonance Analytics Snapshot
        try:
            from backend.modules.aion_cognition.cee_resonance_analytics import snapshot_memory
            snapshot_memory(tag=self.session_id)
            logger.info(f"[CEE-Playback] Logged resonance snapshot for {self.session_id}")
        except Exception as e:
            logger.warning(f"[CEE-Playback] Could not snapshot resonance analytics: {e}")
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