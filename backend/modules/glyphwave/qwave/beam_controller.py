import time
import threading

from backend.modules.glyphwave.core.wave_state import WaveState, ENTANGLED_WAVE_STORE
from backend.modules.sqi.metrics.collapse_timeline_writer import log_collapse_tick
from backend.modules.sqi.sqi_scorer import score_all_electrons
from backend.modules.websocket_manager import broadcast_event

# ✅ New QFC WebSocket stream helper
from backend.modules.visualization.stream_qfc_from_entangled_wave import stream_qfc_from_entangled_wave
from backend.modules.visualization.qfc_payload_utils import to_qfc_payload
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update
import asyncio


class BeamController:
    def __init__(self, config=None):
        config = config or {}

        self.tick_rate = config.get("tick_rate", 1.0)
        self.enable_sqi = config.get("enable_sqi", True)
        self.enable_logging = config.get("enable_logging", True)
        self.enable_replay = config.get("enable_replay", False)
        self.test_mode = config.get("test_mode", False)
        self.container_id = config.get("container_id", "unknown.dc")
        self.enable_telemetry = config.get("enable_telemetry", False)
        self.enable_hud = config.get("enable_hud", False)
        self.enable_qfc_stream = config.get("enable_qfc_stream", True)

        self._running = False
        self._tick_count = 0
        self._collapse_rate_history = []

    def _log_hud_overlay(self, wave_state):
        print(f"[HUD] BeamTick {self._tick_count} | SQI: {wave_state.last_sqi_score:.2f}")

    def _record_telemetry(self, tick_duration_ms):
        self._collapse_rate_history.append(tick_duration_ms)
        if len(self._collapse_rate_history) > 100:
            self._collapse_rate_history.pop(0)

    def run_tick_loop(self):
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
                            "tick_duration_ms": (time.time() - tick_start) * 1000,
                            "tick_index": self._tick_count
                        }
                    )

                if self.enable_hud:
                    self._log_hud_overlay(wave_state)

                if self.enable_replay:
                    wave_state.export_replay_snapshot()

                if self.enable_telemetry:
                    self._record_telemetry((time.time() - tick_start) * 1000)

                # ✅ Primary: Stream entangled wave to QFC
                if self.enable_qfc_stream:
                    ew = ENTANGLED_WAVE_STORE.get(self.container_id)
                    if ew:
                        try:
                            stream_qfc_from_entangled_wave(self.container_id, ew)
                        except Exception as stream_err:
                            print(f"[⚠️ QFC] Failed to stream from entangled wave: {stream_err}")
                    else:
                        # 🔁 Fallback: Stream from WaveState directly
                        try:
                            node_payload = {
                                "glyph": "🌀",
                                "op": "beam_tick",
                                "metadata": {
                                    "tick": self._tick_count,
                                    "sqi_score": wave_state.last_sqi_score,
                                    "entropy": wave_state.entropy if hasattr(wave_state, "entropy") else None,
                                    "coherence": wave_state.coherence
                                }
                            }
                            context = {
                                "container_id": self.container_id,
                                "source_node": wave_state.id
                            }
                            qfc_payload = to_qfc_payload(node_payload, context)
                            asyncio.create_task(broadcast_qfc_update(self.container_id, qfc_payload))
                        except Exception as qfc_fallback_err:
                            print(f"[⚠️ QFC Fallback] Failed to stream from WaveState: {qfc_fallback_err}")

                # ✅ WebSocket HUD (test only)
                if self.test_mode:
                    hud_payload = {
                        "type": "beam_hud_update",
                        "data": {
                            "tick_duration_ms": (time.time() - tick_start) * 1000,
                            "container_id": self.container_id,
                            "last_sqi_score": getattr(wave_state, "last_sqi_score", None),
                            "beam_enabled": True,
                            "replay_enabled": self.enable_replay
                        }
                    }
                    broadcast_event(hud_payload)

                    print(
                        f"[DEBUG] Tick {self._tick_count} | SQI: {wave_state.last_sqi_score:.3f} "
                        f"| Duration: {(time.time() - tick_start) * 1000:.2f}ms"
                    )

            except Exception as e:
                print(f"[ERROR] Beam tick failed at tick {self._tick_count}: {str(e)}")

            time.sleep(self.tick_rate)

    def start(self, threaded=False):
        print(f"[BEAM MODE] Starting beam loop{' in thread' if threaded else ''} for: {self.container_id}")
        if threaded:
            thread = threading.Thread(target=self.run_tick_loop, daemon=True)
            thread.start()
        else:
            self.run_tick_loop()

    def stop(self):
        print(f"[BEAM MODE] Stopping beam loop for: {self.container_id}")
        self._running = False