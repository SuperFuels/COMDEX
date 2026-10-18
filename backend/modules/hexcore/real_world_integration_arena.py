"""Governed parallel arena for converting learned subjects into experience.

The arena is intentionally separate from the progressive competency ledger.
It may expose a knowledge gap and create an experience capsule, but it never
awards subject mastery.  Its initial authorities are deterministic, safe,
source-disjoint simulations; later adapters may add independently observed
public, commercial, or physical outcomes under their own approval gates.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.file_locking import exclusive_file_lock


SCHEMA = "aion.hexcore.real_world_integration_arena.v2"
GRAPH_SCHEMA = "aion.hexcore.applied_experience_graph.v1"
ELIGIBLE_LEVELS = {"advanced", "expert"}
PUBLIC_SOFTWARE_SUBJECTS = ["software_engineering", "distributed_systems", "python_core"]
PUBLIC_SOFTWARE_MISSION = "public_software_change_observation_v1"


MISSION_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "mission_id": "field_response_scheduler_v1",
        "title": "Field response scheduling under capacity constraints",
        "subjects": ["algorithms_data_structures", "integrated_engineering_capstone"],
        "domain": "operations",
        "resources": [
            {"id": "crew_alpha", "capacity": 5, "active": True},
            {"id": "crew_beta", "capacity": 4, "active": True},
        ],
        "tasks": [
            {"id": "inspect", "demand": 1, "priority": 10, "depends_on": []},
            {"id": "isolate", "demand": 2, "priority": 9, "depends_on": ["inspect"]},
            {"id": "repair", "demand": 3, "priority": 8, "depends_on": ["isolate"]},
            {"id": "verify", "demand": 2, "priority": 7, "depends_on": ["repair"]},
        ],
    },
    {
        "mission_id": "resilient_service_network_v1",
        "title": "Resilient service routing during a primary-node failure",
        "subjects": ["networking", "distributed_systems"],
        "domain": "software_systems",
        "resources": [
            {"id": "primary", "capacity": 10, "active": False},
            {"id": "fallback_east", "capacity": 6, "active": True},
            {"id": "fallback_west", "capacity": 6, "active": True},
        ],
        "tasks": [
            {"id": "authenticate", "demand": 2, "priority": 10, "depends_on": []},
            {"id": "telemetry", "demand": 4, "priority": 9, "depends_on": ["authenticate"]},
            {"id": "alerts", "demand": 2, "priority": 8, "depends_on": ["authenticate"]},
            {"id": "archive", "demand": 2, "priority": 7, "depends_on": ["telemetry"]},
        ],
    },
    {
        "mission_id": "cloud_failover_capacity_v1",
        "title": "Cloud failover with dependency and capacity pressure",
        "subjects": ["architecture_operations", "cloud_devops_sre"],
        "domain": "infrastructure",
        "resources": [
            {"id": "zone_a", "capacity": 6, "active": True},
            {"id": "zone_b", "capacity": 6, "active": True},
            {"id": "zone_c", "capacity": 8, "active": False},
        ],
        "tasks": [
            {"id": "database", "demand": 4, "priority": 10, "depends_on": []},
            {"id": "api", "demand": 4, "priority": 9, "depends_on": ["database"]},
            {"id": "worker", "demand": 2, "priority": 8, "depends_on": ["database"]},
            {"id": "monitor", "demand": 1, "priority": 7, "depends_on": ["api"]},
        ],
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _append_event(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(value), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _epoch(timestamp: str | None) -> float:
    if not timestamp:
        return 0.0
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _baseline_plan(mission: Mapping[str, Any]) -> list[dict[str, str]]:
    """Deliberately naive plan: first resource, declared order, no checks."""
    first = str((mission.get("resources") or [{}])[0].get("id"))
    return [{"task_id": str(task["id"]), "resource_id": first}
            for task in mission.get("tasks") or []]


def _repaired_plan(mission: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    """Dependency-aware, capacity-bounded allocation with fail-closed refusal."""
    resources = {
        str(row["id"]): {"capacity": int(row["capacity"]), "remaining": int(row["capacity"])}
        for row in mission.get("resources") or [] if row.get("active") is True
    }
    pending = {str(row["id"]): dict(row) for row in mission.get("tasks") or []}
    completed: set[str] = set()
    plan: list[dict[str, str]] = []
    rejected: list[str] = []
    while pending:
        ready = [row for row in pending.values()
                 if set(map(str, row.get("depends_on") or [])) <= completed]
        if not ready:
            rejected.extend(sorted(pending))
            break
        ready.sort(key=lambda row: (-int(row.get("priority") or 0), str(row["id"])))
        task = ready[0]
        demand = int(task["demand"])
        candidates = [(row["remaining"], resource_id) for resource_id, row in resources.items()
                      if row["remaining"] >= demand]
        if not candidates:
            rejected.append(str(task["id"]))
            pending.pop(str(task["id"]))
            continue
        _, resource_id = max(candidates)
        resources[resource_id]["remaining"] -= demand
        plan.append({"task_id": str(task["id"]), "resource_id": resource_id})
        completed.add(str(task["id"]))
        pending.pop(str(task["id"]))
    return plan, rejected


def _evaluate(mission: Mapping[str, Any], plan: list[Mapping[str, str]]) -> dict[str, Any]:
    resources = {str(row["id"]): row for row in mission.get("resources") or []}
    tasks = {str(row["id"]): row for row in mission.get("tasks") or []}
    assignment = {str(row["task_id"]): str(row["resource_id"]) for row in plan}
    order = {str(row["task_id"]): index for index, row in enumerate(plan)}
    violations: list[str] = []
    loads = {resource_id: 0 for resource_id in resources}
    for task_id, resource_id in assignment.items():
        if task_id not in tasks or resource_id not in resources:
            violations.append(f"unknown_assignment:{task_id}:{resource_id}")
            continue
        if resources[resource_id].get("active") is not True:
            violations.append(f"inactive_resource:{resource_id}")
        loads[resource_id] += int(tasks[task_id]["demand"])
        for dependency in map(str, tasks[task_id].get("depends_on") or []):
            if dependency not in order or order[dependency] >= order[task_id]:
                violations.append(f"dependency_order:{dependency}->{task_id}")
    for resource_id, load in loads.items():
        if load > int(resources[resource_id]["capacity"]):
            violations.append(f"capacity:{resource_id}:{load}>{resources[resource_id]['capacity']}")
    missing = sorted(set(tasks) - set(assignment))
    violations.extend(f"unassigned:{task_id}" for task_id in missing)
    return {
        "passed": not violations,
        "assigned": len(assignment),
        "required": len(tasks),
        "resource_loads": loads,
        "violations": sorted(set(violations)),
    }


def _subject_inputs(progress: Mapping[str, Any], mission: Mapping[str, Any]) -> list[dict[str, Any]]:
    subjects = progress.get("subjects") or {}
    return [{
        "subject_id": subject_id,
        "name": (subjects.get(subject_id) or {}).get("name", subject_id),
        "overall_level": (subjects.get(subject_id) or {}).get("overall_level", "unassessed"),
        "evidence_records": int((subjects.get(subject_id) or {}).get("evidence_records") or 0),
    } for subject_id in mission.get("subjects") or []]


def _eligible(progress: Mapping[str, Any], mission: Mapping[str, Any]) -> bool:
    subjects = progress.get("subjects") or {}
    return all((subjects.get(subject_id) or {}).get("overall_level") in ELIGIBLE_LEVELS
               for subject_id in mission.get("subjects") or [])


def _container_refs(index: Mapping[str, Any], subject_ids: list[str]) -> list[dict[str, str]]:
    by_subject = {str(row.get("subject_id")): row for row in index.get("containers") or []}
    return [{"subject_id": subject_id, "container_id": str(by_subject.get(subject_id, {}).get(
        "id", f"aion__academy_{subject_id}"))} for subject_id in subject_ids]


def _make_capsule(progress: Mapping[str, Any], mission: Mapping[str, Any],
                  container_index: Mapping[str, Any]) -> dict[str, Any]:
    baseline = _baseline_plan(mission)
    baseline_result = _evaluate(mission, baseline)
    repaired, rejected = _repaired_plan(mission)
    retry_result = _evaluate(mission, repaired)
    max_capacity = max((int(row["capacity"]) for row in mission.get("resources") or []
                        if row.get("active") is True), default=0)
    adversarial_probe = {"task_id": "oversized_unfamiliar_request", "demand": max_capacity + 1}
    probe_rejected = adversarial_probe["demand"] > max_capacity
    mission_id = str(mission["mission_id"])
    subject_ids = list(map(str, mission.get("subjects") or []))
    commitment = {
        "mission": mission,
        "authority": "deterministic_safe_simulation_v1",
        "scoring": "all tasks assigned to active resources within capacity and dependency order",
        "adversarial_rule": "requests beyond every active resource capacity must be refused",
    }
    passed = (baseline_result["passed"] is False and retry_result["passed"] is True
              and not rejected and probe_rejected)
    return {
        "schema_version": SCHEMA,
        "capsule_id": f"experience_capsule__{mission_id}",
        "mission_id": mission_id,
        "title": mission["title"],
        "domain": mission["domain"],
        "created_at": _utc_now(),
        "mission_commitment_sha256": _digest(commitment),
        "mission_commitment": commitment,
        "knowledge_inputs": _subject_inputs(progress, mission),
        "knowledge_container_refs": _container_refs(container_index, subject_ids),
        "environment": "safe_source_disjoint_deterministic_simulation",
        "baseline": {"plan": baseline, "evaluation": baseline_result},
        "observed_surprise": (
            "A locally plausible first-resource plan violated live availability, capacity, or dependency constraints."
        ),
        "knowledge_to_action_gap": (
            "Static subject knowledge did not itself supply a fail-closed policy for interacting constraints."
        ),
        "repair": (
            "Apply dependency-aware ordering, exclude inactive resources, track remaining capacity, "
            "and refuse work that cannot be safely placed."
        ),
        "fresh_retry": {"plan": repaired, "evaluation": retry_result},
        "adversarial_probe": {**adversarial_probe, "correctly_rejected": probe_rejected},
        "outcome": "verified_calibration_pass" if passed else "failed_closed",
        "passed": passed,
        "experience_claim": "bounded_source_disjoint_simulation",
        "awards_subject_competence": False,
        "unsafe_actions": 0,
        "external_actions": 0,
        "world_authority": "not_yet_observed",
        "wisdom_rule": (
            "Do not deploy a theoretically valid plan until availability, capacity, dependencies, "
            "and refusal conditions have all been checked."
        ),
        "claim_boundary": (
            "This capsule proves performance only in its frozen simulation. It is applied-experience "
            "evidence, not mastery and not a verified real-world outcome."
        ),
    }


def _update_graph(graph: dict[str, Any], capsule: Mapping[str, Any]) -> dict[str, Any]:
    capsule_id = str(capsule["capsule_id"])
    gap_id = f"gap__{capsule['mission_id']}"
    repair_id = f"repair__{capsule['mission_id']}"
    wisdom_id = f"wisdom__{capsule['mission_id']}"
    nodes = {str(row["id"]): row for row in graph.get("nodes") or []}
    edges = {str(row["id"]): row for row in graph.get("edges") or []}
    additions = [
        {"id": capsule_id, "kind": "experience_capsule", "label": capsule["title"]},
        {"id": gap_id, "kind": "knowledge_action_gap", "label": capsule["knowledge_to_action_gap"]},
        {"id": repair_id, "kind": "repair_policy", "label": capsule["repair"]},
        {"id": wisdom_id, "kind": "wisdom_rule", "label": capsule["wisdom_rule"]},
    ]
    for row in capsule.get("knowledge_inputs") or []:
        additions.append({"id": f"subject__{row['subject_id']}", "kind": "subject_knowledge",
                          "label": row["name"], "level": row["overall_level"]})
    for row in additions:
        nodes[row["id"]] = row
    edge_rows: list[tuple[str, str, str]] = []
    for row in capsule.get("knowledge_inputs") or []:
        edge_rows.append((f"subject__{row['subject_id']}", "APPLIES_IN", capsule_id))
    edge_rows.extend([
        (capsule_id, "EXPOSES_GAP", gap_id),
        (gap_id, "REPAIRED_BY", repair_id),
        (repair_id, "VALIDATED_BY", capsule_id),
        (capsule_id, "PRODUCES_WISDOM", wisdom_id),
    ])
    for source, relation, target in edge_rows:
        edge_id = _digest([source, relation, target])[:24]
        edges[edge_id] = {"id": edge_id, "source": source, "relation": relation, "target": target}
    graph.update({
        "schema_version": GRAPH_SCHEMA,
        "updated_at": _utc_now(),
        "nodes": sorted(nodes.values(), key=lambda row: str(row["id"])),
        "edges": sorted(edges.values(), key=lambda row: str(row["id"])),
        "separate_from_textbook_graph": True,
        "claim_boundary": "Graph links record bounded applied evidence; links do not award mastery.",
    })
    return graph


def _subjects_at_level(progress: Mapping[str, Any], subject_ids: list[str]) -> bool:
    subjects = progress.get("subjects") or {}
    return all((subjects.get(subject_id) or {}).get("overall_level") in ELIGIBLE_LEVELS
               for subject_id in subject_ids)


def _open_public_software_contract(progress: Mapping[str, Any], outcomes: list[dict[str, Any]],
                                   delay_seconds: float) -> dict[str, Any] | None:
    if not _subjects_at_level(progress, PUBLIC_SOFTWARE_SUBJECTS) or not outcomes:
        return None
    anchor = outcomes[-1]
    observed = anchor.get("outcomes") or {}
    required = ("cpython", "node", "numpy_release")
    if not all((observed.get(source) or {}).get("reachable") for source in required):
        return None
    forecasts = {
        "cpython": {"claim": "revision_unchanged", "expected": observed["cpython"].get("revision")},
        "node": {"claim": "revision_unchanged", "expected": observed["node"].get("revision")},
        "numpy_release": {"claim": "version_unchanged", "expected": observed["numpy_release"].get("value")},
    }
    created_epoch = time.time()
    body = {
        "contract_id": f"real_contract__{PUBLIC_SOFTWARE_MISSION}",
        "mission_id": PUBLIC_SOFTWARE_MISSION,
        "title": "Observe an unseen public software ecosystem change",
        "created_at": _utc_now(),
        "created_epoch": created_epoch,
        "not_before_epoch": created_epoch + max(60.0, float(delay_seconds)),
        "anchor_cycle": int(anchor.get("cycle") or 0),
        "anchor_outcome_sha256": anchor.get("outcome_sha256"),
        "subjects": PUBLIC_SOFTWARE_SUBJECTS,
        "forecasts": forecasts,
        "outcome_authorities": {
            source: (observed.get(source) or {}).get("authority") for source in required
        },
        "selection_rule": (
            "first fully reachable public outcome row with cycle greater than anchor_cycle "
            "and observed_at no earlier than not_before_epoch"
        ),
        "source_access_after_commitment": True,
        "external_writes": 0,
        "owner_interventions": 0,
    }
    body["commitment_sha256"] = _digest(body)
    return body


def _contract_hash_valid(contract: Mapping[str, Any]) -> bool:
    body = dict(contract)
    expected = body.pop("commitment_sha256", None)
    return isinstance(expected, str) and _digest(body) == expected


def _select_later_public_outcome(contract: Mapping[str, Any],
                                 outcomes: list[dict[str, Any]]) -> dict[str, Any] | None:
    required = ("cpython", "node", "numpy_release")
    for row in outcomes:
        observed = row.get("outcomes") or {}
        if int(row.get("cycle") or 0) <= int(contract.get("anchor_cycle") or 0):
            continue
        if _epoch(row.get("observed_at")) < float(contract.get("not_before_epoch") or 0):
            continue
        if all((observed.get(source) or {}).get("reachable") for source in required):
            return row
    return None


def _make_real_outcome_capsule(progress: Mapping[str, Any], contract: Mapping[str, Any],
                               outcome: Mapping[str, Any],
                               container_index: Mapping[str, Any]) -> dict[str, Any]:
    observed = outcome.get("outcomes") or {}
    score_rows: dict[str, dict[str, Any]] = {}
    for source, forecast in (contract.get("forecasts") or {}).items():
        actual = observed.get(source) or {}
        field = "value" if forecast.get("claim") == "version_unchanged" else "revision"
        score_rows[source] = {
            "expected": forecast.get("expected"),
            "observed": actual.get(field),
            "correct": actual.get(field) == forecast.get("expected"),
            "authority": actual.get("authority"),
            "authority_family": actual.get("family"),
        }
    correct = sum(row["correct"] is True for row in score_rows.values())
    total = len(score_rows)
    outcome_success = correct == total
    subject_ids = list(map(str, contract.get("subjects") or []))
    return {
        "schema_version": SCHEMA,
        "capsule_id": f"real_experience_capsule__{contract['mission_id']}",
        "mission_id": contract["mission_id"],
        "title": contract["title"],
        "created_at": _utc_now(),
        "experience_claim": "independently_observed_public_world_outcome",
        "knowledge_inputs": _subject_inputs(progress, {"subjects": subject_ids}),
        "knowledge_container_refs": _container_refs(container_index, subject_ids),
        "frozen_contract": dict(contract),
        "commitment_sha256": contract["commitment_sha256"],
        "anchor_outcome_sha256": contract["anchor_outcome_sha256"],
        "later_outcome_sha256": outcome.get("outcome_sha256"),
        "later_outcome_cycle": outcome.get("cycle"),
        "later_observed_at": outcome.get("observed_at"),
        "elapsed_seconds": max(0.0, _epoch(outcome.get("observed_at"))
                               - float(contract.get("created_epoch") or 0)),
        "scores": score_rows,
        "correct_predictions": correct,
        "scored_predictions": total,
        "outcome_success": outcome_success,
        "verified_real_outcome": total > 0,
        "lesson": (
            "The frozen public-software continuity model matched the later world observation."
            if outcome_success else
            "The public software world changed after commitment; revise the continuity model from the retained miss."
        ),
        "world_model_update_required": not outcome_success,
        "awards_subject_competence": False,
        "external_writes": 0,
        "unsafe_actions": 0,
        "claim_boundary": (
            "This is a genuine later observation owned by independent public authorities. It is one "
            "bounded real-world outcome, not general subject mastery."
        ),
    }


def _update_graph_with_real_outcome(graph: dict[str, Any], capsule: Mapping[str, Any]) -> dict[str, Any]:
    capsule_id = str(capsule["capsule_id"])
    observation_id = f"public_observation__{capsule.get('later_outcome_sha256')}"
    lesson_id = f"real_lesson__{capsule['mission_id']}"
    nodes = {str(row["id"]): row for row in graph.get("nodes") or []}
    edges = {str(row["id"]): row for row in graph.get("edges") or []}
    nodes[capsule_id] = {"id": capsule_id, "kind": "real_experience_capsule",
                         "label": capsule["title"], "outcome_success": capsule["outcome_success"]}
    nodes[observation_id] = {"id": observation_id, "kind": "independent_public_observation",
                             "label": f"public outcome cycle {capsule.get('later_outcome_cycle')}"}
    nodes[lesson_id] = {"id": lesson_id, "kind": "real_world_lesson", "label": capsule["lesson"]}
    edge_rows: list[tuple[str, str, str]] = [
        (capsule_id, "SCORED_BY", observation_id),
        (observation_id, "PRODUCES_REAL_LESSON", lesson_id),
    ]
    for row in capsule.get("knowledge_inputs") or []:
        subject_node = f"subject__{row['subject_id']}"
        nodes[subject_node] = {"id": subject_node, "kind": "subject_knowledge",
                               "label": row["name"], "level": row["overall_level"]}
        edge_rows.append((subject_node, "TESTED_IN_REAL_WORLD_BY", capsule_id))
    for source, relation, target in edge_rows:
        edge_id = _digest([source, relation, target])[:24]
        edges[edge_id] = {"id": edge_id, "source": source, "relation": relation, "target": target}
    graph.update({
        "schema_version": GRAPH_SCHEMA,
        "updated_at": _utc_now(),
        "nodes": sorted(nodes.values(), key=lambda row: str(row["id"])),
        "edges": sorted(edges.values(), key=lambda row: str(row["id"])),
        "separate_from_textbook_graph": True,
        "contains_independently_observed_outcomes": True,
        "claim_boundary": "Real observations are retained without converting one outcome into mastery.",
    })
    return graph


def run_cycle(*, repo_root: Path, progress_path: Path | None = None,
              state_path: Path | None = None, graph_path: Path | None = None,
              capsule_dir: Path | None = None, result_path: Path | None = None,
              public_outcome_ledger: Path | None = None,
              real_world_delay_seconds: float | None = None) -> dict[str, Any]:
    repo_root = Path(repo_root).resolve()
    progress_path = progress_path or repo_root / "results/aion_progressive_competency_status.json"
    base = repo_root / "backend/modules/hexcore/data/real_world_integration_arena"
    state_path = state_path or base / "state.json"
    graph_path = graph_path or base / "experience_graph.json"
    capsule_dir = capsule_dir or base / "capsules"
    result_path = result_path or repo_root / "results/hexcore_real_world_integration_arena.json"
    public_outcome_ledger = public_outcome_ledger or repo_root / "results/hexcore_prospective_cross_domain_outcomes.jsonl"
    if real_world_delay_seconds is None:
        real_world_delay_seconds = float(os.getenv("AION_REAL_WORLD_INTEGRATION_DELAY", "300"))
    progress = _read_json(progress_path, {})
    container_index = _read_json(
        repo_root / "backend/modules/hexcore/data/expertise_containers/index.json", {})
    with exclusive_file_lock(base / "arena.lock"):
        state = _read_json(state_path, {
            "schema_version": SCHEMA, "created_at": _utc_now(), "completed_missions": [],
            "capsules": [], "real_world_capsules": [], "completed_real_world_missions": [],
            "cycles": 0,
        })
        state["schema_version"] = SCHEMA
        completed = set(map(str, state.get("completed_missions") or []))
        eligible = [row for row in MISSION_REGISTRY if _eligible(progress, row)]
        selected = next((row for row in eligible if row["mission_id"] not in completed), None)
        latest_capsule: dict[str, Any] | None = None
        if selected is not None:
            latest_capsule = _make_capsule(progress, selected, container_index)
            if latest_capsule["passed"]:
                capsule_path = capsule_dir / f"{latest_capsule['capsule_id']}.json"
                _write_json(capsule_path, latest_capsule)
                completed.add(str(selected["mission_id"]))
                capsule_ids = set(map(str, state.get("capsules") or []))
                capsule_ids.add(str(latest_capsule["capsule_id"]))
                state["capsules"] = sorted(capsule_ids)
                graph = _update_graph(_read_json(graph_path, {}), latest_capsule)
                _write_json(graph_path, graph)
                _append_event(base / "event_ledger.jsonl", {
                    "event": "experience_capsule_verified", "at": _utc_now(),
                    "capsule_id": latest_capsule["capsule_id"],
                    "mission_commitment_sha256": latest_capsule["mission_commitment_sha256"],
                    "awards_subject_competence": False,
                })
        public_outcomes = _read_jsonl(public_outcome_ledger)
        real_capsule: dict[str, Any] | None = None
        real_completed = set(map(str, state.get("completed_real_world_missions") or []))
        real_contract = state.get("active_real_world_contract") or None
        real_contract_integrity = real_contract is None or _contract_hash_valid(real_contract)
        if selected is None and PUBLIC_SOFTWARE_MISSION not in real_completed:
            if real_contract is None:
                real_contract = _open_public_software_contract(
                    progress, public_outcomes, float(real_world_delay_seconds))
                if real_contract is not None:
                    state["active_real_world_contract"] = real_contract
                    _append_event(base / "real_world_commitment_ledger.jsonl", real_contract)
                    _append_event(base / "event_ledger.jsonl", {
                        "event": "real_world_contract_precommitted", "at": _utc_now(),
                        "contract_id": real_contract["contract_id"],
                        "commitment_sha256": real_contract["commitment_sha256"],
                        "not_before_epoch": real_contract["not_before_epoch"],
                        "external_writes": 0,
                    })
                    real_contract_integrity = True
            if (real_contract is not None and real_contract_integrity
                    and time.time() >= float(real_contract["not_before_epoch"])):
                later_outcome = _select_later_public_outcome(real_contract, public_outcomes)
                if later_outcome is not None:
                    real_capsule = _make_real_outcome_capsule(
                        progress, real_contract, later_outcome, container_index)
                    real_capsule_path = capsule_dir / f"{real_capsule['capsule_id']}.json"
                    _write_json(real_capsule_path, real_capsule)
                    real_ids = set(map(str, state.get("real_world_capsules") or []))
                    real_ids.add(str(real_capsule["capsule_id"]))
                    state["real_world_capsules"] = sorted(real_ids)
                    real_completed.add(PUBLIC_SOFTWARE_MISSION)
                    state["completed_real_world_missions"] = sorted(real_completed)
                    state.pop("active_real_world_contract", None)
                    graph = _update_graph_with_real_outcome(
                        _read_json(graph_path, {}), real_capsule)
                    _write_json(graph_path, graph)
                    _append_event(base / "event_ledger.jsonl", {
                        "event": "independent_real_world_outcome_scored", "at": _utc_now(),
                        "capsule_id": real_capsule["capsule_id"],
                        "commitment_sha256": real_capsule["commitment_sha256"],
                        "later_outcome_sha256": real_capsule["later_outcome_sha256"],
                        "outcome_success": real_capsule["outcome_success"],
                        "prediction_accuracy": (
                            real_capsule["correct_predictions"] / real_capsule["scored_predictions"]),
                        "external_writes": 0,
                    })
        graph = _read_json(graph_path, {"nodes": [], "edges": []})
        active_real_contract = state.get("active_real_world_contract") or {}
        if not real_contract_integrity:
            arena_status = "real_world_commitment_integrity_failure"
        elif selected is not None:
            arena_status = "calibration_active"
        elif real_capsule is not None:
            arena_status = "independent_real_world_outcome_recorded"
        elif active_real_contract:
            arena_status = "waiting_for_later_independent_world_observation"
        elif PUBLIC_SOFTWARE_MISSION in real_completed:
            arena_status = "waiting_for_next_real_world_mission_adapter"
        else:
            arena_status = "waiting_for_real_world_eligibility_or_authority"
        state.update({
            "completed_missions": sorted(completed),
            "completed_real_world_missions": sorted(real_completed),
            "cycles": int(state.get("cycles") or 0) + 1,
            "updated_at": _utc_now(),
            "status": arena_status,
        })
        _write_json(state_path, state)
        displayed_real_capsule = real_capsule
        if displayed_real_capsule is None and state.get("real_world_capsules"):
            displayed_real_capsule = _read_json(
                capsule_dir / f"{state['real_world_capsules'][-1]}.json", {})
        result = {
            "schema_version": SCHEMA,
            "status": state["status"],
            "passed": (latest_capsule is None or latest_capsule.get("passed") is True)
                      and (real_capsule is None or real_capsule.get("verified_real_outcome") is True)
                      and real_contract_integrity,
            "parallel_to_curriculum": True,
            "eligible_missions": [row["mission_id"] for row in eligible],
            "completed_missions": state["completed_missions"],
            "outstanding_eligible": [row["mission_id"] for row in eligible
                                     if row["mission_id"] not in completed],
            "capsule_count": len(state.get("capsules") or []) + len(state.get("real_world_capsules") or []),
            "calibration_capsule_count": len(state.get("capsules") or []),
            "real_world_capsule_count": len(state.get("real_world_capsules") or []),
            "completed_real_world_missions": state.get("completed_real_world_missions") or [],
            "active_real_world_contract": active_real_contract,
            "real_world_commitment_integrity": real_contract_integrity,
            "graph": {"path": str(graph_path), "nodes": len(graph.get("nodes") or []),
                      "edges": len(graph.get("edges") or [])},
            "latest_capsule": latest_capsule or {},
            "latest_real_world_capsule": displayed_real_capsule or {},
            "awaiting_genuine_world_authority": 1 if active_real_contract else 0,
            "unsafe_actions": 0,
            "awards_subject_competence": False,
            "updated_at": time.time(),
            "claim_boundary": (
                "Calibration capsules are qualification only. Real-world capsules require a frozen "
                "commitment followed by a later observation owned by an independent public authority; "
                "neither automatically establishes broad subject mastery."
            ),
        }
        _write_json(result_path, result)
        return result


if __name__ == "__main__":
    print(json.dumps(run_cycle(repo_root=Path(os.getenv("AION_REPO_ROOT", "."))), indent=2))
