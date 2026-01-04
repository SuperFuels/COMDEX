from __future__ import annotations

import hashlib
import json

from backend.genome_engine.sle_adapter import SLEAdapter


def _stable_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_sle_adapter_deterministic_trace():
    thresholds = {"warmup_ticks": 16, "eval_ticks": 32}
    scenarios = [
        {"scenario_id": "matched_key", "mode": "matched", "k": 1},
        {"scenario_id": "mux_2", "mode": "multiplex", "k": 2},
    ]

    a1 = SLEAdapter(seed=7, dt=1 / 30)
    r1 = a1.run(scenarios=scenarios, thresholds=thresholds)

    a2 = SLEAdapter(seed=7, dt=1 / 30)
    r2 = a2.run(scenarios=scenarios, thresholds=thresholds)

    assert _stable_hash(r1["trace"]) == _stable_hash(r2["trace"])

    ev0 = r1["trace"][0]
    for k in (
        "trace_kind",
        "tick",
        "t",
        "event_type",
        "source",
        "target",
        "qscore",
        "drift",
        "scenario_id",
        "channel",
        "meta",
    ):
        assert k in ev0
