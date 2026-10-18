from backend.modules.aion.goal_engine.memory_model import (
    MemoryPolicyContract,
    MemoryRecordContract,
)
from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def test_preview_bundle_exposes_memory_runtime_summary():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint7_memory_test",
        workflow_id="workflow_sprint7_memory_test",
        contracts=[
            MemoryRecordContract(
                memory_id="mem_goal_001",
                tier="goal",
                content_ref="goal://objective/001",
                source_ref="run://run_001",
                provenance={"source": "goal_engine"},
                confidence=0.8,
                goal_id="goal_001",
                glyph_code="MK-001",
            ),
            MemoryPolicyContract(
                policy_id="policy_goal_memory",
                tier="goal",
                retention_policy="goal_lifetime",
                write_guard="human_review",
                read_guard="allow",
                allow_consolidation=True,
                max_records=20,
            ),
        ],
    )

    payload = bundle.to_dict()

    assert "memory_runtime_summary" in payload
    summary = payload["memory_runtime_summary"]

    assert summary["schema_version"] == "aion.goal_engine.memory_runtime_summary.v1"
    assert summary["trace_type"] == "memory_runtime_summary"
    assert summary["memory_record_count"] == 1
    assert summary["memory_policy_count"] == 1
    assert summary["valid_record_count"] == 1
    assert summary["blocked_record_count"] == 0
    assert summary["valid_policy_count"] == 1
    assert summary["blocked_policy_count"] == 0
    assert summary["tier_counts"]["goal"] == 1
    assert summary["write_guard_counts"]["human_review"] == 1
    assert summary["read_guard_counts"]["allow"] == 1
    assert summary["retention_policy_counts"]["goal_lifetime"] == 1
    assert summary["dry_run_only"] is True
    assert summary["would_write_memory"] is False


def test_preview_bundle_memory_summary_tracks_blocked_reasons():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint7_memory_blocked_test",
        workflow_id="workflow_sprint7_memory_blocked_test",
        contracts=[
            MemoryRecordContract(
                memory_id="",
                tier="unknown",
                content_ref="",
                source_ref="",
                provenance={},
                confidence=2.0,
            ),
            MemoryPolicyContract(
                policy_id="policy_long_term_bad",
                tier="long_term_advisory",
                retention_policy="long_term",
                write_guard="allow",
                read_guard="allow",
                max_records=10,
            ),
        ],
    )

    summary = bundle.to_dict()["memory_runtime_summary"]

    assert summary["memory_record_count"] == 1
    assert summary["memory_policy_count"] == 1
    assert summary["blocked_record_count"] == 1
    assert summary["blocked_policy_count"] == 1

    assert "memory_id_required" in summary["blocked_reasons"]
    assert "unsupported_memory_tier" in summary["blocked_reasons"]
    assert "content_ref_required" in summary["blocked_reasons"]
    assert "source_ref_required" in summary["blocked_reasons"]
    assert "confidence_out_of_range" in summary["blocked_reasons"]
    assert "long_term_memory_requires_human_review_write_guard" in summary["blocked_reasons"]


def test_preview_bundle_memory_summary_preserves_record_and_policy_previews():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint7_memory_preserve_test",
        workflow_id="workflow_sprint7_memory_preserve_test",
        contracts=[
            MemoryRecordContract(
                memory_id="mem_semantic_001",
                tier="semantic_glyph",
                content_ref="glyph://MK-001/pattern",
                source_ref="run://run_123",
                provenance={"source": "workflow_outcome", "evidence_hash": "hash_001"},
                confidence=0.91,
                glyph_code="MK-001",
                run_id="run_123",
                tags=["glyph", "pattern"],
            ),
            MemoryPolicyContract(
                policy_id="policy_semantic_glyph",
                tier="semantic_glyph",
                retention_policy="manual_review",
                write_guard="human_review",
                read_guard="allow",
                allow_forgetting=True,
                allow_consolidation=True,
                max_records=50,
            ),
        ],
    )

    summary = bundle.to_dict()["memory_runtime_summary"]

    assert "memory_record_previews" in summary
    assert "memory_policy_previews" in summary

    record = summary["memory_record_previews"][0]
    policy = summary["memory_policy_previews"][0]

    assert record["memory_id"] == "mem_semantic_001"
    assert record["tier"] == "semantic_glyph"
    assert record["glyph_code"] == "MK-001"
    assert record["provenance"]["evidence_hash"] == "hash_001"
    assert record["confidence"] == 0.91

    assert policy["policy_id"] == "policy_semantic_glyph"
    assert policy["tier"] == "semantic_glyph"
    assert policy["retention_policy"] == "manual_review"
    assert policy["allow_consolidation"] is True


def test_preview_bundle_memory_summary_counts_all_tiers():
    contracts = [
        MemoryRecordContract(
            memory_id=f"mem_{tier}",
            tier=tier,
            content_ref=f"memory://{tier}",
            source_ref="run://tier_count",
            provenance={"source": "test"},
            confidence=0.5,
        )
        for tier in [
            "working",
            "session",
            "goal",
            "episodic_run",
            "semantic_glyph",
            "long_term_advisory",
        ]
    ]

    bundle = build_goal_engine_preview_bundle(
        run_id="run_sprint7_memory_tiers_test",
        workflow_id="workflow_sprint7_memory_tiers_test",
        contracts=contracts,
    )

    summary = bundle.to_dict()["memory_runtime_summary"]

    assert summary["memory_record_count"] == 6
    assert summary["valid_record_count"] == 6

    for tier in [
        "working",
        "session",
        "goal",
        "episodic_run",
        "semantic_glyph",
        "long_term_advisory",
    ]:
        assert summary["tier_counts"][tier] == 1
