# ================================================================
# ✅ CEE Grammar Rules - Minimal Rule Checks for CEE
# ================================================================
import re

def is_agreement_correct(subject: str, verb: str) -> bool:
    """
    Very simple subject-verb agreement:
      - singular 3rd person: he/she/it + verb+s
      - plural/others: I/you/we/they + base form
    """
    s = subject.strip().lower()
    v = verb.strip().lower()
    singular = {"he", "she", "it", "this", "that"}
    plural   = {"i", "you", "we", "they", "these", "those"}

    # naive s-form check
    def is_s_form(token): return token.endswith("s") and token not in {"is", "was", "has", "does"}

    if s in singular:
        # singular should take s-form (or irregular: is/has/does)
        return is_s_form(v) or v in {"is", "has", "does"}
    if s in plural:
        # plural should NOT take s-form (or irregular are/have/do)
        return (not is_s_form(v)) or v in {"are", "have", "do"}
    # default neutral: accept both
    return True

def needs_article(noun_phrase: str) -> bool:
    """Heuristic: singular count noun likely needs an article."""
    np = noun_phrase.strip().lower()
    if np.startswith(("a ", "an ", "the ")): return False
    # crude guess: a single bare noun
    return len(np.split()) == 1

def fix_article(noun_phrase: str) -> str:
    """Choose 'a' vs 'an' before a noun phrase based on first vowel sound."""
    w = noun_phrase.strip()
    if not w: return w
    first = w[0].lower()
    art = "an" if first in "aeiou" else "a"
    return f"{art} {w}"

def has_comma_splice(sentence: str) -> bool:
    """
    Detects a basic comma splice pattern: <clause>, <clause> without coordinator.
    Naive: two independent-like chunks separated by a comma.
    """
    return bool(re.search(r"[a-zA-Z0-9]\s*,\s*[A-Z]", sentence))

def insert_basic_punctuation(sentence: str) -> str:
    """Ensure sentence ends with a period if absent; simple fix."""
    s = sentence.strip()
    if not s: return s
    if s[-1] in ".!?": return s
    return s + "."