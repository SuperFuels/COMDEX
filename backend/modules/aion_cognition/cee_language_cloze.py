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
# ================================================================
# 🧩 Group Sort Generator — Lexical Cognitive Exercise
# ================================================================
def generate_group_sort(groups=None):
    """Generate semantic grouping exercise."""
    import random, time

    # Support both dict- and list-style group input
    if groups is None:
        groups = ["Fruits", "Animals"]

    if isinstance(groups, list):
        # Build default word sets for these groups
        group_data = {
            "Fruits": ["apple", "banana", "pear", "grape"],
            "Animals": ["dog", "cat", "bird", "lion"],
        }
    elif isinstance(groups, dict):
        group_data = groups
    else:
        raise TypeError("groups must be list or dict")

    # Flatten items
    items = [(word, group) for group, words in group_data.items() for word in words]
    random.shuffle(items)
    mapping = {word: group for word, group in items}
    all_items = [word for word, _ in items]

    ρ = round(random.uniform(0.6, 0.9), 3)
    I = round(random.uniform(0.7, 0.95), 3)
    SQI = round((ρ + I) / 2, 3)

    return {
        "type": "group_sort",
        "groups": list(group_data.keys()),
        "items": all_items,
        "mapping": mapping,
        "resonance": {"ρ": ρ, "I": I, "SQI": SQI},
        "timestamp": time.time(),
    }


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