import json
import pytest
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger
from backend.modules.holograms.ghx_ledger_auditor import GHXLedgerAuditor


def test_verify_valid_snapshot():
    ledger = GHXContinuityLedger("Auditor.Node")
    ledger.append_event("alpha", {"x": 1})
    ledger.append_event("beta", {"y": 2})
    snap = ledger.snapshot()

    result = GHXLedgerAuditor.verify_snapshot(snap)
    assert result["verified"] is True
    assert result["count"] == 2


def test_detect_tampered_hash():
    ledger = GHXContinuityLedger("Tamper.Node")
    ledger.append_event("alpha", {"x": 1})
    snap = ledger.snapshot()
    snap["chain"][0]["meta"]["x"] = 999  # tamper data

    result = GHXLedgerAuditor.verify_snapshot(snap)
    assert result["verified"] is False
    assert result["error"] == "hash_mismatch"


def test_replay_snapshot_verifies_chain():
    ledger = GHXContinuityLedger("Replay.Node")
    ledger.append_event("one", {})
    ledger.append_event("two", {})
    snap = ledger.snapshot()

    result = GHXLedgerAuditor.replay(snap)
    assert result["verified"] is True
    assert result["count"] == 2


def test_diff_detects_divergence():
    a = GHXContinuityLedger("A"); a.append_event("alpha", {})
    b = GHXContinuityLedger("B"); b.append_event("beta", {}); b.append_event("gamma", {})

    diff = GHXLedgerAuditor.diff(a.snapshot(), b.snapshot())
    assert diff["diverged"] is True
    assert diff["delta"] == 1


def test_report_returns_json_summary():
    ledger = GHXContinuityLedger("Report.Node")
    ledger.append_event("alpha", {})
    snap = ledger.snapshot()

    report_str = GHXLedgerAuditor.report(snap)
    data = json.loads(report_str)
    assert data["verified"] is True
    assert data["length"] == 1