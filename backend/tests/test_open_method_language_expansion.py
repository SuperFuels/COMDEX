from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.hierarchical_mission_graph import compile_graph
from backend.modules.hexcore.open_method_language_expansion import METHOD_ID, run


class _System:
    def assess(self, subject_id: str) -> dict[str, str]:
        level = "beginner" if "business" in subject_id else "advanced"
        return {"overall_level": level, "knowledge_level": level, "practical_level": level}


class _Harness:
    system = _System()

    def infer_subjects(self, description: str) -> list[str]:
        return ["business_management"] if "customer" in description.lower() else ["python_core"]


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_invents_missing_graph_audit_and_transfers_before_install(tmp_path: Path) -> None:
    objectives = [
        "Build AION into a continuously improving system.",
        "Create a profitable website business and acquire customers.",
        "Investigate an unfamiliar scientific claim.",
        "Build and operate a reliable distributed application.",
    ]
    graphs = [compile_graph(objective=value, harness=_Harness()) for value in objectives]
    _write(tmp_path / "results/hexcore_hierarchical_mission_graph.json", {
        "live_mission": graphs[0], "sealed_transfer_graphs": graphs[1:], "passed": True,
    })
    _write(tmp_path / "results/hexcore_experience_compiled_project_intelligence.json", {
        "passed": True, "method_library": {"prototypes": {"old_method": {}}},
    })
    state = tmp_path / "state.json"; registry = tmp_path / "registry.json"; result_path = tmp_path / "result.json"
    waiting = run(repo_root=tmp_path, state_path=state, registry_path=registry,
                  result_path=result_path, minimum_delay_seconds=0)
    assert waiting["status"] == "WAITING"
    promoted = run(repo_root=tmp_path, state_path=state, registry_path=registry,
                   result_path=result_path, minimum_delay_seconds=0)
    assert promoted["passed"] is True
    assert promoted["gate"]["source_disjoint_transfers"] == 3
    assert promoted["gate"]["counterexamples_rejected"] == promoted["gate"]["counterexamples_total"]
    retained = json.loads(registry.read_text())["methods"]
    assert METHOD_ID in retained
