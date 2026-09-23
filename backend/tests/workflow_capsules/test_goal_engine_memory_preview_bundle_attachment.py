from backend.modules.aion.goal_engine.memory_model import (
    MemoryPolicyContract,
    MemoryRecordContract,
)
from backend.modules.aion.goal_engine.preview_bundle import (
    _build_memory_runtime_summary,
    build_goal_engine_preview_bundle,
)


def _contracts():
    return [
        MemoryRecordContract(
            memory_id="mem_preview_bundle_1",
            tier="goal",
            content_ref="content://goal/onboarding-plan",
            source_ref="run://run_memory_preview_bundle",
            provenance={"source": "memory_preview_bundle_test"},
            confidence=0.91,
            goal_id="goal_memory_1",
            glyph_code="WD-101",
            run_id="run_memory_preview_bundle",
            tags=["goal", "preview"],
        ),
        MemoryPolicyContract(
            policy_id="policy_preview_bundle_1",
            tier="goal",
            retention_policy="goal_lifetime",
            write_guard="human_review",
            read_guard="allow",
            allow_forgetting=True,
            allow_consolidation=True,
            max_records=50,
            expiry_required=False,
            provenance_required=True,
        ),
    ]


def test_memory_runtime_summary_preserves_preview_only_rows():
    summary = _build_memory_runtime_summary(contracts=_contracts())

    assert summary["trace_type"] == "memory_runtime_summary"
    assert summary["memory_record_count"] == 1
    assert summary["memory_policy_count"] == 1
    assert summary["tier_counts"]["goal"] == 1
    assert summary["retention_policy_counts"]["goal_lifetime"] == 1
    assert len(summary["memory_record_previews"]) == 1
    assert len(summary["memory_policy_previews"]) == 1

    record = summary["memory_record_previews"][0]
    policy = summary["memory_policy_previews"][0]

    assert record["memory_id"] == "mem_preview_bundle_1"
    assert record["would_write_memory"] is False
    assert policy["policy_id"] == "policy_preview_bundle_1"
    assert policy["would_write_memory"] is False
    assert summary["dry_run_only"] is True
    assert summary["would_write_memory"] is False
    assert summary["would_grant_permission"] is False


def test_preview_bundle_exposes_memory_top_level_and_machine_trace():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_memory_preview_bundle",
        workflow_id="workflow_memory_preview_bundle",
        contracts=_contracts(),
    )

    payload = bundle.to_dict()
    machine_trace = payload["machine_trace"]

    assert "memory_runtime_summary" in payload
    assert "goal_engine_memory_runtime_summary" in payload
    assert "memory_record_previews" in payload
    assert "memory_policy_previews" in payload
    assert len(payload["memory_record_previews"]) == 1
    assert len(payload["memory_policy_previews"]) == 1

    assert "memory_runtime_summary" in machine_trace
    assert "goal_engine_memory_runtime_summary" in machine_trace
    assert "memory_record_previews" in machine_trace
    assert "memory_policy_previews" in machine_trace
    assert len(machine_trace["memory_record_previews"]) == 1
    assert len(machine_trace["memory_policy_previews"]) == 1

    assert machine_trace["memory_runtime_summary"]["would_write_memory"] is False
    assert machine_trace["memory_runtime_summary"]["dry_run_only"] is True


def test_preview_bundle_mapping_access_supports_memory_fields():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_memory_mapping",
        workflow_id="workflow_memory_mapping",
        contracts=_contracts(),
    )

    assert bundle["memory_runtime_summary"]["memory_record_count"] == 1
    assert bundle["memory_record_previews"][0]["memory_id"] == "mem_preview_bundle_1"
    assert bundle.get("memory_policy_previews")[0]["policy_id"] == "policy_preview_bundle_1"


def test_empty_contracts_keep_safe_empty_memory_summary():
    summary = _build_memory_runtime_summary(contracts=[])

    assert summary["memory_record_count"] == 0
    assert summary["memory_policy_count"] == 0
    assert summary["memory_record_previews"] == []
    assert summary["memory_policy_previews"] == []
    assert summary["dry_run_only"] is True
    assert summary["would_write_memory"] is False
    assert summary["would_grant_permission"] is False
