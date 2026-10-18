from __future__ import annotations

from copy import deepcopy

from backend.modules.hexcore.hierarchical_mission_graph import _validate, compile_graph


class _System:
    def assess(self, subject_id: str) -> dict[str, str]:
        level = "advanced" if subject_id in {"python_core", "software_engineering"} else "beginner"
        return {"overall_level": level, "knowledge_level": level, "practical_level": level}


class _Harness:
    system = _System()

    def infer_subjects(self, description: str) -> list[str]:
        if "market" in description.lower() or "customer" in description.lower():
            return ["business_management"]
        return ["python_core", "software_engineering"]


def test_business_objective_becomes_capability_gated_goal_dag() -> None:
    graph = compile_graph(
        objective="Create a profitable website business and prove sustainable revenue.",
        harness=_Harness(),
    )
    gate = _validate(graph)
    assert graph["archetype"] == "venture"
    assert gate["acyclic"] is True
    assert gate["learning_dependencies"] > 0
    assert gate["measurable_work"] == gate["work_nodes"]
    assert gate["recovery_coverage"] == gate["work_nodes"]
    assert gate["approval_gated_external"] > 0
    gated_work = [row for row in graph["nodes"] if row.get("kind") == "work"
                  and any(cap.get("ready") is False for cap in row.get("required_capabilities") or [])]
    assert gated_work
    assert all(any(":learn:" in dep for dep in row["depends_on"]) for row in gated_work)


def test_invalid_cycle_and_external_authority_fail_validation() -> None:
    graph = compile_graph(objective="Build a reliable application.", harness=_Harness())
    bad = deepcopy(graph)
    target = next(row for row in bad["nodes"] if row.get("kind") == "work")
    target["depends_on"] = [target["node_id"]]
    assert _validate(bad)["acyclic"] is False
    bad = deepcopy(graph)
    bad["external_actions_authorized"] = 1
    assert _validate(bad)["premature_external_authority"] == 1
