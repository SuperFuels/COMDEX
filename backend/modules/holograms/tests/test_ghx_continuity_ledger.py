import pytest
import json
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


@pytest.mark.asyncio
async def test_append_and_verify_chain():
    ledger = GHXContinuityLedger(node_id="TestNode")
    e1 = ledger.append_event("init", {"mode": "test"})
    e2 = ledger.append_event("heartbeat", {"coherence": 0.99})

    assert len(ledger.chain) == 2
    assert e2["prev_hash"] == e1["curr_hash"]
    assert ledger.verify_chain() is True


@pytest.mark.asyncio
async def test_tamper_detection_breaks_chain():
    ledger = GHXContinuityLedger()
    ledger.append_event("alpha")
    ledger.append_event("beta")
    ledger.chain[0]["meta"] = {"tampered": True}

    assert ledger.verify_chain() is False


@pytest.mark.asyncio
async def test_snapshot_and_restore_preserves_integrity():
    ledger = GHXContinuityLedger()
    ledger.append_event("phase_a", {"C": 0.8})
    snap = ledger.snapshot()

    new_ledger = GHXContinuityLedger()
    new_ledger.restore(snap)
    assert new_ledger.verify_chain() is True
    assert new_ledger.last_hash == ledger.last_hash
    assert new_ledger.chain[0]["event_type"] == "phase_a"