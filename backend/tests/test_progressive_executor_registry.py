from pathlib import Path

from backend.modules.hexcore.progressive_executor_registry import ProgressiveExecutorRegistry


def test_registry_persists_missing_adapter_as_resumable_acquisition(tmp_path: Path):
    path = tmp_path / "registry.json"
    registry = ProgressiveExecutorRegistry(path=path)
    contract = {"subject_id": "unknown_science", "requirement": {
        "kind": "project", "subskills": ["measurement"], "authority": "outcome"}}
    subject = {"name": "Unknown Science", "group": "science"}
    gap = registry.observe_contract(contract=contract, subject=subject,
                                    available_subjects={"python_core"})
    assert gap["status"] == "acquisition_required"
    assert gap["family"] == "empirical_dataset_or_experiment"
    restarted = ProgressiveExecutorRegistry(path=path)
    summary = restarted.summary(subjects={"unknown_science": subject})
    assert summary["open_gaps"] == 1
    assert summary["catalog_coverage_gaps"] == 1


def test_registry_resolves_gap_when_verified_adapter_appears(tmp_path: Path):
    registry = ProgressiveExecutorRegistry(path=tmp_path / "registry.json")
    contract = {"subject_id": "new_subject", "requirement": {
        "kind": "lesson", "subskills": ["alpha"], "authority": "execution"}}
    subject = {"name": "New Subject", "group": "computing"}
    registry.observe_contract(contract=contract, subject=subject, available_subjects=set())
    result = registry.observe_contract(contract=contract, subject=subject,
                                       available_subjects={"new_subject"})
    assert result["status"] == "available"
    summary = registry.summary(subjects={"new_subject": subject})
    assert summary["open_gaps"] == 0
    assert summary["catalog_coverage_gaps"] == 0
