import asyncio
import pytest

from backend.modules.photonlang.page_runner import PageRunner, CapsuleExecutionError


@pytest.mark.asyncio
async def test_page_runner_executes_each_line_round_robin():
    runner = PageRunner(max_lanes=2, timeout_sec=2.0)

    page = [
        "💡 = 🌊 ⊕ 🌊",
        "💡 = 🌊 ↔ 💡",
        "μ 💡",
    ]

    result = await runner.run_page(page)

    assert result["status"] == "ok"
    assert len(result["lanes"]) == 2
    assert result["executed_lines"] == 3
    assert result["fairness"]["rounds"] >= 2  # at least 2 scheduling passes


@pytest.mark.asyncio
async def test_page_runner_honors_timeout():
    runner = PageRunner(max_lanes=1, timeout_sec=0.01)

    # Force a sleep so it triggers timeout
    page = ["SLEEP 0.1"]

    result = await runner.run_page(page)

    assert result["status"] == "timeout"
    assert "cancelled" in result
    assert result["cancelled"] is True


@pytest.mark.asyncio
async def test_page_runner_captures_execution_error():
    runner = PageRunner(max_lanes=1, timeout_sec=2.0)

    # Something invalid in Photon grammar
    page = ["💡 = BAD_OP 123"]

    with pytest.raises(CapsuleExecutionError):
        await runner.run_page(page)


@pytest.mark.asyncio
async def test_page_runner_sqi_events_emitted(monkeypatch):
    runner = PageRunner(max_lanes=2, timeout_sec=2.0)

    emitted = []

    async def fake_emit(event):
        emitted.append(event)

    monkeypatch.setattr(
        "backend.modules.photonlang.telemetry.emit_sqi_event",
        fake_emit
    )

    page = [
        "💡 = 🌊 ⊕ 🌊",
        "μ 💡"
    ]

    result = await runner.run_page(page)

    assert result["status"] == "ok"
    assert len(emitted) >= 2

    # Basic structural properties
    assert all("lane" in e for e in emitted)
    assert all("sqi" in e for e in emitted)
    assert all("timestamp" in e for e in emitted)