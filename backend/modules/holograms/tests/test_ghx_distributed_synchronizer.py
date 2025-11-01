"""
🧪 SRK-17 Task 5 - GHX Distributed Ledger Synchronizer (GHX-DLS)
Test Suite: backend/modules/holograms/tests/test_ghx_distributed_synchronizer.py

Validates:
    * Peer registration and broadcast simulation
    * Local bundle registration (chain hash continuity)
    * Distributed hash-chain integrity verification
"""

import pytest
import asyncio
import time
import hashlib
from backend.modules.holograms.ghx_distributed_synchronizer import GHXDistributedSynchronizer


@pytest.mark.asyncio
async def test_peer_registration_and_broadcast():
    """Ensure peers can be added and broadcast simulates correctly."""
    dls = GHXDistributedSynchronizer()
    dls.add_peer("node-A", "http://127.0.0.1:7001")
    dls.add_peer("node-B", "http://127.0.0.1:7002")

    assert len(dls.peers) == 2
    assert "node-A" in dls.peers

    fake_bundle = {"ghx_id": "GHX-001", "integrity": {"hash": "abc123"}}
    result = await dls.broadcast_bundle(fake_bundle)

    assert result["status"] == "broadcasted"
    assert set(result["recipients"]) == {"node-A", "node-B"}


@pytest.mark.asyncio
async def test_bundle_registration_and_chain_hash_continuity():
    """Validate that chain links form correct continuity between bundles."""
    dls = GHXDistributedSynchronizer()

    # Create two sequential bundles
    bundle1 = {"ghx_id": "GHX-101", "integrity": {"hash": hashlib.sha3_512(b"A").hexdigest()}}
    bundle2 = {"ghx_id": "GHX-102", "integrity": {"hash": hashlib.sha3_512(b"B").hexdigest()}}

    rec1 = await dls.register_bundle(bundle1)
    rec2 = await dls.register_bundle(bundle2)

    # Chain continuity: second record must reference first chain_hash
    assert rec2["prev_hash"] == rec1["chain_hash"]
    assert len(dls.chain) == 2

    # Verify internal chain linkage
    assert dls.chain[1]["prev_hash"] == dls.chain[0]["chain_hash"]


@pytest.mark.asyncio
async def test_chain_integrity_verification_valid():
    """Ensure a valid chain passes integrity verification."""
    dls = GHXDistributedSynchronizer()

    for i in range(3):
        bundle = {"ghx_id": f"GHX-{i}", "integrity": {"hash": hashlib.sha3_512(f"B{i}".encode()).hexdigest()}}
        await dls.register_bundle(bundle)

    result = await dls.verify_chain_integrity()
    assert result["valid"] is True
    assert result["entries"] == 3
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_chain_integrity_verification_detects_tampering():
    """Deliberately break continuity and verify detection."""
    dls = GHXDistributedSynchronizer()

    for i in range(3):
        bundle = {"ghx_id": f"GHX-{i}", "integrity": {"hash": hashlib.sha3_512(f"C{i}".encode()).hexdigest()}}
        await dls.register_bundle(bundle)

    # Tamper with the second link
    dls.chain[1]["prev_hash"] = "tampered-hash"

    result = await dls.verify_chain_integrity()
    assert result["valid"] is False
    assert len(result["errors"]) > 0