from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib
import json

from .contracts_workflow_glyph import assert_safe_workflow_glyph
from .workflow_approval_repository import WorkflowApprovalRepository


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resume_item_for_step(
    *,
    step: dict[str, Any],
    index: int,
    previous_items: list[dict[str, Any]],
    approval_id: str,
) -> dict[str, Any]:
    op = str(step.get("op") or "")
    node_id = str(step.get("node_id") or f"step_{index}")
    title = str(step.get("title") or node_id)

    base = {
        "item_id": f"resume_item_{index}",
        "source_node_id": node_id,
        "source_title": title,
        "dry_run": True,
        "resumed_after_approval": True,
        "approval_id": approval_id,
    }

    if op == "aion.workflow:action":
        latest_email_draft = None
        for item in reversed(previous_items or []):
            if isinstance(item, dict) and item.get("kind") == "email_draft":
                latest_email_draft = item
                break

        payload = {
            "approved_ready_to_send": True,
            "external_write_performed": False,
            "send_enabled": False,
            "message": "Approved action is ready, but external sending is still disabled.",
        }

        if latest_email_draft and isinstance(latest_email_draft.get("payload"), dict):
            payload["email_draft"] = latest_email_draft["payload"]

        return {
            **base,
            "kind": "approved_email_send_preview" if latest_email_draft else "approved_action_preview",
            "payload": payload,
        }

    return {
        **base,
        "kind": "resumed_step_preview",
        "payload": {
            "status": "simulated_after_approval",
        },
    }


def resume_workflow_after_approval(
    *,
    workflow_record: dict[str, Any],
    approval_id: str,
    audit_root: Path | str = ".runtime/local_node",
) -> dict[str, Any]:
    compiled_glyph = workflow_record.get("compiled_glyph") or {}
    assert_safe_workflow_glyph(compiled_glyph)

    workflow = compiled_glyph.get("workflow") or {}
    workflow_id = str(workflow.get("workflow_id") or workflow_record.get("workflow_id") or "workflow_draft_1")
    business_container = str(
        workflow.get("business_container")
        or workflow_record.get("business_container")
        or "costa-conexion"
    )

    approval_repo = WorkflowApprovalRepository(runtime_root=audit_root)
    approval = approval_repo.load(business_container, workflow_id, approval_id)

    if approval is None:
        raise FileNotFoundError("Approval request not found")

    if approval.get("status") != "approved" or approval.get("decision") != "approved":
        raise ValueError("Approval request is not approved")

    approval_step_index = int((approval.get("payload") or {}).get("approval_step_index", -1))
    if approval_step_index < 0:
        raise ValueError("Approval request missing approval_step_index")

    steps = list(compiled_glyph.get("steps") or [])
    flow_links = list(compiled_glyph.get("flow_links") or [])
    glyph_hash = stable_json_hash(compiled_glyph)

    approval_payload = approval.get("payload") or {}

    # Preserve both the approval checkpoint output and the artifact that entered
    # the approval gate. The email_draft lives in input_items; the approval
    # checkpoint lives in output_items. Downstream send-preview steps need both.
    approval_input_items = list(approval_payload.get("input_items") or [])
    approval_output_items = list(approval_payload.get("output_items") or [])
    current_items = approval_output_items + [
        item for item in approval_input_items
        if isinstance(item, dict) and item.get("kind") == "email_draft"
    ]

    trace = []

    for index, step in enumerate(steps):
        op = str(step.get("op") or "")
        node_id = str(step.get("node_id") or f"step_{index}")
        title = str(step.get("title") or node_id)

        if index < approval_step_index:
            trace.append({
                "step_index": index,
                "node_id": node_id,
                "title": title,
                "op": op,
                "status": "already_completed_before_approval",
                "safety": "historical",
                "approval_required": False,
                "input_items_count": 0,
                "output_items_count": 0,
                "input_items_preview": [],
                "output_items_preview": [],
            })
            continue

        if index == approval_step_index:
            trace.append({
                "step_index": index,
                "node_id": node_id,
                "title": title,
                "op": op,
                "status": "approved",
                "safety": "approval_gate",
                "approval_required": False,
                "approval_id": approval_id,
                "input_items_count": len(approval_input_items),
                "output_items_count": len(current_items),
                "input_items_preview": approval_input_items[:2],
                "output_items_preview": current_items[:2],
            })
            continue

        input_items = list(current_items)
        output_item = _resume_item_for_step(
            step=step,
            index=index,
            previous_items=input_items,
            approval_id=approval_id,
        )
        output_items = [output_item]
        current_items = output_items

        is_action = op == "aion.workflow:action"

        trace.append({
            "step_index": index,
            "node_id": node_id,
            "title": title,
            "op": op,
            "status": "approved_ready_to_send" if is_action else "simulated_after_approval",
            "safety": "approved_draft_only" if is_action else "read_only",
            "approval_required": False,
            "approval_id": approval_id,
            "input_items_count": len(input_items),
            "output_items_count": len(output_items),
            "input_items_preview": input_items[:2],
            "output_items_preview": output_items[:2],
        })

    result = {
        "ok": True,
        "mode": "resume_after_approval_dry_run",
        "workflow_id": workflow_id,
        "business_container": business_container,
        "approval_id": approval_id,
        "approval_status": approval.get("status"),
        "compiled_glyph_hash": glyph_hash,
        "steps": len(steps),
        "links": len(flow_links),
        "external_writes_performed": False,
        "trace": trace,
        "final_output_items": current_items,
        "ran_at": utc_now_iso(),
    }

    audit_dir = Path(audit_root) / business_container / "aion_workflow_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{workflow_id}.jsonl"

    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    result["audit_path"] = str(audit_path)
    return result
