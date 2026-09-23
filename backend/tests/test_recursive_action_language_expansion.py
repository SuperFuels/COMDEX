import json
from pathlib import Path

import backend.modules.hexcore.recursive_action_language_expansion as recursive


def test_private_atom_requires_later_authority_before_runtime_install(tmp_path: Path, monkeypatch) -> None:
    world_bank = [{"page": 1}, [{"indicator": {"value": "GDP current US dollars"}, "date": "2025", "value": 10},
                                 {"indicator": {"value": "GDP current US dollars"}, "date": "2024", "value": 9}]]
    treasury = {"data": [{"record_date": "2026-06-30", "exchange_rate": "1.25", "src_line_nbr": "8"},
                           {"record_date": "2026-03-31", "exchange_rate": "1.20", "src_line_nbr": "7"}]}
    fred = b"observation_date,GDP\n2025-01-01,100\n2025-04-01,101\n"
    noaa = b"DATE,TEMP,DEWP,STATION\n2025-01-01,10,4,123\n2025-01-02,11,5,123\n"

    def fake_get(url: str):
        if "worldbank" in url:
            body, content = json.dumps(world_bank).encode(), "application/json"
        elif "treasury" in url:
            body, content = json.dumps(treasury).encode(), "application/json"
        elif "fred" in url:
            body, content = fred, "text/csv"
        else:
            body, content = noaa, "text/csv"
        return {"status": 200, "body": body, "oversize": False, "content_type": content, "url": url}

    monkeypatch.setattr(recursive, "_get", fake_get)
    private = tmp_path / "private.json"
    runtime = tmp_path / "runtime.json"
    state = tmp_path / "state.json"
    result_path = tmp_path / "result.json"
    result = recursive.run(private_registry_path=private, runtime_registry_path=runtime,
                           state_path=state, result_path=result_path, minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["properties_passed"] == 6
    assert result["gate"]["source_disjoint_transfers"] == 3
    assert runtime.exists() is False
    stored = json.loads(state.read_text())
    for episode in stored["episodes"]:
        episode["later_challenge"]["not_before_epoch"] = 0
    state.write_text(json.dumps(stored))
    closed = recursive.close_later_challenges(state_path=state, result_path=result_path)
    assert closed["gate"]["later_retention_credits"] == 4
    assert closed["runtime_installation"]["installed"] is True
    registry = json.loads(runtime.read_text())
    assert registry["atoms"][recursive.ATOM_ID]["capability_class"] == "pure_read_only_transform"
    restarted = recursive.RecursiveActionAtomRuntime(runtime)
    assert restarted.available_atoms() == [recursive.ATOM_ID]
    executed = restarted.execute(recursive.ATOM_ID, body=fred, content_type="text/csv",
                                 mission="extract the GDP time series")
    assert executed["passed"] is True
    assert executed["time_field"] == "observation_date"
    assert executed["measure_field"] == "GDP"


def test_atom_abstains_on_ambiguous_and_capability_escalating_inputs() -> None:
    spec, _ = recursive._invent_atom()
    ambiguous = recursive.execute_atom(spec, b"date,left,right\n2025-01-01,1,2\n2025-01-02,3,4\n",
                                       "text/csv", "extract measurements")
    assert ambiguous["passed"] is False
    assert ambiguous["reason"] == "ambiguous_schema_abstention"
    escalated = recursive.execute_atom({**spec, "capability_class": "network_write"},
                                       b"date,value\n2025-01-01,1\n", "text/csv", "extract value")
    assert escalated["passed"] is False
    assert escalated["reason"] == "unapproved_atom"
