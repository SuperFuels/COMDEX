"""
🧪 SRK-17 Task 6 - GHX Vault Exporter (GVE)
Test Suite: backend/modules/holograms/tests/test_ghx_vault_exporter.py

Validates:
    * GHX chain archival to GlyphVault
    * Metadata integrity and continuity tracking
    * Replay restoration logic
"""

import pytest
import asyncio
import hashlib
from backend.modules.holograms.ghx_vault_exporter import GHXVaultExporter


@pytest.mark.asyncio
async def test_export_chain_snapshot_and_integrity():
    """Ensure GHX chain snapshot is exported with correct integrity metadata."""
    gve = GHXVaultExporter()

    chain = [
        {"chain_hash": hashlib.sha3_512(b"A").hexdigest()},
        {"chain_hash": hashlib.sha3_512(b"B").hexdigest()},
        {"chain_hash": hashlib.sha3_512(b"C").hexdigest()},
    ]

    snapshot = await gve.export_chain_snapshot(chain)

    assert "export_id" in snapshot
    assert snapshot["chain_length"] == 3
    assert snapshot["chain_head"] == chain[-1]["chain_hash"]
    assert "integrity" in snapshot


@pytest.mark.asyncio
async def test_replay_from_vault_restores_continuity():
    """Simulate replay after export and verify continuity restoration."""
    gve = GHXVaultExporter()
    chain = [{"chain_hash": hashlib.sha3_512(b"X").hexdigest()}]
    await gve.export_chain_snapshot(chain)

    replay_meta = await gve.replay_from_vault()
    assert replay_meta["verified"] is True
    assert "restored_head" in replay_meta
    assert replay_meta["restored_length"] == 1


@pytest.mark.asyncio
async def test_export_raises_on_empty_chain():
    """Empty chain exports must raise ValueError."""
    gve = GHXVaultExporter()
    with pytest.raises(ValueError):
        await gve.export_chain_snapshot([])