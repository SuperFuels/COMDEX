"""
🌈 GHX Feedback Bridge — Real-Time Coherence Telemetry Relay
-----------------------------------------------------------
Connects CFE feedback + GlyphWave runtime metrics to the GHX/QFC visualization stack.

Features:
    • Subscribes to adaptive parameter updates from CFEFeedbackLoop
    • Streams live coherence / collapse / decoherence data to GHX/QFC renderers
    • Provides async broadcast hook for WebSocket, CodexHUD, or local debug console
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable


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

    async def emit(self, feedback: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """
        Combine feedback + runtime metrics and push to GHX/QFC layers.

        Args:
            feedback: Dict of CFE adaptive parameters
            metrics: Dict of runtime + telemetry values
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

        # Option 2: Direct callback (e.g. GHXVisualizer)
        if self.send_callback:
            try:
                self.send_callback(packet)
            except Exception as e:
                print(f"[GHXFeedbackBridge] Callback error: {e}")

    async def live_monitor(
        self,
        runtime,
        interval: float = 1.0,
        max_samples: int = 0,
    ):
        """
        Periodically poll GlyphWaveRuntime + CFE feedback for visualization updates.

        Args:
            runtime: GlyphWaveRuntime instance
            interval: polling interval (seconds)
            max_samples: optional stop condition (0 = infinite)
        """
        self._running = True
        count = 0
        print(f"[GHXFeedbackBridge] 🌀 Live telemetry relay active @ {interval}s")

        while self._running:
            try:
                metrics = runtime.metrics()
                feedback = getattr(runtime, "parameters", {})
                await self.emit(feedback, metrics)
            except Exception as e:
                print(f"[GHXFeedbackBridge] Error: {e}")

            count += 1
            if max_samples and count >= max_samples:
                break

            await asyncio.sleep(interval)

        self._running = False
        print("[GHXFeedbackBridge] 🌀 Relay stopped.")

    def stop(self):
        """Stop live monitor loop."""
        self._running = False