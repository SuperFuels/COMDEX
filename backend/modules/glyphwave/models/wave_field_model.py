# backend/modules/glyphwave/models/wave_field_model.py
from dataclasses import dataclass
from typing import Tuple, Dict
from .wave_glyph import WaveGlyph

@dataclass
class Field:
    dimensions: Tuple[int, int]  # rows x cols (for now)
    grid: Dict[Tuple[int, int], WaveGlyph]  # (x, y) → WaveGlyph

    def get(self, x: int, y: int) -> WaveGlyph:
        return self.grid.get((x, y))

    def set(self, x: int, y: int, glyph: WaveGlyph):
        self.grid[(x, y)] = glyph