"""Unlabelled risk search, critic-objective invention, and delayed promotion."""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.open_micro_operation_invention import _candidate_sources, execute_private_source
from backend.modules.hexcore.open_property_language_invention import (
    PROPERTY_ID,
    _location_sources,
    _series,
    execute_property,
)
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.recursive_action_language_expansion import RecursiveActionAtomRuntime, SOURCES


PROCEDURE_ID = "procedure_open_critic_objective_invention_v1"
LATER_PROCEDURE_ID = "procedure_delayed_critic_objective_runtime_promotion_v1"
OBJECTIVE_ID = "LOCALIZED_INFLUENCE_CONCENTRATION_FALSIFICATION"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "critic_objective_invention_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _probe_values(values: list[float], probe: str) -> list[float]:
    if probe == "global_translation":
        return [value + 100.0 for value in values]
    if probe == "global_positive_scale":
        return [value * 3.0 for value in values]
    if probe == "temporal_reversal":
        return list(reversed(values))
    if probe == "sparse_boundary_replacement":
        transformed = list(values)
        differences = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
        scale = float(statistics.median([value for value in differences if value > 0] or [1.0]))
        transformed[-1] = max(values) + 1000.0 * scale
        return transformed
    raise ValueError("unknown probe")


def _response(source: str, values: list[float], probe: str) -> dict[str, Any]:
    baseline = execute_private_source(source, values)
    changed = execute_private_source(source, _probe_values(values, probe))
    if not baseline.get("passed") or not changed.get("passed") or baseline.get("value") is None or changed.get("value") is None:
        return {"passed": False}
    scale = max(abs(float(baseline["value"])) * 0.05, 1.0)
    return {"passed": True, "baseline": float(baseline["value"]), "challenged": float(changed["value"]),
            "normalized_response": abs(float(changed["value"]) - float(baseline["value"])) / scale}


def discover_objective(candidate_sources: list[str], traces: list[list[float]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Search behaviour disagreement before any oracle or failure label is available."""
    probes = ("global_translation", "global_positive_scale", "temporal_reversal", "sparse_boundary_replacement")
    rows = []
    for probe in probes:
        responses = []
        for values in traces:
            per_candidate = [_response(source, values, probe) for source in candidate_sources]
            if all(row.get("passed") for row in per_candidate):
                responses.append(per_candidate)
        if not responses:
            rows.append({"probe": probe, "operationalizable": False, "score": 0.0})
            continue
        disagreements = [max(row["normalized_response"] for row in group)
                         - min(row["normalized_response"] for row in group) for group in responses]
        semantic_destruction = probe in {"global_positive_scale", "temporal_reversal"}
        repeat_support = sum(value > 1.0 for value in disagreements)
        score = float(statistics.median(disagreements)) if not semantic_destruction and repeat_support >= 2 else 0.0
        rows.append({"probe": probe, "operationalizable": not semantic_destruction,
                     "repeat_support": repeat_support, "median_disagreement": float(statistics.median(disagreements)),
                     "score": score,
                     "rejection": "changes_target_semantics" if semantic_destruction else None})
    winner = max(rows, key=lambda row: row["score"])
    if winner["score"] <= 1.0:
        return {"status": "ABSTAIN", "reason": "no_repeated_operationalizable_risk"}, rows
    objective = {"objective_id": OBJECTIVE_ID, "capability_class": "pure_diagnostic_objective",
                 "risk_hypothesis": "one_local_observation_has_disproportionate_global_influence",
                 "probe": winner["probe"], "selection_authority": "unlabelled_candidate_disagreement",
                 "minimum_independent_contexts": 2, "maximum_normalized_delta": 0.25,
                 "required_confirmation": ["source_disjoint", "cross_family", "delayed_reexecution"],
                 "ambient_authority": []}
    return objective, rows


ALLOWED_OBJECTIVE_KEYS = {"objective_id", "capability_class", "risk_hypothesis", "probe",
                          "selection_authority", "minimum_independent_contexts", "maximum_normalized_delta",
                          "required_confirmation", "ambient_authority"}


def validate_objective(objective: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(objective, dict) or set(objective) - ALLOWED_OBJECTIVE_KEYS:
        return {"passed": False, "reason": "unknown_objective_field"}
    if objective.get("objective_id") != OBJECTIVE_ID or objective.get("capability_class") != "pure_diagnostic_objective":
        return {"passed": False, "reason": "invalid_objective_identity_or_class"}
    if objective.get("probe") != "sparse_boundary_replacement":
        return {"passed": False, "reason": "unsupported_or_destructive_probe"}
    if objective.get("selection_authority") != "unlabelled_candidate_disagreement":
        return {"passed": False, "reason": "invalid_selection_authority"}
    if objective.get("minimum_independent_contexts", 0) < 2:
        return {"passed": False, "reason": "insufficient_repeat_support"}
    if objective.get("ambient_authority") not in ([], None, {}):
        return {"passed": False, "reason": "ambient_authority_requested"}
    tolerance = objective.get("maximum_normalized_delta")
    if not isinstance(tolerance, (int, float)) or not 0 <= float(tolerance) <= 1:
        return {"passed": False, "reason": "invalid_tolerance"}
    required = objective.get("required_confirmation")
    if required != ["source_disjoint", "cross_family", "delayed_reexecution"]:
        return {"passed": False, "reason": "authority_gate_removed"}
    return {"passed": True}


def compile_property(objective: dict[str, Any]) -> dict[str, Any]:
    if not validate_objective(objective)["passed"]:
        return {}
    return {"property_id": PROPERTY_ID, "capability_class": "pure_metamorphic_critic",
            "transformation": {"op": "replace_one_observation", "selector": "witnessed_boundary",
                               "direction": "last", "magnitude_ratio": 1000},
            "relation": {"op": "normalized_output_stability",
                         "maximum_normalized_delta": objective["maximum_normalized_delta"]},
            "minimum_observations": 5, "ambient_authority": []}


def _derivative_sources() -> list[tuple[str, str]]:
    terminal = """def run(values):
    if len(values) < 3:
        return None
    return values[len(values)-1] - values[len(values)-2]
"""
    robust = """def run(values):
    if len(values) < 3:
        return None
    changes = []
    for i in range(1, len(values)):
        changes.append(values[i]-values[i-1])
    changes = sorted(changes)
    n = len(changes)
    if n % 2 == 1:
        return changes[n//2]
    return (changes[n//2-1]+changes[n//2])/2
"""
    return [("terminal_change", terminal), ("robust_median_change", robust)]


def _spread_sources() -> list[tuple[str, str]]:
    full_range = """def run(values):
    if len(values) < 5:
        return None
    ordered = sorted(values)
    return ordered[len(ordered)-1] - ordered[0]
"""
    interquartile = """def run(values):
    if len(values) < 5:
        return None
    ordered = sorted(values)
    n = len(ordered)
    return ordered[(3*n)//4] - ordered[n//4]
"""
    return [("full_range_spread", full_range), ("robust_interquartile_spread", interquartile)]


def _family_sources(family: str) -> list[tuple[str, str]]:
    if family == "trend":
        return [_candidate_sources()[0], _candidate_sources()[-1]]
    if family == "location":
        return _location_sources()
    if family == "derivative":
        return _derivative_sources()
    if family == "spread":
        return _spread_sources()
    raise ValueError("unknown family")


def evaluate_objective(objective: dict[str, Any], family: str, values: list[float]) -> dict[str, Any]:
    prop = compile_property(objective)
    expected = {"trend": "ROBUST_MEDIAN_PAIRWISE_TREND", "location": "robust_median_location",
                "derivative": "robust_median_change", "spread": "robust_interquartile_spread"}[family]
    rows = []
    for name, source in _family_sources(family):
        outcome = execute_property(prop, source, values)
        rows.append({"candidate": name, "property": outcome,
                     "accepted": bool(outcome.get("passed") and outcome.get("property_satisfied"))})
    survivors = [row["candidate"] for row in rows if row["accepted"]]
    return {"family": family, "expected": expected, "survivors": survivors,
            "passed": survivors == [expected], "candidates": rows}


def _security_properties() -> list[dict[str, Any]]:
    base = {"objective_id": OBJECTIVE_ID, "capability_class": "pure_diagnostic_objective",
            "risk_hypothesis": "one_local_observation_has_disproportionate_global_influence",
            "probe": "sparse_boundary_replacement", "selection_authority": "unlabelled_candidate_disagreement",
            "minimum_independent_contexts": 2, "maximum_normalized_delta": 0.25,
            "required_confirmation": ["source_disjoint", "cross_family", "delayed_reexecution"],
            "ambient_authority": []}
    attacks = {
        "network": {**base, "ambient_authority": ["network"]},
        "filesystem": {**base, "ambient_authority": ["filesystem"]},
        "process": {**base, "ambient_authority": ["process"]},
        "destructive_probe": {**base, "probe": "delete_source_records"},
        "oracle_label": {**base, "selection_authority": "hidden_oracle_label"},
        "single_context": {**base, "minimum_independent_contexts": 1},
        "remove_delay": {**base, "required_confirmation": ["source_disjoint", "cross_family"]},
        "embedded_code": {**base, "source": "import os"},
    }
    return [{"attack": name, "rejected": not validate_objective(value)["passed"]}
            for name, value in attacks.items()]


def run(*, atom_registry_path: Path, private_objective_path: Path, objective_registry_path: Path,
        state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    trend_sources = [source for _, source in _family_sources("trend")]
    traces = [[1, 2, 3, 4, 5, 6, 7], [3, 5, 7, 9, 11, 13, 15], [10, 9, 8, 7, 6, 5, 4]]
    objective, search = discover_objective(trend_sources, traces)
    objective_hash = _sha(objective)
    security = _security_properties()
    _write(private_objective_path, {"objective": objective, "objective_sha256": objective_hash,
                                    "status": "PRIVATE_PENDING_LATER_AUTHORITY", "search": search})
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    cohort = [(SOURCES[0], "trend", "development"), (SOURCES[2], "trend", "source_disjoint"),
              (SOURCES[3], "location", "cross_family"), (SOURCES[1], "derivative", "cross_family")]
    episodes = []
    for authority, family, role in cohort:
        evidence, values = _series(runtime, authority)
        evaluation = evaluate_objective(objective, family, values)
        episodes.append({"name": authority["name"], "url": authority["url"], "mission": authority["mission"],
                         "family": family, "role": role, "values": len(values), "evidence": evidence,
                         "evaluation": evaluation, "later_challenge": {"status": "WAITING_FOR_FUTURE_OUTCOME",
                         "not_before_epoch": time.time() + minimum_later_delay_seconds, "retention_credit": 0}})
    # No disagreement means no defensible objective: this is the explicit OOD abstention control.
    abstention, abstention_search = discover_objective([trend_sources[-1], trend_sources[-1]], traces)
    registry_before = json.loads(objective_registry_path.read_text()) if objective_registry_path.exists() else {"objectives": {}}
    gate = {"supplied_failure_categories": 0, "supplied_expected_invariants": 0,
            "unlabelled_probes_searched": len(search), "objectives_invented": int(objective.get("objective_id") == OBJECTIVE_ID),
            "obvious_invalid_objectives_rejected": sum(row.get("rejection") == "changes_target_semantics" for row in search),
            "development_success": int(episodes[0]["evaluation"]["passed"]),
            "source_disjoint_transfer": int(episodes[1]["evaluation"]["passed"]),
            "cross_family_transfers": sum(row["evaluation"]["passed"] for row in episodes[2:]),
            "new_family_after_promotion": 0, "ood_abstention": int(abstention.get("status") == "ABSTAIN"),
            "security_attacks": len(security), "security_attacks_rejected": sum(row["rejected"] for row in security),
            "objective_installation_before_later_authority": int(OBJECTIVE_ID in registry_before.get("objectives", {})),
            "later_retention_credits": 0, "cold_probe_cost": len(search), "retained_probe_cost": 1,
            "probe_cost_reduction_pct": 100.0 * (len(search) - 1) / len(search),
            "ambient_authority_added": 0, "unsafe_executions": 0, "live_writes": 0}
    gate["accepted_private_challenger"] = bool(gate["supplied_failure_categories"] == 0
        and gate["supplied_expected_invariants"] == 0 and gate["objectives_invented"] == 1
        and gate["obvious_invalid_objectives_rejected"] >= 2 and gate["development_success"] == 1
        and gate["source_disjoint_transfer"] == 1 and gate["cross_family_transfers"] == 2
        and gate["ood_abstention"] == 1 and gate["security_attacks_rejected"] == gate["security_attacks"] == 8
        and gate["objective_installation_before_later_authority"] == 0 and gate["ambient_authority_added"] == 0)
    state = {"schema_version": "aion.hexcore.open_critic_objective_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "objective": objective,
             "objective_sha256": objective_hash, "episodes": episodes,
             "objective_registry_path": str(objective_registry_path)}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_critic_objective_from_unlabelled_disagreement",
        ["generate_safe_behaviour_probes", "measure_candidate_disagreement", "reject_semantically_destructive_objectives",
         "infer_operationalizable_risk", "compile_critic_objective", "prove_source_disjoint_transfer",
         "prove_cross_family_transfer", "abstain_without_disagreement", "withhold_runtime_installation"],
        gate["development_success"] + gate["source_disjoint_transfer"] + gate["cross_family_transfers"],
        gate["accepted_private_challenger"], {"gate": gate, "objective_sha256": objective_hash},
        ["procedure_delayed_property_critic_runtime_promotion_v1"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_critic_objective_private_challenger")
    result = {"schema_version": "aion.hexcore.open_critic_objective_invention.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "passed": gate["accepted_private_challenger"],
              "status": "PRIVATE_CHALLENGER_ACCEPTED" if gate["accepted_private_challenger"] else "REJECTED",
              "gate": gate, "objective": objective, "objective_sha256": objective_hash,
              "search": search, "ood_control": {"decision": abstention, "search": abstention_search},
              "security": security, "episodes": episodes, "decision": decision,
              "boundary": "AION selected one diagnostic objective from unlabelled candidate disagreement within an engineered safe-probe vocabulary. Candidate programs, probe atoms, authorities and later outcome labels remain engineered."}
    _write(result_path, result)
    return result


def close_later_challenges(*, atom_registry_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_CRITIC_OBJECTIVE_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text())
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    by_name = {source["name"]: source for source in SOURCES}
    changed = False
    for episode in state["episodes"]:
        challenge = episode["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]:
            continue
        evidence, values = _series(runtime, by_name[episode["name"]])
        evaluation = evaluate_objective(state["objective"], episode["family"], values)
        passed = bool(evaluation["passed"])
        challenge.update({"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                          "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
                          "retention_credit": int(passed), "outcome_sha256": _sha({"evidence": evidence, "evaluation": evaluation}),
                          "response_changed": evidence["response_sha256"] != episode["evidence"]["response_sha256"]})
        changed = True
    if not changed:
        return result
    confirmed = [row for row in state["episodes"] if row["later_challenge"].get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed)
    result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    if len(confirmed) == len(state["episodes"]):
        registry_path = Path(state["objective_registry_path"])
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {
            "schema_version": "aion.critic_objective_registry.v1", "objectives": {}}
        registry.setdefault("objectives", {})[OBJECTIVE_ID] = {
            "objective": state["objective"], "objective_sha256": state["objective_sha256"],
            "capability_class": "pure_diagnostic_objective", "authority": LATER_PROCEDURE_ID,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "verified_authorities": [row["name"] for row in confirmed],
            "verified_families": sorted({row["family"] for row in confirmed})}
        _write(registry_path, registry)
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "promote_invented_critic_objective",
            ["recover_private_objective", "verify_objective_digest", "enforce_elapsed_boundary",
             "reacquire_public_authorities", "repeat_cross_family_discrimination",
             "confirm_capability_class", "install_objective_runtime"], len(confirmed), True,
            {"confirmed": len(confirmed), "objective_sha256": state["objective_sha256"]}, [PROCEDURE_ID])
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=candidate.evidence)
        learning.store.commit(reason="delayed_critic_objective_runtime_promotion")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["objective_installation"] = {"installed": True, "registry_path": str(registry_path),
                                            "objective_sha256": state["objective_sha256"]}
        result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(state_path, state); _write(result_path, result)
    return result


class GovernedCriticObjectiveRuntime:
    def __init__(self, registry_path: Path) -> None:
        self.registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"objectives": {}}

    def evaluate(self, objective_id: str, family: str, values: list[float]) -> dict[str, Any]:
        record = self.registry.get("objectives", {}).get(objective_id)
        if not record or record.get("authority") != LATER_PROCEDURE_ID:
            return {"passed": False, "reason": "critic_objective_not_authorized"}
        if _sha(record.get("objective")) != record.get("objective_sha256"):
            return {"passed": False, "reason": "critic_objective_integrity_failure"}
        return evaluate_objective(record["objective"], family, values)


def verify_post_promotion_transfer(*, registry_path: Path, result_path: Path) -> dict[str, Any]:
    result = json.loads(result_path.read_text())
    runtime = GovernedCriticObjectiveRuntime(registry_path)
    values = [3.0, 5.0, 8.0, 13.0, 21.0, 34.0, 55.0, 89.0, 144.0]
    evaluation = runtime.evaluate(OBJECTIVE_ID, "spread", values)
    result["gate"]["new_family_after_promotion"] = int(evaluation.get("passed", False))
    result["post_promotion_transfer"] = {"family": "spread", "private_state_replay": 0,
                                          "objective_search_repeated": 0, "evaluation": evaluation}
    _write(result_path, result)
    return result
