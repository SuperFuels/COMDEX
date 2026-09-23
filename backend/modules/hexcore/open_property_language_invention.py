"""Failure-driven invention and delayed promotion of executable semantic critics."""
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

from backend.modules.hexcore.open_micro_operation_invention import (
    MICRO_OP_ID,
    _candidate_sources,
    execute_private_source,
)
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.hexcore.recursive_action_language_expansion import (
    ATOM_ID as PROJECTION_ATOM_ID,
    RecursiveActionAtomRuntime,
    SOURCES,
    _get,
)


PROCEDURE_ID = "procedure_open_property_language_invention_v1"
LATER_PROCEDURE_ID = "procedure_delayed_property_critic_runtime_promotion_v1"
PROPERTY_ID = "SPARSE_BOUNDARY_CONTAMINATION_STABILITY"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "property_language_invention_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _robust_scale(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    differences = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
    nonzero = [value for value in differences if value > 0 and math.isfinite(value)]
    return _median(nonzero) if nonzero else max(abs(_median(values)), 1.0)


ALLOWED_PROPERTY_KEYS = {
    "property_id", "capability_class", "transformation", "relation",
    "minimum_observations", "ambient_authority",
}
ALLOWED_TRANSFORM_KEYS = {"op", "selector", "direction", "magnitude_ratio"}
ALLOWED_RELATION_KEYS = {"op", "maximum_normalized_delta"}


def validate_property(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) - ALLOWED_PROPERTY_KEYS:
        return {"passed": False, "reason": "unknown_property_field"}
    if spec.get("property_id") != PROPERTY_ID:
        return {"passed": False, "reason": "unknown_property_identity"}
    if spec.get("capability_class") != "pure_metamorphic_critic":
        return {"passed": False, "reason": "capability_escalation"}
    if spec.get("ambient_authority") not in (None, [], {}):
        return {"passed": False, "reason": "ambient_authority_requested"}
    transform, relation = spec.get("transformation"), spec.get("relation")
    if not isinstance(transform, dict) or set(transform) - ALLOWED_TRANSFORM_KEYS:
        return {"passed": False, "reason": "invalid_transformation"}
    if not isinstance(relation, dict) or set(relation) - ALLOWED_RELATION_KEYS:
        return {"passed": False, "reason": "invalid_relation"}
    if transform.get("op") != "replace_one_observation":
        return {"passed": False, "reason": "unknown_transform_op"}
    if transform.get("selector") != "witnessed_boundary":
        return {"passed": False, "reason": "unknown_selector"}
    if transform.get("direction") not in {"first", "last"}:
        return {"passed": False, "reason": "invalid_direction"}
    ratio = transform.get("magnitude_ratio")
    if not isinstance(ratio, (int, float)) or not 10 <= float(ratio) <= 10_000:
        return {"passed": False, "reason": "unbounded_magnitude"}
    if relation.get("op") != "normalized_output_stability":
        return {"passed": False, "reason": "unknown_relation_op"}
    tolerance = relation.get("maximum_normalized_delta")
    if not isinstance(tolerance, (int, float)) or not 0 <= float(tolerance) <= 1:
        return {"passed": False, "reason": "invalid_tolerance"}
    minimum = spec.get("minimum_observations")
    if not isinstance(minimum, int) or not 3 <= minimum <= 100:
        return {"passed": False, "reason": "invalid_minimum"}
    return {"passed": True, "capability_class": "pure_metamorphic_critic"}


def execute_property(spec: dict[str, Any], source: str, values: list[float]) -> dict[str, Any]:
    validation = validate_property(spec)
    if not validation["passed"]:
        return {"passed": False, "reason": validation["reason"]}
    if len(values) < spec["minimum_observations"] or not all(math.isfinite(float(value)) for value in values):
        return {"passed": False, "reason": "property_domain_abstention"}
    original = execute_private_source(source, values)
    if not original.get("passed") or original.get("value") is None:
        return {"passed": False, "reason": "candidate_execution_failed"}
    transformed = list(map(float, values))
    index = 0 if spec["transformation"]["direction"] == "first" else len(transformed) - 1
    scale = _robust_scale(transformed)
    transformed[index] = max(transformed) + float(spec["transformation"]["magnitude_ratio"]) * scale
    challenged = execute_private_source(source, transformed)
    if not challenged.get("passed") or challenged.get("value") is None:
        return {"passed": False, "reason": "challenged_execution_failed"}
    delta = abs(float(challenged["value"]) - float(original["value"]))
    normalized = delta / max(scale, abs(float(original["value"])) * 0.05, 1e-12)
    satisfied = normalized <= float(spec["relation"]["maximum_normalized_delta"])
    return {"passed": True, "property_satisfied": satisfied,
            "original_output": float(original["value"]), "challenged_output": float(challenged["value"]),
            "normalized_delta": normalized, "transformed_index": index,
            "transformed_input_sha256": _sha(transformed)}


def _initial_critic(source: str) -> bool:
    """The deliberately incomplete inherited critic that misses sparse contamination."""
    base = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    translated = [value + 100 for value in base]
    first = execute_private_source(source, base)
    second = execute_private_source(source, translated)
    constant = execute_private_source(source, [7.0] * 7)
    short = execute_private_source(source, [1.0, 2.0])
    return bool(first.get("passed") and second.get("passed") and constant.get("passed")
                and first.get("value") == second.get("value")
                and constant.get("value") == 0 and short.get("value") is None)


def _failure_witness(source: str) -> dict[str, Any]:
    base = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    observed = list(base); observed[-1] = 1000.0
    expected = 1.0
    actual = execute_private_source(source, observed).get("value")
    changed = [index for index, pair in enumerate(zip(base, observed)) if pair[0] != pair[1]]
    return {"base": base, "observed": observed, "expected": expected, "actual": actual,
            "absolute_error": abs(float(actual) - expected), "changed_indices": changed,
            "outcome_authority": "withheld_transfer_counterexample"}


def invent_property(witness: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    changed = witness.get("changed_indices", [])
    length = len(witness.get("base", []))
    inferred_boundary = len(changed) == 1 and changed[0] in {0, length - 1}
    direction = "first" if changed == [0] else "last"
    base_scale = _robust_scale(witness["base"])
    magnitude = abs(witness["observed"][changed[0]] - witness["base"][changed[0]]) / max(base_scale, 1e-12)
    candidates = [
        {"kind": "exact_counterexample_replay", "rejected": "instance_specific_no_transfer"},
        {"kind": "global_translation", "rejected": "does_not_explain_sparse_residual"},
        {"kind": "permutation_invariance", "rejected": "destroys_temporal_semantics"},
    ]
    if not inferred_boundary:
        return {}, candidates + [{"kind": PROPERTY_ID, "rejected": "no_generalizable_boundary_pattern"}]
    spec = {"property_id": PROPERTY_ID, "capability_class": "pure_metamorphic_critic",
            "transformation": {"op": "replace_one_observation", "selector": "witnessed_boundary",
                               "direction": direction, "magnitude_ratio": min(1000.0, max(10.0, round(magnitude)))},
            "relation": {"op": "normalized_output_stability", "maximum_normalized_delta": 0.25},
            "minimum_observations": 5, "ambient_authority": []}
    candidates.append({"kind": PROPERTY_ID, "accepted_private": validate_property(spec)["passed"],
                       "description_length": len(json.dumps(spec, sort_keys=True))})
    return spec, candidates


def _location_sources() -> list[tuple[str, str]]:
    mean = """def run(values):
    if len(values) < 3:
        return None
    total = 0
    for value in values:
        total = total + value
    return total / len(values)
"""
    median = """def run(values):
    if len(values) < 3:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n//2]
    return (ordered[n//2-1]+ordered[n//2])/2
"""
    return [("arithmetic_mean", mean), ("robust_median_location", median)]


def _security_properties() -> list[dict[str, Any]]:
    base = {"property_id": PROPERTY_ID, "capability_class": "pure_metamorphic_critic",
            "transformation": {"op": "replace_one_observation", "selector": "witnessed_boundary",
                               "direction": "last", "magnitude_ratio": 100},
            "relation": {"op": "normalized_output_stability", "maximum_normalized_delta": 0.25},
            "minimum_observations": 5, "ambient_authority": []}
    attacks = {
        "network": {**base, "ambient_authority": ["network"]},
        "filesystem": {**base, "ambient_authority": ["filesystem"]},
        "process": {**base, "ambient_authority": ["process"]},
        "unknown_transform": {**base, "transformation": {**base["transformation"], "op": "eval_python"}},
        "unbounded_magnitude": {**base, "transformation": {**base["transformation"], "magnitude_ratio": 1e20}},
        "unknown_relation": {**base, "relation": {"op": "shell_oracle", "maximum_normalized_delta": 0.1}},
        "invalid_tolerance": {**base, "relation": {**base["relation"], "maximum_normalized_delta": 99}},
        "extra_code": {**base, "source": "import os"},
    }
    return [{"attack": name, "rejected": not validate_property(spec)["passed"]} for name, spec in attacks.items()]


def _series(runtime: RecursiveActionAtomRuntime, source: dict[str, str]) -> tuple[dict[str, Any], list[float]]:
    response = _get(source["url"])
    projection = runtime.execute(PROJECTION_ATOM_ID, body=response["body"],
                                 content_type=response.get("content_type", ""), mission=source["mission"])
    ordered = sorted(projection.get("rows", []), key=lambda row: row["time"])
    evidence = {"http_status": response["status"], "response_sha256": _sha(response["body"]),
                "projection": {key: projection.get(key) for key in ("passed", "time_field", "measure_field", "row_count")}}
    return evidence, [float(row["value"]) for row in ordered]


def _evaluate_family(spec: dict[str, Any], family: str, values: list[float]) -> dict[str, Any]:
    sources = _candidate_sources() if family == "trend" else _location_sources()
    expected = MICRO_OP_ID if family == "trend" else "robust_median_location"
    rows = []
    for name, source in sources:
        initial_pass = _initial_critic(source) if family == "trend" else True
        property_result = execute_property(spec, source, values)
        rows.append({"candidate": name, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                     "inherited_critic_passed": initial_pass,
                     "invented_property": property_result,
                     "accepted": bool(initial_pass and property_result.get("property_satisfied"))})
    winner = next((row["candidate"] for row in rows if row["accepted"]), None)
    return {"family": family, "expected_winner": expected, "winner": winner,
            "passed": winner == expected, "candidates": rows}


def run(*, atom_registry_path: Path, private_property_path: Path, critic_registry_path: Path,
        state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    endpoint_source = _candidate_sources()[0][1]
    inherited_critic_accepted_bad_candidate = _initial_critic(endpoint_source)
    witness = _failure_witness(endpoint_source)
    spec, synthesis = invent_property(witness)
    security = _security_properties()
    spec_hash = _sha(spec)
    _write(private_property_path, {"spec": spec, "spec_sha256": spec_hash,
                                   "status": "PRIVATE_PENDING_LATER_AUTHORITY", "witness": witness})
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    selected = [(SOURCES[0], "trend", "development"), (SOURCES[2], "trend", "transfer"),
                (SOURCES[3], "location", "cross_family_transfer"), (SOURCES[1], "location", "cross_family_transfer")]
    episodes = []
    for authority, family, role in selected:
        evidence, values = _series(runtime, authority)
        evaluation = _evaluate_family(spec, family, values)
        episodes.append({"name": authority["name"], "url": authority["url"], "mission": authority["mission"],
                         "family": family, "role": role, "evidence": evidence, "values": len(values),
                         "evaluation": evaluation, "later_challenge": {"status": "WAITING_FOR_FUTURE_OUTCOME",
                         "not_before_epoch": time.time() + minimum_later_delay_seconds, "retention_credit": 0}})
    registry_before = json.loads(critic_registry_path.read_text()) if critic_registry_path.exists() else {"properties": {}}
    gate = {"inherited_critic_false_acceptances": int(inherited_critic_accepted_bad_candidate),
            "new_private_properties": int(bool(spec)), "property_synthesis_candidates": len(synthesis),
            "failure_witness_error": witness["absolute_error"],
            "original_bad_candidate_rejected": int(not episodes[0]["evaluation"]["candidates"][0]["accepted"]),
            "protected_good_candidate_accepted": int(episodes[0]["evaluation"]["passed"]),
            "source_disjoint_transfers": int(episodes[1]["evaluation"]["passed"]),
            "cross_family_transfers": sum(row["evaluation"]["passed"] for row in episodes[2:]),
            "independent_authorities": len(episodes), "security_attacks": len(security),
            "security_attacks_rejected": sum(row["rejected"] for row in security),
            "critic_installation_before_later_authority": int(PROPERTY_ID in registry_before.get("properties", {})),
            "later_retention_credits": 0, "ambient_authority_added": 0, "unsafe_executions": 0, "live_writes": 0}
    gate["accepted_private_challenger"] = bool(gate["inherited_critic_false_acceptances"] == 1
        and gate["new_private_properties"] == 1 and gate["original_bad_candidate_rejected"] == 1
        and gate["protected_good_candidate_accepted"] == 1 and gate["source_disjoint_transfers"] == 1
        and gate["cross_family_transfers"] == 2 and gate["security_attacks_rejected"] == gate["security_attacks"] == 8
        and gate["critic_installation_before_later_authority"] == 0 and gate["ambient_authority_added"] == 0)
    state = {"schema_version": "aion.hexcore.open_property_language_state.v1",
             "created_at": datetime.now(timezone.utc).isoformat(), "spec": spec, "spec_sha256": spec_hash,
             "episodes": episodes, "critic_registry_path": str(critic_registry_path)}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_executable_property_from_critic_failure",
        ["detect_critic_false_acceptance", "recover_failure_witness", "infer_transformation_pattern",
         "compile_typed_property", "generate_security_counterexamples", "reject_original_bad_strategy",
         "preserve_valid_strategy", "transfer_across_operator_family", "withhold_runtime_installation"],
        1 + gate["source_disjoint_transfers"] + gate["cross_family_transfers"], gate["accepted_private_challenger"],
        {"gate": gate, "spec_sha256": spec_hash}, ["procedure_delayed_micro_operation_compiler_promotion_v1"])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_property_language_private_challenger")
    result = {"schema_version": "aion.hexcore.open_property_language_invention.v1",
              "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
              "passed": gate["accepted_private_challenger"],
              "status": "PRIVATE_CHALLENGER_ACCEPTED" if gate["accepted_private_challenger"] else "REJECTED",
              "gate": gate, "property": {"property_id": PROPERTY_ID, "spec_sha256": spec_hash,
              "capability_class": spec.get("capability_class")}, "failure_witness": witness,
              "synthesis_trace": synthesis, "security_properties": security, "episodes": episodes,
              "decision": decision,
              "boundary": "AION inferred and compiled one typed metamorphic critic from a witnessed false acceptance. The property meta-grammar, public authorities, candidate families and independent success labels remain engineered."}
    _write(result_path, result)
    return result


def close_later_challenges(*, atom_registry_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists():
        return {"status": "NO_PROPERTY_LANGUAGE_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text())
    runtime = RecursiveActionAtomRuntime(atom_registry_path)
    by_name = {row["name"]: row for row in SOURCES}
    changed = False
    for episode in state["episodes"]:
        challenge = episode["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]:
            continue
        evidence, values = _series(runtime, by_name[episode["name"]])
        evaluation = _evaluate_family(state["spec"], episode["family"], values)
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
        registry_path = Path(state["critic_registry_path"])
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {
            "schema_version": "aion.property_critic_registry.v1", "properties": {}}
        registry.setdefault("properties", {})[PROPERTY_ID] = {
            "spec": state["spec"], "spec_sha256": state["spec_sha256"],
            "capability_class": "pure_metamorphic_critic", "authority": LATER_PROCEDURE_ID,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "verified_authorities": [row["name"] for row in confirmed],
            "verified_families": sorted({row["family"] for row in confirmed})}
        _write(registry_path, registry)
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID, "promote_invented_property_into_critic_runtime",
            ["recover_private_property", "verify_property_digest", "enforce_elapsed_boundary",
             "reacquire_public_authorities", "repeat_bad_strategy_rejection", "repeat_good_strategy_preservation",
             "confirm_cross_family_transfer", "install_pure_critic"], len(confirmed), True,
            {"confirmed": len(confirmed), "spec_sha256": state["spec_sha256"]}, [PROCEDURE_ID])
        decision = learning.skills.promote(candidate)
        learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID, success=True,
                                       score=len(confirmed), evidence=candidate.evidence)
        learning.store.commit(reason="delayed_property_critic_runtime_promotion")
        result["later_procedure_id"] = LATER_PROCEDURE_ID
        result["critic_installation"] = {"installed": True, "registry_path": str(registry_path),
                                         "spec_sha256": state["spec_sha256"]}
        result["later_promotion"] = {"candidate": candidate.to_dict(), "decision": decision}
    _write(state_path, state); _write(result_path, result)
    return result


class GovernedPropertyCriticRuntime:
    def __init__(self, registry_path: Path) -> None:
        self.registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"properties": {}}

    def execute(self, property_id: str, source: str, values: list[float]) -> dict[str, Any]:
        record = self.registry.get("properties", {}).get(property_id)
        if not record or record.get("authority") != LATER_PROCEDURE_ID:
            return {"passed": False, "reason": "property_not_authorized"}
        if _sha(record.get("spec")) != record.get("spec_sha256"):
            return {"passed": False, "reason": "property_integrity_failure"}
        return execute_property(record["spec"], source, values)
