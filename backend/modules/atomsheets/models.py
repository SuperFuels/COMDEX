# ===============================
# 📁 backend/modules/atomsheets/models.py
# ===============================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List

# Defensive GlyphCell import
try:
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
except Exception:
    class GlyphCell:  # type: ignore
        def __init__(self, id: str, logic: str = "", position=None, emotion: str = "neutral"):
            self.id = id
            self.logic = logic
            self.position = position or [0, 0, 0, 0]
            self.emotion = emotion
            self.prediction = ""
            self.prediction_forks = []
            self.wave_beams = []
            self.sqi_score = 1.0
            self._ctx = {}

@dataclass
class AtomSheet:
    id: str
    title: str = ""
    dims: List[int] = field(default_factory=lambda: [1, 1, 1, 1])  # 4D by default
    meta: Dict[str, Any] = field(default_factory=dict)
    cells: Dict[str, GlyphCell] = field(default_factory=dict)

    def cell_ids(self) -> List[str]:
        return list(self.cells.keys())