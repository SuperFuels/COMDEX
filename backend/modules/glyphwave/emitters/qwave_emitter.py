"""
🔊 QWave Emitter
────────────────────────────────────────
Emit a symbolic beam (WaveState) across multiple systems:
 - QWave Transfer
 - GHX WebSocket
 - QFC HUD Overlay
 - SQI + Codex Metrics
"""

import asyncio
import inspect
import time
from typing import Optional, Dict, List, Any

from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.qwave.qwave_transfer_sender import send_qwave_transfer
from backend.modules.websocket_manager import broadcast_event
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import log_sqi_drift
from backend.modules.codex.codex_metrics import log_collapse_metric
from backend.modules.visualization.glyph_to_qfc import to_qfc_payload
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update


async def emit_qwave_beam(
    wave: WaveState,
    container_id: str,
    source: Any = "unknown",  # Accept any type
    metadata: Optional[Dict[str, Any]] = None,
    broadcast_modes: Optional[List[str]] = None
):
    """
    Dispatches a symbolic beam via QWave, GHX, QFC, and metrics layers.
    """

    # 🛡️ Fix bad source types (dict, etc)
    if isinstance(source, dict):
        print(f"[QWaveEmitter] ⚠️ Invalid source type (dict), converting: {source}")
        source = f"dict_source_{id(source)}"
    elif not isinstance(source, str):
        try:
            source = str(source)
        except Exception:
            source = f"invalid_source_{id(source)}"

    if broadcast_modes is None:
        broadcast_modes = ["qwave", "websocket", "ghx", "qfc", "metrics"]

    wave_id = getattr(wave, 'wave_id', 'unknown')
    print(f"[QWaveEmitter] ⚡ Emitting beam from source: {source} → {wave_id}")

    # 1. QWave Transfer
    if "qwave" in broadcast_modes:
        try:
            await send_qwave_transfer(container_id, source=source, beam_data=wave)
            print(f"🚀 QWave transfer sent from {source} to {container_id}")
        except Exception as e:
            print(f"[QWaveEmitter] ⚠️ QWave transfer failed: {e}")

    # 2. GHX / WebSocket
    if "ghx" in broadcast_modes or "websocket" in broadcast_modes:
        try:
            await broadcast_event("glyphwave.beam", {
                "wave_id": wave_id,
                "container_id": container_id,
                "glow": getattr(wave, "glow_intensity", 0.0),
                "pulse": getattr(wave, "pulse_frequency", 0.0),
                "coherence": getattr(wave, "coherence", 1.0),
                "carrier": getattr(wave, "carrier_type", "default"),
                "modulation": getattr(wave, "modulation_strategy", "default"),
                "mutation_type": getattr(wave, "mutation_type", "none"),
                "mutation_cause": getattr(wave, "mutation_cause", "unknown"),
                "timestamp": getattr(wave, "timestamp", time.time()),
                "source": source
            })
        except Exception as e:
            print(f"[QWaveEmitter] ⚠️ WebSocket emit failed: {e}")

    # 3. Log Collapse Metrics
    if "metrics" in broadcast_modes:
        try:
            log_collapse_metric(
                container_id,
                wave_id,
                getattr(wave, "glow_intensity", 0.0),
                getattr(wave, "collapse_state", "unknown")
            )
            log_sqi_drift(
                container_id,
                wave_id,
                getattr(wave, "glow_intensity", 0.0),
                getattr(wave, "pulse_frequency", 0.0)
            )
        except Exception as e:
            print(f"[QWaveEmitter] ⚠️ Metrics logging failed: {e}")

    # 4. QFC HUD Broadcast
    if "qfc" in broadcast_modes:
        try:
            node_payload = {
                "glyph": "✦",
                "op": getattr(wave, "mutation_type", "beam"),
                "metadata": {
                    "glow": getattr(wave, "glow_intensity", 0.0),
                    "pulse": getattr(wave, "pulse_frequency", 0.0),
                    "wave_id": wave_id,
                    "source": source,
                    **(metadata or {})
                }
            }
            context = {
                "container_id": container_id,
                "source_node": getattr(wave, "source_wave_id", "origin")
            }
            qfc_payload = to_qfc_payload(node_payload, context)
            await broadcast_qfc_update(container_id, qfc_payload)
            print(f"📡 QFC broadcast sent for: {container_id} | Nodes: {len(qfc_payload.get('nodes', []))}")
        except Exception as e:
            print(f"[QWaveEmitter] ⚠️ QFC overlay failed: {e}")