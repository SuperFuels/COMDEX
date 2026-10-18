import json
from pathlib import Path

import backend.modules.hexcore.open_diagnostic_experiment_invention as diag
from backend.modules.hexcore.recursive_action_language_expansion import ATOM_ID, LATER_PROCEDURE_ID, _invent_atom


def test_adaptive_experiment_diagnoses_four_origins_and_delays_install(tmp_path: Path, monkeypatch) -> None:
    atom, _ = _invent_atom(); atom_path = tmp_path / "atoms.json"
    atom_path.write_text(json.dumps({"atoms": {ATOM_ID: {"spec": atom, "implementation_sha256": diag._sha(atom),
                                                         "authority": LATER_PROCEDURE_ID}}}))
    rows = b"".join(f"{year}-01-01,{year-2000}\n".encode() for year in range(2001, 2011))
    payloads = {
        "worldbank": (json.dumps([{"page": 1}, [{"date": str(y), "value": y-2000} for y in range(2001, 2011)]]).encode(), "application/json"),
        "fred": (b"observation_date,GDP\n" + rows, "text/csv"), "noaa": (b"DATE,TEMP\n" + rows, "text/csv"),
        "treasury": (b'{"data":[' + b','.join(f'{{"record_date":"{y}-01-01","exchange_rate":"{y-2000}"}}'.encode() for y in range(2001, 2011)) + b']}', "application/json")}
    def fake_get(url: str):
        key = "worldbank" if "worldbank" in url else "fred" if "fred" in url else "noaa" if "noaa" in url else "treasury"
        body, content = payloads[key]; return {"status": 200, "body": body, "content_type": content, "url": url}
    monkeypatch.setattr("backend.modules.hexcore.open_property_language_invention._get", fake_get)
    private, registry, state, result_path = (tmp_path/name for name in ("private.json","registry.json","state.json","result.json"))
    result = diag.run(atom_registry_path=atom_path, private_experiment_path=private,
                      experiment_registry_path=registry, state_path=state, result_path=result_path,
                      minimum_later_delay_seconds=300)
    assert result["passed"] is True and result["gate"]["diagnostic_accuracy"] == 4
    assert result["gate"]["multi_fault_abstention"] == 1 and not registry.exists()
    stored = json.loads(state.read_text())
    for world in stored["worlds"]: world["later_challenge"]["not_before_epoch"] = 0
    state.write_text(json.dumps(stored))
    closed = diag.close_later_challenges(atom_registry_path=atom_path, state_path=state, result_path=result_path)
    assert closed["gate"]["later_retention_credits"] == 4
    runtime = diag.GovernedDiagnosticExperimentRuntime(registry)
    assert runtime.diagnose(diag.EXPERIMENT_ID, diag.PREDICTIONS["critic_defect"])["diagnosis"] == "critic_defect"


def test_experiment_security_and_multi_fault_abstention() -> None:
    assert all(row["rejected"] for row in diag._security_properties())
    spec, _ = diag.invent_experiment()
    mixed = dict(diag.PREDICTIONS["candidate_defect"]); mixed[diag.ACTIONS[1]] = True
    assert diag.execute_experiment(spec, mixed)["diagnosis"] == "ABSTAIN"
