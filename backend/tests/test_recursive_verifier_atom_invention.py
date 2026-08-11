from pathlib import Path

from backend.modules.hexcore.recursive_verifier_atom_invention import execute_atom, run


def test_typed_atom_executes_three_artifact_families_and_rejects_authority_expansion():
    assert execute_atom({"kind": "text", "min_words": 2, "required_concepts": ["proof"]},
                        "Proof remains independently checkable.")["passed"]
    graph = {"nodes": [{"id": "a", "depends_on": [], "success": ["ok"], "recovery": ["retry"]}]}
    assert execute_atom({"kind": "json_graph"}, graph)["passed"]
    tests = "import candidate\nassert candidate.f(3) == 6\n"
    assert execute_atom({"kind": "python", "test_program": tests},
                        "def f(value):\n    return value * 2\n")["passed"]
    assert not execute_atom({"kind": "python", "test_program": tests},
                            "import os\ndef f(value): return value * 2")["passed"]
    assert not execute_atom({"kind": "shell"}, "echo unsafe")["passed"]


def test_atom_requires_precommit_then_promotes_by_digest(tmp_path: Path):
    root = tmp_path
    (root / "data/aion/canonical_runtime").mkdir(parents=True)
    (root / "data/aion/canonical_runtime/method_registry.json").write_text('{"methods":{}}')
    state = root / "state.json"
    registry = root / "atom_registry.json"
    result = root / "result.json"
    first = run(repo_root=root, state_path=state, registry_path=registry,
                result_path=result, minimum_delay_seconds=0)
    assert first["status"] == "WAITING"
    second = run(repo_root=root, state_path=state, registry_path=registry,
                 result_path=result, minimum_delay_seconds=0)
    assert second["status"] == "PROMOTED"
    assert second["gate"]["source_disjoint_execution"] == 3
    assert second["gate"]["counterexamples_rejected"] == 6

