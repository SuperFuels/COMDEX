from backend.modules.aion_lrm.reasoning_memory_snapshot import (
    REASONING_MEMORY_SNAPSHOT_VERSION,
    build_default_home_fixed_reasoning_memory_snapshot,
    build_reasoning_memory_snapshot,
)


def test_phase20b_default_snapshot_builds():
    snapshot = build_default_home_fixed_reasoning_memory_snapshot()

    assert snapshot["snapshot_version"] == REASONING_MEMORY_SNAPSHOT_VERSION
    assert snapshot["workspace_id"] == "home_fixed"
    assert snapshot["memory_scope"] == "business_runtime_preview"
    assert snapshot["preview_only"] if "preview_only" in snapshot else snapshot["safety"]["preview_only"]
    assert snapshot["safety"]["human_review_required"] is True
    assert snapshot["snapshot_hash"].startswith("reasoning_memory_snapshot_")
    assert snapshot["summary_hash"].startswith("reasoning_memory_summary_")


def test_phase20b_snapshot_contains_required_context_slots():
    snapshot = build_default_home_fixed_reasoning_memory_snapshot()
    slots = snapshot["memory_slots"]

    for key in [
        "website_intake",
        "commercial_ticket",
        "workflow_context",
        "agentmap_context",
        "boardroom_context",
        "proof_context",
        "ets_context",
    ]:
        assert key in slots


def test_phase20b_snapshot_is_deterministic():
    one = build_default_home_fixed_reasoning_memory_snapshot()
    two = build_default_home_fixed_reasoning_memory_snapshot()

    assert one["snapshot_hash"] == two["snapshot_hash"]
    assert one["summary_hash"] == two["summary_hash"]


def test_phase20b_snapshot_changes_when_context_changes():
    one = build_reasoning_memory_snapshot({
        "website_intake": {"customer_message": "Roof leak in Albox"}
    })
    two = build_reasoning_memory_snapshot({
        "website_intake": {"customer_message": "Pergola repair in Arboleas"}
    })

    assert one["snapshot_hash"] != two["snapshot_hash"]


def test_phase20b_does_not_store_private_chain_of_thought_or_secrets():
    snapshot = build_reasoning_memory_snapshot({
        "website_intake": {
            "customer_message": "Need a quote",
            "private_chain_of_thought": "PRIVATE_COT_VALUE",
            "access_token": "ACCESS_TOKEN_VALUE",
        },
        "chain_of_thought": "ROOT_COT_VALUE",
        "api_key": "API_KEY_VALUE",
    })

    text = str(snapshot)

    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "ROOT_COT_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    # Secret values and raw credential values must not be retained.
    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "ROOT_COT_VALUE" not in text
    assert "API_KEY_VALUE" not in text

    # Policy keys are allowed because they prove the storage boundary.
    assert snapshot["retention_policy"]["store_hidden_reasoning"] is False
    assert snapshot["retention_policy"]["store_private_chain_of_thought"] is False
    assert snapshot["retention_policy"]["store_credentials"] is False


def test_phase20b_snapshot_has_no_live_side_effects():
    snapshot = build_default_home_fixed_reasoning_memory_snapshot()
    safety = snapshot["safety"]

    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20b_retention_policy_is_preview_only():
    snapshot = build_default_home_fixed_reasoning_memory_snapshot()
    policy = snapshot["retention_policy"]

    assert policy["preview_only"] is True
    assert policy["store_private_chain_of_thought"] is False
    assert policy["store_hidden_reasoning"] is False
    assert policy["store_credentials"] is False
    assert policy["store_live_execution_authority"] is False
    assert policy["human_review_required"] is True
