"""Continuously discover and govern relationships between expertise containers.

"Entanglement" here means a typed, inspectable association.  It never merges
containers and never treats lexical similarity as proof.  Every relationship
retains its signals, provenance, scope and outstanding verification work.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "aion.hexcore.continuous_knowledge_entanglement.v1"
CONTAINER_SCHEMA = "aion.container.dynamic_cross_domain_associations.v1"
GENERIC_CONCEPTS = {
    "analysis", "application", "communication", "control", "controls", "cost",
    "data", "design", "ethics", "governance", "management", "measurement",
    "metrics", "model", "operations", "policy", "process", "research", "risk",
    "safety", "strategy", "system", "systems", "testing", "validation",
}


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _tokens(values: Iterable[Any]) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.update(re.findall(r"[a-z0-9]+", str(value).lower().replace("_", " ")))
    return {token for token in result if len(token) > 2 and token not in GENERIC_CONCEPTS}


def _closure(subject_id: str, prerequisites: Mapping[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    pending = list(prerequisites.get(subject_id) or [])
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(prerequisites.get(current) or [])
    return seen


def _edge_id(source: str, target: str, relation: str) -> str:
    return "association_" + _digest([source, target, relation])[:20]


def _update_index(index_path: Path, container_path: Path) -> None:
    if not index_path.exists():
        return
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entry = {
        "id": "aion__dynamic_associations", "kind": "dynamic_cross_domain_graph",
        "path": str(container_path),
    }
    containers = [row for row in index.get("containers") or [] if row.get("id") != entry["id"]]
    containers.append(entry)
    index["containers"] = sorted(containers, key=lambda row: str(row.get("id")))
    index["container_count"] = len(containers)
    shared = [row for row in index.get("shared") or [] if row.get("id") != entry["id"]]
    shared.append({
        "id": entry["id"], "label": "Dynamic Cross-Domain Associations",
        "role": "owner", "permissions": ["read", "post"],
    })
    index["shared"] = shared
    index["index_digest"] = _digest({key: value for key, value in index.items() if key != "index_digest"})
    _atomic(index_path, index)


def run(
    *, competency_state_path: Path, curriculum_path: Path, state_path: Path,
    container_path: Path, index_path: Path, result_path: Path,
    now: float | None = None,
) -> dict[str, Any]:
    now = time.time() if now is None else float(now)
    competency = json.loads(competency_state_path.read_text(encoding="utf-8"))
    curriculum = json.loads(curriculum_path.read_text(encoding="utf-8"))
    old_state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {
        "schema_version": SCHEMA, "relationships": {}, "cycles": 0,
    }
    if old_state.get("schema_version") != SCHEMA:
        raise ValueError("unsupported dynamic association state")

    curriculum_subjects = curriculum.get("subjects") or {}
    subjects: dict[str, dict[str, Any]] = {}
    for subject_id, row in (competency.get("subjects") or {}).items():
        declared = curriculum_subjects.get(subject_id) or {}
        concepts = set(row.get("subskills") or declared.get("competencies") or [])
        subjects[subject_id] = {
            "name": row.get("name") or declared.get("name") or subject_id,
            "domain": row.get("group") or declared.get("domain") or "unknown",
            "concepts": concepts,
            "concept_tokens": _tokens(concepts),
            "keywords": set(declared.get("keywords") or []),
        }
    prerequisites = {
        subject_id: set((curriculum_subjects.get(subject_id) or {}).get("prerequisites") or [])
        for subject_id in subjects
    }
    ancestry = {subject_id: _closure(subject_id, prerequisites) for subject_id in subjects}
    curated: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for bridge in curriculum.get("cross_domain_bridges") or []:
        curated.setdefault((str(bridge["source"]), str(bridge["target"])), []).append(bridge)

    evidence_counts: dict[str, int] = {}
    for row in competency.get("evidence") or []:
        if row.get("verified") is True:
            sid = str(row.get("subject_id") or "")
            evidence_counts[sid] = evidence_counts.get(sid, 0) + 1

    discovered: dict[str, dict[str, Any]] = {}
    subject_ids = sorted(subjects)
    for index, left in enumerate(subject_ids):
        for right in subject_ids[index + 1:]:
            lrow, rrow = subjects[left], subjects[right]
            signals: list[dict[str, Any]] = []
            direction = (left, right)
            relation = "ASSOCIATED_WITH"
            if left in prerequisites.get(right, set()):
                direction, relation = (left, right), "DIRECTLY_ENABLES"
                signals.append({"kind": "direct_prerequisite", "weight": 1.0, "values": [left]})
            elif right in prerequisites.get(left, set()):
                direction, relation = (right, left), "DIRECTLY_ENABLES"
                signals.append({"kind": "direct_prerequisite", "weight": 1.0, "values": [right]})
            elif left in ancestry.get(right, set()):
                direction, relation = (left, right), "TRANSITIVELY_ENABLES"
                signals.append({"kind": "prerequisite_chain", "weight": 0.88, "values": [left]})
            elif right in ancestry.get(left, set()):
                direction, relation = (right, left), "TRANSITIVELY_ENABLES"
                signals.append({"kind": "prerequisite_chain", "weight": 0.88, "values": [right]})

            bridges = curated.get((left, right), []) + curated.get((right, left), [])
            if bridges:
                bridge = bridges[0]
                direction = (str(bridge["source"]), str(bridge["target"]))
                relation = str(bridge.get("relation") or "CURATED_BRIDGE").upper()
                signals.append({
                    "kind": "curated_bridge", "weight": 0.95,
                    "values": list(bridge.get("bridge_variables") or []),
                    "bridge_id": bridge.get("bridge_id"),
                })

            shared_concepts = sorted(lrow["concepts"] & rrow["concepts"])
            shared_tokens = sorted(lrow["concept_tokens"] & rrow["concept_tokens"])
            shared_prerequisites = sorted(ancestry[left] & ancestry[right])
            if shared_concepts:
                signals.append({
                    "kind": "shared_declared_concept", "weight": min(0.9, 0.68 + 0.07 * len(shared_concepts)),
                    "values": shared_concepts,
                })
                if relation == "ASSOCIATED_WITH":
                    relation = "SHARES_CONCEPT"
            elif shared_tokens:
                signals.append({
                    "kind": "lexical_concept_candidate", "weight": min(0.58, 0.38 + 0.05 * len(shared_tokens)),
                    "values": shared_tokens,
                })
            if shared_prerequisites:
                signals.append({
                    "kind": "shared_foundation", "weight": min(0.75, 0.52 + 0.04 * len(shared_prerequisites)),
                    "values": shared_prerequisites[:8],
                })

            strong = [signal for signal in signals if float(signal["weight"]) >= 0.65]
            if not strong and len(signals) < 2:
                continue
            confidence = 1.0
            for signal in signals:
                confidence *= 1.0 - float(signal["weight"])
            confidence = round(1.0 - confidence, 4)
            source, target = direction
            edge_id = _edge_id(source, target, relation)
            prior = (old_state.get("relationships") or {}).get(edge_id) or {}
            evidence_activity = evidence_counts.get(source, 0) + evidence_counts.get(target, 0)
            status = "supported_association" if strong else "candidate_association"
            if any(signal["kind"] == "curated_bridge" for signal in signals):
                status = "curated_unverified_bridge"
            discovered[edge_id] = {
                "edge_id": edge_id, "source": source, "target": target,
                "source_container": f"aion__academy_{source}",
                "target_container": f"aion__academy_{target}",
                "relation": relation, "status": status,
                "confidence": confidence, "signals": signals,
                "cross_domain": subjects[source]["domain"] != subjects[target]["domain"],
                "valid_scope": "association and retrieval routing; not a causal or competence claim",
                "counterexamples": list(prior.get("counterexamples") or []),
                "verification_required": [
                    "derive_explicit_mapping", "attack_with_counterexample",
                    "apply_in_source_disjoint_cross_domain_project",
                ],
                "verified_transfer": False,
                "evidence_activity": evidence_activity,
                "first_seen_epoch": float(prior.get("first_seen_epoch") or now),
                "last_seen_epoch": now,
                "assessment_cycles": int(prior.get("assessment_cycles") or 0) + 1,
            }

    # Relationships that lose their support remain visible as stale audit rows.
    for edge_id, prior in (old_state.get("relationships") or {}).items():
        if edge_id not in discovered:
            discovered[edge_id] = {
                **prior, "status": "stale_candidate", "confidence": 0.0,
                "last_reassessed_epoch": now,
            }

    active = [row for row in discovered.values() if row.get("status") != "stale_candidate"]
    active.sort(key=lambda row: (-float(row.get("confidence") or 0), row["edge_id"]))
    nodes = [{
        "id": f"work:aion@wave.tp:subject:{subject_id}", "type": "subject",
        "label": row["name"], "domain": row["domain"],
        "container_id": f"aion__academy_{subject_id}",
    } for subject_id, row in sorted(subjects.items())]
    edges = [{
        "id": row["edge_id"], "kind": row["relation"],
        "from": f"work:aion@wave.tp:subject:{row['source']}",
        "to": f"work:aion@wave.tp:subject:{row['target']}",
        "status": row["status"], "confidence": row["confidence"],
        "signals": row["signals"], "verified_transfer": False,
    } for row in active]
    container = {
        "schema_version": CONTAINER_SCHEMA, "id": "aion__dynamic_associations",
        "type": "container", "meta": {
            "title": "AION · Dynamic Cross-Domain Associations", "ownerWA": "aion@wave.tp",
            "graph": "work", "kind": "dynamic_cross_domain_graph",
        },
        "knowledge_graph": {"nodes": nodes, "edges": edges},
        "glyphs": nodes, "dimensions": edges,
        "container_refs": [{
            "container_id": f"aion__academy_{subject_id}", "kind": "knowledge_academy",
            "subject_id": subject_id,
        } for subject_id in sorted(subjects)],
        "association_only": True, "competence_awarded": False,
        "causal_claims_awarded": False,
    }
    _atomic(container_path, container)
    _update_index(index_path, container_path)
    state = {
        "schema_version": SCHEMA, "relationships": discovered,
        "cycles": int(old_state.get("cycles") or 0) + 1,
        "last_cycle_epoch": now,
    }
    _atomic(state_path, state)
    result = {
        "schema_version": SCHEMA, "status": "association_graph_refreshed", "passed": True,
        "summary": {
            "subjects": len(subjects), "active_relationships": len(active),
            "cross_domain_relationships": sum(bool(row["cross_domain"]) for row in active),
            "candidate_relationships": sum(row["status"] == "candidate_association" for row in active),
            "supported_relationships": sum(row["status"] == "supported_association" for row in active),
            "curated_unverified_bridges": sum(row["status"] == "curated_unverified_bridge" for row in active),
            "verified_transfer_relationships": 0,
            "stale_relationships": sum(row.get("status") == "stale_candidate" for row in discovered.values()),
            "assessment_cycles": state["cycles"], "competence_awarded": False,
        },
        "strongest_relationships": active[:20],
        "next_cross_domain_tests": [
            row for row in active if row["cross_domain"] and not row["verified_transfer"]
        ][:20],
        "claim_boundary": (
            "The graph improves associative retrieval and proposes transfer tests. A relationship is not "
            "a causal fact, proof, or competence claim until its explicit verification obligations pass."
        ),
    }
    result["result_sha256"] = _digest(result)
    _atomic(result_path, result)
    return result

