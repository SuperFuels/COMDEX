from __future__ import annotations

from backend.modules.workflow_capsules.execution.goal_engine_child_run_creation_bridge import (
    create_child_workflow_run_preview_from_bridge_packet,
)


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run_dry(self, value, **kwargs):
        self.calls.append({"value": value, "kwargs": kwargs})

        class Result:
            def to_dict(self):
                return {
                    "ok": True,
                    "run_id": "dry_run_generated_001",
                    "canonical_key": "workflow:gmail.enquiry_reply.v1",
                    "display_name": "Handle Gmail Enquiry",
                    "approval": {},
                    "errors": [],
                    "warnings": [],
                    "run": {
                        "approval_required": True,
                        "external_writes_blocked": True,
                    },
                }

        return Result()


def _packet():
    return {
        "schema_version": "aion.goal_engine.child_run_executor_bridge.v1",
        "trace_type": "child_run_executor_bridge_packet",
        "status": "ready_for_workflow_runtime",
        "execution_allowed": False,
        "parent_run_id": "parent_run_001",
        "runtime_seed": {
            "workflow_id": "workflow:gmail.enquiry_reply.v1",
            "run_id": "child_run_001",
            "parent_goal_id": "goal_parent_001",
            "child_goal_id": "goal_child_001",
            "child_agent_id": "agent_child_001",
            "child_glyph_id": "glyph_child_001",
            "created_by": "pytest",
            "requires_runtime_executor": True,
            "external_writes_allowed": False,
            "business_mutation_allowed": False,
        },
    }


def test_child_run_creation_bridge_creates_dry_run_preview_only():
    runner = FakeRunner()

    result = create_child_workflow_run_preview_from_bridge_packet(
        _packet(),
        runner=runner,
        rebuild_registry=False,
    )

    assert result["ok"] is True
    assert result["schema_version"] == "aion.goal_engine.child_workflow_run_creation_preview.v1"
    assert result["trace_type"] == "child_workflow_run_creation_preview"
    assert result["status"] == "dry_run_created"
    assert result["workflow_id"] == "workflow:gmail.enquiry_reply.v1"
    assert result["requested_run_id"] == "child_run_001"
    assert result["workflow_capsule_run_id"] == "dry_run_generated_001"

    assert result["dry_run_only"] is True
    assert result["would_execute"] is False
    assert result["would_write_external"] is False
    assert result["would_mutate_business_state"] is False
    assert result["would_grant_permission"] is False
    assert result["child_workflow_run_created"] is False
    assert result["approval_created"] is False


def test_child_run_creation_bridge_trusts_runtime_seed_workflow_id_only():
    packet = _packet()
    packet["workflow_id"] = "workflow:outer.untrusted.v1"

    runner = FakeRunner()
    create_child_workflow_run_preview_from_bridge_packet(
        packet,
        runner=runner,
        rebuild_registry=False,
    )

    assert runner.calls[0]["value"] == "workflow:gmail.enquiry_reply.v1"


def test_child_run_creation_bridge_forces_safe_runner_options():
    runner = FakeRunner()

    create_child_workflow_run_preview_from_bridge_packet(
        _packet(),
        runner=runner,
        rebuild_registry=False,
    )

    kwargs = runner.calls[0]["kwargs"]
    assert kwargs["create_approval"] is False
    assert kwargs["rebuild_registry"] is False
    assert kwargs["cau_state"]["allow_learn"] is False
    assert kwargs["cau_state"]["adr_active"] is False
    assert kwargs["extra"]["dry_run_only"] is True
    assert kwargs["extra"]["visibility_only"] is True


def test_child_run_creation_bridge_blocks_unready_packet():
    packet = _packet()
    packet["status"] = "blocked"

    result = create_child_workflow_run_preview_from_bridge_packet(packet)

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert "packet_not_ready_for_workflow_runtime" in result["blocked_reasons"]


def test_child_run_creation_bridge_blocks_missing_runtime_seed():
    packet = _packet()
    packet.pop("runtime_seed")

    result = create_child_workflow_run_preview_from_bridge_packet(packet)

    assert result["ok"] is False
    assert "missing_runtime_seed" in result["blocked_reasons"]


def test_child_run_creation_bridge_blocks_missing_workflow_or_run_id():
    packet = _packet()
    packet["runtime_seed"]["workflow_id"] = ""

    result = create_child_workflow_run_preview_from_bridge_packet(packet)

    assert result["ok"] is False
    assert "missing_runtime_seed_workflow_id" in result["blocked_reasons"]

    packet = _packet()
    packet["runtime_seed"]["run_id"] = ""

    result = create_child_workflow_run_preview_from_bridge_packet(packet)

    assert result["ok"] is False
    assert "missing_runtime_seed_run_id" in result["blocked_reasons"]


def test_child_run_creation_bridge_blocks_seed_side_effect_flags():
    packet = _packet()
    packet["runtime_seed"]["external_writes_allowed"] = True

    result = create_child_workflow_run_preview_from_bridge_packet(packet)

    assert result["ok"] is False
    assert "runtime_seed_external_writes_not_allowed" in result["blocked_reasons"]

    packet = _packet()
    packet["runtime_seed"]["business_mutation_allowed"] = True

    result = create_child_workflow_run_preview_from_bridge_packet(packet)

    assert result["ok"] is False
    assert "runtime_seed_business_mutation_not_allowed" in result["blocked_reasons"]
