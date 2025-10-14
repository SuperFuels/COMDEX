import pytest
from backend.modules.holograms.ghx_continuity_hooks import GHXContinuityHooks


@pytest.mark.asyncio
async def test_heartbeat_creates_ledger_entry():
    hooks = GHXContinuityHooks()
    hb = await hooks.heartbeat(interval=0)
    assert "integrity_score" in hb
    assert len(hooks.ledger.chain) >= 1
    assert hooks.ledger.chain[-1]["event_type"] == "heartbeat"


@pytest.mark.asyncio
async def test_auto_realign_appends_to_ledger():
    hooks = GHXContinuityHooks()
    replay = await hooks.auto_realign()
    last_event = hooks.ledger.chain[-1]
    assert last_event["event_type"] == "auto_realign"
    assert "curr_hash" in last_event


@pytest.mark.asyncio
async def test_continuity_report_contains_snapshot():
    hooks = GHXContinuityHooks()
    await hooks.heartbeat(interval=0)
    report = await hooks.continuity_report()
    assert "ledger" in report
    assert report["ledger"]["verified"] is True