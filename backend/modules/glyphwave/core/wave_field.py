# File: backend/modules/glyphwave/core/wave_field.py

import numpy as np
from typing import List, Optional
from backend.modules.glyphwave.core.wave_glyph import WaveGlyph

class WaveField:
    """
    A 2D or 3D lattice of WaveGlyphs represented as a NumPy object array.
    Enables fast, vectorized symbolic field simulations.
    """

    def __init__(self, dimensions: List[int]):
        """
        dimensions: [width, height] or [width, height, depth]
        """
        self.dimensions = dimensions
        self.ndim = len(dimensions)
        self.grid = self._init_grid(dimensions)

    def _init_grid(self, dims: List[int]):
        """
        Initializes a NumPy object array for storing WaveGlyphs.
        """
        shape = tuple(dims)
        return np.empty(shape, dtype=object)

    def set_glyph(self, x: int, y: int, glyph: WaveGlyph, z: Optional[int] = None):
        if self.ndim == 3 and z is not None:
            self.grid[x, y, z] = glyph
        else:
            self.grid[x, y] = glyph

    def get_glyph(self, x: int, y: int, z: Optional[int] = None) -> Optional[WaveGlyph]:
        if self.ndim == 3 and z is not None:
            return self.grid[x, y, z]
        return self.grid[x, y]

    def all_glyphs(self) -> List[WaveGlyph]:
        """
        Returns a flat list of all non-null glyphs.
        """
        return [g for g in self.grid.flat if g is not None]

    def batch_set(self, coords: List[tuple], glyphs: List[WaveGlyph]):
        """
        Batch assign glyphs to given coordinates.
        """
        assert len(coords) == len(glyphs)
        for idx, coord in enumerate(coords):
            self.grid[coord] = glyphs[idx]

    def batch_get(self, coords: List[tuple]) -> List[Optional[WaveGlyph]]:
        """
        Batch retrieve glyphs at given coordinates.
        """
        return [self.grid[coord] for coord in coords]

    def shape(self):
        return self.grid.shape

    def vectorized_mask(self) -> np.ndarray:
        """
        Returns a boolean mask of where glyphs exist in the grid.
        """
        return np.vectorize(lambda x: x is not None)(self.grid)

    def __repr__(self):
        return f"<WaveField shape={self.grid.shape} glyphs={len(self.all_glyphs())}>"