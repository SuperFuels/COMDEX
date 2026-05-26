from pathlib import Path


CONTRACTS = Path("backend/modules/aion_business/contracts/business_containers.py")
REPOSITORY = Path("backend/modules/aion_business/runtime/business_container_repository.py")
SERVICE = Path("backend/modules/aion_business/runtime/business_container_service.py")


GOAL_ENGINE_CONTAINER_KINDS = [
    "goal_engine_state",
    "goal_engine_memory",
    "goal_engine_evidence",
    "goal_engine_experiments",
    "goal_engine_loops",
    "goal_engine_outcomes",
]


GOAL_ENGINE_FILES = [
    "goal_engine_state.json",
    "goal_engine_memory.json",
    "goal_engine_evidence.json",
    "goal_engine_experiments.json",
    "goal_engine_loops.json",
    "goal_engine_outcomes.json",
]


def test_goal_engine_container_kinds_are_canonical_business_container_kinds():
    text = CONTRACTS.read_text()

    for kind in GOAL_ENGINE_CONTAINER_KINDS:
        assert f'"{kind}"' in text or f"'{kind}'" in text


def test_goal_engine_container_files_are_mapped_by_repository():
    text = REPOSITORY.read_text()

    for kind in GOAL_ENGINE_CONTAINER_KINDS:
        assert f'"{kind}"' in text or f"'{kind}'" in text

    for filename in GOAL_ENGINE_FILES:
        assert filename in text


def test_goal_engine_containers_are_created_by_business_container_service():
    text = SERVICE.read_text()

    assert "_ensure_goal_engine_containers" in text or "goal_engine_state" in text

    for kind in GOAL_ENGINE_CONTAINER_KINDS:
        assert kind in text

    for topic in [
        "business.goal_engine.state",
        "business.goal_engine.memory",
        "business.goal_engine.evidence",
        "business.goal_engine.experiments",
        "business.goal_engine.loops",
        "business.goal_engine.outcomes",
    ]:
        assert topic in text


def test_goal_engine_business_containers_have_human_review_write_guard():
    text = SERVICE.read_text()

    assert "human_review" in text
    assert "read_guard" in text
    assert "write_guard" in text

    for kind in GOAL_ENGINE_CONTAINER_KINDS:
        assert kind in text


def test_preview_bundle_remains_dry_run_not_persistent_truth():
    text = SERVICE.read_text()

    assert "goal_engine_preview_bundle" in text
    assert "dry_run_only" in text
    assert "would_execute" in text
    assert "would_write_external" in text
    assert "would_grant_permission" in text

    # Boardroom may expose preview data, but it must not be the persistent truth store.
    assert "PreviewBundle" not in text or "dry-run" in text or "dry_run_only" in text


def test_boardroom_snapshot_is_projection_not_goal_engine_storage():
    text = SERVICE.read_text()

    assert "boardroom_snapshot" in text
    assert "operational_runtime_summary" in text

    # Boardroom payload can include projected Goal Engine runtime preview.
    assert "goal_engine_runtime_preview" in text
    assert "goal_engine_preview_bundle" in text

    # But canonical Goal Engine domains must have their own containers.
    for kind in GOAL_ENGINE_CONTAINER_KINDS:
        assert kind in text
