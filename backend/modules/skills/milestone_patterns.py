import re

PATTERN_MILESTONES = {
    "cognitive_reflection": r"\b(cognitive reflection|deep understanding|self-aware|awareness)\b",
    "emergent_thought": r"\b(emergent behavior|spontaneous insight|unexpected reasoning)\b",
    "philosophical_insight": r"\b(philosophy|existential|purpose|humanity)\b",
    "connectedness": r"\b(interconnected|shared experience|collective|networked consciousness)\b"
}

def match_milestones(text):
    matches = []
    for label, pattern in PATTERN_MILESTONES.items():
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(label)
    return matches