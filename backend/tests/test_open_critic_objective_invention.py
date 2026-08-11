import json
from pathlib import Path

import backend.modules.hexcore.open_critic_objective_invention as objective
from backend.modules.hexcore.recursive_action_language_expansion import (
    ATOM_ID,
    LATER_PROCEDURE_ID as ATOM_AUTHORITY,
    _invent_atom,
)


def test_unlabelled_objective_discovery_transfer_delay_and_restart(tmp_path: Path, monkeypatch) -> None:
    atom, _ = _invent_atom()
    atoms = tmp_path / "atoms.json"
    atoms.write_text(json.dumps({"atoms": {ATOM_ID: {"spec": atom,
        "implementation_sha256": objective._sha(atom), "authority": ATOM_AUTHORITY}}}))
    rows = b"".join(f"{year}-01-01,{year-2000}\n".encode() for year in range(2001, 2011))
    payloads = {
        "worldbank": (json.dumps([{"page": 1}, [{"indicator": {"value": "GDP"}, "date": str(year), "value": year-2000}
                                                   for year in range(2001, 2011)]]).encode(), "application/json"),
        "fred": (b"observation_date,GDP\n" + rows, "text/csv"),
        "noaa": (b"DATE,TEMP\n" + rows, "text/csv"),
        "treasury": (b'{"data":[' + b','.join(f'{{"record_date":"{year}-01-01","exchange_rate":"{year-2000}"}}'.encode() for year in range(2001, 2011)) + b']}', "application/json"),
    }
    def fake_get(url: str):
        key = "worldbank" if "worldbank" in url else "fred" if "fred" in url else "noaa" if "noaa" in url else "treasury"
        body, content = payloads[key]
        return {"status": 200, "body": body, "content_type": content, "url": url}
    monkeypatch.setattr("backend.modules.hexcore.open_property_language_invention._get", fake_get)
    private, registry = tmp_path / "private.json", tmp_path / "objectives.json"
    state, result_path = tmp_path / "state.json", tmp_path / "result.json"
    result = objective.run(atom_registry_path=atoms, private_objective_path=private,
                           objective_registry_path=registry, state_path=state,
                           result_path=result_path, minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["supplied_failure_categories"] == 0
    assert result["gate"]["supplied_expected_invariants"] == 0
    assert result["gate"]["cross_family_transfers"] == 2
    assert result["gate"]["ood_abstention"] == 1
    assert not registry.exists()
    stored = json.loads(state.read_text())
    for episode in stored["episodes"]:
        episode["later_challenge"]["not_before_epoch"] = 0
    state.write_text(json.dumps(stored))
    closed = objective.close_later_challenges(atom_registry_path=atoms, state_path=state,
                                               result_path=result_path)
    assert closed["gate"]["later_retention_credits"] == 4
    restarted = objective.GovernedCriticObjectiveRuntime(registry)
    transfer = restarted.evaluate(objective.OBJECTIVE_ID, "derivative", [1, 2, 3, 4, 5, 6, 7])
    assert transfer["passed"] is True
    post = objective.verify_post_promotion_transfer(registry_path=registry, result_path=result_path)
    assert post["gate"]["new_family_after_promotion"] == 1
    assert post["post_promotion_transfer"]["private_state_replay"] == 0


def test_objective_security_and_no_disagreement_abstention() -> None:
    assert all(row["rejected"] for row in objective._security_properties())
    robust = objective._family_sources("trend")[-1][1]
    decision, search = objective.discover_objective([robust, robust], [[1,2,3,4,5,6,7], [2,4,6,8,10,12,14]])
    assert decision["status"] == "ABSTAIN"
    assert len(search) == 4
