from __future__ import annotations

from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowCapsuleExpander,
)


def _sample_canvas():
    return {
        "canonical_key": "workflow:gmail.canvas_reply.v1",
        "display_name": "Canvas Gmail Reply",
        "meaning": "Canvas-built Gmail enquiry reply workflow.",
        "display_glyph": "WG-CANVAS-001",
        "tags": ["gmail", "canvas", "reply"],
        "vault_requirements": ["vault.gmail.credentials"],
        "nodes": [
            {
                "id": "read",
                "type": "read_email",
                "data": {
                    "step_id": "read_email",
                    "kind": "read_email",
                    "label": "Read Gmail message",
                    "connector": "gmail",
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
                    "output_ref": "gmail.reply_draft",
                },
            },
            {
                "id": "approval",
                "type": "approval_checkpoint",
                "data": {
                    "step_id": "approval",
                    "kind": "approval_checkpoint",
                    "label": "Human approval",
                    "requires_approval": True,
                    "output_ref": "approval.result",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "read", "target": "draft"},
            {"id": "e2", "source": "draft", "target": "approval"},
        ],
    }


def test_canvas_compiler_builds_workflow_capsule_and_compiled_steps() -> None:
    result = CanvasWorkflowCompiler().compile(_sample_canvas())

    assert result.ok is True
    assert result.capsule is not None

    capsule = result.capsule
    assert capsule.canonical_key == "workflow:gmail.canvas_reply.v1"
    assert capsule.display_glyph == "WG-CANVAS-001"
    assert capsule.vault_requirements == ["vault.gmail.credentials"]
    assert capsule.compiled_glyph["schema_version"] == "aion.workflow_glyph.v1"
    assert len(capsule.compiled_glyph["steps"]) == 3


def test_canvas_compiler_output_expands_with_existing_expander() -> None:
    result = CanvasWorkflowCompiler().compile(_sample_canvas())
    expansion = WorkflowCapsuleExpander().expand(result.capsule)

    assert expansion.ok is True
    assert len(expansion.steps) == 3
    assert expansion.steps[0].step_id == "read_email"
    assert expansion.steps[1].input_refs == ["read"] or expansion.steps[1].input_refs == ["read_email"]


def test_canvas_compiler_rejects_reserved_primitive_display_glyph() -> None:
    canvas = _sample_canvas()
    canvas["display_glyph"] = "^"

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is False
    assert "display_glyph_collides_with_reserved_glyphos_primitive" in result.errors


def test_canvas_compiler_rejects_secret_fields() -> None:
    canvas = _sample_canvas()
    canvas["nodes"][0]["data"]["access_token"] = "must-not-be-here"

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is False
    assert "canvas_payload_must_not_contain_secret_fields" in result.errors


def test_canvas_compiler_rejects_invalid_edges() -> None:
    canvas = _sample_canvas()
    canvas["edges"].append({"id": "bad", "source": "missing", "target": "draft"})

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is False
    assert "edge[2]_source_missing:missing" in result.errors


def test_canvas_compiler_preserves_taught_process_binding() -> None:
    canvas = _sample_canvas()
    canvas["nodes"] = [{
        "id": "taught-crm-entry",
        "type": "Taught Processes",
        "data": {
            "step_id": "taught_crm_entry",
            "kind": "capability",
            "label": "Enter lead into CRM",
            "action_id": "pilot.demonstrated_skill.execute",
            "capability_id": "pilot.demonstrated_skill.execute",
            "skill_id": "pilot_skill_one",
            "skill_hash": "hash-one",
            "department_id": "sales",
            "required_inputs": ["runtime_input"],
            "output_contract": "verified_skill_result",
        },
    }]
    canvas["edges"] = []

    result = CanvasWorkflowCompiler().compile(canvas)

    assert result.ok is True
    step = result.capsule.compiled_glyph["steps"][0]
    assert step["action_id"] == "pilot.demonstrated_skill.execute"
    assert step["skill_id"] == "pilot_skill_one"
    assert step["skill_hash"] == "hash-one"
    assert step["department_id"] == "sales"
