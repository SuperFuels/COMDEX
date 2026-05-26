from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_versioning_reproducibility_lock.tex")


def test_versioning_reproducibility_lock_doc_exists():
    assert DOC.exists()


def test_versioning_reproducibility_lock_names_canonical_block():
    text = DOC.read_text()
    assert "goal_engine_reproducibility" in text
    assert "trace_type = goal_engine_reproducibility" in text


def test_versioning_reproducibility_lock_names_required_versions_and_checksums():
    text = DOC.read_text()
    for token in [
        "goal_version",
        "experiment_version",
        "loop_version",
        "outcome_schema_version",
        "memory_schema_version",
        "checkpoint_schema_version",
        "source_capsule_checksum",
        "goal_contract_checksum",
    ]:
        assert token in text


def test_versioning_reproducibility_lock_names_safety_invariants():
    text = DOC.read_text()
    assert "versions_pinned = true" in text
    assert "preserve_old_versions = true" in text
    assert "rollback_supported = false" in text
    assert "dry_run_only = true" in text
    assert "MUST NOT mutate business containers or external systems" in text


def test_versioning_reproducibility_lock_has_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-VERSIONING-REPRODUCIBILITY-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
