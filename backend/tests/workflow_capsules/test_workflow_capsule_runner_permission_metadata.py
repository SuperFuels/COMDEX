from __future__ import annotations

from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)


def _runner_with_permission_capsule(tmp_path) -> WorkflowCapsuleRunner:
    canvas = {
        "canonical_key": "workflow:gmail.permission_runtime.v1",
        "display_name": "Permission Runtime Gmail Workflow",
        "meaning": "Runtime permission dry-run test workflow.",
        "display_glyph": "WG-PERM-RUN",
        "tags": ["gmail", "permission", "runtime"],
        "vault_requirements": ["vault.gmail.credentials"],
        "permission_mode": "draft_auto",
        "permission_policy": {
            "min_confidence": 0.86,
            "allowed_recipient_scope": "original_thread_only",
            "max_auto_sends_per_day": 5,
        },
        "nodes": [
            {
                "id": "read",
                "type": "read_email",
                "data": {
                    "step_id": "read_email",
                    "kind": "read_email",
                    "label": "Read Gmail message",
                    "connector": "gmail",
                    "action": "gmail.read",
                    "risk_tier": "low",
                    "permission_mode": "auto_with_exceptions",
                    "permission": {
                        "node_mode": "auto_with_exceptions",
                        "requires_approval": False,
                        "is_external_write": False,
                    },
                    "requires": ["vault.gmail.credentials"],
                    "output_ref": "gmail.message",
                },
            },
            {
                "id": "draft",
                "type": "draft_reply",
                "data": {
                    "step_id": "draft_reply",
                    "kind": "draft_content",
                    "label": "Draft reply",
                    "action": "gmail.create_draft",
                    "risk_tier": "low",
                    "permission_mode": "draft_auto",
                    "permission": {
                        "node_mode": "draft_auto",
                        "requires_approval": False,
                        "is_draft_action": True,
                        "is_external_write": False,
                    },
                    "output_ref": "gmail.reply_draft",
                },
            },
            {
                "id": "send",
                "type": "send_email",
                "data": {
                    "step_id": "send_reply",
                    "kind": "send_email",
                    "label": "Send reply",
                    "connector": "gmail",
                    "action": "gmail.send",
                    "risk_tier": "medium",
                    "permission_mode": "review",
                    "permission": {
                        "node_mode": "review",
                        "requires_approval": True,
                        "is_external_write": True,
                    },
                    "external_write": True,
                    "requires_approval": True,
                    "requires": ["vault.gmail.credentials"],
                    "output_ref": "gmail.sent",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "read", "target": "draft"},
            {"id": "e2", "source": "draft", "target": "send"},
        ],
    }

    compiled = CanvasWorkflowCompiler().compile(canvas)
    assert compiled.ok is True

    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")
    repo.save(
        compiled.capsule,
        scope="workspace",
        workspace_id="costa-conexion",
        overwrite=True,
    )

    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )
    registry.rebuild_and_save()

    return WorkflowCapsuleRunner(registry=registry)


def test_runner_dry_run_attaches_permission_decision_to_each_step(tmp_path) -> None:
    runner = _runner_with_permission_capsule(tmp_path)

    result = runner.run_dry(
        "workflow:gmail.permission_runtime.v1",
        available_vault_requirements=["vault.gmail.credentials"],
        rebuild_registry=False,
        create_approval=True,
    ).to_dict()

    assert result["ok"] is True
    steps = result["run"]["steps"]

    assert len(steps) == 3
    assert all("permission_decision" in step for step in steps)
    assert steps[0]["permission_decision"]["decision"] == "auto_run"
    assert steps[1]["permission_decision"]["decision"] == "draft_only"
    assert steps[2]["permission_decision"]["decision"] == "request_approval"


def test_runner_permission_metadata_marks_send_as_external_write_and_dry_run_blocked(tmp_path) -> None:
    runner = _runner_with_permission_capsule(tmp_path)

    result = runner.run_dry(
        "workflow:gmail.permission_runtime.v1",
        available_vault_requirements=["vault.gmail.credentials"],
        rebuild_registry=False,
        create_approval=True,
    ).to_dict()

    send_step = result["run"]["steps"][2]

    assert send_step["step_id"] == "send_reply"
    assert send_step["status"] == "blocked"
    assert "dry_run_blocks_external_write" in send_step["blocked_reasons"]
    assert send_step["permission_decision"]["requires_approval"] is True
    assert send_step["permission_decision"]["context"]["action"] == "gmail.send"
    assert send_step["permission_decision"]["context"]["risk_tier"] == "medium"
    assert send_step["permission_decision"]["context"]["is_external_write"] is True


def test_runner_permission_metadata_never_introduces_live_execute(tmp_path) -> None:
    runner = _runner_with_permission_capsule(tmp_path)

    result = runner.run_dry(
        "workflow:gmail.permission_runtime.v1",
        available_vault_requirements=["vault.gmail.credentials"],
        rebuild_registry=False,
        create_approval=True,
    ).to_dict()

    combined = str(result).lower()

    assert "permission_decision" in combined
    assert "live_execute" not in combined
    assert "external_write_ready" not in combined
