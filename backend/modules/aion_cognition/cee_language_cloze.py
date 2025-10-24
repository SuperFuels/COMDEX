# ================================================================
# ✍️ CEE Language Path — Cloze + Group Sort Generators
# ================================================================
"""
Adds advanced language exercises for the Cognitive Exercise Engine (CEE).

Implements:
  • Cloze (fill-in-the-blank) questions using LexiCoreBridge
  • Group-Sort classification tasks (semantic grouping)

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
def generate_cloze(sentence: str, missing_word: str):
    """
    Create a Cloze-type exercise:
      Input: "The sky is ____", "blue"
      Output: dict with prompt, options, answer, resonance
    """
    bridge = LexiCoreBridge()
    distractors = bridge.get_antonyms(missing_word) + bridge.get_related(missing_word)
    options = [missing_word] + random.sample(
        distractors or ["red", "green", "dark", "bright"],
        k=min(3, len(distractors) or 3),
    )
    random.shuffle(options)

    packet = {
        "type": "cloze",
        "prompt": sentence.replace(missing_word, "_____"),
        "options": options,
        "answer": missing_word,
        "resonance": _resonance(),
        "timestamp": time.time(),
    }
    logger.info(f"[CEE-Cloze] Generated prompt for '{missing_word}' → {options}")
    return packet


# ------------------------------------------------------------
def generate_group_sort(groups: dict):
    """
    Create a Group-Sort exercise:
      Input: {"Fruits": ["apple","pear"], "Animals":["cat","dog"]}
    """
    items = []
    for g, words in groups.items():
        for w in words:
            items.append({"word": w, "group": g})

    random.shuffle(items)
    packet = {
        "type": "group_sort",
        "groups": list(groups.keys()),
        "items": [i["word"] for i in items],
        "mapping": {i["word"]: i["group"] for i in items},
        "resonance": _resonance(),
        "timestamp": time.time(),
    }
    logger.info(f"[CEE-GroupSort] Generated {len(items)} items across {len(groups)} groups.")
    return packet


# ------------------------------------------------------------
# CLI smoke-test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Cloze example
    c = generate_cloze("The sky is blue", "blue")
    print(c)

    # Group-Sort example
    g = generate_group_sort({
        "Fruits": ["apple", "pear", "banana"],
        "Animals": ["dog", "cat", "bird"]
    })
    print(g)