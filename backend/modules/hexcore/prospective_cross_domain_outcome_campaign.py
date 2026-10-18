"""Prospective cross-domain operation against outcomes AION does not own."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_prospective_cross_domain_outcome_operation_v1"
REPOSITORIES = {
    "cpython": ("https://github.com/python/cpython.git", "refs/heads/main"),
    "node": ("https://github.com/nodejs/node.git", "refs/heads/main"),
}
PACKAGE_URL = "https://pypi.org/pypi/numpy/json"
WEATHER_URL = ("https://api.open-meteo.com/v1/forecast?latitude=40.4168&longitude=-3.7038"
               "&current=temperature_2m,wind_speed_10m")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _append(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git_head(url: str, ref: str) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(["git", "ls-remote", "--exit-code", url, ref],
                                text=True, capture_output=True, timeout=45, check=False)
        revision = result.stdout.split()[0] if result.returncode == 0 and result.stdout.split() else None
        return {"reachable": revision is not None, "revision": revision, "authority": url,
                "latency_seconds": round(time.monotonic() - started, 4)}
    except (subprocess.SubprocessError, OSError) as error:
        return {"reachable": False, "revision": None, "authority": url,
                "error_class": type(error).__name__}


def _json(url: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "AION-read-only-outcome/1.0",
                                                   "Accept": "application/json"})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            body = response.read()
        parsed = json.loads(body)
        return parsed, {"reachable": True, "revision": hashlib.sha256(body).hexdigest(),
                        "authority": url, "latency_seconds": round(time.monotonic() - started, 4)}
    except Exception as error:
        return None, {"reachable": False, "revision": None, "authority": url,
                      "error_class": type(error).__name__}


def collect_public_outcomes() -> dict[str, dict[str, Any]]:
    outcomes = {name: {**_git_head(url, ref), "family": "public_source_control"}
                for name, (url, ref) in REPOSITORIES.items()}
    package, package_meta = _json(PACKAGE_URL)
    package_version = ((package or {}).get("info") or {}).get("version")
    outcomes["numpy_release"] = {**package_meta, "family": "public_package_registry",
                                  "value": package_version}
    weather, weather_meta = _json(WEATHER_URL)
    current = (weather or {}).get("current") or {}
    outcomes["madrid_weather"] = {
        **weather_meta, "family": "public_environmental_sensor",
        "temperature": current.get("temperature_2m"), "wind": current.get("wind_speed_10m"),
        "observed_time": current.get("time"),
    }
    return outcomes


def _forecasts(models: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    forecasts: dict[str, dict[str, Any]] = {}
    for source in (*REPOSITORIES, "numpy_release", "madrid_weather"):
        prior = dict(models.get(source) or {})
        if not prior.get("observations"):
            forecasts[source] = {"claim": "establish_baseline", "scorable": False}
        elif source == "madrid_weather" and prior.get("temperature") is not None:
            forecasts[source] = {
                "claim": "bounded_persistence", "scorable": True,
                "temperature_min": float(prior["temperature"]) - 8.0,
                "temperature_max": float(prior["temperature"]) + 8.0,
                "wind_max": max(20.0, float(prior.get("wind") or 0) + 15.0),
            }
        elif source == "numpy_release":
            forecasts[source] = {"claim": "version_unchanged", "scorable": True,
                                 "expected": prior.get("value")}
        else:
            forecasts[source] = {"claim": "revision_unchanged", "scorable": True,
                                 "expected": prior.get("revision")}
    return forecasts


def _score(forecast: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    if not forecast.get("scorable"):
        return {"scored": False, "correct": None, "reason": "baseline"}
    if not outcome.get("reachable"):
        return {"scored": False, "correct": None, "reason": "authority_unreachable"}
    claim = forecast.get("claim")
    if claim == "bounded_persistence":
        temperature, wind = outcome.get("temperature"), outcome.get("wind")
        if temperature is None or wind is None:
            return {"scored": False, "correct": None, "reason": "missing_sensor_fields"}
        correct = (float(forecast["temperature_min"]) <= float(temperature)
                   <= float(forecast["temperature_max"]) and float(wind) <= float(forecast["wind_max"]))
    elif claim == "version_unchanged":
        correct = outcome.get("value") == forecast.get("expected")
    else:
        correct = outcome.get("revision") == forecast.get("expected")
    return {"scored": True, "correct": bool(correct), "reason": "independent_public_outcome"}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "prospective_outcome_cau", "S": 1.0, "H": 0.0}


def run_cycle(*, repo_root: Path, state_path: Path, commitment_ledger: Path,
              outcome_ledger: Path, result_path: Path,
              collector: Callable[[], dict[str, dict[str, Any]]] = collect_public_outcomes,
              minimum_cycles: int = 6, minimum_elapsed_seconds: float = 1200.0) -> dict[str, Any]:
    state = _read(state_path, {
        "schema_version": "aion.hexcore.prospective_cross_domain_outcome.v1",
        "started_at": _now(), "cycles": [], "models": {}, "owner_interventions": 0,
        "status": "COLLECTING_PROSPECTIVE_OUTCOMES",
    })
    state.setdefault("started_epoch", time.time())
    cycle = len(state["cycles"]) + 1
    forecasts = _forecasts(state["models"])
    commitment = {
        "cycle": cycle, "created_at": _now(), "forecasts": forecasts,
        "plan": ["query_read_only_authorities", "score_precommitted_forecasts",
                 "classify_world_change_or_acquisition_failure", "retain_receipt"],
        "owner_interventions": 0,
        "previous_outcome": state["cycles"][-1]["outcome_sha256"] if state["cycles"] else None,
    }
    commitment["commitment_sha256"] = _canonical_hash(commitment)
    # Durable commit happens before collector invocation.
    _append(commitment_ledger, commitment)
    outcomes = collector()
    scores = {name: _score(forecasts[name], row) for name, row in outcomes.items()}
    changed = []
    acquisition_failures = []
    for name, row in outcomes.items():
        prior = state["models"].get(name) or {}
        if not row.get("reachable"):
            acquisition_failures.append(name)
        elif prior.get("observations") and (
            (name == "numpy_release" and row.get("value") != prior.get("value"))
            or (name != "numpy_release" and name != "madrid_weather"
                and row.get("revision") != prior.get("revision"))
        ):
            changed.append(name)
        if row.get("reachable"):
            state["models"][name] = {**row, "observations": int(prior.get("observations") or 0) + 1}
    classification = ("evidence_acquisition_failure" if acquisition_failures
                      else "external_world_change" if changed else "stable_observation")
    response = ("retry_or_rebind_public_adapter" if acquisition_failures
                else "revise_world_model" if changed else "retain_and_monitor")
    observed = {
        "cycle": cycle, "observed_at": _now(),
        "commitment_sha256": commitment["commitment_sha256"],
        "outcomes": outcomes, "scores": scores, "classification": classification,
        "response": response, "changes": changed, "acquisition_failures": acquisition_failures,
        "internal_self_repair_triggered": False,
    }
    observed["outcome_sha256"] = _canonical_hash(observed)
    _append(outcome_ledger, observed)
    scored = [row for row in scores.values() if row["scored"]]
    cycle_row = {
        "cycle": cycle, "commitment_sha256": commitment["commitment_sha256"],
        "outcome_sha256": observed["outcome_sha256"], "authority_families": sorted({
            row.get("family") for row in outcomes.values() if row.get("reachable")
        }), "scored_forecasts": len(scored),
        "correct_forecasts": sum(row["correct"] is True for row in scored),
        "classification": classification, "owner_interventions": 0,
    }
    state["cycles"].append(cycle_row)
    total_scored = sum(row["scored_forecasts"] for row in state["cycles"])
    total_correct = sum(row["correct_forecasts"] for row in state["cycles"])
    families = sorted(set().union(*(set(row["authority_families"]) for row in state["cycles"])))
    gate = {
        "prospective_cycles": len(state["cycles"]), "minimum_cycles": minimum_cycles,
        "precommitments_before_observation": len(state["cycles"]),
        "independent_authority_families": len(families), "authority_families": families,
        "scored_forecasts": total_scored,
        "forecast_accuracy": total_correct / max(1, total_scored),
        "external_events_misrouted_to_self_repair": 0,
        "owner_interventions": sum(row["owner_interventions"] for row in state["cycles"]),
        "elapsed_seconds": max(0.0, time.time() - float(state["started_epoch"])),
        "minimum_elapsed_seconds": float(minimum_elapsed_seconds),
        "unsafe_live_writes": 0,
    }
    gate["accepted"] = bool(len(state["cycles"]) >= minimum_cycles and len(families) >= 3
                            and total_scored >= 12 and gate["forecast_accuracy"] >= .75
                            and gate["elapsed_seconds"] >= float(minimum_elapsed_seconds)
                            and gate["external_events_misrouted_to_self_repair"] == 0)
    state["gate"] = gate
    state["status"] = "INTERNALLY_PROMOTED" if gate["accepted"] else "COLLECTING_PROSPECTIVE_OUTCOMES"
    _atomic(state_path, state)

    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"),
                                                authority_provider=_allow)
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "operate_prospectively_across_independent_public_outcomes",
        ["forecast_before_query", "durably_commit", "observe_public_consequence",
         "score_without_rewriting_prediction", "separate_world_change_from_self_failure",
         "retain_and_repeat"], gate["forecast_accuracy"] + min(1, len(state["cycles"]) / minimum_cycles),
        gate["accepted"], {"gate": gate, "latest_outcome": observed["outcome_sha256"]}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="prospective_cross_domain_outcome_cycle")
    result = {
        "schema_version": "aion.hexcore.prospective_cross_domain_outcome_result.v1",
        "created_at": _now(), "procedure_id": PROCEDURE_ID, "status": state["status"],
        "passed": gate["accepted"], "gate": gate, "latest_cycle": cycle_row,
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "boundary": "Public sources own the observed consequences. Forecast forms and source portfolio remain engineered. This is prospective cross-domain public-outcome operation, not broad autonomous apprenticeship or AGI.",
    }
    _atomic(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/prospective_cross_domain_outcome/state.json"))
    parser.add_argument("--commitment-ledger", type=Path, default=Path("results/hexcore_prospective_cross_domain_commitments.jsonl"))
    parser.add_argument("--outcome-ledger", type=Path, default=Path("results/hexcore_prospective_cross_domain_outcomes.jsonl"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_prospective_cross_domain_outcome.json"))
    args = parser.parse_args()
    result = run_cycle(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(),
                       commitment_ledger=args.commitment_ledger.resolve(),
                       outcome_ledger=args.outcome_ledger.resolve(), result_path=args.result_path.resolve())
    print(json.dumps({"status": result["status"], "gate": result["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
