# 📁 backend/tests/test_emit_qwave_beam.py

import asyncio
from backend.modules.glyphwave.emitters.qwave_emitter import emit_qwave_beam
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.websocket_manager import websocket_manager

# --- Dummy WebSocket client that prints everything it receives ---
class _DummyWS:
    async def accept(self):  # websocket_manager.connect() expects this
        print("[DUMMY WS] accepted")
    async def send_text(self, text: str):
        print(f"[DUMMY CLIENT] <- {text}")

async def attach_dummy_client():
    ws = _DummyWS()
    await websocket_manager.connect(ws)
    # Subscribe to the two tags our emitter uses
    await websocket_manager.subscribe(ws, "glyphwave.beam")
    await websocket_manager.subscribe(ws, "qfc_update")
    return ws

# ---------------------------------------------------------------

async def run_test():
    # Attach the dummy client so broadcasts have a subscriber
    await attach_dummy_client()

    wave = WaveState(
        wave_id="test_beam_123",
        glyph_data={"test": "data"},
        glyph_id="test_glyph",
        carrier_type="test_carrier",
        modulation_strategy="test_modulation",
        delay_ms=0,
        origin_trace=["unit_test"],
        metadata={"test_meta": True},
        prediction={"expected": "pass"},
        sqi_score=0.88,
        collapse_state="entangled",
        tick=42,
        state="active",
        container_id="test_container_001",
        source="unit_test_emit",
        target="test_target",
        timestamp=None,  # auto-generated in WaveState
    )

    await emit_qwave_beam(
        wave=wave,
        container_id="test_container_001",
        source="unit_test_emit",
        metadata={"test_key": "✅ passed"}
    )

if __name__ == "__main__":
    asyncio.run(run_test())