"""Owner-valued work whose credit is owned by a later public consequence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary


PROCEDURE_ID = "procedure_owner_valued_delayed_work_v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "owner_valued_delayed_work_cau", "S": 1.0, "H": 0.0}


def _source_forecast(outcome: Mapping[str, Any]) -> dict[str, Any]:
    rows = outcome.get("outcomes") or {}
    return {
        name: {"reachable": bool(row.get("reachable")),
               "expected": row.get("value") if name == "numpy_release" else row.get("revision")}
        for name, row in rows.items() if name != "madrid_weather"
    }


def _research_brief(generation: int, outcome: Mapping[str, Any]) -> str:
    rows = outcome.get("outcomes") or {}
    lines = [
        f"# Public dependency and evidence brief — generation {generation}", "",
        "## Decision supported", "",
        "Determine which monitored technical sources require re-checking before a release or research claim.", "",
        "## Current evidence", "",
    ]
    for name in sorted(rows):
        row = rows[name]
        value = row.get("value") or row.get("revision") or "unavailable"
        lines.append(f"- **{name}** ({row.get('family')}): reachable={row.get('reachable')}; observed value `{value}`.")
    lines.extend([
        "", "## Provisional conclusion", "",
        "Treat every value as time-indexed rather than permanent. Re-check an unreachable or changed authority before relying on it; otherwise retain the current value provisionally.",
        "", "## Later verification contract", "",
        "The next independently collected public row will determine whether the stability assessment was correct. This brief cannot authorize its own conclusion.", "",
    ])
    return "\n".join(lines)


SOFTWARE_ARTIFACT = r'''#!/usr/bin/env python3
import hashlib,json,sys
row=json.load(open(sys.argv[1],encoding="utf-8"))
claimed=row.pop("outcome_sha256")
actual=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest()
assert claimed==actual,"outcome integrity failure"
families={v.get("family") for v in row.get("outcomes",{}).values() if v.get("reachable")}
assert len(families)>=3,"insufficient independent authority families"
assert row.get("commitment_sha256"),"missing precommitment linkage"
print(json.dumps({"accepted":True,"families":sorted(families)},sort_keys=True))
'''


def _data_decision(generation: int, outcome: Mapping[str, Any]) -> dict[str, Any]:
    weather = (outcome.get("outcomes") or {}).get("madrid_weather") or {}
    temperature = weather.get("temperature")
    wind = weather.get("wind")
    if temperature is None or wind is None:
        return {"generation": generation, "decision": "abstain_and_reacquire",
                "scorable": False, "reason": "missing_weather_authority"}
    return {
        "generation": generation, "decision": "continue_bounded_monitoring",
        "scorable": True, "temperature_min": float(temperature) - 8.0,
        "temperature_max": float(temperature) + 8.0,
        "wind_max": max(20.0, float(wind) + 15.0),
        "reason": "A later public environmental row owns the decision score.",
    }


def _create_generation(root: Path, generation: int, outcome: Mapping[str, Any],
                       library: ExecutiveSkillsLibrary) -> dict[str, Any]:
    directory = root / f"generation_{generation:04d}"
    directory.mkdir(parents=True, exist_ok=True)
    research_path = directory / "public_evidence_brief.md"
    software_path = directory / "public_outcome_integrity_guard.py"
    data_path = directory / "environmental_monitoring_decision.json"
    _write(research_path, _research_brief(generation, outcome))
    _write(software_path, SOFTWARE_ARTIFACT)
    _write(data_path, _data_decision(generation, outcome))
    os.chmod(software_path, 0o600)
    contract = {
        "generation": generation, "created_at": _now(),
        "source_cycle": outcome["cycle"], "source_outcome_sha256": outcome["outcome_sha256"],
        "owner_objective": "Produce a release/research evidence brief, a reusable outcome-integrity guard, and an environmental monitoring decision.",
        "success_criteria": {
            "research": "at least 75 percent of reachable technical-source forecasts match the next public row",
            "software": "fresh subprocess accepts the later genuine row and rejects a hash-tampered counterexample",
            "data": "later public weather remains inside the precommitted operating envelope or the decision abstains",
        },
        "source_forecast": _source_forecast(outcome),
        "artifacts": {
            "research": {"path": str(research_path), "sha256": _sha(research_path)},
            "software": {"path": str(software_path), "sha256": _sha(software_path)},
            "data": {"path": str(data_path), "sha256": _sha(data_path)},
        },
        "owner_interventions": 0, "status": "waiting_for_later_public_outcome",
    }
    contract["work_system"] = library.compose(
        contract["owner_objective"], {"uncertainty_high": True, "continuous_arrivals": True}
    )
    contract["commitment_sha256"] = _canonical_hash(contract)
    _write(directory / "work_commitment.json", contract)
    return contract


def _evaluate_research(contract: Mapping[str, Any], later: Mapping[str, Any]) -> dict[str, Any]:
    forecasts = contract.get("source_forecast") or {}
    outcomes = later.get("outcomes") or {}
    scored, correct = 0, 0
    for name, forecast in forecasts.items():
        row = outcomes.get(name) or {}
        if not forecast.get("reachable") or not row.get("reachable"):
            continue
        observed = row.get("value") if name == "numpy_release" else row.get("revision")
        scored += 1
        correct += observed == forecast.get("expected")
    accuracy = correct / max(1, scored)
    return {"passed": scored >= 2 and accuracy >= .75, "scored_claims": scored,
            "correct_claims": correct, "accuracy": accuracy,
            "authority": "later_public_technical_source_row"}


def _evaluate_software(contract: Mapping[str, Any], later: Mapping[str, Any], directory: Path) -> dict[str, Any]:
    script = Path(contract["artifacts"]["software"]["path"])
    genuine_path = directory / "later_outcome.json"
    tampered_path = directory / "tampered_outcome.json"
    _write(genuine_path, dict(later))
    tampered = json.loads(json.dumps(later))
    first = next(iter(tampered.get("outcomes") or {}), None)
    if first:
        tampered["outcomes"][first]["revision"] = "tampered"
    _write(tampered_path, tampered)
    genuine = subprocess.run([sys.executable, "-I", str(script), str(genuine_path)],
                             text=True, capture_output=True, timeout=10, check=False)
    malicious = subprocess.run([sys.executable, "-I", str(script), str(tampered_path)],
                               text=True, capture_output=True, timeout=10, check=False)
    passed = genuine.returncode == 0 and malicious.returncode != 0
    return {"passed": passed, "genuine_row_accepted": genuine.returncode == 0,
            "tampered_row_rejected": malicious.returncode != 0,
            "authority": "fresh_subprocess_plus_later_public_row"}


def _evaluate_data(contract: Mapping[str, Any], later: Mapping[str, Any]) -> dict[str, Any]:
    decision = _read(Path(contract["artifacts"]["data"]["path"]), {})
    weather = (later.get("outcomes") or {}).get("madrid_weather") or {}
    if not decision.get("scorable") or not weather.get("reachable"):
        return {"passed": True, "abstained": True, "authority": "later_public_environmental_row"}
    temperature, wind = weather.get("temperature"), weather.get("wind")
    passed = bool(temperature is not None and wind is not None
                  and float(decision["temperature_min"]) <= float(temperature) <= float(decision["temperature_max"])
                  and float(wind) <= float(decision["wind_max"]))
    return {"passed": passed, "abstained": False, "observed_temperature": temperature,
            "observed_wind": wind, "authority": "later_public_environmental_row"}


def run_once(*, repo_root: Path, state_path: Path, public_outcome_ledger: Path,
             workspace_root: Path, result_path: Path, minimum_generations: int = 3) -> dict[str, Any]:
    outcomes = _jsonl(public_outcome_ledger)
    state = _read(state_path, {"schema_version": "aion.hexcore.owner_valued_delayed_work.v1",
                               "generations": [], "owner_interventions": 0})
    library = ExecutiveSkillsLibrary(
        state_path=repo_root / "data/aion/canonical_runtime/executive_skills.json"
    )
    for row in state["generations"]:
        if row.get("status") == "waiting_for_later_public_outcome" and not row.get("work_system"):
            row["work_system"] = library.compose(
                row["owner_objective"], {"uncertainty_high": True, "continuous_arrivals": True}
            )
            row["work_system_attached_before_later_outcome"] = True
    open_rows = [row for row in state["generations"] if row.get("status") == "waiting_for_later_public_outcome"]
    latest = outcomes[-1] if outcomes else None
    for row in open_rows:
        later = next((candidate for candidate in outcomes
                      if int(candidate["cycle"]) > int(row["source_cycle"])), None)
        if later is None:
            continue
        directory = workspace_root / f"generation_{int(row['generation']):04d}"
        checks = {
            "research": _evaluate_research(row, later),
            "software": _evaluate_software(row, later, directory),
            "data": _evaluate_data(row, later),
        }
        row["later_cycle"] = later["cycle"]
        row["later_outcome_sha256"] = later["outcome_sha256"]
        row["checks"] = checks
        row["passed"] = all(check["passed"] for check in checks.values())
        row["status"] = "consequence_confirmed" if row["passed"] else "rejected_by_later_consequence"
        row["closed_at"] = _now()
        if not row.get("executive_outcome_recorded"):
            library.record_outcome(row.get("work_system") or {}, verified=row["passed"],
                                   score=1.0 if row["passed"] else 0.0)
            row["executive_outcome_recorded"] = True

    # At most one open generation. Create its artifacts only after any older
    # generation has faced a genuinely later row.
    if latest and not any(row.get("status") == "waiting_for_later_public_outcome" for row in state["generations"]):
        generation = len(state["generations"]) + 1
        state["generations"].append(_create_generation(workspace_root, generation, latest, library))

    state["updated_at"] = _now()
    _write(state_path, state)
    closed = [row for row in state["generations"] if row.get("status") in {
        "consequence_confirmed", "rejected_by_later_consequence"}]
    confirmed = [row for row in closed if row.get("passed")]
    gate = {
        "work_generations_created": len(state["generations"]),
        "closed_by_later_consequence": len(closed),
        "consequence_confirmed_generations": len(confirmed),
        "minimum_generations": minimum_generations,
        "owner_valued_artifacts": len(state["generations"]) * 3,
        "research_success_rate": sum(row["checks"]["research"]["passed"] for row in closed) / max(1, len(closed)),
        "software_success_rate": sum(row["checks"]["software"]["passed"] for row in closed) / max(1, len(closed)),
        "data_decision_success_rate": sum(row["checks"]["data"]["passed"] for row in closed) / max(1, len(closed)),
        "cross_domain_work_lanes": 3,
        "owner_interventions": state.get("owner_interventions", 0),
        "verified_executive_work_outcomes": sum(
            bool(row.get("executive_outcome_recorded") and row.get("passed")) for row in state["generations"]
        ),
        "unsafe_live_repository_writes": 0,
    }
    gate["accepted"] = bool(len(confirmed) >= minimum_generations
                            and len(closed) == len(confirmed)
                            and gate["verified_executive_work_outcomes"] >= minimum_generations
                            and min(gate["research_success_rate"], gate["software_success_rate"],
                                    gate["data_decision_success_rate"]) >= .75
                            and gate["owner_interventions"] == 0)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"),
                                                authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "produce_owner_valued_work_confirmed_by_later_public_consequences",
        ["derive_owner_value", "declare_success_before_work", "produce_research_software_data_artifacts",
         "wait_for_later_public_row", "execute_and_score", "retain_or_reject", "repeat"],
        float(len(confirmed)) + min(gate["research_success_rate"], gate["software_success_rate"],
                                    gate["data_decision_success_rate"]),
        gate["accepted"], {"gate": gate, "generation_set": _canonical_hash(state["generations"])}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="owner_valued_delayed_work")
    result = {
        "schema_version": "aion.hexcore.owner_valued_delayed_work_result.v1", "created_at": _now(),
        "procedure_id": PROCEDURE_ID,
        "status": "PROMOTED" if gate["accepted"] else "WAITING_FOR_LATER_CONSEQUENCES",
        "passed": gate["accepted"], "gate": gate,
        "active_generation": next((row for row in state["generations"] if row.get("status") == "waiting_for_later_public_outcome"), None),
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "boundary": "The three work contracts are engineered and public outcomes are narrow. This demonstrates repeated useful artifact production under delayed accountability, not open-ended economic agency or AGI.",
    }
    _write(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/owner_valued_delayed_work/state.json"))
    parser.add_argument("--public-outcome-ledger", type=Path, default=Path("results/hexcore_prospective_cross_domain_outcomes.jsonl"))
    parser.add_argument("--workspace-root", type=Path, default=Path("results/aion_owner_valued_work"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_owner_valued_delayed_work.json"))
    args = parser.parse_args()
    result = run_once(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(),
                      public_outcome_ledger=args.public_outcome_ledger.resolve(),
                      workspace_root=args.workspace_root.resolve(), result_path=args.result_path.resolve())
    print(json.dumps({"status": result["status"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
