"""
🧪 SRK-18 Task 18.3 — GHX Continuity Ledger Integrity Tests
Covers: hash-link verification, signature validation, tamper detection, and snapshot restore.
"""

import json
import os
import pytest
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


@pytest.mark.asyncio
async def test_append_and_verify_chain_integrity(tmp_path):
    """Ensure normal append operations create a valid, verified chain."""
    ledger = GHXContinuityLedger(node_id="Tessaris.Node.Test")
    ledger.append_event("startup", {"status": "ok"})
    ledger.append_event("heartbeat", {"integrity": 0.99})
    ledger.append_event("sync", {"phase": "active"})

    result = ledger.verify_chain()
    assert result["verified"] is True
    assert result["count"] == 3

    # export + reload chain snapshot
    export_path = tmp_path / "ledger_snapshot.json"
    ledger.export_chain(str(export_path))
    restored = GHXContinuityLedger.load_chain(str(export_path))
    assert restored.verify_chain()["verified"] is True
    assert len(restored.chain) == 3


def test_detects_hash_tampering():
    """Tampering with meta or curr_hash should break integrity check."""
    ledger = GHXContinuityLedger()
    ledger.append_event("ping", {"ok": True})
    ledger.append_event("pong", {"ok": True})

    # Corrupt a meta field
    ledger.chain[1]["meta"]["ok"] = False
    result = ledger.verify_chain()
    assert result["verified"] is False
    assert result["error"] == "hash_mismatch"


def test_detects_broken_linkage():
    """A mismatched prev_hash must invalidate the chain."""
    ledger = GHXContinuityLedger()
    ledger.append_event("alpha", {"x": 1})
    ledger.append_event("beta", {"y": 2})

    ledger.chain[1]["prev_hash"] = "deadbeef"  # break link intentionally
    result = ledger.verify_chain()
    assert result["verified"] is False
    # since changing prev_hash alters the hash, it’s detected as hash_mismatch first
    assert result["error"] in ("link_broken", "hash_mismatch")

def test_detects_signature_tampering():
    """A forged or altered signature must invalidate verification."""
    ledger = GHXContinuityLedger()
    ledger.append_event("sigtest", {"phase": 1})
    ledger.append_event("sigtest2", {"phase": 2})

    ledger.chain[1]["signature"] = "tampered-signature"
    result = ledger.verify_chain()
    assert result["verified"] is False
    assert result["error"] == "bad_signature"


def test_snapshot_restore_preserves_verification():
    """Snapshot and restore cycle preserves verified state."""
    ledger = GHXContinuityLedger(node_id="Tessaris.Node.Restore")
    ledger.append_event("a", {"k": 1})
    ledger.append_event("b", {"k": 2})
    snap = ledger.snapshot()

    new_ledger = GHXContinuityLedger()
    new_ledger.restore(snap)
    v = new_ledger.verify_chain()
    assert v["verified"] is True
    assert v["count"] == 2