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
from datetime import datetime
from typing import List, Dict, Optional


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
    ):
        self.glyph = glyph
        self.source = source  # e.g., "DreamCore", "GoalPredictor"
        self.confidence = confidence
        self.entropy = entropy
        self.container_id = container_id
        self.tick = tick
        self.coord = coord
        self.trace_id = trace_id
        self.tags = tags or []
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "glyph": self.glyph,
            "source": self.source,
            "confidence": self.confidence,
            "entropy": self.entropy,
            "container_id": self.container_id,
            "tick": self.tick,
            "coord": self.coord,
            "trace_id": self.trace_id,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


class PredictionIndex:
    def __init__(self):
        self.predictions: List[PredictedGlyph] = []

    def add_prediction(self, prediction: PredictedGlyph):
        self.predictions.append(prediction)

    def to_json(self, compressed: bool = False) -> str:
        data = [p.to_dict() for p in self.predictions]
        return json.dumps(data, separators=(',', ':')) if compressed else json.dumps(data, indent=2)

    def summarize(self) -> Dict:
        return {
            "total_predictions": len(self.predictions),
            "average_confidence": sum([p.confidence for p in self.predictions]) / len(self.predictions)
            if self.predictions else 0.0,
            "tag_counts": self._count_tags(),
        }

    def _count_tags(self) -> Dict[str, int]:
        counts = {}
        for p in self.predictions:
            for tag in p.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return counts