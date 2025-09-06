import time
from typing import Optional, Dict, Any

from backend.modules.glyphwave.core.beam_logger import log_beam_prediction
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.qwave.qwave_writer import generate_qwave_id
from backend.modules.glyphvault.soul_law_validator import validate_beam_event

# ✅ NEW: Import for writing beam to container memory
from backend.modules.container.container_runtime import append_beam_to_container

# 🔋 Optional: metrics streaming or WebSocket hooks can go here
# from backend.modules.glyphwave.hud.metric_streamer import stream_beam_metric


def emit_qwave_beam(
    glyph_id: str,
    result: Optional[Dict[str, Any]] = None,
    source: str = "codex_executor",
    context: Optional[Dict[str, Any]] = None,
    state: Optional[str] = "predicted",  # "collapsed", "contradicted", etc.
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Emits a QWave beam event into the symbolic telemetry system.
    """

    timestamp = time.time()
    context = context or {}
    metadata = metadata or {}

    container_id = context.get("container_id", "unknown")
    qwave_id = generate_qwave_id(glyph_id, state=state)
    tick = context.get("tick") or int(timestamp * 1000)

    # Ensure required metadata values
    target = metadata.get("target", "unspecified")

    wave_state = WaveState(
        wave_id=qwave_id,
        glyph_id=glyph_id,
        container_id=container_id,
        tick=tick,
        state=state,
        source=source,
        target=target,
        timestamp=timestamp,
        metadata=metadata,
    )

    wave_dict = vars(wave_state)

    # ✅ Validate via SoulLaw filter
    try:
        validate_beam_event(wave_dict)
    except Exception as e:
        print(f"[emit_qwave_beam] ⚠️ SoulLaw validation failed: {e}")

    # 📡 Log or broadcast beam
    try:
        log_beam_prediction(wave_dict)
    except Exception as e:
        print(f"[emit_qwave_beam] ⚠️ Failed to log symbolic beam: {e}")

    # ✅ NEW: Inject into container memory for later .dc.json export
    try:
        append_beam_to_container(container_id, wave_dict)
    except Exception as e:
        print(f"[emit_qwave_beam] ⚠️ Failed to append beam to container: {e}")

    # 📊 Optional: HUD / metric streamer
    # stream_beam_metric(wave_dict)

    return wave_state