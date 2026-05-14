"""
🧩 Test - CFE Feedback Loop
Verifies CodexLang-QWave integration and adaptive modulation logic.
"""

import asyncio
import pytest

from backend.cfe.cfe_feedback_loop import CFEFeedbackLoop


class MockCodexRuntime:
    """Mock CodexLang runtime to capture parameter updates."""
    def __init__(self):
        self.parameters = {}

    def update_parameters(self, feedback):
        self.parameters.update(feedback)


class MockTelemetryHandler:
    """Mock QWave telemetry generator for testing."""
    async def collect_metrics(self):
        return {
            "collapse_rate": 0.12,
            "decoherence_rate": 0.08,
            "coherence_stability": 0.75,
        }


@pytest.mark.asyncio
async def test_cfe_feedback_computation():
    """Ensure feedback parameters scale correctly with metrics."""
    runtime = MockCodexRuntime()
    telemetry = MockTelemetryHandler()
    cfe = CFEFeedbackLoop(runtime, telemetry)

    feedback = await cfe.tick()

    assert "symbolic_temperature" in feedback
    assert "resonance_gain" in feedback
    assert "reasoning_depth" in feedback

    # Check parameter relationships
    assert 0.1 <= feedback["symbolic_temperature"] <= 1.0
    assert feedback["resonance_gain"] > 0.0
    assert isinstance(feedback["reasoning_depth"], int)

    # Ensure runtime received update
    assert runtime.parameters == feedback


@pytest.mark.asyncio
async def test_cfe_feedback_loop_runs_multiple_ticks():
    """Confirm continuous feedback loop updates parameters."""
    runtime = MockCodexRuntime()
    telemetry = MockTelemetryHandler()
    cfe = CFEFeedbackLoop(runtime, telemetry)

    async def run_short():
        await asyncio.wait_for(cfe.tick(), timeout=1.0)
        await asyncio.wait_for(cfe.tick(), timeout=1.0)

    await run_short()

    assert "symbolic_temperature" in runtime.parameters
    assert runtime.parameters["reasoning_depth"] >= 3