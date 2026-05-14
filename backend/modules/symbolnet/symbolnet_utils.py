import os
import re
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer, util

# ========================
# 🔧 Label Cleaning + Heuristics
# ========================

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


# ========================
# 🧠 SymbolNet Semantic Scoring
# ========================

_model = None

def get_embedding_model():
    """
    Load SentenceTransformer model once.
    Uses: ./models/all-MiniLM-L6-v2
    Override path with SYMBOLNET_MODEL_PATH env variable.
    """
    global _model
    if _model is None:
        model_path = os.environ.get("SYMBOLNET_MODEL_PATH", "./models/all-MiniLM-L6-v2")
        _model = SentenceTransformer(model_path)
    return _model


def get_embedding(text: str) -> np.ndarray:
    """
    Converts label to dense embedding vector.
    """
    model = get_embedding_model()
    return model.encode(text, convert_to_numpy=True)


def concept_match(label_a: str, label_b: str) -> float:
    """
    Returns cosine similarity between the embeddings of two labels.
    Range: [-1.0, 1.0] -> Scaled to [0.0, 1.0]
    """
    if not label_a or not label_b:
        return 0.0
    emb_a = get_embedding(label_a)
    emb_b = get_embedding(label_b)
    sim = float(util.cos_sim(emb_a, emb_b)[0][0])
    return round((sim + 1.0) / 2.0, 4)  # normalize to [0, 1]


def semantic_distance(label_a: str, label_b: str) -> float:
    """
    Returns 1 - concept match similarity (distance measure).
    Range: 0.0 (identical) -> 1.0 (maximally different)
    """
    return round(1.0 - concept_match(label_a, label_b), 4)