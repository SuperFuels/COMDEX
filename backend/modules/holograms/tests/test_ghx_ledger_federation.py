"""
🧪 SRK-18 Task 18.4 - GHX Ledger Federation Tests
Verifies peer registration, event propagation, merge reconciliation, and federation integrity.
"""

from backend.modules.holograms.ghx_ledger_federation import GHXLedgerFederation
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger


def test_peer_registration_and_event_broadcast():
    node_a = GHXLedgerFederation("A")
    node_b = GHXLedgerFederation("B")

    node_a.register_peer("B", node_b.local_ledger)
    node_b.register_peer("A", node_a.local_ledger)

    event = node_a.broadcast_event("heartbeat", {"ok": True})
    assert event["event_type"] == "heartbeat"
    assert len(node_a.local_ledger.chain) == 1
    assert len(node_b.local_ledger.chain) == 1


def test_merge_ledgers_synchronizes_missing_entries():
    a = GHXLedgerFederation("A")
    b = GHXLedgerFederation("B")

    a.register_peer("B", b.local_ledger)
    b.register_peer("A", a.local_ledger)

    a.broadcast_event("alpha", {"x": 1})
    b.broadcast_event("beta", {"y": 2})

    merge_result = a.merge_ledgers()
    assert merge_result["merged"] is True
    assert len(a.local_ledger.chain) == 2


def test_verify_federation_integrity_consistent_roots():
    a = GHXLedgerFederation("A")
    b = GHXLedgerFederation("B")

    a.register_peer("B", b.local_ledger)
    b.register_peer("A", a.local_ledger)

    a.broadcast_event("pulse", {"freq": 3.5})
    b.merge_ledgers()
    a.merge_ledgers()

    result = a.verify_federation_integrity()
    assert result["consistent"] is True
    assert a.local_ledger.last_hash in result["root_hashes"].values()