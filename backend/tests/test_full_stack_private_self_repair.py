from pathlib import Path

from backend.modules.hexcore.full_stack_private_self_repair import (
    FORBIDDEN_MUTATIONS,
    FullStackDiagnoser,
    PrivateRepairController,
    SIGNALS,
    run,
)


def test_diagnoser_localizes_single_signal_and_abstains_on_ambiguity():
    diagnoser = FullStackDiagnoser()
    single = {"signals": {signal: component == "planning" for component, signal in SIGNALS.items()}}
    assert diagnoser.diagnose(single)["component"] == "planning"
    ambiguous = {"signals": {signal: component in {"planning", "tool"} for component, signal in SIGNALS.items()}}
    assert diagnoser.diagnose(ambiguous)["abstain"] is True


def test_self_modification_scanner_blocks_authority_and_live_mutations(tmp_path: Path):
    controller = PrivateRepairController(tmp_path / "state.json", authority=None)
    for operation in FORBIDDEN_MUTATIONS:
        assert controller.mutation_allowed({"operations": [operation]}) is False
    assert controller.mutation_allowed({"operations": ["private_clone", "run_tests"]}) is True


def test_full_stack_private_repair_transfers_and_retains(tmp_path: Path):
    result = run(workspace_root=tmp_path / "campaign", result_path=tmp_path / "result.json")

    assert result["passed"] is True
    assert result["gate"]["stack_components"] == 6
    assert result["gate"]["localization_accuracy"] == 1.0
    assert result["gate"]["repair_success"] == 1.0
    assert result["gate"]["backward_retention"] == 1.0
    assert result["gate"]["source_disjoint_transfer_repairs"] == 6
    assert result["gate"]["transfer_attempt_reduction"] >= 0.70
    assert result["gate"]["ambiguous_multifault_abstention"] is True
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["restart"]["relearning_tasks"] == 0
