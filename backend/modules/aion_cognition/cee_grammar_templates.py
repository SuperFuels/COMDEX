# ================================================================
# 🧠 CEE Grammar Templates - Exercise Generators
# ================================================================
import time, random

from backend.modules.aion_cognition.cee_grammar_rules import (
    is_agreement_correct,
    fix_article,
    needs_article,
    has_comma_splice,
    insert_basic_punctuation,
)

def _res():
    ρ = round(random.uniform(0.65, 0.9), 3)
    I = round(random.uniform(0.8, 1.0), 3)
    return {"ρ": ρ, "I": I, "SQI": round((ρ + I) / 2, 3)}

# ---------------------------------------------------------------
def grammar_fix_sentence():
    """
    Error correction: show a flawed sentence, ask for the correct form.
    """
    pairs = [
        ("She walk to school every day", "She walks to school every day."),
        ("They is playing in park", "They are playing in the park."),
        ("It an honor to meet you", "It is an honor to meet you."),
        ("We went home, we slept", "We went home, and we slept."),
    ]
    wrong, correct = random.choice(pairs)
    options = [correct,
               insert_basic_punctuation(wrong),
               correct.replace(".", ""),
               correct.replace("the ", "", 1)]
    random.shuffle(options)
    return {
        "type": "grammar_fix",
        "prompt": f"Fix the sentence: {wrong}",
        "options": options,
        "answer": correct,
        "resonance": _res(),
        "timestamp": time.time(),
    }

# ---------------------------------------------------------------
def grammar_agreement_mcq():
    """
    Subject-verb agreement multiple choice.
    """
    items = [
        ("He", ["runs", "run"]),
        ("They", ["plays", "play"]),
        ("She", ["do", "does"]),
        ("We", ["has", "have"]),
    ]
    subj, verbs = random.choice(items)
    # pick the correct one using rule
    correct = [v for v in verbs if is_agreement_correct(subj, v)][0]
    options = verbs[:]
    random.shuffle(options)
    return {
        "type": "grammar_agreement",
        "prompt": f"Choose the correct verb: {subj} ____",
        "options": options,
        "answer": correct,
        "resonance": _res(),
        "timestamp": time.time(),
    }

# ---------------------------------------------------------------
def grammar_punctuation_insert():
    """
    Choose the correctly punctuated sentence.
    """
    base = "When the rain stopped we went outside"
    correct = "When the rain stopped, we went outside."
    distractors = [
        base + ",",
        base,
        "When the rain stopped we went outside?",
    ]
    options = [correct] + distractors
    random.shuffle(options)
    return {
        "type": "grammar_punctuation",
        "prompt": "Select the correctly punctuated sentence:",
        "options": options,
        "answer": correct,
        "resonance": _res(),
        "timestamp": time.time(),
    }

# ---------------------------------------------------------------
def grammar_word_order():
    """
    Grammar 'unjumble': reorder words into a correct sentence.
    """
    target = "The quick brown fox jumps over the lazy dog."
    words = target[:-1].split()
    scrambled = words[:]
    random.shuffle(scrambled)
    prompt = "Reorder to form a correct sentence: " + " | ".join(scrambled)
    options = [
        target,
        insert_basic_punctuation(" ".join(scrambled)),
        "Quick the brown fox jumps over lazy the dog.",
        "The brown quick fox jump over the lazy dog.",
    ]
    random.shuffle(options)
    return {
        "type": "grammar_order",
        "prompt": prompt,
        "options": options,
        "answer": target,
        "resonance": _res(),
        "timestamp": time.time(),
    }