from backend.modules.workflow_capsules.call_workflow_glyph_validation import (
    validate_call_workflow_glyph_contract,
)


def _node(**overrides):
    base = {
        "id": "call_workflow_glyph_1",
        "type": "call_workflow_glyph",
        "glyph_code": "GM-1001",
        "glyph_version": "v1",
        "glyph_scope": "universal",
        "child_workflow_id": "universal.gmail_enquiry_reply.v1",
        "version_hash": "abc123",
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
                "reply_text": {"type": "string"},
            },
        },
        "required_connectors": ["gmail"],
        "approval_policy": {
            "dry_run_first": True,
            "approval_before_external_write": True,
            "live_send_enabled": False,
        },
        "runtime_plan": {
            "dry_run_only": True,
            "steps": [{"op": "aion.prepare_gmail_reply"}],
        },
        "dry_run_only": True,
        "live_send_enabled": False,
    }
    base.update(overrides)
    return base


def _registry(**overrides):
    base = {
        "glyph_code": "GM-1001",
        "glyph_version": "v1",
        "workflow_id": "universal.gmail_enquiry_reply.v1",
        "version_hash": "abc123",
        "required_connectors": ["gmail"],
        "approval_policy": {
            "approval_before_external_write": True,
        },
        "runtime_plan": {
            "dry_run_only": True,
        },
    }
    base.update(overrides)
    return base


def test_validates_parent_output_schema_against_child_input_schema():
    result = validate_call_workflow_glyph_contract(
        parent_output_schema={
            "type": "object",
            "properties": {
                "gmail_message_id": {"type": "string"},
            },
        },
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    assert result.valid is True
    assert result.errors == []
    assert result.runtime_blocked is False


def test_blocks_when_parent_output_schema_missing_child_required_input():
    result = validate_call_workflow_glyph_contract(
        parent_output_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
            },
        },
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    assert result.valid is False
    assert "parent_output_schema_missing_child_input:gmail_message_id" in result.errors
    assert result.runtime_blocked is True


def test_blocks_when_parent_payload_has_wrong_child_input_type():
    result = validate_call_workflow_glyph_contract(
        parent_output_payload={"gmail_message_id": 123},
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    assert result.valid is False
    assert "parent_payload_child_input_type_mismatch:gmail_message_id:integer->string" in result.errors
    assert result.runtime_blocked is True


def test_validates_child_output_payload_against_child_output_schema():
    result = validate_call_workflow_glyph_contract(
        parent_output_payload={"gmail_message_id": "msg_123"},
        child_output_payload={"draft_created": "yes", "reply_text": "Hello"},
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    assert result.valid is False
    assert "child_output_type_mismatch:draft_created:string->boolean" in result.errors


def test_detects_missing_connectors():
    result = validate_call_workflow_glyph_contract(
        parent_output_payload={"gmail_message_id": "msg_123"},
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=[],
        parent_approval_policy={"approval_before_external_write": True},
    )

    assert result.valid is False
    assert result.missing_connectors == ["gmail"]
    assert "missing_required_connectors" in result.errors
    assert result.runtime_blocked is True
def test_detects_pinned_glyph_version_and_hash_mismatch():
    result = validate_call_workflow_glyph_contract(
        parent_output_payload={"gmail_message_id": "msg_123"},
        call_node=_node(glyph_version="v1", version_hash="abc123"),
        registry_glyph=_registry(glyph_version="v2", version_hash="def456"),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    assert result.valid is False
    assert result.version_mismatch is True
    assert "pinned_glyph_version_mismatch" in result.errors
    assert "pinned_glyph_hash_mismatch" in result.errors


def test_detects_approval_policy_mismatch_and_blocks_runtime():
    result = validate_call_workflow_glyph_contract(
        parent_output_payload={"gmail_message_id": "msg_123"},
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": False},
    )

    assert result.valid is False
    assert result.approval_policy_mismatch is True
    assert "approval_policy_mismatch" in result.errors
    assert result.runtime_blocked is True


def test_result_is_serialisable_contract_for_inspector_and_runtime():
    result = validate_call_workflow_glyph_contract(
        parent_output_payload={"gmail_message_id": "msg_123"},
        call_node=_node(),
        registry_glyph=_registry(),
        available_connectors=["gmail"],
        parent_approval_policy={"approval_before_external_write": True},
    )

    payload = result.to_dict()

    assert payload == {
        "valid": True,
        "errors": [],
        "warnings": [],
        "missing_connectors": [],
        "version_mismatch": False,
        "approval_policy_mismatch": False,
        "runtime_blocked": False,
    }
