from backend.modules.aion.goal_engine.memory_model import (
    MEMORY_POLICY_SCHEMA_VERSION,
    MEMORY_RECORD_SCHEMA_VERSION,
    MemoryPolicyContract,
    MemoryRecordContract,
    build_memory_policy_preview,
    build_memory_record_preview,
)


def test_memory_schema_versions_locked():
    assert MEMORY_RECORD_SCHEMA_VERSION == "aion.goal_engine.memory_record.v1"
    assert MEMORY_POLICY_SCHEMA_VERSION == "aion.goal_engine.memory_policy.v1"


def test_memory_record_preview_preserves_core_fields():
    record = MemoryRecordContract(
        memory_id="mem_goal_001",
        tier="goal",
        content_ref="goal://objective/001",
        source_ref="run://run_001",
        provenance={"source": "goal_engine", "step_id": "step_001"},
        confidence=0.86,
        goal_id="goal_001",
        glyph_code="MK-001",
        run_id="run_001",
        tags=["campaign", "outcome"],
    )

    preview = build_memory_record_preview(record)

    assert preview["schema_version"] == MEMORY_RECORD_SCHEMA_VERSION
    assert preview["trace_type"] == "memory_record_preview"
    assert preview["memory_id"] == "mem_goal_001"
    assert preview["tier"] == "goal"
    assert preview["content_ref"] == "goal://objective/001"
    assert preview["source_ref"] == "run://run_001"
    assert preview["provenance"]["step_id"] == "step_001"
    assert preview["confidence"] == 0.86
    assert preview["goal_id"] == "goal_001"
    assert preview["glyph_code"] == "MK-001"
    assert preview["valid"] is True
    assert preview["dry_run_only"] is True
    assert preview["would_write_memory"] is False


def test_memory_record_blocks_missing_required_fields():
    record = MemoryRecordContract(
        memory_id="",
        tier="unknown",
        content_ref="",
        source_ref="",
        provenance={},
        confidence=1.2,
    )

    preview = build_memory_record_preview(record)

    assert preview["valid"] is False
    assert "memory_id_required" in preview["blocked_reasons"]
    assert "unsupported_memory_tier" in preview["blocked_reasons"]
    assert "content_ref_required" in preview["blocked_reasons"]
    assert "source_ref_required" in preview["blocked_reasons"]
    assert "confidence_out_of_range" in preview["blocked_reasons"]


def test_memory_policy_preview_preserves_guard_and_retention_fields():
    policy = MemoryPolicyContract(
        policy_id="policy_goal_memory",
        tier="goal",
        retention_policy="goal_lifetime",
        write_guard="human_review",
        read_guard="allow",
        allow_forgetting=True,
        allow_consolidation=True,
        max_records=25,
        expiry_required=False,
        provenance_required=True,
    )

    preview = build_memory_policy_preview(policy)

    assert preview["schema_version"] == MEMORY_POLICY_SCHEMA_VERSION
    assert preview["trace_type"] == "memory_policy_preview"
    assert preview["policy_id"] == "policy_goal_memory"
    assert preview["tier"] == "goal"
    assert preview["retention_policy"] == "goal_lifetime"
    assert preview["write_guard"] == "human_review"
    assert preview["read_guard"] == "allow"
    assert preview["allow_forgetting"] is True
    assert preview["allow_consolidation"] is True
    assert preview["max_records"] == 25
    assert preview["valid"] is True
    assert preview["dry_run_only"] is True
    assert preview["would_write_memory"] is False


def test_memory_policy_blocks_invalid_guards_and_retention():
    policy = MemoryPolicyContract(
        policy_id="policy_bad",
        tier="bad_tier",
        retention_policy="forever_without_review",
        write_guard="auto_write",
        read_guard="auto_exfiltrate",
        max_records=0,
    )

    preview = build_memory_policy_preview(policy)

    assert preview["valid"] is False
    assert "unsupported_memory_tier" in preview["blocked_reasons"]
    assert "unsupported_retention_policy" in preview["blocked_reasons"]
    assert "unsupported_write_guard" in preview["blocked_reasons"]
    assert "unsupported_read_guard" in preview["blocked_reasons"]
    assert "max_records_required" in preview["blocked_reasons"]


def test_long_term_memory_requires_human_review_write_guard():
    policy = MemoryPolicyContract(
        policy_id="policy_long_term",
        tier="long_term_advisory",
        retention_policy="long_term",
        write_guard="allow",
        read_guard="allow",
        max_records=50,
    )

    preview = build_memory_policy_preview(policy)

    assert preview["valid"] is False
    assert "long_term_memory_requires_human_review_write_guard" in preview["blocked_reasons"]


def test_all_memory_tiers_are_supported():
    tiers = [
        "working",
        "session",
        "goal",
        "episodic_run",
        "semantic_glyph",
        "long_term_advisory",
    ]

    for tier in tiers:
        record = MemoryRecordContract(
            memory_id=f"mem_{tier}",
            tier=tier,
            content_ref=f"memory://{tier}",
            source_ref="run://test",
            provenance={"source": "test"},
            confidence=0.5,
        )
        preview = build_memory_record_preview(record)
        assert preview["valid"] is True
        assert preview["tier"] == tier
