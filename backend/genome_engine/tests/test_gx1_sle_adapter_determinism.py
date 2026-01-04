from __future__ import annotations

import os

# MUST be set before importing anything that reads env at import time.
os.environ["TESSARIS_DETERMINISTIC_TIME"] = "1"
os.environ["TESSARIS_TEST_QUIET"] = "1"

from backend.genome_engine.sle_adapter import SLEAdapter
from backend.genome_engine.stable_json import stable_hash


def test_sle_adapter_deterministic_trace() -> None:
    thresholds = {"warmup_ticks": 16, "eval_ticks": 32}
    scenarios = [
        {"scenario_id": "matched_key", "mode": "matched", "k": 1},
        {"scenario_id": "mux_2", "mode": "multiplex", "k": 2},
    ]

    a1 = SLEAdapter(seed=7, dt=1 / 30)
    r1 = a1.run(scenarios=scenarios, thresholds=thresholds)

    a2 = SLEAdapter(seed=7, dt=1 / 30)
    r2 = a2.run(scenarios=scenarios, thresholds=thresholds)

    assert stable_hash(r1["trace"]) == stable_hash(r2["trace"])

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