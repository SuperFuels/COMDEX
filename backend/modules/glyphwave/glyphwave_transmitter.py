# File: backend/modules/glyphwave/glyphwave_transmitter.py

from typing import List, Dict, Optional, Any
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.qwave_emitter import emit_qwave_beam
from backend.modules.glyphwave.qwave_multiplexer import multiplex_beams
from backend.modules.visualization.glyph_to_qfc import to_qfc_payload

class GlyphWaveTransmitter:
    """
    Handles dispatch and transmission of symbolic QWave beams across systems
    like GHX, QFC, Replay, and external broadcast layers.
    """

    def __init__(self):
        self.enabled = True

    def transmit_beams(
        self,
        wave_state: WaveState,
        context: Optional[Dict[str, Any]] = None,
        target_channels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Emits one or more QWave beams from a given WaveState, targeting QFC/GHX/subscribers.
        """

        if not self.enabled:
            print("⚠️ GlyphWaveTransmitter is disabled.")
            return []

        # 🌀 Step 1: Extract beam(s) from wave state
        raw_beams = wave_state.extract_active_beams()
        if not raw_beams:
            print("⚠️ No active beams found in WaveState.")
            return []

        # 🔀 Step 2: Multiplex beams if needed
        multiplexed_beams = multiplex_beams(raw_beams)

        # 📡 Step 3: Emit beams to downstream systems
        emitted = []
        for beam in multiplexed_beams:
            try:
                emit_qwave_beam(beam, context=context, channels=target_channels)
                emitted.append(beam)
                print(f"📡 Emitted QWave beam with id: {beam.get('id')}")
            except Exception as e:
                print(f"❌ Failed to emit QWave beam: {e}")

        return emitted

    def transmit_as_qfc_update(
        self,
        wave_state: WaveState,
        observer_id: Optional[str] = None,
        include_beams: bool = True
    ) -> Dict[str, Any]:
        """
        Converts the wave state into a QFC payload and emits it via WebSocket or CodexLang.
        """

        try:
            payload = to_qfc_payload(
                wave_state,
                observer_id=observer_id,
                include_beams=include_beams
            )
            # Direct WebSocket broadcast should be called from outer runtime
            print(f"📤 Prepared QFC payload from wave state for observer: {observer_id}")
            return payload
        except Exception as e:
            print(f"❌ Failed to prepare QFC payload: {e}")
            return {}