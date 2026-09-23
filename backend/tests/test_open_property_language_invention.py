import json
from pathlib import Path

import backend.modules.hexcore.open_property_language_invention as prop
from backend.modules.hexcore.recursive_action_language_expansion import (
    ATOM_ID,
    LATER_PROCEDURE_ID as ATOM_AUTHORITY,
    _invent_atom,
)


def test_property_is_invented_transfers_and_stays_private_until_later(tmp_path: Path, monkeypatch) -> None:
    spec, _ = _invent_atom()
    atom_registry = tmp_path / "atoms.json"
    atom_registry.write_text(json.dumps({"atoms": {ATOM_ID: {"spec": spec,
        "implementation_sha256": prop._sha(spec), "authority": ATOM_AUTHORITY}}}))
    payloads = {
        "worldbank": (json.dumps([{"page": 1}, [{"indicator": {"value": "GDP"}, "date": str(year), "value": year - 2000}
                                                   for year in range(2001, 2011)]]).encode(), "application/json"),
        "fred": (b"observation_date,GDP\n" + b"".join(f"{year}-01-01,{year-2000}\n".encode() for year in range(2001, 2011)), "text/csv"),
        "noaa": (b"DATE,TEMP,DEWP\n" + b"".join(f"{year}-01-01,{year-2000},1\n".encode() for year in range(2001, 2011)), "text/csv"),
        "treasury": (b'{"data":[' + b','.join(f'{{"record_date":"{year}-01-01","exchange_rate":"{year-2000}"}}'.encode() for year in range(2001, 2011)) + b']}', "application/json"),
    }

    def fake_get(url: str):
        key = "worldbank" if "worldbank" in url else "fred" if "fred" in url else "noaa" if "noaa" in url else "treasury"
        body, content = payloads[key]
        return {"status": 200, "body": body, "oversize": False, "content_type": content, "url": url}

    monkeypatch.setattr(prop, "_get", fake_get)
    private, registry = tmp_path / "private.json", tmp_path / "critics.json"
    state, result_path = tmp_path / "state.json", tmp_path / "result.json"
    result = prop.run(atom_registry_path=atom_registry, private_property_path=private,
                      critic_registry_path=registry, state_path=state, result_path=result_path,
                      minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["inherited_critic_false_acceptances"] == 1
    assert result["gate"]["cross_family_transfers"] == 2
    assert result["gate"]["security_attacks_rejected"] == 8
    assert not registry.exists()
    stored = json.loads(state.read_text())
    for episode in stored["episodes"]:
        episode["later_challenge"]["not_before_epoch"] = 0
    state.write_text(json.dumps(stored))
    closed = prop.close_later_challenges(atom_registry_path=atom_registry, state_path=state,
                                         result_path=result_path)
    assert closed["gate"]["later_retention_credits"] == 4
    runtime = prop.GovernedPropertyCriticRuntime(registry)
    robust = prop._candidate_sources()[-1][1]
    outcome = runtime.execute(prop.PROPERTY_ID, robust, [1, 2, 3, 4, 5, 6, 7])
    assert outcome["passed"] is True
    assert outcome["property_satisfied"] is True


def test_property_validator_rejects_authority_and_unbounded_critics() -> None:
    security = prop._security_properties()
    assert len(security) == 8
    assert all(row["rejected"] for row in security)
    endpoint = prop._candidate_sources()[0][1]
    assert prop._initial_critic(endpoint) is True
    invented, traces = prop.invent_property(prop._failure_witness(endpoint))
    assert prop.validate_property(invented)["passed"] is True
    assert len(traces) == 4
    assert prop.execute_property(invented, endpoint, [1, 2, 3, 4, 5, 6, 7])["property_satisfied"] is False
