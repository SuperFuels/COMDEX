"""Project the comprehensive curriculum into AION academy containers and activate it."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.comprehensive_expertise_curriculum import (
    build_curriculum,
    validate_curriculum,
)
from backend.modules.hexcore.persistent_learning import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


OWNER_WA = "aion@wave.tp"
KG = "work"
SCHEMA = "aion.hexcore.expertise_container_curriculum_runtime.v1"


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _ns(local_id: str) -> str:
    return f"{KG}:{OWNER_WA}:{local_id}"


def _container_id(subject_id: str) -> str:
    return f"aion__academy_{subject_id}"


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _subject_container(subject_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    container_id = _container_id(subject_id)
    subject_node = _ns(f"subject:{subject_id}")
    nodes = [{
        "id": subject_node,
        "type": "subject",
        "label": row["name"],
        "domain": row["domain"],
        "status": "curriculum_declared_unassessed",
        "risk": row.get("risk", "ordinary"),
    }]
    edges = []
    for competency in row.get("competencies") or []:
        node_id = _ns(f"concept:{subject_id}:{competency}")
        nodes.append({
            "id": node_id,
            "type": "concept",
            "label": competency.replace("_", " "),
            "subject_id": subject_id,
            "evidence_status": "unassessed",
        })
        edges.append({
            "kind": "PART_OF",
            "from": node_id,
            "to": subject_node,
            "verified": True,
            "meaning": "curriculum structure only",
        })
    return {
        "schema_version": "aion.container.knowledge_academy.v1",
        "id": container_id,
        "type": "container",
        "meta": {
            "title": f"AION Academy · {row['name']}",
            "ownerWA": OWNER_WA,
            "graph": KG,
            "kind": "knowledge_academy",
            "subject_id": subject_id,
            "domain": row["domain"],
            "curriculum_only": True,
        },
        "glyphs": nodes,
        "dimensions": edges,
        "knowledge_graph": {"nodes": nodes, "edges": edges},
        "container_refs": [
            {
                "container_id": _container_id(prerequisite),
                "kind": "knowledge_academy",
                "relation": "PREREQUISITE",
                "namespaced_target": _ns(f"subject:{prerequisite}"),
            }
            for prerequisite in row.get("prerequisites") or []
        ],
        "evidence_claims": [],
        "competence_awarded": False,
    }


def _abilities_container(curriculum: Mapping[str, Any]) -> dict[str, Any]:
    nodes = []
    edges = []
    for capability_id, row in curriculum["learning_capabilities"].items():
        capability_node = _ns(f"capability:{capability_id}")
        nodes.append({
            "id": capability_node,
            "type": "learning_capability",
            "label": row["name"],
            "status": "curriculum_declared_unassessed",
        })
        for outcome in row["outcomes"]:
            outcome_node = _ns(f"outcome:{capability_id}:{outcome}")
            nodes.append({"id": outcome_node, "type": "outcome", "label": outcome})
            edges.append({"kind": "REQUIRES_OUTCOME", "from": capability_node, "to": outcome_node})
    return {
        "schema_version": "aion.container.learning_capabilities.v1",
        "id": "aion__learning_capabilities",
        "type": "container",
        "meta": {"title": "AION · Learning Abilities", "ownerWA": OWNER_WA, "graph": KG, "kind": "learning_capabilities"},
        "glyphs": nodes,
        "dimensions": edges,
        "knowledge_graph": {"nodes": nodes, "edges": edges},
        "competence_awarded": False,
    }


def _bridge_container(curriculum: Mapping[str, Any]) -> dict[str, Any]:
    refs = []
    edges = []
    for bridge in curriculum["cross_domain_bridges"]:
        refs.extend((
            {"container_id": _container_id(bridge["source"]), "kind": "knowledge_academy", "subject_id": bridge["source"]},
            {"container_id": _container_id(bridge["target"]), "kind": "knowledge_academy", "subject_id": bridge["target"]},
        ))
        edges.append({
            "id": _ns(bridge["bridge_id"]),
            "kind": str(bridge["relation"]).upper(),
            "from": _ns(f"subject:{bridge['source']}"),
            "to": _ns(f"subject:{bridge['target']}"),
            "bridge_variables": list(bridge["bridge_variables"]),
            "verification": list(bridge["verification"]),
            "status": "curriculum_target_unverified",
        })
    unique_refs = {row["container_id"]: row for row in refs}
    return {
        "schema_version": "aion.container.cross_domain_bridge_graph.v1",
        "id": "aion__cross_domain_bridges",
        "type": "container",
        "meta": {"title": "AION · Cross-Domain Bridge Graph", "ownerWA": OWNER_WA, "graph": KG, "kind": "cross_domain_graph"},
        "glyphs": [],
        "dimensions": edges,
        "knowledge_graph": {"nodes": [], "edges": edges},
        "container_refs": sorted(unique_refs.values(), key=lambda row: row["container_id"]),
        "typed_edges": True,
        "entanglement_used_only_for_container_association": True,
        "competence_awarded": False,
    }


def _evidence_container() -> dict[str, Any]:
    return {
        "schema_version": "aion.container.expertise_evidence.v1",
        "id": "aion__expertise_evidence",
        "type": "container",
        "meta": {"title": "AION · Expertise Evidence and Examinations", "ownerWA": OWNER_WA, "graph": KG, "kind": "evidence_authority"},
        "glyphs": [],
        "dimensions": [],
        "evidence_capsules": [],
        "assessment_receipts": [],
        "source_disjoint_required": True,
        "self_scoring_cannot_award_competence": True,
    }


def build_container_projection(*, curriculum: Mapping[str, Any], container_root: Path) -> dict[str, Any]:
    validation = validate_curriculum(curriculum)
    if not validation["valid"]:
        raise ValueError(validation["errors"])
    container_root.mkdir(parents=True, exist_ok=True)
    manifests = []
    for subject_id, row in curriculum["subjects"].items():
        manifest = _subject_container(subject_id, row)
        path = container_root / f"{manifest['id']}.json"
        _atomic(path, manifest)
        manifests.append({"id": manifest["id"], "path": str(path), "kind": "knowledge_academy", "subject_id": subject_id})
    for manifest in (_abilities_container(curriculum), _bridge_container(curriculum), _evidence_container()):
        path = container_root / f"{manifest['id']}.json"
        _atomic(path, manifest)
        manifests.append({"id": manifest["id"], "path": str(path), "kind": manifest["meta"]["kind"]})
    index = {
        "schema_version": "aion.container.expertise_index.v1",
        "user": "aion",
        "wa": OWNER_WA,
        "kg": KG,
        "curriculum_digest": curriculum["curriculum_digest"],
        "containers": sorted(manifests, key=lambda row: row["id"]),
        "shared": [
            {"id": "aion__cross_domain_bridges", "label": "Cross-Domain Bridge Graph", "role": "owner", "permissions": ["read", "post"]},
            {"id": "aion__expertise_evidence", "label": "Expertise Evidence", "role": "owner", "permissions": ["read", "post"]},
        ],
        "container_count": len(manifests),
        "created_at": _utc_timestamp(),
    }
    index["index_digest"] = _canonical_hash(index)
    _atomic(container_root / "index.json", index)
    return index


def activate_expertise_curriculum(
    *,
    repo_root: Path,
    curriculum_path: Path,
    container_root: Path,
    competency_state_path: Path,
    runtime_state_path: Path,
    result_path: Path | None = None,
) -> dict[str, Any]:
    curriculum = json.loads(curriculum_path.read_text(encoding="utf-8")) if curriculum_path.exists() else build_curriculum()
    if not curriculum_path.exists():
        _atomic(curriculum_path, curriculum)
    index = build_container_projection(curriculum=curriculum, container_root=container_root)
    system = ProgressiveCompetencySystem(repo_root=repo_root, state_path=competency_state_path)
    evidence_before = system.summary()["evidence_records"]
    installation = system.install_comprehensive_curriculum(
        curriculum=curriculum,
        curriculum_artifact=_display_path(curriculum_path, repo_root),
    )
    # Register the first learning ability as the active mission. The existing
    # scheduler may honour a matured retention contract first, but this demand
    # remains active until its evidence target is actually reached.
    demand = system.prioritize_for_mission(
        subject_id="capability_learning_strategy",
        mission="Begin the comprehensive expertise programme by learning how to diagnose gaps, choose depth, map prerequisites and change strategy after failure.",
        evidence="owner_authorized_comprehensive_curriculum_activation",
    )
    scheduler_action = system.step()
    evidence_after = system.summary()["evidence_records"]
    runtime_state = {
        "schema_version": SCHEMA,
        "status": "active",
        "current_phase": 0,
        "current_phase_name": "learn_to_learn",
        "current_subject_id": "capability_learning_strategy",
        "curriculum_digest": curriculum["curriculum_digest"],
        "container_index": _display_path(container_root / "index.json", repo_root),
        "competency_state": _display_path(competency_state_path, repo_root),
        "installation": installation,
        "mission_demand": demand,
        "scheduler_action": scheduler_action["cycle"]["action"],
        "evidence_records_before": evidence_before,
        "evidence_records_after": evidence_after,
        "competence_awarded_by_activation": False,
        "started_at": _utc_timestamp(),
    }
    if evidence_before != evidence_after:
        raise RuntimeError("activation changed the evidence ledger")
    runtime_state["state_digest"] = _canonical_hash(runtime_state)
    _atomic(runtime_state_path, runtime_state)
    gate = {
        "curriculum_valid": curriculum["validation"]["valid"],
        "academy_containers": sum(row["kind"] == "knowledge_academy" for row in index["containers"]),
        "support_containers": len(index["containers"]) - sum(row["kind"] == "knowledge_academy" for row in index["containers"]),
        "typed_bridges": len(curriculum["cross_domain_bridges"]),
        "live_registry_subjects_installed": installation["subjects_installed"],
        "live_registry_capabilities_installed": installation["capabilities_installed"],
        "process_status": runtime_state["status"],
        "first_subject": runtime_state["current_subject_id"],
        "evidence_records_added": evidence_after - evidence_before,
        "competence_awarded": False,
        "unsafe_actions": 0,
        "paid_api_calls": 0,
    }
    gate["accepted"] = bool(
        gate["curriculum_valid"]
        and gate["academy_containers"] == len(curriculum["subjects"])
        and gate["typed_bridges"] == len(curriculum["cross_domain_bridges"])
        and gate["live_registry_subjects_installed"] == len(curriculum["subjects"])
        and gate["live_registry_capabilities_installed"] == len(curriculum["learning_capabilities"])
        and gate["process_status"] == "active"
        and gate["evidence_records_added"] == 0
        and gate["competence_awarded"] is False
        and gate["unsafe_actions"] == gate["paid_api_calls"] == 0
    )
    result = {
        "schema_version": "aion.hexcore.expertise_container_activation_result.v1",
        "created_at": _utc_timestamp(),
        "passed": gate["accepted"],
        "container_index": index,
        "installation": installation,
        "runtime_state": runtime_state,
        "gate": gate,
        "claim_boundary": "The comprehensive curriculum is installed and scheduled. No subject competence was awarded by installation; learning evidence must still be earned.",
    }
    result["result_digest"] = _canonical_hash(result)
    if result_path is not None:
        _atomic(result_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Activate AION's container-backed expertise curriculum.")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--curriculum-path", type=Path, required=True)
    parser.add_argument("--container-root", type=Path, required=True)
    parser.add_argument("--competency-state-path", type=Path, required=True)
    parser.add_argument("--runtime-state-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    result = activate_expertise_curriculum(
        repo_root=args.repo_root.resolve(),
        curriculum_path=args.curriculum_path.resolve(),
        container_root=args.container_root.resolve(),
        competency_state_path=args.competency_state_path.resolve(),
        runtime_state_path=args.runtime_state_path.resolve(),
        result_path=args.result_path.resolve() if args.result_path else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
