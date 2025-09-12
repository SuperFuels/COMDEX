import time
import threading
from typing import Optional
from backend.modules.glyphwave.core.wave_state_store import WaveStateStore
from backend.modules.glyphwave.core.wave_glyph import WaveGlyph
from backend.modules.glyphwave.holographic.ghx_replay_broadcast import emit_gwave_replay
from backend.modules.codex.websocket.codex_ws_broadcast import send_codex_ws_event


class GHXFieldLoop:
    """
    GHX visual field loop that continuously polls active WaveStates and broadcasts
    visual holographic updates to the HUD overlay.
    """

    def __init__(self, store: Optional[WaveStateStore] = None, interval: float = 0.2):
        self.store = store or WaveStateStore()
        self.interval = interval  # Seconds between updates
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _loop(self):
        while self._running:
            self._broadcast_field()
            time.sleep(self.interval)

    def _broadcast_field(self):
        for wave in self.store.all_waves():
            glyphs: list[WaveGlyph] = wave.field.all_glyphs()
            if not glyphs:
                continue

            packet = {
                "type": "ghx_field",
                "wave_id": wave.id,
                "tick": wave.tick,
                "glyphs": [g.to_dict() for g in glyphs],
                "field_shape": wave.field.shape(),
            }

            send_codex_ws_event("ghx_field", packet)

            # Optional: also emit individual replay traces
            for g in glyphs:
                emit_gwave_replay(wave, glyph=g)


# Singleton field loop
ghx_field_loop = GHXFieldLoop()