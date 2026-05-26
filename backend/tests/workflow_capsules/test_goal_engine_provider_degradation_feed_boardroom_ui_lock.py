from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_provider_degradation_feed_renderer_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineProviderDegradationFeedV1" in text
    assert 'data-aion-goal-engine-provider-degradation-feed="v1"' in text
    assert "Provider Degradation Feed" in text


def test_provider_degradation_feed_reads_fallback_and_degradation_fields():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineProviderDegradationFeedV1"):
        text.index("/* AION PATCH: Goal Engine Provider Runtime Metrics Boardroom Visibility v1 */")
    ]

    for field in [
        "provider_audit",
        "provider_audits",
        "fallback_used",
        "failed_closed",
        "degradation_mode",
        "degradation_event",
        "error_code",
        "provider",
        "model",
        "capability",
    ]:
        assert field in block


def test_provider_degradation_feed_is_visibility_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineProviderDegradationFeedV1"):
        text.index("/* AION PATCH: Goal Engine Provider Runtime Metrics Boardroom Visibility v1 */")
    ]

    assert "Read-only fallback/degradation telemetry" in block
    assert "does not retry, escalate, or mutate provider state" in block
    assert "addSection" not in block


def test_provider_degradation_feed_mounts_after_runtime_metrics():
    text = APP.read_text()
    assert "renderAionGoalEngineProviderDegradationFeedV1(snapshot)" in text
    assert text.index("renderAionGoalEngineProviderRuntimeMetricsPanelV1(snapshot)") < text.index(
        "renderAionGoalEngineProviderDegradationFeedV1(snapshot)"
    )


def test_provider_degradation_feed_exported_to_window():
    text = APP.read_text()
    assert "window.renderAionGoalEngineProviderDegradationFeedV1" in text
