# ================================================================
# 🧠 CEE Lexical Templates — Phase 45G:g4
# ================================================================
"""
Provides lexical exercise templates for the Cognitive Exercise Engine (CEE).

Templates:
    • MatchUpExercise — match word to synonym or antonym
    • AnagramExercise — reconstruct a scrambled word
    • UnjumbleExercise — reorder phrase fragments

Each generator emits a dict with resonance metadata for GHX↔Habit feedback.
"""

import random, time, logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# Utility --------------------------------------------------------
def _resonance_field(difficulty: float = 0.5) -> Dict[str, float]:
    """Generate synthetic resonance metrics scaled by difficulty [0–1]."""
    return {
        "ρ": round(0.6 + difficulty * 0.4 * random.random(), 3),
        "I": round(0.8 + difficulty * 0.2 * random.random(), 3),
        "SQI": round(0.7 + difficulty * 0.3 * random.random(), 3),
    }

# ----------------------------------------------------------------
class MatchUpExercise:
    """Pair a word with its synonym or antonym."""

    @staticmethod
    def generate(word: str, candidates: List[str], synonym: bool = True) -> Dict:
        """Generate a matchup question."""
        correct = candidates[0]
        distractors = random.sample(candidates[1:], min(3, len(candidates) - 1))
        options = [correct] + distractors
        random.shuffle(options)

        data = {
            "type": "matchup",
            "mode": "synonym" if synonym else "antonym",
            "prompt": word,
            "options": options,
            "answer": correct,
            "resonance": _resonance_field(0.6),
            "timestamp": time.time(),
        }
        logger.info(f"[MatchUpExercise] Generated {data['mode']} for '{word}'")
        return data

# ----------------------------------------------------------------
class AnagramExercise:
    """Scramble and reconstruct a word."""

    @staticmethod
    def generate(word: str) -> Dict:
        chars = list(word)
        random.shuffle(chars)
        scrambled = "".join(chars)

        data = {
            "type": "anagram",
            "prompt": scrambled,
            "answer": word,
            "resonance": _resonance_field(0.5),
            "timestamp": time.time(),
        }
        logger.info(f"[AnagramExercise] Generated anagram for '{word}' → '{scrambled}'")
        return data

# ----------------------------------------------------------------
class UnjumbleExercise:
    """Reorder a phrase or sequence."""

    @staticmethod
    def generate(phrase: str) -> Dict:
        words = phrase.split()
        scrambled = words.copy()
        random.shuffle(scrambled)

        data = {
            "type": "unjumble",
            "prompt": " ".join(scrambled),
            "answer": phrase,
            "resonance": _resonance_field(0.7),
            "timestamp": time.time(),
        }
        logger.info(f"[UnjumbleExercise] Generated unjumble for phrase '{phrase}'")
        return data

# ----------------------------------------------------------------
def generate_sample_batch() -> List[Dict]:
    """Produce a small batch of demo exercises."""
    return [
        MatchUpExercise.generate("happy", ["joyful", "sad", "angry", "content"]),
        AnagramExercise.generate("planet"),
        UnjumbleExercise.generate("quantum wave resonance"),
    ]

if __name__ == "__main__":
    batch = generate_sample_batch()
    for ex in batch:
        print(ex)