# ================================================================
# 🧠 CEE Language Templates - Phase 45G.9 Step 2
# ================================================================
"""
Provides template generators for lexical and symbolic cognitive exercises.
Expanded in this phase to include advanced semantic and creative modes.

Existing types:
  - Match Up     (word ↔ definition)
  - Anagram      (unscramble)
  - Unjumble     (reorder)
  - Cloze        (sentence completion)
  - Group Sort   (semantic clustering)

New additions:
  - Flash Card   (quick recall)
  - Find Match   (synonym/antonym resonance)
  - Spin Wheel   (random context challenge)

Each generator outputs a dict compatible with the CEE runtime schema:
{
  "type": "...",
  "prompt": "...",
  "options": [...],
  "answer": "...",
  "resonance": {"ρ": ..., "I": ..., "SQI": ...},
  "timestamp": ...
}
"""

import time, random, logging
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
def _resonance():
    ρ = round(random.uniform(0.6, 0.9), 3)
    I = round(random.uniform(0.8, 1.0), 3)
    SQI = round((ρ + I) / 2, 3)
    return {"ρ": ρ, "I": I, "SQI": SQI}


# ================================================================
# 🧩 Core Exercise Types (existing)
# ================================================================

def generate_matchup():
    """Match a word to its correct definition."""
    word = random.choice(["happy", "bright", "wave", "resonance"])
    definitions = {
        "happy": "feeling or showing pleasure",
        "bright": "giving out or reflecting much light",
        "wave": "oscillation transferring energy through space",
        "resonance": "amplification of oscillation at natural frequency",
    }
    distractors = random.sample(
        [d for w, d in definitions.items() if w != word], 3
    )
    options = [definitions[word]] + distractors
    random.shuffle(options)
    return {
        "type": "matchup",
        "prompt": word,
        "options": options,
        "answer": definitions[word],
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


def generate_anagram():
    """Unscramble a shuffled word."""
    word = random.choice(["planet", "quantum", "light", "field", "resonance"])
    shuffled = "".join(random.sample(word, len(word)))
    return {
        "type": "anagram",
        "prompt": shuffled,
        "options": [],
        "answer": word,
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


def generate_unjumble(word=None):
    """Unscramble a given or random word."""
    import random, time

    if not word:
        word = random.choice(["resonance", "quantum", "wave", "field", "light"])

    scrambled = "".join(random.sample(word, len(word)))

    return {
        "type": "unjumble",
        "prompt": f"Unscramble the word: {scrambled}",
        "options": [scrambled, word],
        "answer": word,
        "resonance": {
            "ρ": round(random.uniform(0.6, 0.9), 3),
            "I": round(random.uniform(0.8, 1.0), 3),
            "SQI": round(random.uniform(0.7, 0.95), 3),
        },
        "timestamp": time.time(),
    }


# ================================================================
# 🧠 New Phase 45G.9 Exercise Types
# ================================================================

def generate_flashcard():
    """Quick recall of concept ↔ definition (reinforcement)."""
    cards = {
        "Photon": "quantum of electromagnetic energy",
        "Entropy": "measure of disorder or randomness",
        "Amplitude": "maximum displacement in oscillation",
        "Frequency": "number of oscillations per second",
    }
    term = random.choice(list(cards.keys()))
    correct = cards[term]
    distractors = random.sample(
        [v for k, v in cards.items() if k != term], 3
    )
    options = [correct] + distractors
    random.shuffle(options)
    return {
        "type": "flashcard",
        "prompt": f"What is the definition of '{term}'?",
        "options": options,
        "answer": correct,
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


def generate_find_match():
    """Synonym/antonym resonance challenge."""
    pairs = {
        "happy": ("joyful", "sad"),
        "bright": ("luminous", "dim"),
        "fast": ("quick", "slow"),
        "calm": ("peaceful", "angry"),
    }
    word = random.choice(list(pairs.keys()))
    synonym, antonym = pairs[word]
    mode = random.choice(["synonym", "antonym"])
    correct = synonym if mode == "synonym" else antonym
    options = random.sample([synonym, antonym, "neutral", "random"], 4)
    return {
        "type": "find_match",
        "prompt": f"Select the {mode} of '{word}'",
        "options": options,
        "answer": correct,
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


def generate_spin_wheel():
    """Adaptive linguistic creativity challenge."""
    contexts = [
        ("river", "Describe a wave using this context."),
        ("music", "Relate resonance to this domain."),
        ("emotion", "Express 'energy' in this context."),
        ("light", "Imagine what color represents this feeling."),
    ]
    topic, instruction = random.choice(contexts)
    hint = random.choice(["flow", "vibration", "intensity", "tone"])
    return {
        "type": "spin_wheel",
        "prompt": f"{instruction}",
        "options": [topic, hint, "skip"],
        "answer": topic,  # open-ended symbolic response
        "resonance": _resonance(),
        "timestamp": time.time(),
    }


# ================================================================
# 🚀 Test Harness
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gens = [
        generate_matchup,
        generate_anagram,
        generate_unjumble,
        generate_flashcard,
        generate_find_match,
        generate_spin_wheel,
    ]
    for gen in gens:
        ex = gen()
        print(f"\n▶ {ex['type'].upper()} :: {ex['prompt']}")
        print(json.dumps(ex, indent=2))