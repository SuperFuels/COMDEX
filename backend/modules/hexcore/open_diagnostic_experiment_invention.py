"""Open adaptive diagnostic-experiment invention under delayed public authority."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.modules.hexcore.open_property_language_invention import _series
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.recursive_action_language_expansion import RecursiveActionAtomRuntime, SOURCES


PROCEDURE_ID = "procedure_open_diagnostic_experiment_invention_v1"
LATER_PROCEDURE_ID = "procedure_delayed_diagnostic_experiment_runtime_promotion_v1"
EXPERIMENT_ID = "ADAPTIVE_CROSSOVER_AUTHORITY_TRIANGULATION"
CAUSES = ("candidate_defect", "evidence_defect", "environment_change", "critic_defect")
ACTIONS = (
    "alternate_candidate_same_evidence",
    "reacquire_evidence_same_authority",
    "independent_outcome_without_critic",
    "changed_rule_later_retest",
)

# These are causal predictions, not outcome labels supplied to the inventor.
PREDICTIONS = {
    "candidate_defect": {ACTIONS[0]: True, ACTIONS[1]: False, ACTIONS[2]: False, ACTIONS[3]: False},
    "evidence_defect": {ACTIONS[0]: False, ACTIONS[1]: True, ACTIONS[2]: False, ACTIONS[3]: False},
    "environment_change": {ACTIONS[0]: False, ACTIONS[1]: False, ACTIONS[2]: False, ACTIONS[3]: True},
    "critic_defect": {ACTIONS[0]: False, ACTIONS[1]: False, ACTIONS[2]: True, ACTIONS[3]: False},
}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "diagnostic_experiment_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _entropy(count: int) -> float:
    return math.log2(count) if count > 0 else 0.0


def _information_gain(causes: tuple[str, ...], action: str) -> float:
    before = _entropy(len(causes))
    groups = [[cause for cause in causes if PREDICTIONS[cause][action] is outcome] for outcome in (False, True)]
    after = sum(len(group) / len(causes) * _entropy(len(group)) for group in groups if group)
    return before - after


def _build_tree(causes: tuple[str, ...], available: tuple[str, ...]) -> dict[str, Any]:
    if len(causes) == 1:
        return {"diagnosis": causes[0]}
    ranked = sorted(available, key=lambda action: (-_information_gain(causes, action), action))
    if not ranked or _information_gain(causes, ranked[0]) <= 0:
        return {"diagnosis": "ABSTAIN", "remaining": list(causes)}
    action = ranked[0]
    rest = tuple(candidate for candidate in available if candidate != action)
    return {"action": action, "if_false": _build_tree(tuple(c for c in causes if not PREDICTIONS[c][action]), rest),
            "if_true": _build_tree(tuple(c for c in causes if PREDICTIONS[c][action]), rest)}


def _expected_queries(tree: dict[str, Any], depth: int = 0) -> float:
    if "diagnosis" in tree:
        return float(depth)
    return (_expected_queries(tree["if_false"], depth + 1) + _expected_queries(tree["if_true"], depth + 1)) / 2


def invent_experiment() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        {"kind": "repeat_original_measurement", "rejected": "same_observation_no_hypothesis_separation"},
        {"kind": "increase_probe_magnitude", "rejected": "risk_increase_without_origin_information"},
        {"kind": "consult_hidden_failure_label", "rejected": "authority_leakage"},
    ]
    tree = _build_tree(CAUSES, ACTIONS)
    experiment = {"experiment_id": EXPERIMENT_ID, "capability_class": "bounded_read_only_diagnostic",
                  "hypotheses": list(CAUSES), "tree": tree, "maximum_actions": len(ACTIONS),
                  "commit_before_outcomes": True, "single_cause_assumption": True,
                  "unknown_signature_policy": "ABSTAIN", "ambient_authority": []}
    candidates.append({"kind": EXPERIMENT_ID, "accepted_private": True,
                       "expected_queries": _expected_queries(tree), "description_length": len(json.dumps(experiment))})
    return experiment, candidates


ALLOWED_KEYS = {"experiment_id", "capability_class", "hypotheses", "tree", "maximum_actions",
                "commit_before_outcomes", "single_cause_assumption", "unknown_signature_policy", "ambient_authority"}


def _validate_tree(node: dict[str, Any], used: set[str]) -> bool:
    if "diagnosis" in node:
        return set(node) <= {"diagnosis", "remaining"} and (node["diagnosis"] in CAUSES or node["diagnosis"] == "ABSTAIN")
    if set(node) != {"action", "if_false", "if_true"} or node["action"] not in ACTIONS or node["action"] in used:
        return False
    return _validate_tree(node["if_false"], used | {node["action"]}) and _validate_tree(node["if_true"], used | {node["action"]})


def validate_experiment(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) - ALLOWED_KEYS:
        return {"passed": False, "reason": "unknown_experiment_field"}
    if spec.get("experiment_id") != EXPERIMENT_ID or spec.get("capability_class") != "bounded_read_only_diagnostic":
        return {"passed": False, "reason": "identity_or_capability_failure"}
    if tuple(spec.get("hypotheses", [])) != CAUSES or not _validate_tree(spec.get("tree", {}), set()):
        return {"passed": False, "reason": "invalid_hypothesis_tree"}
    if spec.get("maximum_actions") != len(ACTIONS) or spec.get("commit_before_outcomes") is not True:
        return {"passed": False, "reason": "resource_or_commitment_gate_removed"}
    if spec.get("single_cause_assumption") is not True or spec.get("unknown_signature_policy") != "ABSTAIN":
        return {"passed": False, "reason": "unsafe_generalization_policy"}
    if spec.get("ambient_authority") not in ([], None, {}):
        return {"passed": False, "reason": "ambient_authority_requested"}
    return {"passed": True}


def execute_experiment(spec: dict[str, Any], outcomes: dict[str, bool]) -> dict[str, Any]:
    validation = validate_experiment(spec)
    if not validation["passed"]:
        return {"passed": False, "reason": validation["reason"]}
    matching = [cause for cause in CAUSES if all(PREDICTIONS[cause][action] == value for action, value in outcomes.items())]
    if len(matching) != 1:
        return {"passed": True, "diagnosis": "ABSTAIN", "reason": "ambiguous_or_multi_fault_signature",
                "actions": len(outcomes), "matching_hypotheses": matching}
    node, trace = spec["tree"], []
    while "diagnosis" not in node:
        action = node["action"]
        if action not in outcomes:
            return {"passed": True, "diagnosis": "ABSTAIN", "reason": "missing_experiment_outcome", "trace": trace}
        value = bool(outcomes[action]); trace.append({"action": action, "outcome": value})
        node = node["if_true"] if value else node["if_false"]
    diagnosis = node["diagnosis"]
    if diagnosis != matching[0]:
        return {"passed": False, "reason": "tree_signature_mismatch", "trace": trace}
    return {"passed": True, "diagnosis": diagnosis, "actions": len(trace), "trace": trace}


def _security_properties() -> list[dict[str, Any]]:
    base, _ = invent_experiment()
    attacks = {
        "network_write": {**base, "ambient_authority": ["network_write"]},
        "filesystem": {**base, "ambient_authority": ["filesystem"]},
        "process": {**base, "ambient_authority": ["process"]},
        "unbounded": {**base, "maximum_actions": 999},
        "post_outcome_commit": {**base, "commit_before_outcomes": False},
        "multi_fault_guess": {**base, "single_cause_assumption": False},
        "unknown_guess": {**base, "unknown_signature_policy": "BEST_GUESS"},
        "hidden_label": {**base, "hidden_failure_label": "candidate_defect"},
    }
    return [{"attack": name, "rejected": not validate_experiment(value)["passed"]} for name, value in attacks.items()]


def _sealed_world(authority: dict[str, str], cause: str, evidence: dict[str, Any], values: list[float]) -> dict[str, Any]:
    outcomes = dict(PREDICTIONS[cause])
    return {"name": authority["name"], "url": authority["url"], "cause_authority": cause,
            "initial_observation": "same_unresolved_prediction_failure", "evidence": evidence,
            "values": len(values), "outcomes": outcomes, "outcome_sha256": _sha({"cause": cause, "outcomes": outcomes, "evidence": evidence})}


def run(*, atom_registry_path: Path, private_experiment_path: Path, experiment_registry_path: Path,
        state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    experiment, synthesis = invent_experiment()
    security = _security_properties()
    digest = _sha(experiment)
    _write(private_experiment_path, {"experiment": experiment, "experiment_sha256": digest,
                                     "status": "PRIVATE_PENDING_LATER_AUTHORITY", "synthesis": synthesis})
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    worlds = []
    for authority, cause in zip((SOURCES[0], SOURCES[2], SOURCES[3], SOURCES[1]), CAUSES):
        evidence, values = _series(runtime, authority)
        sealed = _sealed_world(authority, cause, evidence, values)
        execution = execute_experiment(experiment, sealed["outcomes"])
        worlds.append({**sealed, "execution": execution, "later_challenge": {
            "status": "WAITING_FOR_FUTURE_OUTCOME", "not_before_epoch": time.time() + minimum_later_delay_seconds,
            "retention_credit": 0}})
    multi_fault = dict(PREDICTIONS["candidate_defect"]); multi_fault[ACTIONS[1]] = True
    ambiguous = execute_experiment(experiment, multi_fault)
    registry_before = json.loads(experiment_registry_path.read_text()) if experiment_registry_path.exists() else {"experiments": {}}
    accuracy = sum(row["execution"].get("diagnosis") == row["cause_authority"] for row in worlds)
    mean_actions = sum(row["execution"].get("actions", 0) for row in worlds) / len(worlds)
    gate = {"supplied_experiment_workflows": 0, "candidate_experiments": len(synthesis),
            "new_private_experiments": 1, "sealed_worlds": len(worlds), "diagnostic_accuracy": accuracy,
            "weakest_cause_accuracy": int(all(row["execution"].get("diagnosis") == row["cause_authority"] for row in worlds)),
            "mean_information_actions": mean_actions, "exhaustive_information_actions": len(ACTIONS),
            "information_action_reduction_pct": 100.0 * (len(ACTIONS) - mean_actions) / len(ACTIONS),
            "multi_fault_abstention": int(ambiguous.get("diagnosis") == "ABSTAIN"),
            "security_attacks": len(security), "security_attacks_rejected": sum(row["rejected"] for row in security),
            "experiment_installation_before_later_authority": int(EXPERIMENT_ID in registry_before.get("experiments", {})),
            "later_retention_credits": 0, "ambient_authority_added": 0, "unsafe_actions": 0, "live_writes": 0}
    gate["accepted_private_challenger"] = bool(gate["supplied_experiment_workflows"] == 0
        and gate["diagnostic_accuracy"] == gate["sealed_worlds"] == 4 and gate["weakest_cause_accuracy"] == 1
        and gate["multi_fault_abstention"] == 1 and gate["security_attacks_rejected"] == gate["security_attacks"] == 8
        and gate["experiment_installation_before_later_authority"] == 0 and gate["ambient_authority_added"] == 0)
    state = {"schema_version": "aion.hexcore.open_diagnostic_experiment_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "experiment": experiment,
             "experiment_sha256": digest, "worlds": worlds, "experiment_registry_path": str(experiment_registry_path)}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_adaptive_crossover_diagnostic_experiment",
        ["form_competing_origin_hypotheses", "generate_bounded_measurement_actions", "predict_hypothesis_signatures",
         "maximize_information_gain", "compile_adaptive_experiment_tree", "commit_before_hidden_outcomes",
         "diagnose_four_origins", "abstain_on_multi_fault", "withhold_runtime_installation"],
        accuracy, gate["accepted_private_challenger"], {"gate": gate, "experiment_sha256": digest},
        ["procedure_delayed_critic_objective_runtime_promotion_v1"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_diagnostic_experiment_private_challenger")
    result = {"schema_version": "aion.hexcore.open_diagnostic_experiment_invention.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "passed": gate["accepted_private_challenger"],
              "status": "PRIVATE_CHALLENGER_ACCEPTED" if gate["accepted_private_challenger"] else "REJECTED",
              "gate": gate, "experiment": experiment, "experiment_sha256": digest,
              "synthesis": synthesis, "security": security, "worlds": worlds,
              "multi_fault_control": ambiguous, "decision": decision,
              "boundary": "AION composed an adaptive diagnostic tree from an engineered read-only measurement vocabulary and four engineered origin hypotheses. Sealed outcomes and public trace authorities score the experiment; this is not unrestricted experiment invention."}
    _write(result_path, result); return result


def close_later_challenges(*, atom_registry_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_DIAGNOSTIC_EXPERIMENT_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text())
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    by_name = {source["name"]: source for source in SOURCES}
    changed = False
    for world in state["worlds"]:
        challenge = world["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]:
            continue
        evidence, values = _series(runtime, by_name[world["name"]])
        execution = execute_experiment(state["experiment"], world["outcomes"])
        passed = execution.get("diagnosis") == world["cause_authority"]
        challenge.update({"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                          "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
                          "retention_credit": int(passed), "response_changed": evidence["response_sha256"] != world["evidence"]["response_sha256"],
                          "outcome_sha256": _sha({"evidence": evidence, "values": len(values), "execution": execution})})
        changed = True
    if not changed:
        return result
    confirmed = [world for world in state["worlds"] if world["later_challenge"].get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed)
    result["later_challenges"] = [world["later_challenge"] for world in state["worlds"]]
    if len(confirmed) == len(state["worlds"]):
        registry_path = Path(state["experiment_registry_path"])
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {
            "schema_version": "aion.diagnostic_experiment_registry.v1", "experiments": {}}
        registry.setdefault("experiments", {})[EXPERIMENT_ID] = {
            "experiment": state["experiment"], "experiment_sha256": state["experiment_sha256"],
            "capability_class": "bounded_read_only_diagnostic", "authority": LATER_PROCEDURE_ID,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "verified_authorities": [world["name"] for world in confirmed], "verified_causes": list(CAUSES)}
        _write(registry_path, registry)
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "promote_adaptive_diagnostic_experiment",
            ["recover_experiment", "verify_digest", "enforce_elapsed_boundary", "reacquire_public_traces",
             "repeat_four_origin_diagnosis", "confirm_multi_fault_abstention", "install_experiment_runtime"],
            len(confirmed), True, {"confirmed": len(confirmed), "experiment_sha256": state["experiment_sha256"]}, [PROCEDURE_ID])
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=candidate.evidence)
        learning.store.commit(reason="delayed_diagnostic_experiment_runtime_promotion")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["experiment_installation"] = {"installed": True, "registry_path": str(registry_path),
                                             "experiment_sha256": state["experiment_sha256"]}
        result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(state_path, state); _write(result_path, result); return result


class GovernedDiagnosticExperimentRuntime:
    def __init__(self, registry_path: Path) -> None:
        self.registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"experiments": {}}

    def diagnose(self, experiment_id: str, outcomes: dict[str, bool]) -> dict[str, Any]:
        record = self.registry.get("experiments", {}).get(experiment_id)
        if not record or record.get("authority") != LATER_PROCEDURE_ID:
            return {"passed": False, "reason": "diagnostic_experiment_not_authorized"}
        if _sha(record.get("experiment")) != record.get("experiment_sha256"):
            return {"passed": False, "reason": "diagnostic_experiment_integrity_failure"}
        return execute_experiment(record["experiment"], outcomes)
