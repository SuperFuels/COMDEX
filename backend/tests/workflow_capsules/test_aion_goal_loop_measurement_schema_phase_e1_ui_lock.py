from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE E1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE E1 */", start)
    return APP_JS[start:end]


def test_phase_e1_helpers_exist():
    block = phase_block()

    assert "function buildAionGoalLoopMetricSchema" in block
    assert "function buildAionGoalLoopDepartmentMetricSet" in block
    assert "function attachAionGoalLoopMetricsToGraph" in block
    assert "function renderAionGoalLoopMeasurementSchemaPanel" in block


def test_phase_e1_metric_schema_fields_are_locked():
    block = function_block("buildAionGoalLoopMetricSchema")

    for field in [
        "metric_id",
        "goal_id",
        "department",
        "source_node_id",
        "name",
        "target",
        "actual",
        "unit",
        "trend",
        "confidence",
        "source",
        "evidence_ids",
    ]:
        assert field in block

    assert "aion.goal_loop_metric.v1" in block


def test_phase_e1_metric_enums_are_locked():
    block = phase_block()

    for value in ["improving", "flat", "declining", "unknown"]:
        assert value in block

    for value in ["unknown", "partial", "verified"]:
        assert value in block

    assert "manual" in block
    assert "connector_placeholder" in block


def test_phase_e1_attaches_metrics_to_goal_loop_graph_preview():
    block = function_block("attachAionGoalLoopMetricsToGraph")

    assert "goal_loop_metrics" in block
    assert "goal_loop_metric_sets" in block
    assert "goal_loop_measurement_attachment" in block
    assert "goal_loop_contract.goal_loop_metrics" in block
    assert "window.__aionWorkflowGraph" in block
    assert "window.__aionGoalLoopWorkflowGraph" in block
    assert "measurement_schema_attached_preview" in block


def test_phase_e1_renderer_exposes_visible_measurement_schema_panel():
    block = function_block("renderAionGoalLoopMeasurementSchemaPanel")

    assert 'data-aion-goal-loop-measurement-schema-panel="true"' in block
    assert 'data-aion-goal-loop-metric-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-metric-department-count="true"' in block
    assert 'data-aion-goal-loop-metric-count="true"' in block
    assert 'data-aion-goal-loop-metric-confidence="true"' in block
    assert 'data-aion-goal-loop-metric-sets="true"' in block
    assert 'data-aion-goal-loop-metric-preview-boundary="true"' in block
    assert "No connector call" in block


def test_phase_e1_is_schema_only_safe_boundary():
    block = phase_block()
    forbidden = block.lower()

    assert "manual_entry_supported: true" in block
    assert "connector_placeholder_supported: true" in block
    assert "connector_call_required: false" in block
    assert "preview_only: true" in block
    assert "execution_blocked: true" in block
    assert "persistence_required: false" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

    assert "fetch(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_e1_is_mounted_after_d4_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopDepartmentTaskQueueWritebackPanel()}" in APP_JS
    assert "${renderAionGoalLoopMeasurementSchemaPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    d4_index = APP_JS.index("${renderAionGoalLoopDepartmentTaskQueueWritebackPanel()}")
    e1_index = APP_JS.index("${renderAionGoalLoopMeasurementSchemaPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert d4_index < e1_index < cockpit_index
