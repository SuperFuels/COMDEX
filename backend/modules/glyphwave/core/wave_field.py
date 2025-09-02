# backend/modules/glyphwave/core/wave_field.py

from typing import List, Optional
from backend.modules.glyphwave.core.wave_glyph import WaveGlyph

class WaveField:
    """
    A 2D or 3D lattice of WaveGlyphs representing a coherent interference field.
    Can be used to simulate spatial interference patterns or symbolic glyph propagation.
    """
    def __init__(self, dimensions: List[int]):
        """
        dimensions: [width, height] or [width, height, depth]
        """
        self.dimensions = dimensions
        self.grid = self._init_grid(dimensions)

    def _init_grid(self, dims: List[int]):
        if len(dims) == 2:
            return [[None for _ in range(dims[1])] for _ in range(dims[0])]
        elif len(dims) == 3:
            return [[[None for _ in range(dims[2])] for _ in range(dims[1])] for _ in range(dims[0])]
        else:
            raise ValueError("WaveField only supports 2D or 3D.")

    def set_glyph(self, x: int, y: int, glyph: WaveGlyph, z: Optional[int] = None):
        if z is not None and len(self.dimensions) == 3:
            self.grid[x][y][z] = glyph
        else:
            self.grid[x][y] = glyph

    def get_glyph(self, x: int, y: int, z: Optional[int] = None) -> Optional[WaveGlyph]:
        if z is not None and len(self.dimensions) == 3:
            return self.grid[x][y][z]
        return self.grid[x][y]

    def all_glyphs(self) -> List[WaveGlyph]:
        glyphs = []
        if len(self.dimensions) == 2:
            for row in self.grid:
                for g in row:
                    if g: glyphs.append(g)
        else:
            for x in self.grid:
                for y in x:
                    for g in y:
                        if g: glyphs.append(g)
        return glyphs