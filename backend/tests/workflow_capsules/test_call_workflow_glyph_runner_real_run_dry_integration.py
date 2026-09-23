from __future__ import annotations

from pathlib import Path

from backend.modules.workflow_capsules.execution.workflow_capsule_runner import WorkflowCapsuleRunner
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import WorkflowGlyphRepository
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import WorkflowGlyph
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import WorkflowCapsuleRepository
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import WorkflowGlyphRegistry
from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import make_workflow_capsule


def _child_glyph() -> WorkflowGlyph:
    return WorkflowGlyph.from_dict({
        "glyph_id": "glyph.gm-9100.v1",
        "glyph_code": "GM-9100",
        "name": "Nested Gmail Reply Child",
        "workflow_id": "workflow:gmail.nested_child.v1",
        "workflow_version": "v1",
        "glyph_version": "v1",
        "scope": "my",
        "callable": True,
        "input_schema": {
            "type": "object",
            "properties": {"gmail_message_id": {"type": "string"}},
            "required": ["gmail_message_id"],
        },
        "output_schema": {
            "type": "object",
            "properties": {"draft_reply": {"type": "string"}},
        },
        "required_connectors": ["gmail"],
        "risk_tier": "medium",
        "approval_policy": {"requires_approval": True},
        "runtime_plan": {
            "dry_run_only": True,
            "steps": [
                {"step_id": "read_parent_message", "kind": "read_email"},
                {"step_id": "draft_child_reply", "kind": "draft_content"},
            ],
        },
        "tags": ["gmail", "nested", "call_workflow_glyph"],
    })


def _parent_capsule():
    return make_workflow_capsule(
        meaning="Test parent workflow that calls a persisted child workflow glyph via call_workflow_glyph dry-run.",
        canonical_key="workflow:test.parent_calls_child.v1",
        display_name="Parent Calls Child",
        display_glyph="TP-910",
        workflow_id="workflow:test.parent_calls_child.v1",
        workflow_graph={
            "nodes": [
                {
                    "id": "start",
                    "kind": "read_email",
                    "title": "Read parent email",
                },
                {
                    "id": "call_child",
                    "kind": "call_workflow_glyph",
                    "title": "Call nested child glyph",
                    "glyph_code": "GM-9100",
                    "glyph_version": "v1",
                    "required_connectors": ["gmail"],
                    "approval_policy": {"requires_approval": True},
                    "input_schema": {
                        "type": "object",
                        "properties": {"gmail_message_id": {"type": "string"}},
                        "required": ["gmail_message_id"],
                    },
                },
                {
                    "id": "finish",
                    "kind": "draft_content",
                    "title": "Use child output",
                },
            ],
            "edges": [
                {"from": "start", "to": "call_child"},
                {"from": "call_child", "to": "finish"},
            ],
        },
        compiled_glyph={
            "schema_version": "aion.workflow_glyph.v1",
            "steps": [
                {
                    "step_id": "start",
                    "kind": "read_email",
                },
                {
                    "step_id": "call_child",
                    "kind": "call_workflow_glyph",
                    "glyph_code": "GM-9100",
                    "glyph_version": "v1",
                    "required_connectors": ["gmail"],
                    "approval_policy": {"requires_approval": True},
                    "input_schema": {
                        "type": "object",
                        "properties": {"gmail_message_id": {"type": "string"}},
                        "required": ["gmail_message_id"],
                    },
                },
                {
                    "step_id": "finish",
                    "kind": "draft_content",
                },
            ]
        },
        tags=["test", "call_workflow_glyph"],
    )


def _runner(tmp_path: Path) -> WorkflowCapsuleRunner:
    capsule_repo = WorkflowCapsuleRepository(
        root=tmp_path / "capsules",
        workspace_dir="workspace",
        core_dir="core",
    )
    capsule_repo.save(_parent_capsule(), scope="workspace", workspace_id="test")

    registry = WorkflowGlyphRegistry(
        repository=capsule_repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )
    registry.rebuild_and_save()

    glyph_repo = WorkflowGlyphRepository(
        glyph_dir=tmp_path / "glyphs",
        index_path=tmp_path / "workflow_glyph_index.json",
    )
    glyph_repo.save(_child_glyph())

    return WorkflowCapsuleRunner(
        registry=registry,
        workflow_glyph_repository=glyph_repo,
    )


def test_runner_run_dry_executes_call_workflow_glyph_from_backend_registry(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    result = runner.run_dry(
        "TP-910",
        inputs={"gmail_message_id": "msg_parent_123"},
        available_vault_requirements=["gmail"],
        cau_state={"allow_learn": False, "adr_active": False},
        create_approval=False,
        rebuild_registry=False,
    )

    payload = result.to_dict()

    assert payload["ok"] is True
    assert payload["canonical_key"] == "workflow:test.parent_calls_child.v1"

    nested = payload["run"]["call_workflow_glyph_runs"]
    assert len(nested) == 1
    assert nested[0]["ok"] is True
    assert nested[0]["glyph_code"] == "GM-9100"
    assert nested[0]["glyph_version"] == "v1"
    assert nested[0]["child_workflow_id"] == "workflow:gmail.nested_child.v1"
    assert nested[0]["child_input"]["gmail_message_id"] == "msg_parent_123"
    assert nested[0]["child_output"]["runtime_plan_completed"] is True


def test_runner_run_dry_records_parent_child_provenance_and_metrics(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    result = runner.run_dry(
        "workflow:test.parent_calls_child.v1",
        inputs={"gmail_message_id": "msg_parent_456"},
        available_vault_requirements=["gmail"],
        cau_state={"allow_learn": False, "adr_active": False},
        create_approval=False,
        rebuild_registry=False,
    ).to_dict()

    nested = result["run"]["call_workflow_glyph_runs"][0]

    assert nested["runner_integration"]["real_runtime_path"] is True
    assert nested["runner_integration"]["backend_registry_source"] == "backend_workflow_glyph_repository"
    assert nested["provenance"]["parent_payload_passed_to_child"] is True
    assert nested["provenance"]["child_output_returned_to_parent"] is True
    assert nested["metrics"]["ai_planning_bypassed"] is True
    assert nested["metrics"]["external_writes_performed"] == 0
    assert nested["metrics"]["estimated_cost"]["cost_model"] == "compiled_dry_run_zero_cost_v1"
    assert nested["provenance"]["boardroom_events"][0]["event_type"] == "call_workflow_glyph.dry_run"


def test_runner_run_dry_is_deterministic_for_repeated_nested_runs(tmp_path: Path) -> None:
    runner = _runner(tmp_path)

    kwargs = dict(
        value="TP-910",
        inputs={"gmail_message_id": "msg_parent_repeat"},
        available_vault_requirements=["gmail"],
        cau_state={"allow_learn": False, "adr_active": False},
        create_approval=False,
        rebuild_registry=False,
    )

    first = runner.run_dry(**kwargs).to_dict()["run"]["call_workflow_glyph_runs"][0]
    second = runner.run_dry(**kwargs).to_dict()["run"]["call_workflow_glyph_runs"][0]

    assert first["glyph_code"] == second["glyph_code"]
    assert first["glyph_version"] == second["glyph_version"]
    assert first["child_input"] == second["child_input"]
    assert first["child_output"]["glyph_code"] == second["child_output"]["glyph_code"]
    assert first["metrics"]["steps_executed"] == second["metrics"]["steps_executed"]
    assert first["metrics"]["estimated_cost"] == second["metrics"]["estimated_cost"]
