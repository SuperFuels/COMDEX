# File: backend/modules/glyphwave/qwave/beam_controller.py

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Dict, Optional

from backend.modules.glyphwave.core.wave_state import WaveState, ENTANGLED_WAVE_STORE
from backend.modules.sqi.metrics.collapse_timeline_writer import log_collapse_tick
from backend.modules.sqi.sqi_scorer import score_all_electrons

# ✅ Async WS broadcaster
from backend.modules.websocket_manager import broadcast_event

# ✅ QFC streaming helpers
from backend.modules.visualization.stream_qfc_from_entangled_wave import stream_qfc_from_entangled_wave
from backend.modules.visualization.glyph_to_qfc import to_qfc_payload
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update

logger = logging.getLogger(__name__)


def _fire_and_forget(coro: "asyncio.Future[Any] | asyncio.Task[Any] | Any") -> None:
    """
    Schedule a coroutine from sync code without blocking.
    If no running loop exists, we create one in a background thread to avoid stalling ticks.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)  # type: ignore[arg-type]
        return
    except RuntimeError:
        pass

    def _runner() -> None:
        try:
            asyncio.run(coro)  # type: ignore[arg-type]
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True).start()


class BeamController:
    """
    Runs a synchronous tick loop (sleep-based), and only schedules async work (WS/QFC)
    in fire-and-forget mode so it cannot slow down transactions/ticks.

    Key fixes vs older versions:
      - Never blocks on asyncio.run() inside the hot loop.
      - Never calls broadcast_event(payload_dict) (wrong signature); always (tag, payload).
      - Avoids importing asyncio repeatedly / creating tasks without a loop.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        self.tick_rate = float(config.get("tick_rate", 1.0))
        self.enable_sqi = bool(config.get("enable_sqi", True))
        self.enable_logging = bool(config.get("enable_logging", True))
        self.enable_replay = bool(config.get("enable_replay", False))
        self.test_mode = bool(config.get("test_mode", False))
        self.container_id = str(config.get("container_id", "unknown.dc"))
        self.enable_telemetry = bool(config.get("enable_telemetry", False))
        self.enable_hud = bool(config.get("enable_hud", False))
        self.enable_qfc_stream = bool(config.get("enable_qfc_stream", True))

        self._running = False
        self._tick_count = 0
        self._collapse_rate_history: list[float] = []

    def _log_hud_overlay(self, wave_state: WaveState) -> None:
        try:
            print(f"[HUD] BeamTick {self._tick_count} | SQI: {float(getattr(wave_state, 'last_sqi_score', 0.0)):.2f}")
        except Exception:
            pass

    def _record_telemetry(self, tick_duration_ms: float) -> None:
        self._collapse_rate_history.append(tick_duration_ms)
        if len(self._collapse_rate_history) > 100:
            self._collapse_rate_history.pop(0)

    def run_tick_loop(self) -> None:
        self._running = True
        print(f"[BEAM MODE] Running beam loop @ {self.tick_rate}s for container: {self.container_id}")

        while self._running:
            tick_start = time.time()
            self._tick_count += 1

            try:
                wave_state = WaveState.from_container_id(self.container_id)
                wave_state.evolve()

                if self.enable_sqi:
                    score_all_electrons(wave_state)

                if self.enable_logging:
                    log_collapse_tick(
                        wave_state,
                        profile_data={
                            "tick_duration_ms": (time.time() - tick_start) * 1000.0,
                            "tick_index": self._tick_count,
                        },
                    )

                if self.enable_hud:
                    self._log_hud_overlay(wave_state)

                if self.enable_replay:
                    try:
                        wave_state.export_replay_snapshot()
                    except Exception:
                        pass

                if self.enable_telemetry:
                    self._record_telemetry((time.time() - tick_start) * 1000.0)

                # ✅ Primary: Stream entangled wave to QFC (sync helper; should be lightweight)
                if self.enable_qfc_stream:
                    ew = ENTANGLED_WAVE_STORE.get(self.container_id)
                    if ew:
                        try:
                            stream_qfc_from_entangled_wave(self.container_id, ew)
                        except Exception as stream_err:
                            print(f"[⚠️ QFC] Failed to stream from entangled wave: {stream_err}")
                    else:
                        # 🔁 Fallback: Stream from WaveState directly (async broadcast; fire-and-forget)
                        try:
                            node_payload = {
                                "glyph": "🌀",
                                "op": "beam_tick",
                                "metadata": {
                                    "tick": self._tick_count,
                                    "sqi_score": getattr(wave_state, "last_sqi_score", None),
                                    "entropy": getattr(wave_state, "entropy", None),
                                    "coherence": getattr(wave_state, "coherence", None),
                                },
                            }
                            context = {"container_id": self.container_id, "source_node": getattr(wave_state, "id", "wave")}
                            qfc_payload = to_qfc_payload(node_payload, context)
                            _fire_and_forget(broadcast_qfc_update(self.container_id, qfc_payload))
                        except Exception as qfc_fallback_err:
                            print(f"[⚠️ QFC Fallback] Failed to stream from WaveState: {qfc_fallback_err}")

                # ✅ WebSocket HUD (test only) — IMPORTANT: broadcast_event(tag, payload)
                if self.test_mode:
                    hud_payload = {
                        "type": "beam_hud_update",
                        "data": {
                            "tick_duration_ms": (time.time() - tick_start) * 1000.0,
                            "container_id": self.container_id,
                            "last_sqi_score": getattr(wave_state, "last_sqi_score", None),
                            "beam_enabled": True,
                            "replay_enabled": self.enable_replay,
                        },
                    }

                    # Don't block the tick loop on websocket sends
                    _fire_and_forget(broadcast_event("beam_hud_update", hud_payload))

                    print(
                        f"[DEBUG] Tick {self._tick_count} | SQI: {float(getattr(wave_state, 'last_sqi_score', 0.0)):.3f} "
                        f"| Duration: {(time.time() - tick_start) * 1000.0:.2f}ms"
                    )

            except Exception as e:
                print(f"[ERROR] Beam tick failed at tick {self._tick_count}: {str(e)}")

            time.sleep(self.tick_rate)

    def start(self, threaded: bool = False) -> None:
        print(f"[BEAM MODE] Starting beam loop{' in thread' if threaded else ''} for: {self.container_id}")
        if threaded:
            thread = threading.Thread(target=self.run_tick_loop, daemon=True)
            thread.start()
        else:
            self.run_tick_loop()

    def stop(self) -> None:
        print(f"[BEAM MODE] Stopping beam loop for: {self.container_id}")
        self._running = False


# ────────────────────────────────────────────────────────────────
# ✅ SRK-16: Integrated QWave Writer + PMG archiving support
# ────────────────────────────────────────────────────────────────
from backend.modules.qwave.qwave_writer import QWaveWriter
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid


class BeamPersistenceMixin:
    def __init__(self):
        self.qwave_writer = QWaveWriter(out_dir="runtime/qwave_logs")
        self.pmg = PhotonMemoryGrid()

    def persist_snapshot(self, wave_state: WaveState, tick_index: int) -> Optional[str]:
        """
        Writes a beam snapshot to disk and archives coherence state to PMG.
        Non-blocking PMG store: scheduled fire-and-forget.
        """
        snapshot = {
            "wave_id": getattr(wave_state, "id", "unknown"),
            "tick_index": tick_index,
            "sqi_score": getattr(wave_state, "last_sqi_score", None),
            "entropy": getattr(wave_state, "entropy", None),
            "coherence": getattr(wave_state, "coherence", None),
            "timestamp": time.time(),
            "container_id": getattr(self, "container_id", "unknown"),
        }

        try:
            path = self.qwave_writer.write_snapshot(getattr(wave_state, "id", "unknown"), snapshot)
            _fire_and_forget(self.pmg.store_capsule_state(getattr(wave_state, "id", "unknown"), snapshot))
            return path
        except Exception as e:
            print(f"[⚠️ BeamPersistence] Failed to persist snapshot: {e}")
            return None


class AdvancedBeamController(BeamController, BeamPersistenceMixin):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BeamController.__init__(self, config)
        BeamPersistenceMixin.__init__(self)

    def run_tick_loop(self) -> None:
        self._running = True
        print(f"[BEAM MODE+] Running enhanced loop @ {self.tick_rate}s for container: {self.container_id}")

        while self._running:
            tick_start = time.time()
            self._tick_count += 1

            try:
                wave_state = WaveState.from_container_id(self.container_id)
                wave_state.evolve()

                if self.enable_sqi:
                    score_all_electrons(wave_state)

                if self.enable_logging:
                    log_collapse_tick(
                        wave_state,
                        profile_data={
                            "tick_duration_ms": (time.time() - tick_start) * 1000.0,
                            "tick_index": self._tick_count,
                        },
                    )
                    self.persist_snapshot(wave_state, self._tick_count)

                if self.enable_qfc_stream:
                    ew = ENTANGLED_WAVE_STORE.get(self.container_id)
                    if ew:
                        try:
                            stream_qfc_from_entangled_wave(self.container_id, ew)
                        except Exception:
                            pass

            except Exception as e:
                print(f"[ERROR] Beam tick failed: {e}")

            time.sleep(self.tick_rate)