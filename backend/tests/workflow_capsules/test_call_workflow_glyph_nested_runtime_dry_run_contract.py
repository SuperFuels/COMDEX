from backend.modules.workflow_capsules.call_workflow_glyph_runtime import (
    execute_call_workflow_glyph_dry_run,
    resolve_call_workflow_glyph,
)


def _registry():
    return [
        {
            "glyph_code": "GM-1001",
            "glyph_version": "v1",
            "workflow_id": "universal.gmail_enquiry_reply.v1",
            "version_hash": "hash_abc",
            "required_connectors": ["gmail"],
            "input_schema": {
                "type": "object",
                "required": ["gmail_message_id"],
                "properties": {
                    "gmail_message_id": {"type": "string"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "draft_created": {"type": "boolean"},
                },
            },
            "approval_policy": {
                "approval_before_external_write": True,
                "live_send_enabled": False,
            },
            "runtime_plan": {
                "dry_run_only": True,
                "steps": [
                    {"op": "gmail.read_message"},
                    {"op": "aion.prepare_reply_draft"},
                ],
            },
        }
    ]


def _node(**overrides):
    base = {
        "id": "call_workflow_glyph_1",
        "type": "call_workflow_glyph",
        "glyph_code": "GM-1001",
        "glyph_version": "v1",
        "child_workflow_id": "universal.gmail_enquiry_reply.v1",
        "version_hash": "hash_abc",
        "required_connectors": ["gmail"],
        "dry_run_only": True,
        "live_send_enabled": False,
        "approval_policy": {
            "approval_before_external_write": True,
            "live_send_enabled": False,
        },
    }
    base.update(overrides)
    return base


def test_resolves_call_workflow_glyph_from_registry():
    glyph = resolve_call_workflow_glyph(_node(), _registry())

    assert glyph is not None
    assert glyph["glyph_code"] == "GM-1001"


def test_executes_nested_runtime_plan_in_dry_run_only():
    result = execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(),
        parent_payload={"gmail_message_id": "msg_123"},
        glyph_registry=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    payload = result.to_dict()

    assert payload["ok"] is True
    assert payload["status"] == "dry_run_completed"
    assert payload["dry_run"] is True
    assert payload["glyph_code"] == "GM-1001"
    assert payload["child_workflow_id"] == "universal.gmail_enquiry_reply.v1"
    assert payload["parent_run_id"] == "parent_run_1"
    assert payload["child_run_id"] == "parent_run_1::GM-1001::dry_run_child"
    assert payload["validation"]["valid"] is True
    assert payload["metrics"]["ai_planning_bypassed"] is True
    assert payload["metrics"]["external_writes_performed"] == 0
    assert payload["metrics"]["steps_executed"] == 2
    assert [step["op"] for step in payload["steps"]] == [
        "gmail.read_message",
        "aion.prepare_reply_draft",
    ]


def test_passes_parent_payload_into_child_and_returns_child_output():
    result = execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(),
        parent_payload={"gmail_message_id": "msg_123"},
        glyph_registry=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    payload = result.to_dict()

    assert payload["child_input"] == {"gmail_message_id": "msg_123"}
    assert payload["child_output"]["gmail_message_id"] == "msg_123"
    assert payload["child_output"]["glyph_code"] == "GM-1001"
    assert payload["child_output"]["dry_run"] is True
    assert payload["provenance"]["parent_payload_passed_to_child"] is True
    assert payload["provenance"]["child_output_returned_to_parent"] is True


def test_blocks_runtime_when_validation_fails():
    result = execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(),
        parent_payload={},
        glyph_registry=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    payload = result.to_dict()

    assert payload["ok"] is False
    assert payload["status"] == "blocked_by_validation"
    assert payload["validation"]["runtime_blocked"] is True
    assert "parent_output_missing_child_input:gmail_message_id" in payload["validation"]["errors"]
    assert payload["steps"] == []
    assert payload["metrics"]["runtime_blocked"] is True
    assert payload["metrics"]["external_writes_performed"] == 0


def test_blocks_runtime_when_registry_resolution_fails():
    result = execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(glyph_code="GM-9999"),
        parent_payload={"gmail_message_id": "msg_123"},
        glyph_registry=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    payload = result.to_dict()

    assert payload["ok"] is False
    assert payload["status"] == "blocked_by_validation"
    assert "glyph_registry_resolution_failed" in payload["validation"]["errors"]
    assert payload["metrics"]["steps_executed"] == 0


def test_runtime_respects_approval_policy_and_connector_validation():
    result = execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(),
        parent_payload={"gmail_message_id": "msg_123"},
        glyph_registry=_registry(),
        available_connectors=[],
        parent_approval_policy={"approval_before_external_write": False},
    )

    payload = result.to_dict()

    assert payload["ok"] is False
    assert "approval_policy_mismatch" in payload["validation"]["errors"]
    assert "missing_required_connectors" in payload["validation"]["errors"]
    assert payload["validation"]["missing_connectors"] == ["gmail"]


def test_runtime_contract_does_not_enable_live_execution():
    result = execute_call_workflow_glyph_dry_run(
        parent_run_id="parent_run_1",
        call_node=_node(),
        parent_payload={"gmail_message_id": "msg_123"},
        glyph_registry=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    payload = result.to_dict()

    assert payload["dry_run"] is True
    assert payload["provenance"]["mode"] == "dry_run_only"
    assert payload["metrics"]["external_writes_performed"] == 0
    assert payload["metrics"]["ai_planning_bypassed"] is True
