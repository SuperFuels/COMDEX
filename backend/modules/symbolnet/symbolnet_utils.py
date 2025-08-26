import re
from typing import List, Dict


def clean_label(label: str) -> str:
    """
    Normalize a label for better matching across sources.
    Removes parentheses, punctuation, lowercases, trims.
    """
    if not label:
        return ""
    label = re.sub(r"\(.*?\)", "", label)  # remove text in parentheses
    label = re.sub(r"[^a-zA-Z0-9\s]", "", label)  # remove punctuation
    return label.strip().lower()


def score_entity_alignment(entity: Dict, target_label: str) -> float:
    """
    Score the alignment between an entity label and the target query.
    Uses basic overlap heuristics. Later versions can use embeddings.
    """
    if not entity or "label" not in entity:
        return 0.0

    candidate = clean_label(entity["label"])
    target = clean_label(target_label)

    if not candidate or not target:
        return 0.0

    candidate_tokens = set(candidate.split())
    target_tokens = set(target.split())

    if not candidate_tokens or not target_tokens:
        return 0.0

    overlap = candidate_tokens.intersection(target_tokens)
    score = len(overlap) / len(target_tokens)

    return round(score, 3)


def sort_entities_by_score(entities: List[Dict], query: str) -> List[Dict]:
    """
    Sorts a list of entities based on their alignment with the query label.
    """
    for ent in entities:
        ent["alignment_score"] = score_entity_alignment(ent, query)

    return sorted(entities, key=lambda x: x["alignment_score"], reverse=True)