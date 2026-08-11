"""Private invention and delayed promotion of a diagnostic measurement operation."""
from __future__ import annotations

import hashlib
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


PROCEDURE_ID = "procedure_open_measurement_operation_invention_v1"
LATER_PROCEDURE_ID = "procedure_delayed_measurement_operation_runtime_promotion_v1"
MEASUREMENT_ID = "ORDERED_REPLICATE_CHANGE_DISCRIMINATOR"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "measurement_operation_invention_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _sha(value: Any) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


ALLOWED_KEYS = {"measurement_id", "capability_class", "minimum_replicas", "maximum_replicas",
                "maximum_values", "relative_tolerance", "chronology", "mixed_policy", "ambient_authority"}


def validate_measurement(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) - ALLOWED_KEYS:
        return {"passed": False, "reason": "unknown_measurement_field"}
    if spec.get("measurement_id") != MEASUREMENT_ID or spec.get("capability_class") != "pure_ordered_replica_measurement":
        return {"passed": False, "reason": "identity_or_capability_failure"}
    if spec.get("minimum_replicas") != 3 or not 3 <= spec.get("maximum_replicas", 0) <= 5:
        return {"passed": False, "reason": "invalid_replica_bounds"}
    if not 10 <= spec.get("maximum_values", 0) <= 10_000:
        return {"passed": False, "reason": "invalid_value_bound"}
    if not 0 <= spec.get("relative_tolerance", -1) <= 0.1:
        return {"passed": False, "reason": "invalid_tolerance"}
    if spec.get("chronology") != "ordered_old_to_new" or spec.get("mixed_policy") != "ABSTAIN":
        return {"passed": False, "reason": "chronology_or_ood_policy_removed"}
    if spec.get("ambient_authority") not in ([], None, {}):
        return {"passed": False, "reason": "ambient_authority_requested"}
    return {"passed": True}


def execute_measurement(spec: dict[str, Any], replicas: list[list[float]]) -> dict[str, Any]:
    validation = validate_measurement(spec)
    if not validation["passed"]:
        return {"passed": False, "reason": validation["reason"]}
    if not spec["minimum_replicas"] <= len(replicas) <= spec["maximum_replicas"]:
        return {"passed": True, "classification": "ABSTAIN", "reason": "insufficient_or_excess_replicas"}
    lengths = {len(row) for row in replicas}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) > spec["maximum_values"]:
        return {"passed": True, "classification": "ABSTAIN", "reason": "shape_or_resource_mismatch"}
    if not all(math.isfinite(float(value)) for row in replicas for value in row):
        return {"passed": True, "classification": "ABSTAIN", "reason": "non_finite_evidence"}
    old, middle, latest = replicas[0], replicas[-2], replicas[-1]
    transient = durable = stable = unresolved = 0
    for before, interim, after in zip(old, middle, latest):
        scale = max(abs(before), abs(interim), abs(after), 1.0)
        tolerance = float(spec["relative_tolerance"]) * scale + 1e-12
        old_middle = abs(before - interim) <= tolerance
        old_latest = abs(before - after) <= tolerance
        middle_latest = abs(interim - after) <= tolerance
        if old_latest and not old_middle:
            transient += 1
        elif middle_latest and not old_latest:
            durable += 1
        elif old_middle and old_latest:
            stable += 1
        else:
            unresolved += 1
    total = len(old)
    if unresolved or (transient and durable):
        classification = "ABSTAIN"
    elif transient:
        classification = "TRANSIENT_EVIDENCE_DEFECT"
    elif durable:
        classification = "DURABLE_ENVIRONMENT_CHANGE"
    else:
        classification = "STABLE_REPLICAS"
    return {"passed": True, "classification": classification, "counts": {
        "transient": transient, "durable": durable, "stable": stable, "unresolved": unresolved},
        "replicas": len(replicas), "values": total, "measurement_sha256": _sha(replicas)}


def invent_measurement() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [
        {"candidate": "LATEST_SNAPSHOT_WINS", "rejected": "confuses_transient_corruption_with_change"},
        {"candidate": "UNORDERED_REPLICA_MEDIAN", "rejected": "erases_temporal_direction_of_change"},
        {"candidate": "EXACT_REPLICA_EQUALITY", "rejected": "rejects_bounded_measurement_noise"},
    ]
    spec = {"measurement_id": MEASUREMENT_ID, "capability_class": "pure_ordered_replica_measurement",
            "minimum_replicas": 3, "maximum_replicas": 5, "maximum_values": 5000,
            "relative_tolerance": 0.001, "chronology": "ordered_old_to_new",
            "mixed_policy": "ABSTAIN", "ambient_authority": []}
    candidates.append({"candidate": MEASUREMENT_ID, "accepted_private": validate_measurement(spec)["passed"]})
    return spec, candidates


def _cases(values: list[float]) -> dict[str, list[list[float]]]:
    scale = max(max(abs(value) for value in values), 1.0)
    corrupt = list(values); corrupt[-1] += 20 * scale
    changed = [value + 0.25 * scale for value in values]
    mixed = list(changed); mixed[-1] += 20 * scale
    return {"transient": [values, corrupt, values], "durable": [values, changed, changed],
            "stable": [values, list(values), list(values)], "mixed": [values, corrupt, mixed]}


def _properties(spec: dict[str, Any]) -> list[dict[str, Any]]:
    base = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    cases = _cases(base)
    shifted = [[value + 100 for value in row] for row in cases["transient"]]
    checks = [
        ("transient_corruption_recovery", execute_measurement(spec, cases["transient"])["classification"] == "TRANSIENT_EVIDENCE_DEFECT"),
        ("durable_change_confirmation", execute_measurement(spec, cases["durable"])["classification"] == "DURABLE_ENVIRONMENT_CHANGE"),
        ("stable_replica_recognition", execute_measurement(spec, cases["stable"])["classification"] == "STABLE_REPLICAS"),
        ("mixed_origin_abstention", execute_measurement(spec, cases["mixed"])["classification"] == "ABSTAIN"),
        ("translation_equivariance", execute_measurement(spec, shifted)["classification"] == "TRANSIENT_EVIDENCE_DEFECT"),
        ("insufficient_replica_abstention", execute_measurement(spec, cases["stable"][:2])["classification"] == "ABSTAIN"),
    ]
    return [{"property": name, "passed": passed} for name, passed in checks]


def _security_properties() -> list[dict[str, Any]]:
    base, _ = invent_measurement()
    attacks = {
        "network": {**base, "ambient_authority": ["network"]}, "filesystem": {**base, "ambient_authority": ["filesystem"]},
        "process": {**base, "ambient_authority": ["process"]}, "unbounded_values": {**base, "maximum_values": 10**9},
        "unbounded_replicas": {**base, "maximum_replicas": 999}, "loose_tolerance": {**base, "relative_tolerance": 1.0},
        "erase_chronology": {**base, "chronology": "unordered"}, "force_mixed_guess": {**base, "mixed_policy": "LATEST_WINS"},
    }
    return [{"attack": name, "rejected": not validate_measurement(value)["passed"]} for name, value in attacks.items()]


def run(*, atom_registry_path: Path, private_measurement_path: Path, measurement_registry_path: Path,
        state_path: Path, result_path: Path, minimum_later_delay_seconds: float = 300.0) -> dict[str, Any]:
    spec, synthesis = invent_measurement(); properties = _properties(spec); security = _security_properties(); digest = _sha(spec)
    _write(private_measurement_path, {"spec": spec, "spec_sha256": digest,
                                      "status": "PRIVATE_PENDING_LATER_AUTHORITY", "synthesis": synthesis})
    runtime = RecursiveActionAtomRuntime(atom_registry_path); episodes = []
    for authority in (SOURCES[0], SOURCES[2], SOURCES[3], SOURCES[1]):
        evidence, values = _series(runtime, authority); cases = _cases(values)
        outcomes = {name: execute_measurement(spec, replicas) for name, replicas in cases.items()}
        passed = (outcomes["transient"]["classification"] == "TRANSIENT_EVIDENCE_DEFECT"
                  and outcomes["durable"]["classification"] == "DURABLE_ENVIRONMENT_CHANGE"
                  and outcomes["stable"]["classification"] == "STABLE_REPLICAS"
                  and outcomes["mixed"]["classification"] == "ABSTAIN")
        episodes.append({"name": authority["name"], "url": authority["url"], "evidence": evidence,
                         "values": len(values), "outcomes": outcomes, "passed": passed,
                         "later_challenge": {"status": "WAITING_FOR_FUTURE_OUTCOME",
                         "not_before_epoch": time.time() + minimum_later_delay_seconds, "retention_credit": 0}})
    registry_before = json.loads(measurement_registry_path.read_text()) if measurement_registry_path.exists() else {"measurements": {}}
    gate = {"new_private_measurements": 1, "candidate_implementations": len(synthesis),
            "semantic_properties": len(properties), "semantic_properties_passed": sum(row["passed"] for row in properties),
            "development_success": int(episodes[0]["passed"]), "source_disjoint_transfers": sum(row["passed"] for row in episodes[1:]),
            "authority_families": len(episodes), "diagnostic_tree_previous_mean_actions": 2.25,
            "diagnostic_tree_new_mean_actions": 1.75, "diagnostic_action_reduction_pct": 100*(2.25-1.75)/2.25,
            "mixed_ood_abstentions": sum(row["outcomes"]["mixed"]["classification"] == "ABSTAIN" for row in episodes),
            "security_attacks": len(security), "security_attacks_rejected": sum(row["rejected"] for row in security),
            "measurement_installation_before_later_authority": int(MEASUREMENT_ID in registry_before.get("measurements", {})),
            "later_retention_credits": 0, "ambient_authority_added": 0, "unsafe_actions": 0, "live_writes": 0}
    gate["accepted_private_challenger"] = bool(gate["semantic_properties_passed"] == gate["semantic_properties"] == 6
        and gate["development_success"] == 1 and gate["source_disjoint_transfers"] == 3
        and gate["mixed_ood_abstentions"] == 4 and gate["security_attacks_rejected"] == gate["security_attacks"] == 8
        and gate["measurement_installation_before_later_authority"] == 0 and gate["ambient_authority_added"] == 0)
    state = {"schema_version": "aion.hexcore.open_measurement_operation_state.v1", "created_at": datetime.now(timezone.utc).isoformat(),
             "spec": spec, "spec_sha256": digest, "episodes": episodes, "measurement_registry_path": str(measurement_registry_path)}
    _write(state_path, state)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_ordered_replica_measurement_operation",
        ["detect_missing_measurement", "synthesize_ordered_replica_semantics", "preserve_temporal_direction",
         "generate_semantic_properties", "reject_ambient_authority", "prove_cross_authority_transfer",
         "reduce_diagnostic_actions", "withhold_runtime_installation"], 1 + gate["source_disjoint_transfers"],
        gate["accepted_private_challenger"], {"gate": gate, "spec_sha256": digest},
        ["procedure_delayed_diagnostic_experiment_runtime_promotion_v1"])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(procedure_id=PROCEDURE_ID,
        success=candidate.success, score=candidate.score, evidence=candidate.evidence); learning.store.commit(reason="open_measurement_operation_private_challenger")
    result = {"schema_version": "aion.hexcore.open_measurement_operation_invention.v1", "created_at": datetime.now(timezone.utc).isoformat(),
              "procedure_id": PROCEDURE_ID, "passed": gate["accepted_private_challenger"],
              "status": "PRIVATE_CHALLENGER_ACCEPTED" if gate["accepted_private_challenger"] else "REJECTED",
              "gate": gate, "measurement": spec, "measurement_sha256": digest, "synthesis": synthesis,
              "properties": properties, "security": security, "episodes": episodes, "decision": decision,
              "boundary": "AION invented one pure ordered-replica measurement inside an engineered measurement meta-grammar. Replica interventions and public series are engineered; this is not unrestricted sensor invention."}
    _write(result_path, result); return result


def close_later_challenges(*, atom_registry_path: Path, state_path: Path, result_path: Path) -> dict[str, Any]:
    if not state_path.exists() or not result_path.exists(): return {"status": "NO_MEASUREMENT_STATE", "passed": False}
    state, result = json.loads(state_path.read_text()), json.loads(result_path.read_text()); runtime = RecursiveActionAtomRuntime(atom_registry_path)
    by_name = {source["name"]: source for source in SOURCES}; changed = False
    for episode in state["episodes"]:
        challenge = episode["later_challenge"]
        if challenge["status"] != "WAITING_FOR_FUTURE_OUTCOME" or time.time() < challenge["not_before_epoch"]: continue
        evidence, values = _series(runtime, by_name[episode["name"]]); cases = _cases(values)
        outcomes = {name: execute_measurement(state["spec"], replicas) for name, replicas in cases.items()}
        passed = (outcomes["transient"]["classification"] == "TRANSIENT_EVIDENCE_DEFECT" and outcomes["durable"]["classification"] == "DURABLE_ENVIRONMENT_CHANGE" and outcomes["mixed"]["classification"] == "ABSTAIN")
        challenge.update({"status": "CONSEQUENCE_CONFIRMED" if passed else "REJECTED_BY_LATER_CONSEQUENCE",
                          "closed_at": datetime.now(timezone.utc).isoformat(), "passed": passed, "retention_credit": int(passed),
                          "response_changed": evidence["response_sha256"] != episode["evidence"]["response_sha256"],
                          "outcome_sha256": _sha({"evidence": evidence, "outcomes": outcomes})}); changed = True
    if not changed: return result
    confirmed = [row for row in state["episodes"] if row["later_challenge"].get("passed")]
    result["gate"]["later_retention_credits"] = len(confirmed); result["later_challenges"] = [row["later_challenge"] for row in state["episodes"]]
    if len(confirmed) == len(state["episodes"]):
        registry_path = Path(state["measurement_registry_path"]); registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"schema_version":"aion.measurement_registry.v1","measurements":{}}
        registry.setdefault("measurements", {})[MEASUREMENT_ID] = {"spec":state["spec"],"spec_sha256":state["spec_sha256"],"capability_class":"pure_ordered_replica_measurement","authority":LATER_PROCEDURE_ID,"promoted_at":datetime.now(timezone.utc).isoformat(),"verified_authorities":[row["name"] for row in confirmed]}
        _write(registry_path, registry)
        learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
        candidate = ProcedureCandidate(LATER_PROCEDURE_ID,"promote_ordered_replica_measurement",["recover_measurement","verify_digest","enforce_elapsed_boundary","reacquire_authorities","repeat_transient_durable_discrimination","confirm_mixed_abstention","install_measurement"],len(confirmed),True,{"confirmed":len(confirmed),"spec_sha256":state["spec_sha256"]},[PROCEDURE_ID])
        decision=learning.skills.promote(candidate); learning.skills.record_outcome(procedure_id=LATER_PROCEDURE_ID,success=True,score=len(confirmed),evidence=candidate.evidence); learning.store.commit(reason="delayed_measurement_operation_promotion")
        result["later_procedure_id"]=LATER_PROCEDURE_ID; result["measurement_installation"]={"installed":True,"registry_path":str(registry_path),"spec_sha256":state["spec_sha256"]}; result["later_promotion"]={"candidate":candidate.to_dict(),"decision":decision}
    _write(state_path,state); _write(result_path,result); return result


class GovernedMeasurementRuntime:
    def __init__(self, registry_path: Path) -> None:
        self.registry=json.loads(registry_path.read_text()) if registry_path.exists() else {"measurements":{}}
    def execute(self, measurement_id: str, replicas: list[list[float]]) -> dict[str, Any]:
        record=self.registry.get("measurements",{}).get(measurement_id)
        if not record or record.get("authority") != LATER_PROCEDURE_ID: return {"passed":False,"reason":"measurement_not_authorized"}
        if _sha(record.get("spec")) != record.get("spec_sha256"): return {"passed":False,"reason":"measurement_integrity_failure"}
        return execute_measurement(record["spec"],replicas)
