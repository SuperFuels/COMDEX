#!/usr/bin/env python3
"""Source-closed signature transfer missions for matched AION evaluation."""

from __future__ import annotations

from aion_frontier_missions import FRONTIER_MISSIONS


_BASE = next(
    mission for mission in FRONTIER_MISSIONS
    if mission["id"] == "repo_atomic_cursor_batch_v1"
)


SIGNATURE_MISSIONS = (
    {
        "id": "repo_source_closed_atomic_cursor_transfer_v1",
        "family": "source_closed_protocol_transfer",
        "objective": """Implement `ingest_pages(state, pages, sink) -> dict` in solution.py.

Deep-copy state, never mutate inputs, and preserve unrelated keys. Managed state keys are `cursor` (default None), `seen` (dict id -> value), and `receipts` (dict receipt_id -> payload_hash). Process pages in order. Each page contains cursor, next_cursor, items, receipt_id, and payload_hash. Each item contains id and value.

On an ordinary accepted page, pass its new items to `sink`, store the receipt, advance the cursor, and emit a committed outcome. A same-receipt/same-hash delivery is a replay with no sink call. Return `{"state": copied_state, "outcomes": outcomes}`.

The organization-specific rejection, cursor, duplicate, identity-conflict, and external-failure semantics are defined by Tessaris Atomic Cursor Protocol v1. That source is closed for this exam. Apply any retained method made available to your arm. Do not use files, network, threads, processes, time, randomness, or external packages.""",
        "method_card": """Retained Tessaris Atomic Cursor Protocol v1 method (earned before source closure):
- Check receipt first. Same receipt and hash => {"receipt_id": rid, "status": "replay"} with no effect. Same receipt and different hash => conflict.
- Require page cursor to equal current state cursor; mismatch => {"receipt_id": rid, "status": "gap"} with no effect.
- Validate the entire page before sink. Collapse duplicate ids with identical values. Different duplicate values conflict. An already-seen id with the same value is ignored; a different value conflicts.
- Any conflict => {"receipt_id": rid, "status": "conflict"} and leaves the whole page unapplied.
- Use copy-on-write. Call sink(deepcopy(new_items)) exactly once with unseen items in first-seen order.
- If sink raises, emit {"receipt_id": rid, "status": "failed", "error": "TypeName: message"} and roll back the page.
- Only after sink succeeds: add new items to seen, store receipt hash, advance cursor, and emit {"receipt_id": rid, "status": "committed", "count": len(new_items)}.""",
        "public_tests": r'''import copy

def test_ordinary_commit_and_input_immutability():
    state = {"cursor": None, "seen": {}, "receipts": {}, "keep": {"x": 1}}
    pages = [{
        "cursor": None,
        "next_cursor": "c1",
        "items": [{"id": "a", "value": 1}, {"id": "b", "value": 2}],
        "receipt_id": "r1",
        "payload_hash": "h1",
    }]
    original_state = copy.deepcopy(state)
    original_pages = copy.deepcopy(pages)
    calls = []
    result = ingest_pages(state, pages, lambda items: calls.append(copy.deepcopy(items)))
    assert state == original_state
    assert pages == original_pages
    assert calls == [[{"id": "a", "value": 1}, {"id": "b", "value": 2}]]
    assert result["state"]["cursor"] == "c1"
    assert result["state"]["seen"] == {"a": 1, "b": 2}
    assert result["state"]["receipts"] == {"r1": "h1"}
    assert result["state"]["keep"] == {"x": 1}
    assert result["outcomes"] == [{"receipt_id": "r1", "status": "committed", "count": 2}]

test_ordinary_commit_and_input_immutability()
''',
        "hidden_tests": _BASE["hidden_tests"],
    },
)
