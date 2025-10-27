"""
AION Cognitive Bridge — Extended Commands
────────────────────────────────────────────
Provides live cognitive reasoning and lexical utilities for AION.
"""

import random, difflib, logging
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

log = logging.getLogger(__name__)

# Safe imports
try:
    import backend.modules.aion_cognition.cee_lex_memory as cee_lex
    LEX = cee_lex.LexMemory() if hasattr(cee_lex, "LexMemory") else None
except Exception as e:
    LEX = None
    log.warning(f"[Bridge] ⚠ LexMemory unavailable: {e}")

try:
    from backend.modules.aion_cognition.semantic_benchmark import benchmark_runner
except Exception:
    benchmark_runner = None
    log.warning("[Bridge] ⚠ semantic_benchmark unavailable.")

try:
    from backend.modules.aion_cognition.advanced_cognition import lexical_task_runner
except Exception:
    lexical_task_runner = None
    log.warning("[Bridge] ⚠ advanced_cognition unavailable.")

RMC = ResonantMemoryCache()

# --- LCE-style interactive helpers ---

def anagram_word(word: str):
    """Return a shuffled form of the word and (optionally) solve it back."""
    if not word or not isinstance(word, str):
        return "⚠️ Provide a single word."
    # if you want a solve: try finding the closest lemma in cache by sorted letters
    target_sorted = "".join(sorted(word.lower()))
    candidates = [w for w in getattr(RMC, "cache", {}).keys() if isinstance(w, str)]
    solved = next((w for w in candidates if "".join(sorted(w.lower())) == target_sorted), None)
    # always return an anagram string (shuffled)
    import random
    chars = list(word)
    random.shuffle(chars)
    jumbled = "".join(chars)
    if solved and solved != word:
        return f"🧩 Anagram of '{word}' → '{jumbled}'  (solve: {solved})"
    return f"🧩 Anagram of '{word}' → '{jumbled}'"

def complete_word(word: str):
    """Produce a simple definitional completion cue from LexMemory / RMC."""
    from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory
    lex = recall_from_memory(word) or {}
    definition = lex.get("answer") or lex.get("definition")
    if not definition:
        # try RMC
        entry = RMC.lookup(word) or {}
        definition = entry.get("definition")
    if not definition:
        return f"🤷 No stored definition for '{word}'. Try teaching first: teach {word} 2"
    first = definition.split(".", 1)[0].strip()
    return f"✍️ Completion: {word.capitalize()} is… {first}"

def match_word(word: str):
    """Emit a simple definition-match style prompt from memory."""
    from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory
    lex = recall_from_memory(word) or {}
    definition = lex.get("answer") or lex.get("definition")
    if not definition:
        entry = RMC.lookup(word) or {}
        definition = entry.get("definition")
    if not definition:
        return f"🤷 No definition for '{word}'."
    # Build distractors from other cached lemmas
    pool = [k for k in getattr(RMC, "cache", {}).keys() if isinstance(k, str) and k.lower() != word.lower()]
    import random
    distractors = random.sample(pool, min(3, len(pool))) if pool else ["electron", "wave", "field"]
    choices = distractors + [word]
    random.shuffle(choices)
    pretty = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(choices))
    return f"🧠 Match the definition:\n“{definition}”\nChoices:\n{pretty}\n(answer: {word})"
# ──────────────────────────────────────────────
# Lexical + Symbolic
# ──────────────────────────────────────────────
def define_word(word: str):
    """Return a concept’s recalled definition + resonance info (guaranteed fallback)."""
    from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory, _load_memory

    # 1️⃣ Try lexical fuzzy recall
    lex_entry = recall_from_memory(word)
    definition = None
    if lex_entry:
        definition = lex_entry.get("answer") or lex_entry.get("definition")

    # 2️⃣ Try direct key scan if fuzzy recall fails
    if not definition:
        mem = _load_memory()
        for key in mem.keys():
            if key.startswith(f"{word}↔"):
                definition = key.split("↔", 1)[1].strip()
                break

    # 3️⃣ Fallback to ResonantMemoryCache if still undefined
    if not definition:
        if hasattr(RMC, "cache") and word in RMC.cache:
            entry = RMC.cache[word]
            definition = entry.get("definition", f"(learned resonance concept '{word}')")
            resonance = entry.get("resonance", 0.0)
            stability = entry.get("stability", 0.0)
            symbol = entry.get("symbol", "∅")
            return (
                f"📘 {word}: {definition}\n"
                f"💡 Symbolic: {symbol}\n"
                f"🔮 Resonance={resonance:.3f}, Stability={stability:.3f}"
            )
        return f"❌ No definition found for '{word}'."

    # 4️⃣ Merge with RMC resonance metadata if available
    entry = getattr(RMC, "cache", {}).get(word, {})
    resonance = entry.get("resonance", 0.0)
    stability = entry.get("stability", 0.0)
    symbol = entry.get("symbol", "∅")

    # 5️⃣ Final display
    return (
        f"📘 {word}: {definition}\n"
        f"💡 Symbolic: {symbol}\n"
        f"🔮 Resonance={resonance:.3f}, Stability={stability:.3f}"
    )


def symbol_word(word: str):
    """Return symbolic photon/QMath representation for a word."""
    entry = None

    if hasattr(RMC, "cache") and word in getattr(RMC, "cache", {}):
        entry = RMC.cache[word]
    elif hasattr(RMC, "recall"):
        try:
            entry = RMC.recall(word)
        except Exception:
            entry = None

    if not entry:
        return f"⚠️ No symbolic tensor for '{word}'."

    symbol = entry.get("symbol", None)
    if not symbol:
        return f"💡 {word}: (symbolic tensor undefined)"
    return f"💡 Symbolic QMath({word}) → {symbol}"


# ──────────────────────────────────────────────
# Wordplay + Semantic reasoning
# ──────────────────────────────────────────────
def unjumble_word(letters: str):
    """Attempt to unscramble letters to nearest known lemma."""
    candidates = []
    if LEX and hasattr(LEX, "cache"):
        candidates = list(LEX.cache.keys())
    elif hasattr(RMC, "cache"):
        candidates = list(RMC.cache.keys())

    match = difflib.get_close_matches(letters, candidates, n=1, cutoff=0.5)
    if match:
        return f"🧩 Unjumble → '{letters}' = '{match[0]}'"
    return f"❌ No matching lemma for '{letters}'"


def compare_words(w1: str, w2: str):
    """Compare two words semantically (Meaning Consistency Index)."""
    if not benchmark_runner or not hasattr(benchmark_runner, "compare_pair"):
        return "⚠️ Semantic benchmark unavailable."
    result = benchmark_runner.compare_pair(w1, w2)
    if not result:
        return f"⚠️ Unable to compare '{w1}' and '{w2}'."
    mci = round(result.get("MCI", 0.0), 3)
    sim = round(result.get("similarity", 0.0), 3)
    return f"🔍 Compare '{w1}' ↔ '{w2}' → MCI={mci}, sim={sim}"


def context_word(word: str, phrase: str):
    """Evaluate a word’s meaning stability within a phrase."""
    if not benchmark_runner or not hasattr(benchmark_runner, "context_eval"):
        return "⚠️ Contextual benchmark unavailable."
    result = benchmark_runner.context_eval(word, phrase)
    if not result:
        return f"⚠️ No contextual data for '{word}' in '{phrase}'."
    mci = round(result.get("MCI", 0.0), 3)
    drift = round(result.get("drift", 0.0), 3)
    return f"🧠 Context('{word}' in '{phrase}') → MCI={mci}, drift={drift}"


def connect_concepts(chain: str):
    """Link related concepts in the resonance graph."""
    nodes = [x.strip() for x in chain.replace("→", "->").split("->") if x.strip()]
    if len(nodes) < 2:
        return "⚠️ Need at least two concepts to connect."
    for i in range(len(nodes) - 1):
        try:
            RMC.link(nodes[i], nodes[i + 1])
        except Exception:
            pass
    return f"🔗 Connected: {' → '.join(nodes)}"


def stats_summary():
    """Return compact cognitive metrics snapshot."""
    try:
        s = RMC.get_summary()
    except Exception:
        s = {"avg_SQI": 0, "avg_stability": 0, "avg_MCI": 0}
    return (
        f"📊 SQI={round(s.get('avg_SQI', 0), 3)}, "
        f"Stability={round(s.get('avg_stability', 0), 3)}, "
        f"MCI={round(s.get('avg_MCI', 0), 3)}"
    )