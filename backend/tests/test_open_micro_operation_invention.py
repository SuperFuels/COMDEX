import json
from pathlib import Path

import backend.modules.hexcore.open_micro_operation_invention as micro
from backend.modules.hexcore.recursive_action_language_expansion import (
    ATOM_ID,
    LATER_PROCEDURE_ID as ATOM_AUTHORITY,
    _invent_atom,
)


def test_micro_operation_is_private_until_later_public_authority(tmp_path: Path, monkeypatch) -> None:
    spec, _ = _invent_atom()
    atom_registry = tmp_path / "atoms.json"
    atom_registry.write_text(json.dumps({"atoms": {ATOM_ID: {"spec": spec,
        "implementation_sha256": micro.hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(),
        "authority": ATOM_AUTHORITY}}}))
    payloads = {
        "worldbank": (json.dumps([{"page": 1}, [{"indicator": {"value": "GDP"}, "date": "2025", "value": 5},
                                                   {"indicator": {"value": "GDP"}, "date": "2024", "value": 4},
                                                   {"indicator": {"value": "GDP"}, "date": "2023", "value": 3}]]).encode(), "application/json"),
        "fred": (b"observation_date,GDP\n2023-01-01,3\n2024-01-01,4\n2025-01-01,5\n", "text/csv"),
        "noaa": (b"DATE,TEMP,DEWP\n2023-01-01,3,1\n2024-01-01,4,1\n2025-01-01,5,1\n", "text/csv"),
    }

    def fake_get(url: str):
        key = "worldbank" if "worldbank" in url else "fred" if "fred" in url else "noaa"
        body, content = payloads[key]
        return {"status": 200, "body": body, "oversize": False, "content_type": content, "url": url}

    monkeypatch.setattr(micro, "_get", fake_get)
    private, compiler = tmp_path / "private.json", tmp_path / "compiler.json"
    state, result_path = tmp_path / "state.json", tmp_path / "result.json"
    result = micro.run(atom_registry_path=atom_registry, private_source_path=private,
                       compiler_registry_path=compiler, state_path=state,
                       result_path=result_path, minimum_later_delay_seconds=300)
    assert result["passed"] is True
    assert result["gate"]["semantic_properties_passed"] == 6
    assert result["gate"]["security_attacks_rejected"] == 8
    assert compiler.exists() is False
    stored = json.loads(state.read_text())
    for episode in stored["episodes"]:
        episode["later_challenge"]["not_before_epoch"] = 0
    state.write_text(json.dumps(stored))
    closed = micro.close_later_challenges(atom_registry_path=atom_registry,
                                           state_path=state, result_path=result_path)
    assert closed["gate"]["later_retention_credits"] == 3
    assert closed["compiler_installation"]["installed"] is True
    restarted = micro.GovernedMicroOperationRuntime(compiler)
    executed = restarted.execute(micro.MICRO_OP_ID, [1, 2, 3, 4, 5])
    assert executed["passed"] is True
    assert executed["value"] == 1


def test_restricted_source_validator_rejects_ambient_authority() -> None:
    attacks = micro._security_properties()
    assert len(attacks) == 8
    assert all(row["rejected"] for row in attacks)
    source, properties, traces = micro._invent()
    assert source
    assert all(row["passed"] for row in properties)
    assert next(row for row in traces if row["candidate"] == "endpoint_slope")["accepted"] is False
