from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_provider_runtime_metrics_lock.tex")


def test_provider_runtime_metrics_lock_doc_exists():
    assert DOC.exists()


def test_provider_runtime_metrics_lock_doc_names_canonical_fields():
    text = DOC.read_text()
    for field in [
        "provider_audit",
        "token_count",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "runtime_duration_ms",
        "cost_estimate",
        "degradation_mode",
        "degradation_event",
    ]:
        assert field in text


def test_provider_runtime_metrics_lock_doc_records_local_safety():
    text = DOC.read_text()
    assert "external_writes = blocked" in text
    assert "business_state_mutation = human_review_guarded" in text
    assert "legacy_business_state_mutation = blocked" in text
    assert "would_grant_permission = false" in text


def test_provider_runtime_metrics_lock_doc_records_numeric_defaults():
    text = DOC.read_text()
    assert "numeric defaults" in text
    assert "0.0" in text
    assert "0" in text


def test_provider_runtime_metrics_lock_doc_records_boardroom_read_only_rule():
    text = DOC.read_text()
    assert "read-only telemetry" in text
    assert "MUST NOT use provider audit fields to perform writes" in text


def test_provider_runtime_metrics_lock_doc_footer():
    text = DOC.read_text()
    assert "Lock ID: AION-GOAL-ENGINE-PROVIDER-RUNTIME-METRICS-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
