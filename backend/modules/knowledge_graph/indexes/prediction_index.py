# File: backend/modules/knowledge_graph/indexes/prediction_index.py

"""
📄 prediction_index.py

🔮 Future Glyph Prediction Index
Tracks symbolic predictions from DreamCore, GoalPredictor, or Reflective Agents
with associated confidence, entropy, source system, and glyph metadata.

Design Rubric:
- 🔮 Symbolic Glyph Predictions .......... ✅
- 📊 Confidence & Entropy Metrics ........ ✅
- 🧠 Source Attribution (e.g. DreamCore) .. ✅
- 🧩 Tag Support for Topics/Themes ........ ✅
- ⏱️ Tick & Timestamp Tracking ........... ✅
- 📦 Container Context Awareness .......... ✅
- 📚 .dc Export + Plugin Integration ...... ✅
"""

import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any

from backend.modules.knowledge_graph.time_utils import get_current_timestamp
from backend.modules.knowledge_graph.id_utils import generate_uuid
from backend.modules.consciousness.state_manager import STATE

INDEX_NAME = "prediction_index"

# ──────────────────────────────────────────────
# 📦 Prediction Entry Class
# ──────────────────────────────────────────────

class PredictedGlyph:
    def __init__(
        self,
        glyph: str,
        source: str,
        confidence: float,
        entropy: Optional[float] = None,
        container_id: Optional[str] = None,
        tick: Optional[int] = None,
        coord: Optional[str] = None,
        trace_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        goal: Optional[str] = None,
    ):
        self.id = generate_uuid()
        self.glyph = glyph
        self.source = source  # e.g., "DreamCore", "GoalPredictor"
        self.confidence = confidence
        self.entropy = entropy
        self.container_id = container_id
        self.tick = tick
        self.coord = coord
        self.trace_id = trace_id
        self.tags = tags or []
        self.goal = goal
        self.timestamp = get_current_timestamp()
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        base = f"{self.glyph}|{self.source}|{self.timestamp}"
        return hashlib.sha256(base.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "glyph": self.glyph,
            "source": self.source,
            "confidence": self.confidence,
            "entropy": self.entropy,
            "container_id": self.container_id,
            "tick": self.tick,
            "coord": self.coord,
            "trace_id": self.trace_id,
            "tags": self.tags,
            "goal": self.goal,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }


# ──────────────────────────────────────────────
# 📈 Prediction Index Manager
# ──────────────────────────────────────────────

class PredictionIndex:
    def __init__(self):
        self.predictions: List[PredictedGlyph] = []

    def add_prediction(self, prediction: PredictedGlyph):
        """Append a prediction to the in-memory index and UCS container index."""
        self.predictions.append(prediction)

        # 🔗 Push into active UCS container
        container = self._get_active_container()
        index = self._get_or_create_index(container)
        index.append(prediction.to_dict())
        container["last_index_update"] = datetime.utcnow().isoformat()

    def to_json(self, compressed: bool = False) -> str:
        """Export all predictions as JSON (optionally compressed)."""
        data = [p.to_dict() for p in self.predictions]
        return json.dumps(data, separators=(',', ':')) if compressed else json.dumps(data, indent=2)

    def export_to_dc(self) -> Dict[str, Any]:
        """Return a `.dc`-compatible block for symbolic replay or export."""
        return {
            "index": INDEX_NAME,
            "timestamp": get_current_timestamp(),
            "entries": [p.to_dict() for p in self.predictions],
        }

    def summarize(self) -> Dict[str, Any]:
        return {
            "total_predictions": len(self.predictions),
            "average_confidence": sum(p.confidence for p in self.predictions) / len(self.predictions)
            if self.predictions else 0.0,
            "tag_counts": self._count_tags(),
        }

    def _count_tags(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for p in self.predictions:
            for tag in p.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    # ──────────────────────────────────────────────
    # 🧠 UCS Container Integration
    # ──────────────────────────────────────────────

    def _get_active_container(self) -> Dict[str, Any]:
        ucs = STATE.get_active_universal_container_system()
        return ucs.get("active_container", {})

    def _get_or_create_index(self, container: Dict[str, Any]) -> List[Dict[str, Any]]:
        if "indexes" not in container:
            container["indexes"] = {}
        if INDEX_NAME not in container["indexes"]:
            container["indexes"][INDEX_NAME] = []
        return container["indexes"][INDEX_NAME]


# ✅ Singleton instance for global access
prediction_index = PredictionIndex()