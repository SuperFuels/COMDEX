# ================================================================
# 🎬 CEE Exercise Playback Engine (LexMemory persistence wired)
# ================================================================
"""
Plays back CEE-generated exercises in either:
  * simulate mode -> automatic answers (with LexMemory recall)
  * interactive mode -> user answers via console input

Key guarantee (per your screenshot):
  ✅ On every correct answer, LexMemory is UPDATED AND SAVED to disk
     so Demo 5 can consume: data/memory/lex_memory.json
"""

import json
import time
import random
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Optional OpenAI key validation (only affects LLM feed)
# ------------------------------------------------------------
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    logger.warning(
        "[CEE-Playback] Missing OPENAI_API_KEY. LLM feed may be unavailable."
    )
# ------------------------------------------------------------
# LexMemory auto-correct (opt-in)
# ------------------------------------------------------------
AUTO_CORRECT = os.getenv("CEE_LEX_AUTO_CORRECT", "1").lower() in ("1", "true", "yes", "on")

# ------------------------------------------------------------
# Project imports
# ------------------------------------------------------------
from backend.modules.aion_cognition.cee_lexicore_bridge import LexiCoreBridge
from backend.modules.aion_cognition.language_habit_engine import update_habit_metrics

from backend.modules.aion_cognition.cee_lex_memory import (
    LexMemory,
    recall_from_memory,
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

from backend.modules.aion_cognition.cee_wordwall_importer import wordwall_to_exercise

from backend.modules.aion_cognition.cee_llm_exercise_generator import (
    generate_llm_exercise_batch,
)

from backend.modules.aion_cognition.cee_grammar_templates import (
    grammar_fix_sentence,
    grammar_agreement_mcq,
    grammar_punctuation_insert,
    grammar_word_order,
)

# ------------------------------------------------------------
# Stable output paths
# ------------------------------------------------------------
OUT_PATH = Path("data/sessions/playback_log.qdata.json")
LEX_PATH = Path("data/memory/lex_memory.json")


def _make_lex():
    """Instantiate LexMemory with stable path if supported; fallback if not."""
    try:
        return LexMemory(path=LEX_PATH)
    except TypeError:
        return LexMemory()


# Module singleton (matches screenshot intent)
_lex = _make_lex()


def _norm_resonance(resonance: dict) -> tuple[float, float, float]:
    """
    Normalize resonance keys from any of:
      - screenshot keys: rho, Ibar, sqi
      - your earlier keys: ρ, I, SQI
      - other variants: Ī
    """
    if not isinstance(resonance, dict):
        resonance = {}

    rho = resonance.get("rho", resonance.get("ρ", 0.6))
    Ibar = resonance.get("Ibar", resonance.get("Ī", resonance.get("I", 0.6)))
    sqi = resonance.get("sqi", resonance.get("SQI", 0.6))

    # Coerce to float safely
    try:
        rho = float(rho)
    except Exception:
        rho = 0.6
    try:
        Ibar = float(Ibar)
    except Exception:
        Ibar = 0.6
    try:
        sqi = float(sqi)
    except Exception:
        sqi = 0.6

    return rho, Ibar, sqi


# ================================================================
# 🧩 Playback Engine
# ================================================================
class CEEPlayback:
    def __init__(self, mode: str = "simulate"):
        self.mode = mode
        self.session_id = f"PLAY-{int(time.time())}"
        self.session = []
        self.bridge = LexiCoreBridge()
        logger.info(f"[CEE-Playback] Session {self.session_id} started in {mode} mode")

    def play_exercise(self, ex: dict):
        """Safely play a single CEE exercise with full fallback handling."""
        ex_type = ex.get("type", "unknown")

        # --- Safe prompt normalization ---
        prompt = ex.get("prompt")
        if not isinstance(prompt, str):
            prompt = str(prompt or "").strip()
        safe_prompt = prompt if prompt else "[no prompt provided]"

        options = ex.get("options", [])
        answer = ex.get("answer")

        # --- Safe resonance default (use screenshot-friendly keys) ---
        resonance = ex.get("resonance", {"rho": 0.6, "Ibar": 0.6, "sqi": 0.6})
        if not isinstance(resonance, dict):
            resonance = {"rho": 0.6, "Ibar": 0.6, "sqi": 0.6}

        # --- Display the exercise ---
        print(f"\n▶ {ex_type} - {safe_prompt}")
        if options:
            print(f"Options: {', '.join(str(o) for o in options if o)}")

        # --------------------------------------------------------
        # 🧠 LexMemory Recall Integration
        memory_hit = recall_from_memory(prompt)
        if memory_hit and memory_hit.get("answer"):
            guess = memory_hit["answer"]
            logger.info(f"[CEE-Playback] 🧠 Recall -> {prompt} -> {guess}")

            if guess and answer and str(guess).strip() != str(answer).strip():
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
        guess = (guess or "").strip() if isinstance(guess, str) else str(guess or "").strip()
        answer = (answer or "").strip() if isinstance(answer, str) else str(answer or "").strip()

        # --------------------------------------------------------
        # Evaluate correctness or handle missing answer
        if not answer:
            logger.info(f"[CEE-Playback] ⚠ No answer provided for {ex_type} - skipping scoring.")
            correct = None
        else:
            correct = (guess == answer)
            if correct:
                logger.info(f"[CEE-Playback] ✅ Correct: {guess}")

                # ✅ Screenshot requirement: update + save in the "correct" branch
                rho, Ibar, sqi = _norm_resonance(resonance)
                try:
                    LEX_PATH.parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass

                _lex.update(prompt, answer, rho=rho, Ibar=Ibar, sqi=sqi)
                _lex.save()
                # ✅ Demo 5 hook: when correct recall is confirmed, reinforce AKG edge (never break CEE)
                try:
                    from backend.modules.aion_cognition.akg_singleton import reinforce_answer_is
                    reinforce_answer_is(prompt, answer, hit=1.0)
                except Exception:
                    pass

            else:
                logger.info(f"[CEE-Playback] ❌ Wrong (expected {answer}): {guess}")

                # Optional: auto-correct memory drift only if recall was used (guarded)
                if (not correct) and memory_hit and answer and AUTO_CORRECT:
                    rho, Ibar, sqi = _norm_resonance(resonance)
                    try:
                        LEX_PATH.parent.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass

                    _lex.update(prompt, answer, rho=rho, Ibar=Ibar, sqi=sqi, meta={"auto_correct": True})
                    _lex.save()
                    logger.info(f"[LexMemory] 🔧 Auto-corrected memory for '{prompt}' -> {answer}")

        # --------------------------------------------------------
        # Log attempt safely
        self.session.append(
            {
                "type": ex_type,
                "prompt": safe_prompt,
                "guess": guess,
                "answer": answer,
                "correct": correct,
                "resonance": resonance,
                "timestamp": time.time(),
            }
        )

    def run(self, n: int = 6, feed: str = "hybrid"):
        """
        Run multiple randomized exercises from selected feed.

        feed:
            - "local"    -> run built-in randomized generators
            - "wordwall" -> import from Wordwall URLs
            - "llm"      -> generate batch via LLM
            - "hybrid"   -> combine both Wordwall + LLM
        """
        exercises = []

        # -------------------------------
        # 1) Feed: Wordwall
        # -------------------------------
        if feed == "wordwall":
            urls = [
                "https://wordwall.net/resource/39252",
            ]
            for u in urls:
                ex = wordwall_to_exercise(u)
                if ex:
                    exercises.append(ex)

        # -------------------------------
        # 2) Feed: LLM
        # -------------------------------
        elif feed == "llm":
            try:
                batch = generate_llm_exercise_batch(topic="symbolic cognition", count=n)
                exercises.extend(batch)
            except Exception as e:
                logger.error(f"[CEE-Playback] LLM feed requested but failed: {e}")
                feed = "local"

        # -------------------------------
        # 3) Feed: Hybrid
        # -------------------------------
        elif feed == "hybrid":
            try:
                llm_batch = generate_llm_exercise_batch(topic="linguistics", count=max(1, n // 2))
            except Exception as e:
                logger.warning(f"[CEE-Playback] Hybrid LLM half failed: {e}")
                llm_batch = []

            wordwall_items = [wordwall_to_exercise("https://wordwall.net/resource/39252")]
            exercises = [e for e in wordwall_items if e] + llm_batch

        # -------------------------------
        # 4) Feed: Local Generators
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
                    # Cloze requires a sentence + missing word
                    if gen.__name__ == "generate_cloze":
                        sentence = random.choice(
                            [
                                "The sun rises in the ____.",
                                "She plays the ____ beautifully.",
                                "Water freezes at zero ____.",
                                "He is reading a ____ book.",
                            ]
                        )
                        if "sun rises" in sentence:
                            missing_word = "east"
                        elif "plays the" in sentence:
                            missing_word = "piano"
                        elif "freezes" in sentence:
                            missing_word = "degrees"
                        else:
                            missing_word = "interesting"
                        ex = gen(sentence, missing_word)

                    # Group sort requires groups mapping
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
        # 5) Playback + Finalize
        # -------------------------------
        for ex in exercises:
            try:
                self.play_exercise(ex)
            except Exception as e:
                logger.warning(f"[CEE-Playback] Error playing exercise: {e}")

        return self.finalize()

    def finalize(self):
        """Compute metrics, export session summary, snapshot resonance."""
        if not self.session:
            logger.warning("[CEE-Playback] No exercises played.")
            return None

        valid_corrects = [e["correct"] for e in self.session if isinstance(e["correct"], bool)]
        perf = round(sum(valid_corrects) / len(valid_corrects), 3) if valid_corrects else 0.0

        # Accept either 'sqi' or 'SQI' keys in resonance
        def _get_sqi(e):
            r = e.get("resonance", {}) if isinstance(e.get("resonance", {}), dict) else {}
            return r.get("sqi", r.get("SQI", 0.0))

        avg_SQI = round(sum(float(_get_sqi(e) or 0.0) for e in self.session) / len(self.session), 3)

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
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"[CEE-Playback] Exported playback log -> {OUT_PATH}")

        # Update overall habit metrics (keep your existing key style)
        try:
            update_habit_metrics({"ρ̄": 0.0, "Ī": 0.0, "SQĪ": avg_SQI})
        except Exception as e:
            logger.warning(f"[CEE-Playback] Habit metrics update failed: {e}")

        print(json.dumps(summary, indent=2))

        # Optional resonance snapshot (safe)
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