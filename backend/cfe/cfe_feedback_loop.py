"""
🧠 CFE Feedback Loop — Step 1
Integrates CodexLang runtime with QWave telemetry.

Monitors:
  • collapse_rate
  • decoherence_rate
  • coherence_stability (SQI)

Feeds telemetry back into the CodexLang reasoning model to
adapt symbolic temperature, exploration depth, and resonance gain.
"""

import asyncio
import time
from typing import Dict, Any

# --- Flexible import layer for production + test ---
try:
    from backend.modules.glyphwave.runtime import CodexRuntime
    from backend.modules.qwave.telemetry_handler import TelemetryHandler
except ModuleNotFoundError:
    # fallback for test/local environments
    try:
        from modules.glyphwave.runtime import CodexRuntime
        from modules.qwave.telemetry_handler import TelemetryHandler
    except ModuleNotFoundError:
        # lightweight mocks for CI/test environments
        class CodexRuntime:
            def update_parameters(self, feedback):
                print(f"[Mock CodexRuntime] params → {feedback}")

        class TelemetryHandler:
            async def collect_metrics(self):
                return {
                    "collapse_rate": 0.12,
                    "decoherence_rate": 0.08,
                    "coherence_stability": 0.75,
                }
# ----------------------------------------------------


class CFEFeedbackLoop:
    """Closed-loop feedback system between CodexLang and QWave telemetry."""

    def __init__(self, codex_runtime: CodexRuntime, telemetry: TelemetryHandler):
        self.codex_runtime = codex_runtime
        self.telemetry = telemetry
        self.last_feedback: Dict[str, Any] = {}
        self._running = False

    async def _compute_feedback(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Derive adaptive runtime parameters from QWave metrics."""
        collapse = metrics.get("collapse_rate", 0.0)
        decohere = metrics.get("decoherence_rate", 0.0)
        stability = metrics.get("coherence_stability", 1.0)

        # symbolic modulation laws
        temperature = max(0.1, 1.0 - stability)
        resonance_gain = 1.0 / (1.0 + collapse + decohere)
        reasoning_depth = int(3 + 5 * stability)

        return {
            "symbolic_temperature": round(temperature, 3),
            "resonance_gain": round(resonance_gain, 3),
            "reasoning_depth": reasoning_depth,
        }

    async def tick(self):
        """Perform one feedback iteration."""
        metrics = await self.telemetry.collect_metrics()
        feedback = await self._compute_feedback(metrics)
        self.codex_runtime.update_parameters(feedback)
        self.last_feedback = feedback
        return feedback

    async def run(self, interval: float = 1.0):
        """Continuously run the feedback loop."""
        self._running = True
        print(f"[CFE] Feedback loop active @ {interval}s interval")
        while self._running:
            try:
                fb = await self.tick()
                print(f"[CFE] feedback → {fb}")
            except Exception as e:
                print(f"[CFE] Error: {e}")
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False
        print("[CFE] Feedback loop stopped")