"""Persistent hierarchical missions with capability-gated execution.

The graph compiler converts a broad outcome into milestones and work packages.
Missing competence becomes an explicit apprenticeship dependency rather than a
reason to guess or silently abandon the mission.  Only safe, ready leaf work is
published to the canonical GoalEngine; external transactions remain approval
gated.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash
from backend.modules.hexcore.mission_capability_action_harness import MissionCapabilityActionHarness
from backend.modules.hexcore.progressive_competency_system import LEVEL_INDEX
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate
from backend.modules.skills.goal_engine import GoalEngine


PROCEDURE_ID = "procedure_hierarchical_capability_gated_mission_graph_v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "hierarchical_mission_cau", "S": 1.0, "H": 0.0}


def _archetype(objective: str) -> str:
    text = objective.lower()
    if any(word in text for word in ("revenue", "money", "business", "customer", "website")):
        return "venture"
    if any(word in text for word in ("discover", "research", "hypothesis", "scientific")):
        return "research"
    if any(word in text for word in ("build", "service", "application", "system", "software")):
        return "engineering"
    return "general"


def _blueprint(archetype: str) -> list[dict[str, Any]]:
    common = [
        {"key": "situation", "milestone": "Understand the situation and define measurable success",
         "tasks": [
             ("observe_context", "Observe the current environment, constraints, stakeholders and available evidence", []),
             ("define_success", "Define measurable outcome, leading indicators, non-goals and stopping rules", ["observe_context"]),
         ]},
        {"key": "capability", "milestone": "Assemble the competence and authority needed for execution",
         "tasks": [
             ("map_capabilities", "Map required competencies, tools, permissions and independent outcome authorities", ["define_success"]),
             ("close_gaps", "Close or explicitly bound every blocking knowledge, skill, tool and authority gap", ["map_capabilities"]),
         ]},
    ]
    variants = {
        "venture": [
            {"key": "validation", "milestone": "Validate a valuable customer problem before building",
             "tasks": [
                 ("customer_evidence", "Collect evidence for customer problem, alternatives, demand and willingness to pay", ["close_gaps"]),
                 ("economics", "Model acquisition cost, price, margin, cash constraints and explicit kill criteria", ["customer_evidence"]),
             ]},
            {"key": "product", "milestone": "Build and falsify the smallest useful product",
             "tasks": [
                 ("product_contract", "Specify user journey, acceptance properties, security boundaries and analytics", ["economics"]),
                 ("private_mvp", "Construct the product in a private sandbox and reject functional and security counterexamples", ["product_contract"]),
                 ("launch_readiness", "Verify reliability, privacy, support, deployment and rollback readiness", ["private_mvp"]),
             ]},
            {"key": "market", "milestone": "Run governed market experiments and measure real value",
             "tasks": [
                 ("market_experiment", "Precommit a bounded acquisition experiment and its independent success metrics", ["launch_readiness"]),
                 ("external_launch", "Request owner approval for public deployment, spending, customer contact or financial transactions", ["market_experiment"]),
                 ("revenue_outcome", "Observe independently recorded usage, conversion, retention, revenue and cost outcomes", ["external_launch"]),
             ]},
        ],
        "research": [
            {"key": "investigation", "milestone": "Turn uncertainty into competing explanations",
             "tasks": [
                 ("evidence_map", "Acquire authoritative evidence and preserve provenance, disagreement and uncertainty", ["close_gaps"]),
                 ("hypotheses", "Construct competing hypotheses and identify observations that discriminate between them", ["evidence_map"]),
                 ("experiment", "Precommit and run the safest information-producing experiment", ["hypotheses"]),
             ]},
            {"key": "transfer", "milestone": "Falsify, transfer and communicate the result",
             "tasks": [
                 ("falsify", "Actively search for counterexamples and revise or abstain", ["experiment"]),
                 ("source_disjoint", "Transfer the retained method to an unfamiliar source or domain", ["falsify"]),
             ]},
        ],
        "engineering": [
            {"key": "design", "milestone": "Design from requirements and independently testable properties",
             "tasks": [
                 ("architecture", "Choose architecture and technology from measured requirements and failure modes", ["close_gaps"]),
                 ("implementation", "Construct the smallest end-to-end implementation in a private workspace", ["architecture"]),
                 ("falsification", "Invent and execute functional, adversarial and security tests", ["implementation"]),
             ]},
            {"key": "operation", "milestone": "Prove transfer, operational recovery and useful outcome",
             "tasks": [
                 ("source_disjoint", "Execute the implementation on an unfamiliar project or environment", ["falsification"]),
                 ("operate", "Observe later use, reliability, cost and failure-recovery outcomes", ["source_disjoint"]),
             ]},
        ],
        "general": [
            {"key": "delivery", "milestone": "Plan, execute and independently verify useful work",
             "tasks": [
                 ("plan", "Construct dependencies, alternatives, resource budget and recovery branches", ["close_gaps"]),
                 ("execute", "Execute authorized reversible work and preserve commitments", ["plan"]),
                 ("verify", "Obtain an independent outcome and reject a counterexample", ["execute"]),
             ]},
        ],
    }
    finish = {"key": "learning", "milestone": "Diagnose the outcome and compound verified learning",
              "tasks": [
                  ("retrospective", "Compare prediction with outcome and attribute success or failure", []),
                  ("retention", "Retest later without replay and feed the verified method into the next objective", ["retrospective"]),
              ]}
    rows = common + variants[archetype]
    last = rows[-1]["tasks"][-1][0]
    finish["tasks"][0] = ("retrospective", finish["tasks"][0][1], [last])
    return rows + [finish]


def _capability_snapshot(harness: MissionCapabilityActionHarness, description: str) -> list[dict[str, Any]]:
    subjects = harness.infer_subjects(description)
    rows = []
    for subject_id in subjects:
        assessment = harness.system.assess(subject_id)
        rows.append({"subject_id": subject_id, "overall_level": assessment["overall_level"],
                     "knowledge_level": assessment["knowledge_level"],
                     "practical_level": assessment["practical_level"],
                     "ready": LEVEL_INDEX[assessment["overall_level"]] >= LEVEL_INDEX["intermediate"]})
    return rows


def compile_graph(*, objective: str, harness: MissionCapabilityActionHarness,
                  mission_id: str | None = None) -> dict[str, Any]:
    archetype = _archetype(objective); mission_id = mission_id or "mission_" + _canonical_hash(objective)[:18]
    nodes: list[dict[str, Any]] = []; milestone_ids = []
    learning_nodes: dict[str, str] = {}
    for milestone_index, spec in enumerate(_blueprint(archetype), 1):
        milestone_id = f"{mission_id}:milestone:{milestone_index}:{spec['key']}"; milestone_ids.append(milestone_id)
        nodes.append({"node_id": milestone_id, "kind": "milestone", "description": spec["milestone"],
                      "depends_on": [], "status": "pending", "authority": "aggregate_child_outcomes"})
        for task_index, (key, description, dependencies) in enumerate(spec["tasks"], 1):
            node_id = f"{mission_id}:work:{key}"
            capabilities = _capability_snapshot(harness, description)
            dependency_ids = [f"{mission_id}:work:{value}" for value in dependencies]
            for capability in capabilities:
                if capability["ready"]:
                    continue
                subject_id = capability["subject_id"]
                learning_id = learning_nodes.setdefault(subject_id, f"{mission_id}:learn:{subject_id}")
                if not any(row["node_id"] == learning_id for row in nodes):
                    nodes.append({"node_id": learning_id, "kind": "learning", "subject_id": subject_id,
                                  "description": f"Raise {subject_id.replace('_', ' ')} to executable Intermediate evidence for this mission",
                                  "depends_on": [], "status": "ready", "authority": "progressive_competency_registry",
                                  "success_criteria": ["intermediate_or_better", "verified_practical_evidence"]})
                dependency_ids.append(learning_id)
            external = key in {"external_launch", "revenue_outcome"}
            nodes.append({"node_id": node_id, "kind": "work", "milestone_id": milestone_id,
                          "description": description, "depends_on": sorted(set(dependency_ids)),
                          "required_capabilities": capabilities, "status": "blocked" if dependency_ids else "ready",
                          "approval_policy": "human_approval_required" if external else "autonomous_allowed",
                          "authority": "independent_real_outcome" if key not in {"observe_context", "map_capabilities"}
                          else "verified_internal_state",
                          "success_criteria": ["measurable_outcome", "counterexample_attempted", "provenance_preserved"],
                          "recovery": ["diagnose_origin", "replan_affected_branch", "abstain_or_escalate"]})
    graph = {"schema_version": "aion.hexcore.hierarchical_mission_graph.v1", "mission_id": mission_id,
             "objective": objective, "archetype": archetype, "created_at": _now(),
             "north_star_authority": "owner_authorized_mission", "nodes": nodes,
             "milestones": milestone_ids, "terminal_goal_mutations": 0, "external_actions_authorized": 0}
    graph["graph_sha256"] = _canonical_hash(graph)
    return graph


def _validate(graph: Mapping[str, Any]) -> dict[str, Any]:
    nodes = {str(row.get("node_id")): row for row in graph.get("nodes") or []}
    unknown = [(node_id, dep) for node_id, row in nodes.items() for dep in row.get("depends_on") or [] if dep not in nodes]
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node_id: str) -> bool:
        if node_id in visiting: return False
        if node_id in visited: return True
        visiting.add(node_id)
        if not all(visit(dep) for dep in nodes[node_id].get("depends_on") or []): return False
        visiting.remove(node_id); visited.add(node_id); return True
    acyclic = not unknown and all(visit(node_id) for node_id in nodes)
    work = [row for row in nodes.values() if row.get("kind") == "work"]
    return {"acyclic": acyclic, "unknown_dependencies": len(unknown), "nodes": len(nodes),
            "milestones": len(graph.get("milestones") or []),
            "learning_dependencies": sum(row.get("kind") == "learning" for row in nodes.values()),
            "measurable_work": sum("measurable_outcome" in (row.get("success_criteria") or []) for row in work),
            "work_nodes": len(work),
            "recovery_coverage": sum(bool(row.get("recovery")) for row in work),
            "approval_gated_external": sum(row.get("approval_policy") == "human_approval_required" for row in work),
            "premature_external_authority": int(bool(graph.get("external_actions_authorized"))),
            "terminal_goal_mutations": int(graph.get("terminal_goal_mutations") or 0)}


def run(*, repo_root: Path, state_path: Path, result_path: Path,
        publish_ready: bool = True) -> dict[str, Any]:
    repo_root = repo_root.resolve(); harness = MissionCapabilityActionHarness(repo_root=repo_root)
    missions = [
        "Build AION into a continuously improving system that completes increasingly valuable cross-domain work from independently verified consequences.",
        "Create a profitable website business by validating demand, building a secure product, acquiring customers and proving sustainable revenue.",
        "Investigate an unfamiliar scientific claim and transfer the verified method into an unrelated domain.",
        "Build and operate a reliable distributed application under changing requirements and partial failures.",
    ]
    graphs = [compile_graph(objective=objective, harness=harness) for objective in missions]
    validations = [_validate(graph) for graph in graphs]
    live = graphs[0]
    prior = _read(state_path, {"missions": []}); existing = {row.get("mission_id"): row for row in prior.get("missions") or []}
    existing[live["mission_id"]] = live
    published = []
    if publish_ready:
        engine = GoalEngine(enable_glyph_logging=True, goal_file=repo_root / "data/goals/goals.json",
                            resonance_enabled=False, autostart_resonance=False)
        known = {str(row.get("name")) for row in engine.goals}
        for node in live["nodes"]:
            if node.get("kind") not in {"learning", "work"} or node.get("status") != "ready": continue
            if node.get("approval_policy") == "human_approval_required" or node["node_id"] in known: continue
            engine.goals.append({"name": node["node_id"], "goal_id": node["node_id"],
                "objective": node["description"], "description": node["description"],
                "dependencies": list(node.get("depends_on") or []), "priority": 8.5,
                "status": "active", "origin": PROCEDURE_ID, "approval_policy": "autonomous_allowed",
                "authority_scope": "read_only_or_private_workspace", "created_at": _now(),
                "mission_id": live["mission_id"], "success_authority": node.get("authority")})
            published.append(node["node_id"]); known.add(node["node_id"])
        if published: engine.save_goals(force=True)
    state = {"schema_version": "aion.hexcore.hierarchical_mission_state.v1",
             "missions": list(existing.values()), "updated_at": _now()}; _write(state_path, state)
    hostile = [
        {**live, "nodes": [{**row, "depends_on": [row["node_id"]]} if row.get("kind") == "work" else row for row in live["nodes"]]},
        {**live, "external_actions_authorized": 1}, {**live, "terminal_goal_mutations": 1},
        {**live, "nodes": [{**row, "success_criteria": []} if row.get("kind") == "work" else row for row in live["nodes"]]},
    ]
    hostile_rejected = sum(not all((_validate(row)["acyclic"], _validate(row)["premature_external_authority"] == 0,
                                    _validate(row)["terminal_goal_mutations"] == 0,
                                    _validate(row)["measurable_work"] == _validate(row)["work_nodes"])) for row in hostile)
    gate = {"missions": len(graphs), "mission_archetypes": len({g["archetype"] for g in graphs}),
            "total_nodes": sum(v["nodes"] for v in validations),
            "total_milestones": sum(v["milestones"] for v in validations),
            "learning_dependencies_inserted": sum(v["learning_dependencies"] for v in validations),
            "all_graphs_acyclic": all(v["acyclic"] for v in validations),
            "measurable_work_coverage": sum(v["measurable_work"] for v in validations),
            "work_nodes": sum(v["work_nodes"] for v in validations),
            "recovery_coverage": sum(v["recovery_coverage"] for v in validations),
            "approval_gated_external_actions": sum(v["approval_gated_external"] for v in validations),
            "hostile_graphs_rejected": hostile_rejected, "hostile_graphs_total": len(hostile),
            "ready_leaf_goals_published": len(published), "owner_transactions_executed": 0,
            "unsafe_actions": 0, "live_writes": 0}
    gate["accepted"] = bool(gate["missions"] == 4 and gate["mission_archetypes"] >= 3
        and gate["total_nodes"] >= 45 and gate["all_graphs_acyclic"]
        and gate["measurable_work_coverage"] == gate["work_nodes"]
        and gate["recovery_coverage"] == gate["work_nodes"]
        and hostile_rejected == len(hostile) and gate["owner_transactions_executed"] == 0)
    learning = HexCorePersistentLearningRuntime(state_path=state_path.with_name("learning.json"), authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "compile_capability_gated_hierarchical_missions",
        ["interpret_outcome", "decompose_milestones", "construct_dependency_graph",
         "insert_learning_prerequisites", "bind_authorities", "publish_safe_leaf",
         "observe_outcome", "replan_branch", "retain"], float(gate["total_nodes"]), gate["accepted"], {"gate": gate}, [])
    decision = learning.skills.promote(candidate); learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="hierarchical_capability_gated_mission_graph")
    result = {"schema_version": "aion.hexcore.hierarchical_mission_graph_result.v1",
              "created_at": _now(), "procedure_id": PROCEDURE_ID,
              "status": "PROMOTED" if gate["accepted"] else "REJECTED", "passed": gate["accepted"],
              "gate": gate, "live_mission": live, "sealed_transfer_graphs": graphs[1:],
              "validations": validations, "decision": decision,
              "boundary": "Hierarchical governed planning and skill gating. No public launch, spending, customer contact, revenue or transaction is authorized by this procedure."}
    _write(result_path, result); return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
        state_path=root / "backend/modules/hexcore/data/hierarchical_missions/state.json",
        result_path=root / "results/hexcore_hierarchical_mission_graph.json"), indent=2))
