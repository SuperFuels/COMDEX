# ===============================
# 📁 backend/quant/ghx/ghx_feedback_bridge.py
# ===============================
"""
🌈 GHX Feedback Bridge - Real-Time Coherence Telemetry Relay
------------------------------------------------------------
Connects CFE feedback + GlyphWave runtime metrics to the GHX/QFC visualization stack.

Integrated with:
    * ResonanceTelemetry (ΔΦ, Δε, μ, κ)
    * QCompilerCore (simulation graph outputs)
    * GHXVisualizer (if live UI present)

Features:
    * Subscribes to adaptive parameter updates from CFEFeedbackLoop
    * Streams live coherence / collapse / decoherence data to GHX/QFC renderers
    * Provides async broadcast hook for WebSocket, CodexHUD, or local debug console
"""
import inspect  
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Callable
from backend.modules.visualization.ghx_ws_server import broadcast
logger = logging.getLogger(__name__)


class GHXFeedbackBridge:
    """Live telemetry bridge between CFE feedback and visualization subsystems."""

    def __init__(
        self,
        send_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        websocket=None,
    ):
        """
        Args:
            send_callback: Optional callable for sending packets (e.g. GHX emitter)
            websocket: Optional async WebSocket for CodexHUD broadcast
        """
        self.websocket = websocket
        self.send_callback = send_callback
        self.last_packet: Optional[Dict[str, Any]] = None
        self._running = False

    # ------------------------------------------------------------------
    async def emit(self, feedback: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """
        Combine feedback + runtime metrics and push to GHX/QFC layers.
        Handles both async and sync callbacks.
        """
        packet = {
            "timestamp": time.time(),
            "type": "ghx_feedback_update",
            "feedback": feedback,
            "metrics": metrics,
        }
        self.last_packet = packet

        # Option 1: WebSocket broadcast
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(packet))
            except Exception as e:
                print(f"[GHXFeedbackBridge] WebSocket error: {e}")

        # Option 2: Callback (can be async or sync)
        if self.send_callback:
            try:
                if inspect.iscoroutinefunction(self.send_callback):
                    await self.send_callback(packet)
                else:
                    self.send_callback(packet)
            except Exception as e:
                print(f"[GHXFeedbackBridge] Callback error: {e}")

        # Option 3: WebSocket broadcast via GHX WS server
        try:
            await broadcast(packet)
        except Exception as e:
            print(f"[GHXFeedbackBridge] Broadcast error: {e}")

    # ------------------------------------------------------------------
    async def live_monitor(
        self,
        runtime,
        interval: float = 1.0,
        max_samples: int = 0,
    ):
        """
        Periodically poll GlyphWaveRuntime + CFE feedback for visualization updates.

        Args:
            runtime: GlyphWaveRuntime-like instance providing metrics() + parameters
            interval: polling interval (seconds)
            max_samples: optional stop condition (0 = infinite)
        """
        self._running = True
        count = 0
        logger.info(f"[GHXFeedbackBridge] 🌀 Live telemetry relay active @ {interval}s")

        while self._running:
            try:
                metrics = runtime.metrics() if hasattr(runtime, "metrics") else {}
                feedback = getattr(runtime, "parameters", {})
                await self.emit(feedback, metrics)
            except Exception as e:
                logger.exception(f"[GHXFeedbackBridge] Error: {e}")

            count += 1
            if max_samples and count >= max_samples:
                break
            await asyncio.sleep(interval)

        self._running = False
        logger.info("[GHXFeedbackBridge] 🌀 Relay stopped.")

    # ------------------------------------------------------------------
    def stop(self):
        """Stop live monitor loop."""
        self._running = False
        logger.info("[GHXFeedbackBridge] Relay manually stopped.")

    # ------------------------------------------------------------------
    def emit_sync(self, feedback: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous emission for non-async contexts (used in tests or QSheets runs).
        """
        packet = {
            "timestamp": time.time(),
            "type": "ghx_feedback_update",
            "feedback": feedback,
            "metrics": metrics,
        }
        self.last_packet = packet
        if self.send_callback:
            try:
                self.send_callback(packet)
            except Exception as e:
                logger.warning(f"[GHXFeedbackBridge] Callback error (sync): {e}")
        return packet