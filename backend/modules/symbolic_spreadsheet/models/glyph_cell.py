# ===============================
# 📁 backend/modules/symbolic_spreadsheet/models/glyph_cell.py
# ===============================
"""
⚛️ GlyphCell - Core symbolic data model for 4D AtomSheet in the SQS system.

Each GlyphCell contains symbolic logic, emotion, prediction, trace history,
SQI scoring, execution result, wave_beams history, and references to linked or nested logic.

📌 Example:
    cell = GlyphCell(
        id="A1",
        logic="x + 2",
        position=[0, 0, 0, 0],
        emotion="inspired",
        nested_logic="if x > 0: return x**2"
    )
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from backend.modules.patterns.pattern_trace_engine import record_trace

# 🔁 Dynamic pattern engine (safe import wrapper)
try:
    from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
    _pattern_engine = SymbolicPatternEngine()

    def detect_patterns(logic: str) -> List[Dict[str, Any]]:
        glyphs = [{"type": "symbol", "text": logic}]
        return _pattern_engine.detect_patterns(glyphs)
except ImportError:
    def detect_patterns(logic: str) -> List[Dict[str, Any]]:
        return []

REQUIRED_FIELDS = {"id", "logic", "position"}


class GlyphCell:
    def __init__(
        self,
        id: str,
        logic: str,
        position: List[int],
        emotion: Optional[str] = "neutral",
        prediction: Optional[str] = "",
        trace: Optional[List[str]] = None,
        result: Optional[str] = None,
        sqi_score: Optional[float] = 0.0,
        validated: Optional[bool] = False,
        linked_cells: Optional[List[List[int]]] = None,
        nested_logic: Optional[str] = "",
        mutation_type: Optional[str] = None,
        mutation_parent_id: Optional[str] = None,
        mutation_score: Optional[float] = None,
        mutation_timestamp: Optional[Union[str, datetime]] = None,
        prediction_forks: Optional[List[str]] = None,  # tracks prediction fork updates
        wave_beams: Optional[List[Dict[str, Any]]] = None,  # per-cell QWave beam history
    ):
        self.id = id
        self.logic = logic
        self.position = (position + [0] * 4)[:4]  # normalize to 4D
        self.emotion = emotion
        self.prediction = prediction
        self.trace = trace or []
        self.result = result
        self.sqi_score = sqi_score
        self.validated = validated
        self.linked_cells = [((lc + [0] * 4)[:4] if isinstance(lc, list) else lc) for lc in (linked_cells or [])]
        self.nested_logic = nested_logic
        self.mutation_type = mutation_type
        self.mutation_parent_id = mutation_parent_id
        self.mutation_score = mutation_score
        if isinstance(mutation_timestamp, datetime):
            self.mutation_timestamp = mutation_timestamp.isoformat()
        else:
            self.mutation_timestamp = mutation_timestamp

        # Initialize prediction forks and wave_beams
        self.prediction_forks = prediction_forks or []
        self.wave_beams: List[Dict[str, Any]] = list(wave_beams) if wave_beams is not None else []

        # Cache for pattern detection per cell
        self._pattern_cache: Optional[List[str]] = None

    def append_trace(self, message: str):
        """Add a message to the execution trace log."""
        self.trace.append(message)
        record_trace(self.id, message)

    def __repr__(self):
        return (
            f"GlyphCell(id={self.id}, pos={self.position}, logic='{self.logic}', "
            f"sqi={self.sqi_score:.2f}, emotion={self.emotion}, validated={self.validated})"
        )

    def expand_nested(self, depth: int = 1) -> Optional[str]:
        """
        🔁 Expand nested logic if defined (CodexLang placeholder).
        Returns:
            A simplified string, or None if no nested logic.
        """
        if self.nested_logic and self.nested_logic.strip():
            nested = self.nested_logic.strip()
            if "if" in nested:
                return nested.split("if", 1)[-1].strip()
            return nested
        return None

    def detect_patterns(self) -> List[str]:
        """
        🧠 Detect symbolic patterns using the pattern engine.
        Returns:
            List of matched pattern names.
        """
        if self._pattern_cache is not None:
            return self._pattern_cache

        try:
            matches = detect_patterns(self.logic)
            if isinstance(matches, list):
                self._pattern_cache = [m.get("name", "") for m in matches]
            else:
                self._pattern_cache = []
        except Exception as e:
            record_trace(self.id, f"[Pattern Detection Error] {e}")
            self._pattern_cache = []

        return self._pattern_cache

    def compute_sqi(self) -> float:
        """
        📈 Compute SQI score based on trace, emotion, logic, prediction, and mutation.
        Returns:
            SQI score (float in [0.0, 1.0])
        """
        base = 0.5
        trace_bonus = 0.2 * len(self.trace)
        emotion_bonus = 0.3 if self.emotion == "inspired" else 0.0
        prediction_bonus = 0.1 * len(self.prediction.split()) if self.prediction else 0.0
        logic_bonus = 0.05 * len(self.logic.split()) if self.logic else 0.0
        pattern_bonus = 0.1 * len(self.detect_patterns())
        mutation_bonus = 0.05 * (self.mutation_score or 0.0)

        total = base + trace_bonus + emotion_bonus + prediction_bonus + logic_bonus + pattern_bonus + mutation_bonus
        self.sqi_score = min(1.0, total)
        return self.sqi_score

    def validate(self) -> Dict[str, Any]:
        """
        ✅ Ensure the cell is valid and safe to execute.
        Returns:
            Dict: { "valid": bool, "errors": List[str] }
        """
        errors = []
        if len(self.position) != 4:
            errors.append(f"Position must be 4D: {self.position}")
        for lc in self.linked_cells:
            if not isinstance(lc, list) or len(lc) != 4:
                errors.append(f"All linked_cells must be 4D: {self.linked_cells}")
        if self.nested_logic is not None and not self.nested_logic.strip():
            errors.append("nested_logic is non-empty but blank")

        return {"valid": len(errors) == 0, "errors": errors}

    def to_dict(self, include_empty: bool = False) -> Dict[str, Any]:
        """
        📤 Serialize cell to dictionary (for .sqs.json or .dc.json).
        Args:
            include_empty (bool): If False, skip optional empty fields.
        Returns:
            Dict: Serialized cell.
        """
        payload = {
            "id": self.id,
            "logic": self.logic,
            "position": self.position,
            "emotion": self.emotion,
            "prediction": self.prediction,
            "trace": self.trace if self.trace else None,
            "result": self.result,
            "sqi_score": self.sqi_score,
            "validated": self.validated,
            "linked_cells": self.linked_cells if self.linked_cells else None,
            "nested_logic": self.nested_logic if self.nested_logic else None,
            "mutation_type": self.mutation_type,
            "mutation_parent_id": self.mutation_parent_id,
            "mutation_score": self.mutation_score,
            "mutation_timestamp": self.mutation_timestamp,
            "prediction_forks": self.prediction_forks if self.prediction_forks else None,
            "wave_beams": self.wave_beams if self.wave_beams else None,
        }

        return {
            k: v for k, v in payload.items()
            if include_empty or (k in REQUIRED_FIELDS or (v is not None and v != []))
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GlyphCell":
        """
        📥 Create a GlyphCell from a dictionary.
        Args:
            data (dict): Dictionary representing a GlyphCell.
        Returns:
            GlyphCell instance.
        """
        cell = GlyphCell(
            id=data.get("id", ""),
            logic=data.get("logic", ""),
            position=data.get("position", [0, 0, 0, 0]),
            emotion=data.get("emotion", "neutral"),
            prediction=data.get("prediction", ""),
            trace=data.get("trace", []),
            result=data.get("result"),
            sqi_score=data.get("sqi_score", 0.0),
            validated=data.get("validated", False),
            linked_cells=data.get("linked_cells", []),
            nested_logic=data.get("nested_logic", ""),
            mutation_type=data.get("mutation_type"),
            mutation_parent_id=data.get("mutation_parent_id"),
            mutation_score=data.get("mutation_score"),
            mutation_timestamp=data.get("mutation_timestamp"),
            prediction_forks=data.get("prediction_forks", []),
            wave_beams=data.get("wave_beams", []),
        )
        return cell