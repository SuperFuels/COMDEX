from backend.modules.aion.goal_engine.preview_bundle import (
    _build_evidence_source_runtime_summary,
    build_goal_engine_preview_bundle,
)


def _contracts():
    return [
        {
            "goal_id": "goal_evidence_1",
            "outcome_id": "outcome_evidence_1",
            "evidence_sources": [
                {
                    "pointer_type": "gmail_reply",
                    "source_ref": "gmail://message/reply_001",
                    "metadata": {"thread_id": "thread_001"},
                },
                {
                    "pointer_type": "crm_lead",
                    "source_ref": "crm://lead/lead_001",
                    "metadata": {"pipeline": "sales"},
                },
                {
                    "pointer_type": "utm_click",
                    "source_ref": "utm://campaign/click_001",
                    "metadata": {"campaign": "spring"},
                },
                {
                    "pointer_type": "booking",
                    "source_ref": "booking://calendar/book_001",
                    "metadata": {"calendar": "ops"},
                },
                {
                    "pointer_type": "payment",
                    "source_ref": "payment://checkout/pay_001",
                    "metadata": {"provider": "revolut"},
                },
                {
                    "pointer_type": "screenshot_file",
                    "source_ref": "file://screenshots/proof_001.png",
                    "metadata": {"kind": "completion_proof"},
                },
            ],
        }
    ]


def test_evidence_source_runtime_summary_preserves_typed_pointer_rows():
    summary = _build_evidence_source_runtime_summary(contracts=_contracts())

    assert summary["trace_type"] == "evidence_source_runtime_summary"
    assert summary["evidence_source_count"] == 6
    assert len(summary["evidence_source_previews"]) == 6
    assert len(summary["evidence_pointer_previews"]) == 6

    types = {item["pointer_type"] for item in summary["evidence_source_previews"]}
    assert {
        "gmail_reply",
        "crm_lead",
        "utm_click",
        "booking",
        "payment",
        "screenshot_file",
    }.issubset(types)

    for row in summary["evidence_source_previews"]:
        assert row["source_ref"]
        assert row["evidence_hash"]
        assert row["dry_run_only"] is True
        assert row["would_fetch_external"] is False
        assert row["would_mutate_business_state"] is False
        assert row["would_mark_outcome_success"] is False
        assert row["would_grant_permission"] is False
        assert row["requires_human_review"] is True


def test_preview_bundle_exposes_evidence_sources_top_level_and_machine_trace():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_evidence_source_bundle_1",
        workflow_id="workflow_evidence_source_bundle_1",
        contracts=_contracts(),
        goal_engine_manifest={"valid": True, "steps": [], "safety_contract": {}},
    )

    payload = bundle.to_dict()
    machine_trace = payload["machine_trace"]

    assert "evidence_source_runtime_summary" in payload
    assert "evidence_source_previews" in payload
    assert "evidence_pointer_previews" in payload
    assert len(payload["evidence_source_previews"]) == 6

    assert "evidence_source_runtime_summary" in machine_trace
    assert "evidence_source_previews" in machine_trace
    assert "evidence_pointer_previews" in machine_trace
    assert len(machine_trace["evidence_source_previews"]) == 6

    assert machine_trace["evidence_source_runtime_summary"]["would_fetch_external"] is False
    assert machine_trace["evidence_source_runtime_summary"]["would_mark_outcome_success"] is False


def test_preview_bundle_mapping_access_supports_evidence_source_fields():
    bundle = build_goal_engine_preview_bundle(
        run_id="run_evidence_source_mapping_1",
        workflow_id="workflow_evidence_source_mapping_1",
        contracts=_contracts(),
        goal_engine_manifest={"valid": True, "steps": [], "safety_contract": {}},
    )

    assert bundle["evidence_source_runtime_summary"]["evidence_source_count"] == 6
    assert bundle.get("evidence_source_previews")[0]["pointer_type"] == "gmail_reply"


def test_empty_contracts_keep_safe_empty_evidence_source_summary():
    summary = _build_evidence_source_runtime_summary(contracts=[])

    assert summary["evidence_source_count"] == 0
    assert summary["evidence_source_previews"] == []
    assert summary["evidence_pointer_previews"] == []
    assert summary["dry_run_only"] is True
    assert summary["would_fetch_external"] is False
    assert summary["would_mutate_business_state"] is False
    assert summary["would_mark_outcome_success"] is False
    assert summary["would_grant_permission"] is False
    assert summary["requires_human_review"] is True
