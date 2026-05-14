from __future__ import annotations

from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)


def _permission_canvas():
    return {
        "canonical_key": "workflow:gmail.canvas_permission_reply.v1",
        "display_name": "Canvas Permission Gmail Reply",
        "meaning": "Canvas-built workflow with workflow and node autonomy metadata.",
        "display_glyph": "WG-PERM-001",
        "tags": ["gmail", "canvas", "permissions"],
        "vault_requirements": ["vault.gmail.credentials"],
        "permission_mode": "draft_auto",
        "permission_policy": {
            "min_confidence": 0.86,
            "allowed_recipient_scope": "original_thread_only",
            "max_auto_sends_per_day": 25,
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
                    "risk_flags": [],
                    "confidence": 0.92,
                    "output_ref": "gmail.sent",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "read", "target": "draft"},
            {"id": "e2", "source": "draft", "target": "send"},
        ],
    }


def test_canvas_compiler_preserves_workflow_permission_metadata() -> None:
    result = CanvasWorkflowCompiler().compile(_permission_canvas())

    assert result.ok is True
    capsule = result.capsule
    assert capsule is not None

    assert capsule.workflow_graph["permission_mode"] == "draft_auto"
    assert capsule.workflow_graph["permission_policy"]["min_confidence"] == 0.86
    assert capsule.meta["workflow_permission_mode"] == "draft_auto"


def test_canvas_compiler_preserves_node_permission_metadata_in_compiled_steps() -> None:
    result = CanvasWorkflowCompiler().compile(_permission_canvas())

    assert result.ok is True
    capsule = result.capsule
    steps = capsule.compiled_glyph["steps"]

    read_step = steps[0]
    draft_step = steps[1]
    send_step = steps[2]

    assert read_step["permission_mode"] == "auto_with_exceptions"
    assert read_step["risk_tier"] == "low"
    assert read_step["permission"]["node_mode"] == "auto_with_exceptions"
    assert read_step["action"] == "gmail.read"

    assert draft_step["permission_mode"] == "draft_auto"
    assert draft_step["permission"]["is_draft_action"] is True
    assert draft_step["action"] == "gmail.create_draft"

    assert send_step["permission_mode"] == "review"
    assert send_step["risk_tier"] == "medium"
    assert send_step["permission"]["requires_approval"] is True
    assert send_step["permission"]["is_external_write"] is True
    assert send_step["external_write"] is True
    assert send_step["requires_approval"] is True
    assert send_step["action"] == "gmail.send"


def test_canvas_compiler_rejects_invalid_workflow_permission_mode() -> None:
    canvas = _permission_canvas()
    canvas["permission_mode"] = "god_mode"

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is False
    assert "invalid_workflow_permission_mode:god_mode" in result.errors


def test_canvas_compiler_rejects_invalid_node_permission_mode() -> None:
    canvas = _permission_canvas()
    canvas["nodes"][0]["data"]["permission_mode"] = "god_mode"

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is False
    assert "node[0]_invalid_permission_mode:god_mode" in result.errors


def test_canvas_compiler_rejects_invalid_node_risk_tier() -> None:
    canvas = _permission_canvas()
    canvas["nodes"][2]["data"]["risk_tier"] = "catastrophic"

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is False
    assert "node[2]_invalid_risk_tier:catastrophic" in result.errors


def test_canvas_permission_metadata_survives_workspace_capsule_save_load(tmp_path) -> None:
    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")
    result = CanvasWorkflowCompiler().compile(_permission_canvas())

    assert result.ok is True
    saved = repo.save(
        result.capsule,
        scope="workspace",
        workspace_id="costa-conexion",
        overwrite=True,
    )

    loaded = repo.require(
        "workflow:gmail.canvas_permission_reply.v1",
        workspace_id="costa-conexion",
    )

    assert saved["ok"] is True
    assert loaded.workflow_graph["permission_mode"] == "draft_auto"
    assert loaded.workflow_graph["permission_policy"]["max_auto_sends_per_day"] == 25
    assert loaded.compiled_glyph["steps"][2]["permission"]["is_external_write"] is True
    assert loaded.compiled_glyph["steps"][2]["risk_tier"] == "medium"
