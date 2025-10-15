"""
🧠 GlyphWaveRuntime – High-Level Runtime for GWIP Routing + Adaptive CFE Feedback

Now includes:
    • Automatic CFEFeedbackLoop startup on initialization
    • Background async feedback coroutine
    • Graceful shutdown and loop stop handling
"""

import asyncio
from typing import Dict, Any, Optional

from .gwip_codec import GWIPCodec
from .scheduler import PhaseScheduler
from .carrier_memory import MemoryCarrier
from .wavescope import WaveScope

# Import TelemetryHandler directly (safe)
from backend.modules.qwave.telemetry_handler import TelemetryHandler


class GlyphWaveRuntime:
    def __init__(
        self,
        carrier: Optional[Any] = None,
        codec: Optional[GWIPCodec] = None,
        scheduler: Optional[PhaseScheduler] = None,
        scope: Optional[WaveScope] = None,
        enable_feedback: bool = True,
    ):
        self.codec = codec or GWIPCodec()
        self.scheduler = scheduler or PhaseScheduler()
        self.carrier = carrier or MemoryCarrier()
        self.scope = scope or WaveScope()
        self.parameters: Dict[str, Any] = {}

        # Feedback loop components
        self.telemetry = TelemetryHandler()
        self._feedback_loop = None
        self._feedback_task: Optional[asyncio.Task] = None
        self._loop_running = False

        if enable_feedback:
            try:
                self._init_feedback_loop()
            except Exception as e:
                print(f"[GlyphWaveRuntime] ⚠️ Feedback loop initialization failed: {e}")

    # ===============================================================
    # Feedback loop initialization (lazy import to avoid circulars)
    # ===============================================================
    def _init_feedback_loop(self):
        """Initialize and asynchronously launch the feedback loop."""
        try:
            # Lazy import — avoids circular dependency on import
            from backend.cfe.cfe_feedback_loop import CFEFeedbackLoop

            self._feedback_loop = CFEFeedbackLoop(codex_runtime=self, telemetry=self.telemetry)
            loop = asyncio.get_event_loop()
            self._feedback_task = loop.create_task(self._feedback_loop.run(interval=1.0))
            self._loop_running = True
            print("[GlyphWaveRuntime] 🧠 CFE feedback loop started.")
        except RuntimeError:
            # Happens if no asyncio loop is active
            print("[GlyphWaveRuntime] No active asyncio loop; feedback deferred.")
        except ImportError as e:
            print(f"[GlyphWaveRuntime] ⚠️ Import error: {e}")

    async def _stop_feedback_loop(self):
        """Gracefully stop feedback loop if active."""
        if self._feedback_loop and self._loop_running:
            self._feedback_loop.stop()
            if self._feedback_task:
                self._feedback_task.cancel()
            self._loop_running = False
            print("[GlyphWaveRuntime] 🧠 CFE feedback loop stopped.")

    # ===============================================================
    # Core Send / Receive
    # ===============================================================
    def send(self, gip_packet: Dict[str, Any]) -> None:
        upgraded = self.codec.upgrade(gip_packet)
        shaped = self.scheduler.schedule(upgraded)
        self.carrier.emit(shaped)
        self.scope.log_beam_event(
            event="emitted",
            signal_power=shaped["envelope"].get("freq", 1.0),
            noise_power=0.0001,
            kind="gwip",
            tags=shaped["envelope"].get("tags", []),
            container_id=gip_packet.get("container_id"),
        )

    def recv(self) -> Optional[Dict[str, Any]]:
        gwip = self.carrier.capture()
        if not gwip:
            return None
        gip = self.codec.downgrade(gwip)
        self.scope.log_beam_event(
            event="received",
            signal_power=gwip["envelope"].get("freq", 1.0),
            noise_power=0.0001,
            kind="gwip",
            tags=gwip["envelope"].get("tags", []),
            container_id=gip.get("container_id"),
        )
        return gip

    # ===============================================================
    # Runtime Metrics / Telemetry
    # ===============================================================
    def metrics(self) -> Dict[str, Any]:
        return {
            "scheduler": self.scheduler.metrics(),
            "carrier": self.carrier.stats(),
            "throughput": self.scope.track_throughput(),
            "adaptive_parameters": self.parameters,
        }

    def recent_logs(self, limit: int = 100) -> Any:
        return self.scope.recent(limit)

    # ===============================================================
    # Adaptive Runtime Parameter Interface (for CFE Feedback Loop)
    # ===============================================================
    def update_parameters(self, params: Dict[str, Any]) -> None:
        self.parameters.update(params)
        print(f"[GlyphWaveRuntime] Adaptive parameters updated → {params}")

    # ===============================================================
    # Lifecycle Management
    # ===============================================================
    async def close(self) -> None:
        """Cleanly shut down carrier, scope, and feedback loop."""
        await self._stop_feedback_loop()
        self.carrier.close()
        self.scope.reset()


# Compatibility alias for legacy imports
CodexRuntime = GlyphWaveRuntime