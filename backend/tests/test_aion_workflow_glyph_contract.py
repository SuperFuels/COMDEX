from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.modules.aion_workflow.contracts_workflow_glyph import (
    WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION,
    WORKFLOW_GLYPH_SCHEMA_VERSION,
    WORKFLOW_NAMESPACE,
    WORKFLOW_SAVE_SCHEMA_VERSION,
    assert_safe_workflow_glyph,
)
from backend.modules.aion_workflow.workflow_glyph_compiler import (
    build_canvas_layout,
    compile_workflow_graph_to_glyph,
    order_nodes_for_workflow_glyph,
)
from backend.modules.aion_workflow.workflow_glyph_repository import WorkflowGlyphRepository


def _sample_graph() -> dict:
    return {
        "nodes": [
            {
                "id": "manual",
                "title": "Manual trigger",
                "type": "Trigger",
                "status": "Ready",
                "x": 500,
                "y": 100,
            },
            {
                "id": "classify",
                "title": "Classify enquiry",
                "type": "AI / Router",
                "status": "Draft",
                "x": 50,
                "y": 100,
            },
            {
                "id": "approval",
                "title": "Human approval",
                "type": "Gate",
                "status": "Required",
                "x": 900,
                "y": 100,
            },
        ],
        "edges": [
            {"from": "manual", "to": "classify", "condition": "success"},
            {"from": "classify", "to": "approval", "condition": "approved"},
        ],
    }


def test_safe_workflow_glyph_accepts_namespaced_ops() -> None:
    glyph = {
        "schema_version": WORKFLOW_GLYPH_SCHEMA_VERSION,
        "namespace": WORKFLOW_NAMESPACE,
        "op": "aion.workflow:sequence",
        "policy": {
            "dry_run_first": True,
            "approval_before_external_write": True,
            "raw_glyph_execution": False,
            "raw_glyphs_are_ui_decoration_only": True,
        },
        "steps": [
            {"op": "aion.workflow:trigger"},
            {"op": "aion.workflow:action"},
        ],
    }

    assert_safe_workflow_glyph(glyph)


def test_safe_workflow_glyph_rejects_raw_glyph_ops() -> None:
    glyph = {
        "schema_version": WORKFLOW_GLYPH_SCHEMA_VERSION,
        "namespace": WORKFLOW_NAMESPACE,
        "op": "aion.workflow:sequence",
        "policy": {
            "dry_run_first": True,
            "approval_before_external_write": True,
            "raw_glyph_execution": False,
            "raw_glyphs_are_ui_decoration_only": True,
        },
        "steps": [{"op": "⊕"}],
    }

    with pytest.raises(ValueError, match="unsafe workflow step op"):
        assert_safe_workflow_glyph(glyph)


def test_compiler_uses_edge_order_not_visual_x_order() -> None:
    graph = _sample_graph()

    ordered = order_nodes_for_workflow_glyph(graph)

    assert [node["id"] for node in ordered] == [
        "manual",
        "classify",
        "approval",
    ]

    compiled = compile_workflow_graph_to_glyph(
        {
            "business_container": "costa-conexion",
            "workflow_id": "workflow_test",
            "name": "Test workflow",
            "graph": graph,
        }
    )

    assert compiled["schema_version"] == WORKFLOW_GLYPH_SCHEMA_VERSION
    assert compiled["namespace"] == WORKFLOW_NAMESPACE
    assert compiled["op"] == "aion.workflow:sequence"
    assert [step["node_id"] for step in compiled["steps"]] == [
        "manual",
        "classify",
        "approval",
    ]
    assert [step["op"] for step in compiled["steps"]] == [
        "aion.workflow:trigger",
        "aion.workflow:classify",
        "aion.workflow:approval",
    ]


def test_compiler_falls_back_to_x_order_when_no_edges() -> None:
    graph = {
        "nodes": [
            {"id": "right", "title": "Draft reply", "type": "Action", "x": 900, "y": 0},
            {"id": "left", "title": "Manual trigger", "type": "Trigger", "x": 100, "y": 0},
        ],
        "edges": [],
    }

    ordered = order_nodes_for_workflow_glyph(graph)

    assert [node["id"] for node in ordered] == ["left", "right"]


def test_canvas_layout_preserves_positions_and_edges() -> None:
    graph = _sample_graph()

    layout = build_canvas_layout(graph)

    assert layout["schema_version"] == WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION
    assert layout["coordinate_space"] == "absolute_canvas_px"
    assert layout["nodes"][1] == {
        "node_id": "classify",
        "x": 50.0,
        "y": 100.0,
    }
    assert layout["edges"][1] == {
        "from": "classify",
        "to": "approval",
        "condition": "approved",
    }


def test_repository_save_load_validates_and_preserves_canvas_layout(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_test",
        "name": "Test workflow",
        "status": "draft",
        "graph": _sample_graph(),
    }

    result = repo.save(payload)

    assert result["ok"] is True
    assert result["workflow_id"] == "workflow_test"
    assert result["business_container"] == "costa-conexion"

    saved_path = Path(result["path"])
    assert saved_path.exists()

    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == WORKFLOW_SAVE_SCHEMA_VERSION
    assert saved["canvas_layout"]["schema_version"] == WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION
    assert saved["compiled_glyph"]["schema_version"] == WORKFLOW_GLYPH_SCHEMA_VERSION
    assert saved["compiled_glyph"]["namespace"] == WORKFLOW_NAMESPACE

    loaded = repo.load("costa-conexion", "workflow_test")
    assert loaded is not None
    assert loaded["workflow_id"] == "workflow_test"
    assert loaded["canvas_layout"]["nodes"][0]["node_id"] == "manual"


from backend.modules.aion_workflow.workflow_dry_run import dry_run_workflow_glyph, stable_json_hash


def test_dry_run_blocks_action_steps_and_writes_audit(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_dry_run_test",
        "name": "Dry run test",
        "status": "draft",
        "graph": {
            "nodes": [
                {
                    "id": "manual",
                    "title": "Manual trigger",
                    "type": "Trigger",
                    "status": "Ready",
                    "x": 0,
                    "y": 0,
                },
                {
                    "id": "draft",
                    "title": "Draft reply",
                    "type": "Action",
                    "status": "Prepared only",
                    "x": 200,
                    "y": 0,
                },
            ],
            "edges": [
                {"from": "manual", "to": "draft", "condition": "success"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_dry_run_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)

    assert result["ok"] is True
    assert result["mode"] == "dry_run"
    assert result["workflow_id"] == "workflow_dry_run_test"
    assert result["business_container"] == "costa-conexion"
    assert result["external_writes_performed"] is False
    assert result["approval_required"] is True
    assert result["steps"] == 2
    assert result["links"] == 1

    assert result["blocked_external_writes"] == [
        {
            "step_index": 1,
            "node_id": "draft",
            "title": "Draft reply",
            "reason": "external/action step remains draft-only in dry-run",
        }
    ]

    assert [row["status"] for row in result["trace"]] == [
        "simulated",
        "blocked_dry_run",
    ]

    audit_path = Path(result["audit_path"])
    assert audit_path.exists()
    assert audit_path.read_text(encoding="utf-8").strip()


def test_stable_json_hash_is_deterministic() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert stable_json_hash(left) == stable_json_hash(right)


def test_dry_run_marks_approval_checkpoint_waiting(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_approval_test",
        "name": "Approval test",
        "status": "draft",
        "graph": {
            "nodes": [
                {
                    "id": "manual",
                    "title": "Manual trigger",
                    "type": "Trigger",
                    "status": "Ready",
                    "x": 0,
                    "y": 0,
                },
                {
                    "id": "approval",
                    "title": "Human approval",
                    "type": "Gate",
                    "status": "Required",
                    "x": 200,
                    "y": 0,
                },
            ],
            "edges": [
                {"from": "manual", "to": "approval", "condition": "success"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_approval_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)

    assert result["ok"] is True
    assert result["approval_required"] is False  # no external write was blocked
    assert result["external_writes_performed"] is False

    approval_step = result["trace"][1]
    assert approval_step["title"] == "Human approval"
    assert approval_step["op"] == "aion.workflow:approval"
    assert approval_step["status"] == "waiting_approval"
    assert approval_step["safety"] == "approval_gate"
    assert approval_step["approval_required"] is True

    assert result["final_output_items"][0]["kind"] == "approval_checkpoint"
    assert result["final_output_items"][0]["payload"]["decision"] == "pending"


def test_dry_run_pauses_steps_after_approval_checkpoint(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_pause_after_approval_test",
        "name": "Pause after approval test",
        "status": "draft",
        "graph": {
            "nodes": [
                {
                    "id": "manual",
                    "title": "Manual trigger",
                    "type": "Trigger",
                    "status": "Ready",
                    "x": 0,
                    "y": 0,
                },
                {
                    "id": "approval",
                    "title": "Human approval",
                    "type": "Gate",
                    "status": "Required",
                    "x": 200,
                    "y": 0,
                },
                {
                    "id": "send",
                    "title": "Send email",
                    "type": "Action",
                    "status": "Requires approval",
                    "x": 400,
                    "y": 0,
                },
            ],
            "edges": [
                {"from": "manual", "to": "approval", "condition": "success"},
                {"from": "approval", "to": "send", "condition": "approved"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_pause_after_approval_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)

    statuses = [row["status"] for row in result["trace"]]

    assert statuses == [
        "simulated",
        "waiting_approval",
        "not_run_waiting_approval",
    ]

    send_step = result["trace"][2]
    assert send_step["title"] == "Send email"
    assert send_step["output_items_count"] == 0
    assert send_step["output_items_preview"] == []
    assert result["final_output_items"][0]["kind"] == "approval_checkpoint"


from backend.modules.aion_workflow.workflow_approval_repository import WorkflowApprovalRepository


def test_dry_run_creates_approval_request(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_approval_request_test",
        "name": "Approval request test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {"id": "approval", "title": "Human approval", "type": "Gate", "x": 200, "y": 0},
            ],
            "edges": [
                {"from": "manual", "to": "approval", "condition": "success"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_approval_request_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)

    approval = result["approval_request"]
    assert approval["schema_version"] == "aion.workflow_approval.v1"
    assert approval["status"] == "pending"
    assert approval["approval_node_id"] == "approval"
    assert approval["approval_title"] == "Human approval"
    assert Path(approval["path"]).exists()


def test_approval_repository_approve_and_reject(tmp_path: Path) -> None:
    repo = WorkflowApprovalRepository(runtime_root=tmp_path)

    approval = repo.create(
        business_container="costa-conexion",
        workflow_id="workflow_test",
        approval_node_id="approval",
        approval_title="Human approval",
        payload={"hello": "world"},
    )

    approved = repo.decide(
        business_container="costa-conexion",
        workflow_id="workflow_test",
        approval_id=approval["approval_id"],
        decision="approved",
        reason="Looks good",
    )

    assert approved["status"] == "approved"
    assert approved["decision"] == "approved"
    assert approved["reason"] == "Looks good"

    approval_2 = repo.create(
        business_container="costa-conexion",
        workflow_id="workflow_test",
        approval_node_id="approval",
        approval_title="Human approval",
        payload={},
    )

    rejected = repo.decide(
        business_container="costa-conexion",
        workflow_id="workflow_test",
        approval_id=approval_2["approval_id"],
        decision="rejected",
        reason="Needs edits",
    )

    assert rejected["status"] == "rejected"
    assert rejected["decision"] == "rejected"
    assert rejected["reason"] == "Needs edits"


from backend.modules.aion_workflow.workflow_resume import resume_workflow_after_approval


def test_resume_after_approved_approval_marks_later_action_ready(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_resume_after_approval_test",
        "name": "Resume after approval test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {"id": "approval", "title": "Human approval", "type": "Gate", "x": 200, "y": 0},
                {"id": "send", "title": "Send email", "type": "Action", "x": 400, "y": 0},
            ],
            "edges": [
                {"from": "manual", "to": "approval", "condition": "success"},
                {"from": "approval", "to": "send", "condition": "approved"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_resume_after_approval_test")
    assert record is not None

    dry = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)
    approval_id = dry["approval_request"]["approval_id"]

    approval_repo = WorkflowApprovalRepository(runtime_root=tmp_path)
    approval_repo.decide(
        business_container="costa-conexion",
        workflow_id="workflow_resume_after_approval_test",
        approval_id=approval_id,
        decision="approved",
        reason="Approved in test",
    )

    resumed = resume_workflow_after_approval(
        workflow_record=record,
        approval_id=approval_id,
        audit_root=tmp_path,
    )

    assert resumed["ok"] is True
    assert resumed["mode"] == "resume_after_approval_dry_run"
    assert resumed["external_writes_performed"] is False

    statuses = [row["status"] for row in resumed["trace"]]
    assert statuses == [
        "already_completed_before_approval",
        "approved",
        "approved_ready_to_send",
    ]

    send_step = resumed["trace"][2]
    assert send_step["title"] == "Send email"
    assert send_step["safety"] == "approved_draft_only"
    assert send_step["output_items_count"] == 1
    assert send_step["output_items_preview"][0]["kind"] == "approved_action_preview"
    assert send_step["output_items_preview"][0]["payload"]["external_write_performed"] is False


def test_resume_after_rejected_or_pending_approval_fails(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_resume_reject_test",
        "name": "Resume reject test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {"id": "approval", "title": "Human approval", "type": "Gate", "x": 200, "y": 0},
                {"id": "send", "title": "Send email", "type": "Action", "x": 400, "y": 0},
            ],
            "edges": [
                {"from": "manual", "to": "approval", "condition": "success"},
                {"from": "approval", "to": "send", "condition": "approved"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_resume_reject_test")
    assert record is not None

    dry = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)
    approval_id = dry["approval_request"]["approval_id"]

    import pytest

    with pytest.raises(ValueError, match="not approved"):
        resume_workflow_after_approval(
            workflow_record=record,
            approval_id=approval_id,
            audit_root=tmp_path,
        )


def test_text_parser_match_pattern_outputs_matches(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_parser_match_test",
        "name": "Parser match test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {
                    "id": "match",
                    "title": "Match pattern",
                    "type": "Text Parser",
                    "x": 200,
                    "y": 0,
                    "config": {"pattern": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"},
                },
            ],
            "edges": [{"from": "manual", "to": "match", "condition": "success"}],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_parser_match_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)
    parser_step = next(row for row in result["trace"] if row["title"] == "Match pattern")
    parser_item = parser_step["output_items_preview"][0]

    assert parser_item["kind"] == "match_pattern"
    assert "customer@example.com" in parser_item["payload"]["matches"]
    assert parser_item["payload"]["external_write_performed"] is False


def test_text_parser_html_to_text_outputs_text(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_parser_html_to_text_test",
        "name": "Parser HTML to text test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {"id": "html", "title": "HTML to text", "type": "Text Parser", "x": 200, "y": 0},
            ],
            "edges": [{"from": "manual", "to": "html", "condition": "success"}],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_parser_html_to_text_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)
    parser_step = next(row for row in result["trace"] if row["title"] == "HTML to text")
    parser_item = parser_step["output_items_preview"][0]

    assert parser_item["kind"] == "html_to_text"
    assert "Example Customer" in parser_item["payload"]["text"]
    assert parser_item["payload"]["external_write_performed"] is False


def test_tool_compose_string_outputs_text(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_tool_compose_string_test",
        "name": "Tool compose string test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {"id": "classify", "title": "Classify enquiry", "type": "AI / Router", "x": 200, "y": 0},
                {
                    "id": "compose",
                    "title": "Compose string",
                    "type": "Tools",
                    "x": 400,
                    "y": 0,
                    "config": {"template": "Route {{route}} / urgency {{urgency}}"},
                },
            ],
            "edges": [
                {"from": "manual", "to": "classify", "condition": "success"},
                {"from": "classify", "to": "compose", "condition": "success"},
            ],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_tool_compose_string_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)
    tool_step = next(row for row in result["trace"] if row["title"] == "Compose string")
    item = tool_step["output_items_preview"][0]

    assert item["kind"] == "composed_string"
    assert item["payload"]["text"] == "Route standard_follow_up / urgency normal"
    assert item["payload"]["external_write_performed"] is False


def test_tool_sleep_outputs_preview_only(tmp_path: Path) -> None:
    repo = WorkflowGlyphRepository(runtime_root=tmp_path)

    payload = {
        "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
        "business_container": "costa-conexion",
        "workflow_id": "workflow_tool_sleep_test",
        "name": "Tool sleep test",
        "status": "draft",
        "graph": {
            "nodes": [
                {"id": "manual", "title": "Manual trigger", "type": "Trigger", "x": 0, "y": 0},
                {
                    "id": "sleep",
                    "title": "Sleep / delay",
                    "type": "Tools",
                    "x": 200,
                    "y": 0,
                    "config": {"seconds": 7},
                },
            ],
            "edges": [{"from": "manual", "to": "sleep", "condition": "success"}],
        },
    }

    repo.save(payload)
    record = repo.load("costa-conexion", "workflow_tool_sleep_test")
    assert record is not None

    result = dry_run_workflow_glyph(workflow_record=record, audit_root=tmp_path)
    tool_step = next(row for row in result["trace"] if row["title"] == "Sleep / delay")
    item = tool_step["output_items_preview"][0]

    assert item["kind"] == "sleep_preview"
    assert item["payload"]["seconds"] == 7
    assert item["payload"]["slept"] is False
    assert item["payload"]["external_write_performed"] is False
