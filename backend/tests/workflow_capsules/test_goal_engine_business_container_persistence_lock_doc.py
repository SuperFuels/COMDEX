
from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_business_container_persistence_lock.tex")

def test_goal_engine_business_container_persistence_lock_doc_exists():

    assert DOC.exists()

def test_goal_engine_business_container_lock_names_canonical_containers():

    text = DOC.read_text()

    for needle in [

        "goal\\_engine\\_state",

        "goal\\_engine\\_memory",

        "goal\\_engine\\_evidence",

        "goal\\_engine\\_experiments",

        "goal\\_engine\\_loops",

        "goal\\_engine\\_outcomes",

    ]:

        assert needle in text

def test_goal_engine_business_container_lock_forbids_boardroom_as_storage():

    text = DOC.read_text()

    assert "Boardroom MUST read from projections, not act as storage" in text

    assert "persistent_truth_source = business_containers" in text

    assert "boardroom_projection_only = true" in text

def test_goal_engine_business_container_lock_keeps_preview_bundle_dry_run_only():

    text = DOC.read_text()

    assert "GoalEnginePreviewBundle" in text

    assert "dry_run_only = true" in text

    assert "would_write_memory = false" in text

    assert "would_grant_permission = false" in text

def test_goal_engine_business_container_lock_has_footer():

    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-BUSINESS-CONTAINER-PERSISTENCE-V1" in text

    assert "Status: LOCKED" in text

    assert "Maintainer: Tessaris AI" in text

    assert "Author: Kevin Robinson" in text

