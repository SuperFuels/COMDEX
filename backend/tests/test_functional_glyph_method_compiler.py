from backend.modules.hexcore.functional_glyph_method_compiler import (
    PLANNER_OPERATORS,
    RUNNER_OPERATORS,
    compile_python_module,
    verify_transfer,
)


def _programs():
    planner = {
        "ir": "aion.functional_method_program.v1",
        "identifier_field": "id", "dependency_field": "depends_on", "priority_field": "priority",
        "capability_field": "capability",
        "level_order": ["unassessed", "beginner", "intermediate", "advanced", "expert"],
        "learning_threshold": "intermediate", "operators": sorted(PLANNER_OPERATORS),
    }
    runner = {"ir": "aion.functional_state_machine.v1",
              "operators": sorted(RUNNER_OPERATORS)}
    return planner, runner


def test_functional_program_compiles_and_transfers_without_raw_source():
    result = compile_python_module(*_programs())
    assert result["passed"]
    assert "Compiled from content-addressed functional glyph programs" in result["source"]
    assert verify_transfer(result["source"])["passed"]


def test_compiler_abstains_if_a_required_operator_is_missing():
    planner, runner = _programs()
    planner["operators"] = planner["operators"][:-1]
    result = compile_python_module(planner, runner)
    assert not result["passed"]
    assert result["status"] == "ABSTAIN_INCOMPLETE_OR_UNKNOWN_OPERATORS"

