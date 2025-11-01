"""
🧪 SRK-17 Task 7 - GHX Continuity Hooks (GCH)
Test Suite: backend/modules/holograms/tests/test_ghx_continuity_hooks.py
"""

import pytest
import asyncio
import hashlib
from backend.modules.holograms.ghx_continuity_hooks import GHXContinuityHooks


@pytest.mark.asyncio
async def test_heartbeat_emits_integrity_ping():
    """Verify heartbeat produces continuity ping and score."""
    gch = GHXContinuityHooks()
    hb = await gch.heartbeat(interval=0.01)
    assert "integrity_score" in hb
    assert hb["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_auto_realign_triggers_replay():
    """Ensure auto-realign calls VaultExporter.replay_from_vault."""
    gch = GHXContinuityHooks()
    # Create dummy export snapshot
    chain = [{"chain_hash": hashlib.sha3_512(b"T").hexdigest()}]
    await gch.vault_exporter.export_chain_snapshot(chain)

    replay = await gch.auto_realign()
    assert replay["verified"] is True
    assert "restored_head" in replay


@pytest.mark.asyncio
async def test_verify_continuity_detects_mismatch():
    """Ensure integrity mismatch is detected."""
    gch = GHXContinuityHooks()
    chain = [{"chain_hash": hashlib.sha3_512(b"A").hexdigest()}]
    await gch.vault_exporter.export_chain_snapshot(chain)

    # Tamper with integrity
    gch.vault_exporter._last_export["integrity"] = "DEADBEAF"
    score = await gch._verify_continuity()
    assert score == 0.0