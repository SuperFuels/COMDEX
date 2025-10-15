# -*- coding: utf-8 -*-
"""
🧠 GlyphWaveRuntime – High-Level Runtime for GWIP Routing + Adaptive CFE Feedback

Now includes:
    • Automatic CFEFeedbackLoop startup on initialization
    • Background async feedback coroutine
    • RuleManager (Codex) with SQI Drift integration
    • Graceful shutdown and loop stop handling
"""

import asyncio
from typing import Dict, Any, Optional

from .gwip_codec import GWIPCodec
from .scheduler import PhaseScheduler
from .carrier_memory import MemoryCarrier
from .wavescope import WaveScope

# Import TelemetryHandler directly (safe)
from backend.modules.glyphwave.telemetry_handler import TelemetryHandler

# ✅ Adaptive learning manager (Codex)
from backend.modules.codex.rule_manager import RuleManager


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

        # Feedback + adaptive components
        self.telemetry = TelemetryHandler()
        self.rule_manager = RuleManager()  # 🧩 Codex rule evolution controller

        # Async loop/task handles
        self._feedback_loop = None
        self._feedback_task: Optional[asyncio.Task] = None
        self._rule_task: Optional[asyncio.Task] = None
        self._loop_running = False

        if enable_feedback:
            try:
                self._init_feedback_loop()
                self._init_rule_manager()
            except Exception as e:
                print(f"[GlyphWaveRuntime] ⚠️ Feedback initialization failed: {e}")

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

    def _init_rule_manager(self):
        """Launch adaptive rule learning (SQI drift pull)."""
        try:
            loop = asyncio.get_event_loop()
            self._rule_task = loop.create_task(self.rule_manager.pull_sqi_drift())
            print("[GlyphWaveRuntime] 🔁 RuleManager SQI drift adaptation started.")
        except RuntimeError:
            print("[GlyphWaveRuntime] ⚠️ No active event loop for RuleManager drift polling.")

    async def _stop_feedback_loop(self):
        """Gracefully stop feedback loop and adaptive tasks if active."""
        if self._feedback_loop and self._loop_running:
            self._feedback_loop.stop()
            if self._feedback_task:
                self._feedback_task.cancel()
            self._loop_running = False
            print("[GlyphWaveRuntime] 🧠 CFE feedback loop stopped.")

        if self._rule_task:
            self._rule_task.cancel()
            print("[GlyphWaveRuntime] 🔁 RuleManager SQI drift polling stopped.")

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
            "rule_weights": getattr(self.rule_manager, "weights", {}),
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
        print("[GlyphWaveRuntime] 🧩 Runtime closed cleanly.")


# Compatibility alias for legacy imports
CodexRuntime = GlyphWaveRuntime