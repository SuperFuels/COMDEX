"""
MeaningFieldEngine - Phase 37A : Meaning Field Generator (MFG)
---------------------------------------------------------------
Extracts semantic topology from the Aion Knowledge Graph (AKG)
and emotion/goal context to produce the first internal "meaning field".
Now reads directly from the SQLite AKG backend while incorporating
goal and emotion modulation.
"""

import json
import random
import logging
import time
from pathlib import Path
from statistics import mean

# ─────────────────────────────────────────────
# Imports and optional system dependencies
# ─────────────────────────────────────────────
from backend.modules.aion_knowledge.knowledge_graph_core import search as search_graph

logger = logging.getLogger(__name__)

MEANING_FIELD_PATH = Path("data/analysis/meaning_field.json")

try:
    from backend.modules.aion_photon.goal_engine import GOALS
except Exception:
    GOALS = None

try:
    from backend.modules.aion_emotion.emotion_engine import EMOTION
except Exception:
    EMOTION = None


# ─────────────────────────────────────────────
# Meaning Field Engine
# ─────────────────────────────────────────────
class MeaningFieldEngine:
    """Builds semantic clusters from AKG + goal/emotion context."""

    def __init__(self):
        self.field = {"clusters": []}
        self.timestamp = None

    # ─────────────────────────────────────────
    def _load_triplets_from_db(self):
        """Load concept relations through the workspace-scoped AKG boundary."""
        return [
            (
                row["subject"],
                row["predicate"],
                row["object"],
                float(row["strength"]),
            )
            for row in search_graph()
            if row["subject"].startswith("concept:")
            and row["object"].startswith("concept:")
        ]

    # ─────────────────────────────────────────
    def build_field(self):
        """Compute semantic clusters, incorporating emotion and goal influence."""
        triplets = self._load_triplets_from_db()

        if not triplets:
            logger.warning("[MFG] No concept-concept links found in AKG database.")
            self.field = {"clusters": []}
            return self.field

        # Emotional context
        valence = getattr(EMOTION, "valence", 0.0) if EMOTION else 0.0
        arousal = getattr(EMOTION, "arousal", 0.0) if EMOTION else 0.0
        emotion_bias = (valence - arousal) * 0.5 + 0.5

        # Goal context
        active_goals = list(getattr(GOALS, "active_goals", {}).values()) if GOALS else []

        clusters = {}
        for s, p, o, w in triplets:
            if s not in clusters:
                clusters[s] = {"center": s, "neighbors": set(), "weights": []}
            clusters[s]["neighbors"].add(o)
            clusters[s]["weights"].append(w)

        self.field["clusters"] = []
        for s, data in clusters.items():
            goal_align = 0.0
            for g in active_goals:
                if g.intent and g.intent.split("_")[-1] in s:
                    goal_align += g.priority
            goal_align = min(1.0, goal_align)

            cluster = {
                "center": s,
                "neighbors": list(data["neighbors"]),
                "emotion_bias": round(emotion_bias, 3),
                "goal_alignment": round(goal_align, 3),
                "link_count": len(data["neighbors"]),
                "mean_strength": round(mean(data["weights"]), 3)
                if data["weights"]
                else 1.0,
            }
            self.field["clusters"].append(cluster)

        self.timestamp = time.time()
        self.field["timestamp"] = self.timestamp

        MEANING_FIELD_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MEANING_FIELD_PATH, "w") as f:
            json.dump(self.field, f, indent=2)

        logger.info(f"[MFG] Meaning field built with {len(self.field['clusters'])} clusters.")
        return self.field

    # ─────────────────────────────────────────
    def register(self, concept: str, data: dict):
        """
        Phase 41A.3 - Register lexical or semantic entry.
        Inserts or updates a concept node in the Meaning Field.
        """
        if not hasattr(self, "field"):
            self.field = {"timestamp": __import__('time').time(), "clusters": []}

        cluster = {
            "center": concept,
            "definition": data.get("definition", ""),
            "synonyms": data.get("synonyms", []),
            "antonyms": data.get("antonyms", []),
            "emotion_bias": data.get("emotion_bias", 0.5),
            "goal_alignment": data.get("goal_alignment", 0.0),
            "semantic_strength": data.get("semantic_strength", 1.0),
            "timestamp": __import__('time').time(),
        }

        # Replace if concept already exists
        existing = next((c for c in self.field["clusters"] if c["center"] == concept), None)
        if existing:
            existing.update(cluster)
        else:
            self.field["clusters"].append(cluster)

    # ─────────────────────────────────────────
    def get_clusters(self, min_links: int = 1):
        """Return clusters above a minimum link threshold."""
        if not self.field or not self.field.get("clusters"):
            try:
                data = json.load(open(MEANING_FIELD_PATH))
                self.field = data
            except Exception:
                return []
        return [c for c in self.field.get("clusters", []) if c["link_count"] >= min_links]


# ─────────────────────────────────────────────
# Phase 37A - Global Instance
# ─────────────────────────────────────────────
try:
    MFG
except NameError:
    try:
        MFG = MeaningFieldEngine()
        print("🧩 MeaningFieldEngine global instance initialized as MFG")
    except Exception as e:
        print(f"⚠️ Could not initialize MFG: {e}")
        MFG = None
