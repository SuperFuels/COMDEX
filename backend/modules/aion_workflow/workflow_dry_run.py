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


def _first_payload_value(items: list[dict[str, Any]], key: str, fallback: str = "") -> str:
    for item in reversed(items or []):
        payload = item.get("payload") if isinstance(item, dict) else {}
        if isinstance(payload, dict) and payload.get(key):
            return str(payload.get(key))
    return fallback



def _latest_text_from_items(items: list[dict[str, Any]]) -> str:
    for item in reversed(items or []):
        payload = item.get("payload") if isinstance(item, dict) else {}
        if not isinstance(payload, dict):
            continue

        # Prefer real document/body-like content first.
        for key in ("body", "html", "text", "content"):
            value = payload.get(key)
            if value:
                return str(value)

        # If this is structured workflow data, compose a parser-friendly text blob.
        useful_parts = []
        for key in (
            "customer_name",
            "name",
            "email",
            "service",
            "town",
            "route",
            "urgency",
            "subject",
            "message",
        ):
            value = payload.get(key)
            if value:
                useful_parts.append(f"{key}: {value}")

        if useful_parts:
            return "\n".join(useful_parts)

    return (
        "<p>Hello Example Customer,</p>"
        "<p>Your enquiry about example_service in example_town has been received.</p>"
        "<table><tr><th>Field</th><th>Value</th></tr><tr><td>Email</td><td>customer@example.com</td></tr></table>"
    )


def _strip_html_to_text(value: str) -> str:
    import re

    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", str(value or ""))
    text = re.sub(r"(?i)<br\\s*/?>", "\\n", text)
    text = re.sub(r"(?i)</p\\s*>", "\\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\\n\\s+", "\\n", text)
    return text.strip()



def _latest_payload_from_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    for item in reversed(items or []):
        payload = item.get("payload") if isinstance(item, dict) else {}
        if isinstance(payload, dict):
            return payload
    return {}


def _tool_item_for_step(
    step: dict[str, Any],
    index: int,
    previous_items: list[dict[str, Any]],
) -> dict[str, Any]:
    node_id = str(step.get("node_id") or f"step_{index}")
    title = str(step.get("title") or node_id)
    title_lower = title.lower()
    config = step.get("config") if isinstance(step.get("config"), dict) else {}
    source_payload = _latest_payload_from_items(previous_items)

    base = {
        "item_id": f"dry_item_{index}",
        "source_node_id": node_id,
        "source_title": title,
        "dry_run": True,
    }

    if "set variable" in title_lower:
        key = str(config.get("key") or "workflow_variable")
        value_template = str(config.get("value") or "{{first_match}}")
        value = value_template

        for source_key, source_value in source_payload.items():
            value = value.replace("{{" + str(source_key) + "}}", str(source_value))

        return {
            **base,
            "kind": "variable_set",
            "payload": {
                "key": key,
                "value": value,
                "stored": True,
                "scope": "dry_run_memory",
                "external_write_performed": False,
            },
        }

    if "get variable" in title_lower:
        key = str(config.get("key") or "workflow_variable")
        value = source_payload.get("value")

        return {
            **base,
            "kind": "variable_get",
            "payload": {
                "key": key,
                "value": value,
                "found": value is not None,
                "scope": "dry_run_memory",
                "external_write_performed": False,
            },
        }

    if "compose string" in title_lower:
        template = str(
            config.get("template")
            or "Route {{route}} / urgency {{urgency}} / match {{first_match}}"
        )
        text = template

        for source_key, source_value in source_payload.items():
            text = text.replace("{{" + str(source_key) + "}}", str(source_value))

        return {
            **base,
            "kind": "composed_string",
            "payload": {
                "template": template,
                "text": text,
                "external_write_performed": False,
            },
        }

    if "sleep" in title_lower or "delay" in title_lower:
        seconds = int(config.get("seconds") or 5)

        return {
            **base,
            "kind": "sleep_preview",
            "payload": {
                "seconds": seconds,
                "slept": False,
                "message": f"Sleep/delay preview only. Would wait {seconds} seconds.",
                "external_write_performed": False,
            },
        }

    return {
        **base,
        "kind": "tool_preview",
        "payload": {
            "message": "Tool preview only.",
            "external_write_performed": False,
        },
    }



def _parser_item_for_step(
    step: dict[str, Any],
    index: int,
    previous_items: list[dict[str, Any]],
) -> dict[str, Any]:
    import re

    node_id = str(step.get("node_id") or f"step_{index}")
    title = str(step.get("title") or node_id)
    title_lower = title.lower()
    config = step.get("config") if isinstance(step.get("config"), dict) else {}

    source_text = _latest_text_from_items(previous_items)

    parser_kind = "text_parser"
    payload: dict[str, Any] = {
        "source_text_preview": source_text[:240],
        "external_write_performed": False,
    }

    if "html to text" in title_lower or "html_to_text" in title_lower:
        parser_kind = "html_to_text"
        payload["text"] = _strip_html_to_text(source_text)

    elif "replace" in title_lower:
        parser_kind = "replace"
        pattern = str(config.get("pattern") or "Example Customer")
        replacement = str(config.get("replacement") or "Customer")
        payload["pattern"] = pattern
        payload["replacement"] = replacement
        payload["text"] = re.sub(pattern, replacement, source_text)

    elif "html" in title_lower or "element" in title_lower:
        parser_kind = "html_extract"
        # Safe lightweight placeholder extraction. Full selector support comes later.
        links = re.findall(r"(?is)<a\\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", source_text)
        images = re.findall(r"(?is)<img\\s+[^>]*src=[\"']([^\"']+)[\"']", source_text)
        table_rows = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", source_text)
        payload["links"] = [
            {"href": href, "text": _strip_html_to_text(label)}
            for href, label in links
        ]
        payload["images"] = images
        payload["table_rows"] = [_strip_html_to_text(row) for row in table_rows]

    else:
        parser_kind = "match_pattern"
        pattern = str(config.get("pattern") or r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
        matches = re.findall(pattern, source_text)
        payload["pattern"] = pattern
        payload["matches"] = matches
        payload["first_match"] = matches[0] if matches else None

    return {
        "item_id": f"dry_item_{index}",
        "source_node_id": node_id,
        "source_title": title,
        "dry_run": True,
        "kind": parser_kind,
        "payload": payload,
    }



def _email_draft_item_for_step(
    step: dict[str, Any],
    index: int,
    previous_items: list[dict[str, Any]],
) -> dict[str, Any]:
    node_id = str(step.get("node_id") or f"step_{index}")
    title = str(step.get("title") or node_id)

    customer_name = _first_payload_value(previous_items, "customer_name", "Example Customer")
    email = _first_payload_value(previous_items, "email", "customer@example.com")
    service = _first_payload_value(previous_items, "service", "example_service")
    town = _first_payload_value(previous_items, "town", "example_town")
    route = _first_payload_value(previous_items, "route", "standard_follow_up")
    urgency = _first_payload_value(previous_items, "urgency", "normal")

    service_label = service.replace("_", " ")

    return {
        "item_id": f"dry_item_{index}",
        "source_node_id": node_id,
        "source_title": title,
        "dry_run": True,
        "kind": "email_draft",
        "payload": {
            "to": email,
            "subject": f"Re: {service_label} enquiry",
            "body": (
                f"Hi {customer_name},\\n\\n"
                f"Thanks for your enquiry about {service_label} in {town}.\\n\\n"
                "We have received your details and can help route this to the right local provider. "
                "This email has been prepared as a draft and will not be sent until a human approves it.\\n\\n"
                f"Route: {route}\\n"
                f"Urgency: {urgency}\\n\\n"
                "Kind regards,\\n"
                "Aion"
            ),
            "customer_name": customer_name,
            "service": service,
            "town": town,
            "route": route,
            "urgency": urgency,
            "requires_approval": True,
            "send_enabled": False,
            "external_write_performed": False,
            "draft_only": True,
            "message": "Email draft artifact generated. No email has been sent.",
        },
    }


def _sample_item_for_step(
    step: dict[str, Any],
    index: int,
    previous_items: list[dict[str, Any]],
) -> dict[str, Any]:
    op = str(step.get("op") or "")
    node_id = str(step.get("node_id") or f"step_{index}")
    title = str(step.get("title") or node_id)

    base = {
        "item_id": f"dry_item_{index}",
        "source_node_id": node_id,
        "source_title": title,
        "dry_run": True,
    }

    title_lower = title.lower()

    if (
        "set variable" in title_lower
        or "get variable" in title_lower
        or "compose string" in title_lower
        or "sleep" in title_lower
        or "delay" in title_lower
    ):
        return _tool_item_for_step(step, index, previous_items)

    if op == "aion.workflow:trigger":
        return {
            **base,
            "kind": "trigger_event",
            "payload": {
                "message": "Sample trigger event",
                "customer_name": "Example Customer",
                "email": "customer@example.com",
                "service": "example_service",
                "town": "example_town",
            },
        }

    if op == "aion.workflow:extract":
        title_lower = title.lower()

        if (
            "set variable" in title_lower
            or "get variable" in title_lower
            or "compose string" in title_lower
            or "sleep" in title_lower
            or "delay" in title_lower
        ):
            return _tool_item_for_step(step, index, previous_items)

        if "parser" in title_lower or "pattern" in title_lower or "replace" in title_lower or "html" in title_lower:
            return _parser_item_for_step(step, index, previous_items)

        source_payload = (previous_items[0].get("payload") if previous_items else {}) or {}
        return {
            **base,
            "kind": "extracted_fields",
            "payload": {
                "customer_name": source_payload.get("customer_name", "Example Customer"),
                "email": source_payload.get("email", "customer@example.com"),
                "service": source_payload.get("service", "example_service"),
                "town": source_payload.get("town", "example_town"),
            },
        }

    if op == "aion.workflow:classify":
        return {
            **base,
            "kind": "classification",
            "payload": {
                "route": "standard_follow_up",
                "urgency": "normal",
                "confidence": 0.82,
            },
        }

    if op == "aion.workflow:approval":
        return {
            **base,
            "kind": "approval_checkpoint",
            "payload": {
                "approval_required": True,
                "decision": "pending",
            },
        }

    if op == "aion.workflow:wait":
        return {
            **base,
            "kind": "wait_checkpoint",
            "payload": {
                "wait_mode": "simulated",
            },
        }

    if op == "aion.workflow:route":
        return {
            **base,
            "kind": "route_decision",
            "payload": {
                "route": "success",
            },
        }

    if op == "aion.workflow:action":
        lowered_title = title.lower()
        if "draft" in lowered_title or "reply" in lowered_title or "email" in lowered_title:
            return _email_draft_item_for_step(step, index, previous_items)

    return {
        **base,
        "kind": "draft_action",
        "payload": {
            "draft_only": True,
            "external_write_blocked": True,
            "external_write_performed": False,
            "message": "Action prepared in dry-run only.",
        },
    }


def dry_run_workflow_glyph(
    *,
    workflow_record: dict[str, Any],
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

    steps = list(compiled_glyph.get("steps") or [])
    flow_links = list(compiled_glyph.get("flow_links") or [])
    glyph_hash = stable_json_hash(compiled_glyph)

    trace = []
    blocked_external_writes = []
    approval_request = None
    items_by_node_id: dict[str, list[dict[str, Any]]] = {}
    current_items: list[dict[str, Any]] = []

    paused_for_approval = False

    for index, step in enumerate(steps):
        op = str(step.get("op") or "")
        node_id = str(step.get("node_id") or f"step_{index}")
        title = str(step.get("title") or node_id)

        if paused_for_approval:
            trace.append({
                "step_index": index,
                "node_id": node_id,
                "title": title,
                "op": op,
                "status": "not_run_waiting_approval",
                "safety": "pending",
                "approval_required": False,
                "input_items_count": len(current_items),
                "output_items_count": 0,
                "input_items_preview": current_items[:2],
                "output_items_preview": [],
            })
            continue

        input_items = list(current_items)

        safety = "read_only"
        blocked = False

        approval_waiting = False

        if op == "aion.workflow:action":
            safety = "draft_only"
            blocked = True
            blocked_external_writes.append({
                "step_index": index,
                "node_id": node_id,
                "title": title,
                "reason": "external/action step remains draft-only in dry-run",
            })
        elif op == "aion.workflow:approval":
            safety = "approval_gate"
            approval_waiting = True

        output_item = _sample_item_for_step(step, index, input_items)
        output_items = [output_item]
        items_by_node_id[node_id] = output_items
        current_items = output_items

        trace.append({
            "step_index": index,
            "node_id": node_id,
            "title": title,
            "op": op,
            "status": "waiting_approval" if approval_waiting else ("blocked_dry_run" if blocked else "simulated"),
            "safety": safety,
            "approval_required": approval_waiting,
            "input_items_count": len(input_items),
            "output_items_count": len(output_items),
            "input_items_preview": input_items[:2],
            "output_items_preview": output_items[:2],
        })

        if approval_waiting:
            approval_repo = WorkflowApprovalRepository(runtime_root=audit_root)
            approval_request = approval_repo.create(
                business_container=business_container,
                workflow_id=workflow_id,
                approval_node_id=node_id,
                approval_title=title,
                payload={
                    "workflow_id": workflow_id,
                    "business_container": business_container,
                    "compiled_glyph_hash": glyph_hash,
                    "approval_step_index": index,
                    "input_items": input_items,
                    "output_items": output_items,
                    "blocked_external_writes": blocked_external_writes,
                },
            )
            paused_for_approval = True

    result = {
        "ok": True,
        "mode": "dry_run",
        "workflow_id": workflow_id,
        "business_container": business_container,
        "compiled_glyph_hash": glyph_hash,
        "steps": len(steps),
        "links": len(flow_links),
        "external_writes_performed": False,
        "approval_required": bool(blocked_external_writes),
        "blocked_external_writes": blocked_external_writes,
        "approval_request": approval_request,
        "trace": trace,
        "final_output_items": current_items,
        "items_by_node_id": items_by_node_id,
        "ran_at": utc_now_iso(),
    }

    audit_dir = Path(audit_root) / business_container / "aion_workflow_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{workflow_id}.jsonl"

    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    result["audit_path"] = str(audit_path)
    return result
