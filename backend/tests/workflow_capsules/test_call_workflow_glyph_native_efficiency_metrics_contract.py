from backend.modules.workflow_capsules.call_workflow_glyph_runtime import (
    execute_call_workflow_glyph_dry_run,
)


def _node():
    return {
        "id": "call_1",
        "type": "call_workflow_glyph",
        "glyph_code": "GM-1001",
        "glyph_version": "v1",
        "child_workflow_id": "workflow_child_gmail_triage",
        "input_schema": {
            "type": "object",
            "required": ["gmail_message_id"],
            "properties": {"gmail_message_id": {"type": "string"}},
        },
        "output_schema": {"type": "object", "properties": {"label": {"type": "string"}}},
        "required_connectors": ["gmail"],
        "approval_policy": {"approval_before_external_write": True},
        "runtime_plan": {"dry_run_only": True},
        "dry_run_only": True,
        "live_send_enabled": False,
    }


def _registry():
    return [
        {
            "glyph_code": "GM-1001",
            "glyph_version": "v1",
            "workflow_id": "workflow_child_gmail_triage",
            "input_schema": {
                "type": "object",
                "required": ["gmail_message_id"],
                "properties": {"gmail_message_id": {"type": "string"}},
            },
            "output_schema": {"type": "object", "properties": {"label": {"type": "string"}}},
            "required_connectors": ["gmail"],
            "approval_policy": {"approval_before_external_write": True},
            "runtime_plan": {
                "dry_run_only": True,
                "steps": [
                    {"op": "read_email"},
                    {"op": "classify_email"},
                    {"op": "draft_response"},
                ],
            },
        }
    ]


def _run():
    return execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(),
        parent_payload={"gmail_message_id": "msg_123"},
        glyph_registry=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    ).to_dict()


def test_compiled_glyph_bypasses_ai_and_has_zero_cost():
    payload = _run()
    metrics = payload["metrics"]

    assert metrics["ai_planning_bypassed"] is True
    assert metrics["external_writes_performed"] == 0
    assert metrics["estimated_cost"] == {
        "currency": "USD",
        "estimated_total": 0.0,
        "ai_planning_cost": 0.0,
        "external_write_cost": 0.0,
        "compiled_step_count": 3,
        "cost_model": "compiled_dry_run_zero_cost_v1",
    }


def test_registry_lookup_is_cached_inside_runtime_call():
    payload = _run()

    assert payload["metrics"]["registry_lookup_cached"] is True
    assert payload["provenance"]["registry_lookup_cached"] is True


def test_boardroom_event_emitted_from_glyph_execution():
    payload = _run()
    events = payload["provenance"]["boardroom_events"]

    assert payload["metrics"]["boardroom_events_emitted"] == 1
    assert events[0]["event_type"] == "call_workflow_glyph.dry_run"
    assert events[0]["glyph_code"] == "GM-1001"
    assert events[0]["dry_run"] is True
    assert events[0]["external_writes_performed"] == 0
    assert events[0]["ai_planning_bypassed"] is True


def test_repeated_glyph_runs_are_deterministic_except_elapsed_time():
    first = _run()
    second = _run()

    first["metrics"]["elapsed_ms"] = 0
    second["metrics"]["elapsed_ms"] = 0
    first["provenance"]["boardroom_events"][0]["elapsed_ms"] = 0
    second["provenance"]["boardroom_events"][0]["elapsed_ms"] = 0

    assert first == second
