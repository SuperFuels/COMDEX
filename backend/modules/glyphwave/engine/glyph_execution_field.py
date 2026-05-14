# File: backend/modules/glyphwave/engine/glyph_execution_field.py

from typing import List, Dict, Optional, Any
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.core.wave_field import WaveField
from backend.modules.glyphwave.core.wave_glyph import WaveGlyph
from backend.modules.glyphwave.core.entangled_wave import EntangledWave
from backend.modules.glyphwave.runtime.wave_state_store import WaveStateStore
from backend.modules.visualization.ghx_replay_broadcast import emit_gwave_replay
from backend.modules.visualization.broadcast_qfc_update import send_qfc_update
from backend.modules.sqi.sqi_scorer import score_electron_glyph
from backend.modules.codex.codex_executor import execute_codexlang_glyph
from backend.modules.patterns.creative_pattern_mutation import mutate_pattern


class GlyphExecutionField:
    """
    GlyphExecutionField: Manages symbolic wave execution in a live vector field.
    Supports mutation, SQI scoring, CodexLang logic, GHX/QFC visualization, and entanglement.
    """

    def __init__(self, field_dimensions: List[int]):
        self.field = WaveField(field_dimensions)
        self.state_store = WaveStateStore()
        self.tick = 0

    def inject_wave(self, wave: WaveState, x: int, y: int, z: Optional[int] = None) -> None:
        glyph = wave.to_glyph()
        self.field.set_glyph(x, y, glyph, z)
        self.state_store.add_wave(wave)
        emit_gwave_replay(wave)

    def step(self) -> None:
        """
        Execute one full simulation tick:
        - Score all active glyphs
        - Execute CodexLang logic if available
        - Broadcast GHX/QFC state
        - Apply mutations if needed
        """
        glyphs = self.field.all_glyphs()

        for glyph in glyphs:
            wave_id = glyph.metadata.get("wave_id")
            wave = self.state_store.get_wave(wave_id)
            if not wave:
                continue

            sqi_score = score_electron_glyph(glyph)
            collapse_state = "collapsed" if sqi_score < 0.3 else "active"

            prediction = None
            if glyph.metadata.get("codex"):
                prediction = execute_codexlang_glyph(glyph)

            self.state_store.cache_prediction(wave_id, sqi_score, collapse_state, prediction)

            if sqi_score > 0.8:
                mutated = mutate_pattern(glyph)
                self._apply_mutation(wave_id, mutated)

        self._broadcast_field()
        self.tick += 1

    def _apply_mutation(self, wave_id: str, mutated: WaveGlyph) -> None:
        wave = self.state_store.get_wave(wave_id)
        if not wave:
            return

        new_wave = WaveState.from_glyph(mutated)
        self.state_store.add_wave(new_wave)

        coords = self._find_glyph_coords(wave_id)
        if coords:
            x, y, *z = coords
            self.field.set_glyph(x, y, mutated, z[0] if z else None)
            emit_gwave_replay(new_wave)

    def _find_glyph_coords(self, wave_id: str) -> Optional[List[int]]:
        shape = self.field.shape()
        for idx, glyph in enumerate(self.field.grid.flat):
            if glyph and glyph.metadata.get("wave_id") == wave_id:
                return list(np.unravel_index(idx, shape))
        return None

    def _broadcast_field(self) -> None:
        payload = {
            "tick": self.tick,
            "shape": self.field.shape(),
            "glyphs": [g.to_dict() for g in self.field.all_glyphs()],
        }
        send_qfc_update(payload)

    def collapse_entangled_region(self, glyphs: List[Dict]) -> Dict:
        entangled = EntangledWave.from_glyphs(glyphs)
        return entangled.collapse_all()

    def export_state(self) -> Dict:
        return {
            "tick": self.tick,
            "snapshot": self.state_store.snapshot(),
            "field_shape": self.field.shape()
        }

    def clear(self):
        self.state_store.clear()
        self.field = WaveField(self.field.dimensions)
        self.tick = 0
