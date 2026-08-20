"""Hard sealed repository missions for the AION matched-arm evaluation.

These missions deliberately combine state machines, idempotency, atomicity,
external side effects and retry semantics.  Public tests expose the interface;
hidden tests score the failure boundaries that distinguish a robust retained
method from a plausible first-pass implementation.
"""

FRONTIER_MISSIONS = (
    {
        "id": "repo_fenced_lease_executor_v1",
        "family": "concurrent_reservation",
        "objective": """Implement `run_jobs(state, jobs, worker, now, lease_seconds) -> dict` in solution.py.

The function must deep-copy `state`, never mutate any input, preserve unrelated state keys, and manage `state["jobs"]` as a mapping keyed by request id. Each request contains `id`, `payload`, `payload_hash`, and `owner`.

For each request, in order:
- If an existing record has a different payload_hash, emit `{"id": id, "status": "conflict"}`; do not call worker and do not alter that record.
- If an existing same-hash record is done, emit `{"id": id, "status": "replay", "result": existing_result}`; do not call worker or alter it.
- If an existing same-hash record is running with `lease_until > now`, emit `{"id": id, "status": "busy"}`; do not call worker or alter it.
- Otherwise acquire/reacquire it. generation and attempt are each the previous value + 1, or 1 for a new job. Before calling worker, store a running record with exactly these keys: payload_hash, status, owner, lease_until, generation, attempt, result, error. Set lease_until to now + lease_seconds, result/error to None.
- Call `worker(deepcopy(payload), generation)`. It returns a dict containing `generation` and `result`.
- If worker raises, leave the record retryable with status pending, lease_until/result None, error `TypeName: message`; emit `{"id": id, "status": "failed", "error": error}`.
- If the returned generation is not the acquired generation, leave it pending with error `stale_generation`, lease_until/result None; emit `{"id": id, "status": "stale_result"}`.
- Otherwise commit status done, result to the returned result, error/lease_until None; emit `{"id": id, "status": "committed", "result": result}`.

Return `{"state": copied_state, "outcomes": outcomes}`. Do not use threads, processes, files, network, time, randomness, or external packages.""",
        "method_card": """Retained cross-domain method card (earned before this sealed exam):
- Treat a lease as a fenced state transition, not merely a timestamp.
- Reject identity/payload conflicts before any external effect.
- Work on copied state and pass copied payloads across authority boundaries.
- Increment a monotonic generation on every acquisition; accept a result only from the current generation.
- Commit success only after the external effect returns a generation-matching result.
- Convert failures and stale results into explicit retryable pending states; never leave ambiguous running state.""",
        "public_tests": r'''
import copy

def test_new_commit_and_replay():
    state = {"jobs": {}, "keep": {"x": 1}}
    original = copy.deepcopy(state)
    calls = []
    def worker(payload, generation):
        calls.append((payload, generation))
        return {"generation": generation, "result": payload["n"] * 2}
    req = {"id": "a", "payload": {"n": 3}, "payload_hash": "h1", "owner": "w1"}
    first = module.run_jobs(state, [req], worker, 100, 10)
    check(state == original, "input state mutated")
    check(first["outcomes"] == [{"id": "a", "status": "committed", "result": 6}], "bad commit outcome")
    check(first["state"]["jobs"]["a"]["status"] == "done", "not committed")
    replay = module.run_jobs(first["state"], [req], worker, 101, 10)
    check(replay["outcomes"] == [{"id": "a", "status": "replay", "result": 6}], "bad replay")
    check(len(calls) == 1, "worker called on replay")

def test_live_lease_is_busy():
    record = {"payload_hash":"h", "status":"running", "owner":"x", "lease_until":50,
              "generation":2, "attempt":2, "result":None, "error":None}
    state = {"jobs":{"j": copy.deepcopy(record)}}
    calls = []
    req = {"id":"j", "payload":{}, "payload_hash":"h", "owner":"y"}
    out = module.run_jobs(state, [req], lambda p,g: calls.append(1), 49, 10)
    check(out["outcomes"] == [{"id":"j", "status":"busy"}], "live lease not busy")
    check(out["state"]["jobs"]["j"] == record and not calls, "busy path changed state or called worker")

test_new_commit_and_replay()
test_live_lease_is_busy()
''',
        "hidden_tests": r'''
import copy

def req(job_id="j", h="h", owner="new", payload=None):
    return {"id":job_id, "payload": payload or {"v":1}, "payload_hash":h, "owner":owner}

def test_conflict_is_untouched():
    rec = {"payload_hash":"old", "status":"done", "owner":"o", "lease_until":None,
           "generation":4, "attempt":4, "result":9, "error":None}
    state = {"jobs":{"j":copy.deepcopy(rec)}, "other":[1,2]}
    before = copy.deepcopy(state); calls=[]
    out = module.run_jobs(state, [req(h="new")], lambda p,g:calls.append(1), 5, 2)
    check(out["outcomes"] == [{"id":"j","status":"conflict"}], "conflict outcome")
    check(out["state"] == before and state == before and not calls, "conflict was not inert")

def test_expired_reacquisition_increments():
    rec = {"payload_hash":"h", "status":"running", "owner":"old", "lease_until":9,
           "generation":7, "attempt":3, "result":None, "error":None}
    seen=[]
    def worker(payload, generation):
        seen.append((copy.deepcopy(payload), generation))
        payload["v"] = 99
        return {"generation":generation, "result":"ok"}
    payload={"v":1}
    out = module.run_jobs({"jobs":{"j":rec}}, [req(payload=payload)], worker, 10, 5)
    saved=out["state"]["jobs"]["j"]
    check(seen == [({"v":1},8)] and payload == {"v":1}, "generation or payload copy wrong")
    check(saved["generation"] == 8 and saved["attempt"] == 4 and saved["owner"] == "new", "reacquire counters")
    check(saved["status"] == "done" and saved["result"] == "ok", "reacquire did not commit")

def test_failure_is_retryable():
    def worker(payload, generation):
        raise ValueError("boom")
    out = module.run_jobs({"jobs":{}, "keep":3}, [req()], worker, 1, 9)
    saved=out["state"]["jobs"]["j"]
    check(out["outcomes"] == [{"id":"j","status":"failed","error":"ValueError: boom"}], "failure outcome")
    check(saved["status"] == "pending" and saved["lease_until"] is None and saved["result"] is None, "failure not retryable")
    check(saved["error"] == "ValueError: boom" and out["state"]["keep"] == 3, "failure record")

def test_stale_generation_rejected():
    out = module.run_jobs({"jobs":{}}, [req()],
                          lambda p,g:{"generation":g-1,"result":"bad"}, 1, 4)
    saved=out["state"]["jobs"]["j"]
    check(out["outcomes"] == [{"id":"j","status":"stale_result"}], "stale outcome")
    check(saved["status"] == "pending" and saved["error"] == "stale_generation", "stale result accepted")
    check(saved["result"] is None and saved["lease_until"] is None, "stale residue")

test_conflict_is_untouched()
test_expired_reacquisition_increments()
test_failure_is_retryable()
test_stale_generation_rejected()
''',
    },
    {
        "id": "repo_atomic_cursor_batch_v1",
        "family": "transactional_ingestion",
        "objective": """Implement `ingest_pages(state, pages, sink) -> dict` in solution.py.

Deep-copy state, never mutate inputs, and preserve unrelated keys. Managed state keys are: `cursor` (default None), `seen` (dict id -> value), and `receipts` (dict receipt_id -> payload_hash). Process pages in order. Each page contains cursor, next_cursor, items, receipt_id, payload_hash. Each item contains id and value.

For each page:
- Existing receipt_id with the same hash is a replay: emit `{"receipt_id": rid, "status": "replay"}` with no sink call or state change. A different hash is conflict.
- Page cursor must equal current state cursor; otherwise emit gap with no sink call/state change.
- Validate the whole page before calling sink. Duplicate ids inside the page with identical values collapse to one. Different values conflict. An id already in seen with the same value is ignored; a different value conflicts. Any conflict emits `{"receipt_id": rid, "status": "conflict"}` and leaves the whole page unapplied.
- Call `sink(deepcopy(new_items))` exactly once, where new_items retain first-seen page order and contain only unseen ids. If it raises, emit failed with error `TypeName: message` and apply none of the page.
- After sink succeeds, atomically add new items to seen, store the receipt hash, advance cursor to next_cursor, and emit `{"receipt_id": rid, "status": "committed", "count": len(new_items)}`.

Return `{"state": copied_state, "outcomes": outcomes}`. Do not use files, network, threads, processes, time, randomness, or external packages.""",
        "method_card": """Retained cross-domain method card (earned before this sealed exam):
- Validate the entire batch and its cursor/identity contract before crossing an external-effect boundary.
- Use copy-on-write state so a rejected batch has no partial progress.
- Collapse identical duplicates but reject conflicting identities deterministically.
- Invoke the external sink once with only the deduplicated delta.
- Advance receipt and cursor checkpoints only after the sink succeeds; failures preserve a clean retry path.""",
        "public_tests": r'''
import copy

def test_commit_then_replay():
    state={"cursor":None,"seen":{},"receipts":{},"keep":"yes"}; before=copy.deepcopy(state); calls=[]
    page={"cursor":None,"next_cursor":"c1","items":[{"id":"a","value":1},{"id":"b","value":2}],
          "receipt_id":"r1","payload_hash":"h1"}
    def sink(items): calls.append(copy.deepcopy(items))
    first=module.ingest_pages(state,[page],sink)
    check(state == before, "input state mutated")
    check(first["outcomes"] == [{"receipt_id":"r1","status":"committed","count":2}], "commit outcome")
    check(first["state"]["cursor"] == "c1" and first["state"]["seen"] == {"a":1,"b":2}, "commit state")
    second=module.ingest_pages(first["state"],[page],sink)
    check(second["outcomes"] == [{"receipt_id":"r1","status":"replay"}] and len(calls)==1, "replay effect")

def test_cursor_gap():
    calls=[]; state={"cursor":"expected","seen":{},"receipts":{}}
    page={"cursor":"wrong","next_cursor":"x","items":[],"receipt_id":"r","payload_hash":"h"}
    out=module.ingest_pages(state,[page],lambda items:calls.append(items))
    check(out["outcomes"] == [{"receipt_id":"r","status":"gap"}], "gap outcome")
    check(out["state"] == state and not calls, "gap changed state")

test_commit_then_replay()
test_cursor_gap()
''',
        "hidden_tests": r'''
import copy

def page(items, rid="r", h="h", cursor=None, nxt="n"):
    return {"cursor":cursor,"next_cursor":nxt,"items":items,"receipt_id":rid,"payload_hash":h}

def test_intra_page_conflict_atomic():
    state={"cursor":None,"seen":{},"receipts":{},"keep":[1]}; before=copy.deepcopy(state); calls=[]
    out=module.ingest_pages(state,[page([{"id":"a","value":1},{"id":"a","value":2}])],lambda x:calls.append(x))
    check(out["outcomes"] == [{"receipt_id":"r","status":"conflict"}], "intra conflict")
    check(out["state"] == before and state == before and not calls, "partial conflict apply")

def test_existing_conflict_atomic():
    state={"cursor":None,"seen":{"a":1},"receipts":{}}; calls=[]
    out=module.ingest_pages(state,[page([{"id":"b","value":2},{"id":"a","value":9}])],lambda x:calls.append(x))
    check(out["outcomes"][0]["status"] == "conflict" and out["state"] == state and not calls, "global conflict")

def test_sink_failure_rolls_back():
    state={"cursor":None,"seen":{},"receipts":{},"keep":7}
    def sink(items):
        items[0]["value"]=99
        raise RuntimeError("down")
    source=page([{"id":"a","value":1}]); source_before=copy.deepcopy(source)
    out=module.ingest_pages(state,[source],sink)
    check(out["outcomes"] == [{"receipt_id":"r","status":"failed","error":"RuntimeError: down"}], "failure outcome")
    check(out["state"] == state and source == source_before, "failure rollback/input mutation")

def test_identical_duplicates_and_seen_collapse():
    calls=[]; state={"cursor":None,"seen":{"old":5},"receipts":{}}
    items=[{"id":"old","value":5},{"id":"x","value":2},{"id":"x","value":2},{"id":"y","value":3}]
    out=module.ingest_pages(state,[page(items)],lambda xs:calls.append(copy.deepcopy(xs)))
    check(calls == [[{"id":"x","value":2},{"id":"y","value":3}]], "delta/order/dedupe")
    check(out["outcomes"] == [{"receipt_id":"r","status":"committed","count":2}], "dedupe count")
    check(out["state"]["seen"] == {"old":5,"x":2,"y":3} and out["state"]["cursor"] == "n", "dedupe state")

test_intra_page_conflict_atomic()
test_existing_conflict_atomic()
test_sink_failure_rolls_back()
test_identical_duplicates_and_seen_collapse()
''',
    },
)
