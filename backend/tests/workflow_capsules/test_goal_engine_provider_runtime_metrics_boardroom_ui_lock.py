from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_provider_runtime_metrics_boardroom_renderer_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineProviderRuntimeMetricsPanelV1" in text
    assert 'data-aion-goal-engine-provider-runtime-metrics="v1"' in text
    assert "Provider Runtime Metrics" in text


def test_provider_runtime_metrics_boardroom_names_canonical_fields():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineProviderRuntimeMetricsPanelV1"):
        text.index("function renderAionGoalEngineProviderAuditPanelV1")
    ]

    for field in [
        "provider_audit",
        "provider_audits",
        "latency_ms",
        "runtime_duration_ms",
        "token_count",
        "cost_estimate",
        "fallback_used",
        "degradation_mode",
        "degradation_event",
        "failed_closed",
        "external_writes",
        "business_state_mutation",
    ]:
        assert field in block


def test_provider_runtime_metrics_boardroom_is_read_only_visibility():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineProviderRuntimeMetricsPanelV1"):
        text.index("function renderAionGoalEngineProviderAuditPanelV1")
    ]

    assert "Read-only provider telemetry" in block
    assert "does not grant execution permission" in block
    assert "would_grant_permission" not in block


def test_provider_runtime_metrics_boardroom_mounts_after_provider_audit_panel():
    text = APP.read_text()
    assert "renderAionGoalEngineProviderRuntimeMetricsPanelV1(snapshot)" in text
    assert text.index("renderAionGoalEngineProviderAuditPanelV1(snapshot)") < text.index(
        "renderAionGoalEngineProviderRuntimeMetricsPanelV1(snapshot)"
    )


def test_provider_runtime_metrics_boardroom_exported_to_window():
    text = APP.read_text()
    assert "window.renderAionGoalEngineProviderRuntimeMetricsPanelV1" in text
