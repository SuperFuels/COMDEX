# ================================================================
# ✍️ CEE Language Path - Cloze + Group Sort Generators
# ================================================================
"""
Adds advanced language exercises for the Cognitive Exercise Engine (CEE).

Implements:
  * Cloze (fill-in-the-blank) questions using LexiCoreBridge
  * Group-Sort classification tasks (semantic grouping)

Each exercise includes resonance metadata (ρ, I, SQI) compatible with
GHX↔Habit↔CodexMetrics feedback pipelines.
"""

import time, random, logging
from backend.modules.aion_cognition.cee_lexicore_bridge import LexiCoreBridge

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
def _resonance():
    """Generate synthetic resonance parameters for testing."""
    ρ = round(random.uniform(0.6, 0.9), 3)
    I = round(random.uniform(0.8, 1.0), 3)
    SQI = round((ρ + I) / 2, 3)
    return {"ρ": ρ, "I": I, "SQI": SQI}


# ------------------------------------------------------------
def generate_cloze(sentence: str, missing_word: str, bridge: LexiCoreBridge | None = None):
    """
    Generate a cloze (fill-in-the-blank) exercise.
    Always includes `missing_word` in options.
    If LexiCore/ThesauriNet are unavailable, falls back to default distractors.
    """
    bridge = bridge or LexiCoreBridge()

    try:
        syns = bridge.get_synonyms(missing_word)
        ants = bridge.get_antonyms(missing_word)
        rels = bridge.get_related(missing_word)
    except Exception:
        syns, ants, rels = [], [], []

    fallback = ["dark", "bright", "fast", "slow", "east", "west", "violin", "drum", "guitar", "degrees"]
    pool = list({*syns, *ants, *rels, *fallback})
    pool = [w for w in pool if w.lower() != missing_word.lower()]

    distractors = random.sample(pool, k=min(3, len(pool))) if pool else []
    options = [missing_word] + distractors
    random.shuffle(options)

    return {
        "type": "cloze",
        "prompt": sentence.replace(missing_word, "_____"),
        "options": options,
        "answer": missing_word,
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


# ------------------------------------------------------------
def generate_group_sort(groups: dict[str, list[str]]):
    """
    Generate a Group-Sort exercise:
      Input: {"Fruits": ["apple", "pear"], "Animals": ["dog", "cat"]}
      Output: exercise with randomized items and labeled groups.
    """
    items = [(word, group) for group, words in groups.items() for word in words]
    random.shuffle(items)

    return {
        "type": "group_sort",
        "prompt": "Sort the words into their correct categories.",
        "groups": list(groups.keys()),
        "items": [w for w, _ in items],
        "answer": {g: v for g, v in groups.items()},
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


# ------------------------------------------------------------
# CLI smoke-test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Cloze example
    c = generate_cloze("The sun rises in the east", "east")
    print(c)

    # Group-Sort example
    g = generate_group_sort({
        "Fruits": ["apple", "pear", "banana"],
        "Animals": ["dog", "cat", "bird"]
    })
    print(g)