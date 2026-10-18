"""Provider-neutral, approval-gated desktop application harness.

Models describe semantic work. AION validates it, issues a one-use grant and
the signed desktop shell performs only the approved local operation. Models
never receive operating-system control or credentials.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
import threading
import time
from typing import Any, Mapping
from uuid import uuid4
import re

from backend.services.aion_mission_mode.external_tool_gateway import (
    create_capability_receipt,
    create_capability_registry,
    create_tool_call_request,
    evaluate_tool_call,
)


READ_OPERATIONS = {"open_app", "inspect_app", "wait", "verify_text"}
WRITE_OPERATIONS = {
    "click_control",
    "type_text",
    "select_menu_item",
    "press_key",
    "create_note",
    "create_presentation",
    "create_document",
    "style_document",
    "create_spreadsheet",
    "create_email_draft",
}
ALLOWED_OPERATIONS = READ_OPERATIONS | WRITE_OPERATIONS
APP_ALIASES = {
    "notes": "Notes",
    "apple notes": "Notes",
    "keynote": "Keynote",
    "key note": "Keynote",
    "pages": "Pages",
    "numbers": "Numbers",
    "calendar": "Calendar",
    "mail": "Mail",
    "finder": "Finder",
    "preview": "Preview",
    "safari": "Safari",
    "google chrome": "Google Chrome",
    "chrome": "Google Chrome",
    "microsoft word": "Microsoft Word",
    "word": "Microsoft Word",
    "microsoft excel": "Microsoft Excel",
    "excel": "Microsoft Excel",
    "microsoft powerpoint": "Microsoft PowerPoint",
    "powerpoint": "Microsoft PowerPoint",
}
BLOCKED_AUTOMATION_APPS = {
    "terminal", "iterm", "iterm2", "script editor", "automator", "shortcuts",
}
SAFE_KEYS = {
    "return", "enter", "tab", "escape", "space", "delete", "backspace",
    "left", "right", "up", "down", "home", "end", "pageup", "pagedown",
}
SAFE_MODIFIERS = {"command", "shift", "option", "control"}
HIGH_CONSEQUENCE_PATTERN = re.compile(
    r"\b(?:send|publish|post|purchase|buy|pay|checkout|transfer|delete|remove|erase|"
    r"uninstall|upload|share|invite|submit|confirm|sign\s*in|log\s*in|connect\s+account)\b",
    flags=re.IGNORECASE,
)
BROWSER_APPS = {"safari", "google chrome", "chrome", "firefox", "microsoft edge", "edge"}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def computer_tool_contract() -> dict[str, Any]:
    return {
        "schema_version": "aion.computer_tool_contract.v1",
        "provider_neutral": True,
        "planner_role": "approved_connected_model",
        "authority_role": "aion",
        "executor_role": "signed_desktop_shell",
        "operations": sorted(ALLOWED_OPERATIONS),
        "approval_required_operations": [],
        "approval_required_effects": [
            "transactions and payments",
            "sending email or messages",
            "publishing or posting",
            "deleting or removing data",
            "uploads, sharing and invitations",
            "logins, account connections and external submissions",
        ],
        "default_local_write_policy": "execute_then_show_receipt",
        "allowed_apps": "installed_desktop_apps_except_blocked_code_execution_tools",
        "app_recipes": ["Notes", "Keynote", "Pages", "Numbers", "Mail"],
        "generic_primitives": sorted(ALLOWED_OPERATIONS - {
            "create_note", "create_presentation", "create_document",
            "create_spreadsheet", "create_email_draft", "style_document",
        }),
        "rules": [
            "Models propose semantic desktop steps but never control the computer.",
            "Opening an approved local app is non-destructive.",
            "Reversible local work runs automatically and produces a visible receipt.",
            "Externally consequential, destructive, account or transaction actions require exact user approval.",
            "Every execution uses a short-lived one-time grant and produces a receipt.",
        ],
    }


def computer_tool_prompt() -> str:
    return (
        "AION COMPUTER TOOL CONTRACT: If the request requires a desktop application, do not refuse and do not "
        "claim it was done. Return only <AION_COMPUTER_PLAN>{\"objective\":\"...\",\"steps\":[...]}</AION_COMPUTER_PLAN>. "
        "Supported generic operations are open_app, inspect_app, click_control, type_text, select_menu_item, "
        "press_key, wait and verify_text. Stable recipes also include create_note ONLY for Notes, "
        "create_presentation ONLY for Keynote, create_document and style_document ONLY for Pages, create_spreadsheet ONLY for "
        "Numbers and create_email_draft ONLY for Mail; never use those recipes for another app. AION runs reversible "
        "local work automatically and shows a receipt. Sending, publishing, transactions, deletion, uploads, "
        "sharing, login and other externally consequential actions remain approval gated. "
        "For generic controls use target.app and target.control; for menu selection include menu and item; for typing "
        "include value; for verification include expected_text. First inspect when the visible controls are unknown. "
        "Treat 'Keynote' and 'key note' as Apple's Keynote presentation app, never as Notes. Use the fewest steps. AION, not you, controls "
        "execution and approval. If the requested note wording is vague, use the user's exact wording rather than "
        "inventing sensitive content. For requests not involving a desktop app, answer normally."
    )


def computer_plan_repair_prompt(*, user_request: str, proposal: Mapping[str, Any], error: str) -> str:
    """Ask any selected provider to repair its own invalid semantic plan once."""
    return (
        "Your previous desktop plan was rejected by AION and nothing was executed. Repair the plan. "
        f"User request: {str(user_request or '')[:2000]}\n"
        f"Validation error: {str(error or '')[:500]}\n"
        f"Rejected proposal: {_canonical_json(dict(proposal))[:6000]}\n\n"
        f"{computer_tool_prompt()}\n"
        "Use open_app then inspect_app when controls are uncertain. Use generic click_control, type_text, "
        "select_menu_item, press_key and verify_text for all apps without a stable recipe. Return one corrected "
        "AION_COMPUTER_PLAN block and no explanation."
    )


def extract_computer_plan(text: str) -> dict[str, Any] | None:
    raw = str(text or "")
    start_tag = "<AION_COMPUTER_PLAN>" if "<AION_COMPUTER_PLAN>" in raw else "AION_COMPUTER_PLAN>"
    end_tag = "</AION_COMPUTER_PLAN>"
    start = raw.find(start_tag)
    end = raw.find(end_tag, start + len(start_tag))
    if start < 0:
        return None
    try:
        payload = raw[start + len(start_tag):end].strip() if end >= 0 else raw[start + len(start_tag):].lstrip()
        parsed = json.loads(payload) if end >= 0 else json.JSONDecoder().raw_decode(payload)[0]
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def infer_explicit_desktop_app(prompt: str) -> str | None:
    """Resolve an explicitly named desktop app without maintaining an app catalogue."""
    raw = str(prompt or "").strip()
    lowered = raw.lower()
    for alias in sorted(APP_ALIASES, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
            return APP_ALIASES[alias]
    match = re.search(
        r"\b(?:open|launch|use)\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 .&+()'_-]{0,59}?)"
        r"(?:\s+app)?(?=\s+(?:and|to|then)\b|[,.;]|$)",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    try:
        app_name = match.group(1).strip()
        app_name = re.sub(r"\s+app$", "", app_name, flags=re.IGNORECASE).strip()
        return _normalise_app(app_name)
    except ValueError:
        return None


def coerce_computer_proposal(proposal: Mapping[str, Any], *, user_request: str = "") -> dict[str, Any]:
    """Repair common small-model schema drift without widening execution authority."""
    result = deepcopy(dict(proposal))
    objective = str(result.get("objective") or user_request or "Operate a desktop app")
    app_name = infer_explicit_desktop_app(user_request) or infer_explicit_desktop_app(objective)
    raw_steps = result.get("steps") if isinstance(result.get("steps"), list) else []
    typed_match = re.search(
        r"\btype\s+(?:the\s+)?(?:title|text|words?)?\s*[\"“]?(.+?)[\"”]?"
        r"(?=\s*(?:,|\band\s+verify\b|\bthen\b|[.!?]|$))",
        str(user_request or objective),
        flags=re.IGNORECASE,
    )
    typed_value = typed_match.group(1).strip(" \"“”") if typed_match else ""
    steps: list[dict[str, Any]] = []
    for raw_step in raw_steps:
        step = {"operation": raw_step} if isinstance(raw_step, str) else deepcopy(dict(raw_step)) if isinstance(raw_step, Mapping) else {}
        operation = str(step.get("operation") or step.get("type") or "").strip().lower().replace(" ", "_")
        control_as_operation = str(step.get("control") or "").strip().lower().replace(" ", "_")
        if not operation and control_as_operation in (ALLOWED_OPERATIONS - {
            "create_note", "create_presentation", "create_document",
            "create_spreadsheet", "create_email_draft", "style_document",
        }):
            operation = control_as_operation
            step["operation"] = operation
            step.pop("control", None)
        elif not operation and (step.get("expected_text") is not None):
            operation = "verify_text"
            step["operation"] = operation
        elif not operation and (step.get("value") is not None) and step.get("control"):
            operation = "type_text"
            step["operation"] = operation
        elif not operation and step.get("menu") and step.get("item"):
            operation = "select_menu_item"
            step["operation"] = operation
        elif not operation and step.get("key"):
            operation = "press_key"
            step["operation"] = operation
        elif not operation and step.get("control"):
            operation = "click_control"
            step["operation"] = operation
        target = step.get("target") if isinstance(step.get("target"), Mapping) else {}
        target = dict(target)
        if app_name:
            target["app"] = app_name
            step.pop("app", None)
        step["target"] = target
        if operation == "create_presentation" and str(target.get("app") or "").lower() != "keynote":
            step = {"operation": "press_key", "target": {"app": target.get("app")}, "key": "n", "modifiers": ["command"]}
        elif operation in {"create_document", "new_document", "create_blank_document"}:
            step = {"operation": "press_key", "target": {"app": target.get("app")}, "key": "n", "modifiers": ["command"]}
        elif operation == "type_text":
            control = str(step.get("control") or target.get("control") or target.get("label") or "").strip()
            if not control or re.fullmatch(r"(?:(?:title|text|body|document)(?:[_ -]?(?:input|field|area))?|document[_ -]?title)", control, flags=re.IGNORECASE):
                step["control"] = "focused control"
            if not (step.get("value") or target.get("value")) and typed_value:
                step["value"] = typed_value
        elif operation == "verify_text" and not (step.get("expected_text") or target.get("expected_text")) and typed_value:
            step["expected_text"] = typed_value
        steps.append(step)

    wants_new_document = bool(re.search(r"\b(?:create|make)\s+(?:a\s+)?(?:new|blank)?\s*(?:document|file|sheet|presentation)\b", str(user_request or objective), flags=re.IGNORECASE))
    has_new_document = any(
        (
            str(step.get("operation") or "").lower() == "press_key"
            and str(step.get("key") or "").lower() == "n"
            and "command" in [str(item).lower() for item in (step.get("modifiers") or [])]
        )
        or (
            str(step.get("operation") or "").lower() == "click_control"
            and bool(re.search(r"\b(?:new|blank|create)\b", str(step.get("control") or "").replace("_", " "), flags=re.IGNORECASE))
        )
        for step in steps
    )
    if wants_new_document and app_name and not has_new_document:
        insert_at = next((index + 1 for index, step in enumerate(steps) if str(step.get("operation") or "").lower() == "inspect_app"), 1 if steps else 0)
        steps.insert(insert_at, {"operation": "press_key", "target": {"app": app_name}, "key": "n", "modifiers": ["command"]})
    result["objective"] = objective
    result["steps"] = steps
    return result


def proposal_from_user_request(prompt: str) -> dict[str, Any] | None:
    """Compile unambiguous supported desktop requests without prompt leakage."""
    raw = str(prompt or "").strip()
    lowered = raw.lower()

    explicit_app = infer_explicit_desktop_app(raw)

    if explicit_app == "Pages" and any(word in lowered for word in ("open", "create", "type", "write")):
        quoted = re.search(r"[\"“](.+?)[\"”]", raw)
        content = quoted.group(1).strip() if quoted else ""
        if not content:
            content_match = re.search(
                r"\b(?:heading|title|text)\s+(?:as\s+)?(.+?)(?:[.!?]|$)", raw, flags=re.IGNORECASE,
            )
            content = content_match.group(1).strip(" \"“”") if content_match else ""
        steps: list[dict[str, Any]] = [{"operation": "open_app", "target": {"app": "Pages"}}]
        if re.search(r"\b(?:create|make)\b", lowered):
            steps.append({
                "operation": "create_document",
                "target": {"app": "Pages"},
                "value": content or "New document",
            })
        elif content:
            steps.append({
                "operation": "type_text", "target": {"app": "Pages"},
                "control": "focused control", "value": content,
            })
        return {"objective": "Open Pages and create the requested document", "steps": steps}

    if explicit_app == "Numbers" and any(word in lowered for word in ("open", "create", "enter", "type")):
        quoted = re.search(r"[\"“](.+?)[\"”]", raw)
        value = quoted.group(1).strip() if quoted else ""
        if not value:
            value_match = re.search(r"\b(?:enter|type)\s+(.+?)(?:\s+in\s+the\b|[.!?]|$)", raw, flags=re.IGNORECASE)
            value = value_match.group(1).strip(" \"“”") if value_match else ""
        return {
            "objective": "Open Numbers and create the requested spreadsheet",
            "steps": [
                {"operation": "open_app", "target": {"app": "Numbers"}},
                {"operation": "create_spreadsheet", "target": {"app": "Numbers"}, "value": value or "New spreadsheet"},
            ],
        }

    if explicit_app == "Calendar" and any(word in lowered for word in ("open", "inspect", "show", "tell")):
        return {
            "objective": "Open Calendar and inspect its visible controls",
            "steps": [
                {"operation": "open_app", "target": {"app": "Calendar"}},
                {"operation": "inspect_app", "target": {"app": "Calendar"}, "max_elements": 120},
            ],
        }

    mail_intent = explicit_app == "Mail" or bool(re.search(r"\b(?:send|draft)\s+(?:the\s+|an?\s+)?email\b", lowered))
    if mail_intent:
        if re.search(r"\bsend\s+(?:the\s+)?(?:draft\s+)?email\b", lowered) and "do not send" not in lowered:
            return {
                "objective": "Send the open Mail draft",
                "steps": [
                    {"operation": "open_app", "target": {"app": "Mail"}},
                    {"operation": "click_control", "target": {"app": "Mail"}, "control": "Send"},
                ],
            }
        if "draft" in lowered or "subject" in lowered or "body" in lowered:
            subject_match = re.search(r"\bsubject\s+[\"“](.+?)[\"”]", raw, flags=re.IGNORECASE)
            body_match = re.search(r"\bbody\s+[\"“](.+?)[\"”]", raw, flags=re.IGNORECASE)
            return {
                "objective": "Open Mail and create the requested draft without sending it",
                "steps": [
                    {"operation": "open_app", "target": {"app": "Mail"}},
                    {
                        "operation": "create_email_draft",
                        "target": {"app": "Mail"},
                        "subject": subject_match.group(1).strip() if subject_match else "Draft email",
                        "body": body_match.group(1).strip() if body_match else "",
                    },
                ],
            }

    # Resolve Keynote first.  A substring check for "note" must never turn
    # Apple's presentation app into the Notes app.
    is_keynote = bool(re.search(r"\bkey\s*note\b", lowered))
    if is_keynote and any(word in lowered for word in ("open", "create", "produce", "make", "build")):
        steps: list[dict[str, Any]] = [{"operation": "open_app", "target": {"app": "Keynote"}}]
        wants_slide = any(word in lowered for word in ("slide", "presentation", "deck"))
        if wants_slide:
            topic_match = re.search(r"\babout\s+(.+?)(?:[.!?]|$)", raw, flags=re.IGNORECASE)
            if not topic_match:
                topic_match = re.search(r"\b(?:slide|presentation|deck)\s+on\s+(.+?)(?:[.!?]|$)", raw, flags=re.IGNORECASE)
            topic = topic_match.group(1).strip() if topic_match else "AI"
            if topic.lower() in {"ai", "artificial intelligence"}:
                title = "Artificial Intelligence"
                body = "How AI helps businesses automate work, improve decisions and serve customers faster."
            else:
                title = topic[:120].strip().title()
                body = f"An introduction to {topic.strip()}."
            steps.append({
                "operation": "create_presentation",
                "target": {"app": "Keynote"},
                "title": title,
                "body": body,
            })
        return {
            "objective": "Open Keynote" + (" and create the requested slide" if wants_slide else ""),
            "steps": steps,
        }

    is_notes = bool(re.search(r"\bnotes(?:\s+app)?\b", lowered))
    if not is_notes or not any(word in lowered for word in ("open", "write", "create", "add")):
        return None
    steps: list[dict[str, Any]] = [{"operation": "open_app", "target": {"app": "Notes"}}]
    wants_write = any(word in lowered for word in ("write", "create a note", "add a note", "make a note"))
    if wants_write:
        quoted = re.search(r"[\"“](.+?)[\"”]", raw)
        if quoted:
            value = quoted.group(1).strip()
        elif re.search(r"\bwrite\s+something\b", lowered):
            value = "Something"
        else:
            tail = re.split(r"\b(?:write|saying|that says)\b", raw, maxsplit=1, flags=re.IGNORECASE)
            value = tail[-1].strip(" .") if len(tail) > 1 else "New note from Tessaris"
            value = re.sub(r"^(?:in|into|to)\s+(?:my\s+)?notes(?:\s+app)?\s*(?:and\s*)?", "", value, flags=re.IGNORECASE).strip(" .")
            if not value or value.lower() in {"a note", "note"}:
                value = "New note from Tessaris"
        steps.append({"operation": "create_note", "target": {"app": "Notes"}, "title": "Tessaris note", "value": value})
    return {"objective": "Open Notes" + (" and create the requested note" if wants_write else ""), "steps": steps}


def is_research_pages_request(prompt: str) -> bool:
    """Identify a compound research -> Pages deliverable request."""
    raw = str(prompt or "")
    lowered = raw.lower()
    return (
        infer_explicit_desktop_app(raw) == "Pages"
        and bool(re.search(r"\b(?:research|search|find|look up)\b", lowered))
        and bool(re.search(r"\b(?:summari[sz]|report|document|write)\w*\b", lowered))
        and bool(re.search(r"\b(?:source|link|citation|recent|latest|current|today)\w*\b", lowered))
    )


def proposal_from_attachment_request(
    prompt: str,
    attachments: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Compile clear attachment work into a deterministic local application plan."""
    raw = str(prompt or "").strip()
    lowered = raw.lower()
    wants_style = bool(re.search(r"\b(?:style|format|polish|redesign|brand|professional|improve\s+(?:the\s+)?layout)\b", lowered))
    if not wants_style:
        return None
    pages_attachment = next(
        (
            item for item in attachments
            if str(item.get("extension") or "").lower() == ".pages"
            and str(item.get("path") or "").strip()
        ),
        None,
    )
    if not pages_attachment:
        return None
    source_path = str(pages_attachment["path"])
    return {
        "objective": f"Style {Path(source_path).name} professionally in Pages and save a new copy",
        "steps": [
            {"operation": "open_app", "target": {"app": "Pages"}},
            {
                "operation": "style_document",
                "target": {"app": "Pages"},
                "file_path": source_path,
                "style": "tessaris_professional",
            },
        ],
    }


def research_query_from_pages_request(prompt: str) -> str:
    """Keep the research subject and discard the downstream document command."""
    raw = " ".join(str(prompt or "").split()).strip()
    match = re.search(
        r"\b(?:research|search(?:\s+the\s+web)?\s+for|find)\s+(.+?)"
        r"(?:,\s*|\s+and\s+)(?:then\s+)?(?:create|make|write|put)\b",
        raw,
        flags=re.IGNORECASE,
    )
    query = match.group(1).strip() if match else raw
    return query[:500]


def proposal_from_research_evidence(
    prompt: str,
    evidence: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Compile verified web evidence into a useful, locally saved Pages report."""
    if not is_research_pages_request(prompt):
        return None
    items = [dict(item) for item in evidence if isinstance(item, Mapping)][:3]
    if not items:
        return None

    query = research_query_from_pages_request(prompt)
    title = "AI Automation Developments" if "automation" in query.lower() else "Research Briefing"
    prepared = datetime.now(timezone.utc).strftime("%d %B %Y")
    sections = [title, f"Prepared {prepared}", ""]
    for index, item in enumerate(items, start=1):
        item_title = str(item.get("title") or f"Development {index}").strip()
        published = str(item.get("published_at") or item.get("date") or "Date not supplied").strip()
        summary = str(item.get("content") or item.get("summary") or "Current verified research result.").strip()
        url = str(item.get("url") or "").strip()
        sections.extend([
            f"{index}. {item_title}",
            f"Published: {published}",
            f"Summary: {summary}",
            f"Source: {url}",
            "",
        ])
    sections.extend([
        "Method",
        "Prepared by AION using read-only web research. Source links are retained so each development can be checked.",
    ])
    return {
        "objective": f"Research {query} and save a sourced Pages briefing",
        "steps": [
            {"operation": "open_app", "target": {"app": "Pages"}},
            {
                "operation": "create_document",
                "target": {"app": "Pages"},
                "value": "\n".join(sections),
                "file_name": title,
            },
        ],
    }


def _normalise_app(value: Any) -> str:
    key = str(value or "").strip().lower()
    if not key:
        raise ValueError("computer_app_required")
    if key in BLOCKED_AUTOMATION_APPS:
        raise ValueError("computer_app_blocked")
    if not re.fullmatch(r"[a-z0-9][a-z0-9 .&+()'_-]{0,119}", key):
        raise ValueError("computer_app_not_approved")
    return APP_ALIASES.get(key, str(value).strip())


def _clean_control(value: Any, *, required: bool = True) -> str:
    control = str(value or "").strip()
    if required and not control:
        raise ValueError("computer_control_required")
    if len(control) > 300:
        raise ValueError("computer_control_too_long")
    return control


def _step_requires_approval(step: Mapping[str, Any], *, model_requested: bool = False) -> bool:
    if model_requested:
        return True
    operation = str(step.get("operation") or "").lower()
    app_name = str((step.get("target") or {}).get("app") or "").lower()
    if operation not in WRITE_OPERATIONS:
        return False
    # Web mutations belong in the isolated browser harness, where external
    # consequences retain their stricter policy.
    if app_name in BROWSER_APPS:
        return True
    consequence_text = " ".join(
        str(step.get(key) or "") for key in ("control", "menu", "item", "title")
    )
    if HIGH_CONSEQUENCE_PATTERN.search(consequence_text):
        return True
    if operation == "press_key":
        key = str(step.get("key") or "").lower()
        modifiers = {str(item).lower() for item in (step.get("modifiers") or [])}
        if key in {"delete", "backspace"} and ("command" in modifiers or "control" in modifiers):
            return True
        if key in {"return", "enter"} and app_name in {"mail", "messages", "slack", "microsoft outlook", "microsoft teams"}:
            return True
    return False


def normalise_computer_steps(steps: Any) -> list[dict[str, Any]]:
    if not isinstance(steps, list) or not steps:
        raise ValueError("computer_plan_requires_steps")
    if len(steps) > 20:
        raise ValueError("computer_plan_step_limit_exceeded")
    normalised: list[dict[str, Any]] = []
    for index, raw in enumerate(steps):
        if not isinstance(raw, Mapping):
            raise ValueError("computer_step_must_be_object")
        operation = str(raw.get("operation") or raw.get("type") or "").strip().lower()
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"computer_operation_not_allowed:{operation or 'missing'}")
        target = raw.get("target") if isinstance(raw.get("target"), Mapping) else {}
        step: dict[str, Any] = {
            "step_id": f"step_{index + 1}",
            "operation": operation,
            "target": {"app": _normalise_app(target.get("app") or raw.get("app"))},
            "approval_required": False,
        }
        if operation == "create_note":
            value = str(raw.get("value") or raw.get("body") or target.get("value") or target.get("body") or "").strip()
            if not value:
                raise ValueError("computer_note_content_required")
            step["title"] = str(raw.get("title") or target.get("title") or "Tessaris note").strip()[:200]
            step["value"] = value[:20_000]
        if operation == "create_presentation":
            title = str(raw.get("title") or target.get("title") or "New presentation").strip()
            body = str(raw.get("body") or raw.get("value") or target.get("body") or target.get("value") or "").strip()
            if not body:
                raise ValueError("computer_presentation_content_required")
            step["title"] = title[:200]
            step["body"] = body[:20_000]
        if operation == "create_document":
            if step["target"]["app"] != "Pages":
                raise ValueError("computer_document_recipe_requires_pages")
            value = str(raw.get("value") or raw.get("body") or target.get("value") or "").strip()
            if not value:
                raise ValueError("computer_document_content_required")
            step["value"] = value[:20_000]
            file_name = str(raw.get("file_name") or target.get("file_name") or "").strip()
            if file_name:
                file_name = re.sub(r"[^A-Za-z0-9 ._()-]+", "", file_name).strip(" .")[:120]
                if file_name:
                    step["file_name"] = file_name
        if operation == "style_document":
            if step["target"]["app"] != "Pages":
                raise ValueError("computer_document_style_recipe_requires_pages")
            raw_path = str(raw.get("file_path") or target.get("file_path") or "").strip()
            try:
                source_path = Path(raw_path).expanduser().resolve(strict=True)
            except (OSError, RuntimeError):
                raise ValueError("computer_document_style_source_not_found") from None
            if source_path.suffix.lower() != ".pages":
                raise ValueError("computer_document_style_requires_pages_file")
            step["file_path"] = str(source_path)
            step["style"] = str(raw.get("style") or target.get("style") or "tessaris_professional")[:80]
        if operation == "create_spreadsheet":
            if step["target"]["app"] != "Numbers":
                raise ValueError("computer_spreadsheet_recipe_requires_numbers")
            value = str(raw.get("value") or target.get("value") or "").strip()
            if not value:
                raise ValueError("computer_spreadsheet_content_required")
            step["value"] = value[:20_000]
            step["cell"] = str(raw.get("cell") or target.get("cell") or "A1").strip()[:20]
        if operation == "create_email_draft":
            if step["target"]["app"] != "Mail":
                raise ValueError("computer_email_draft_recipe_requires_mail")
            step["subject"] = str(raw.get("subject") or target.get("subject") or "Draft email").strip()[:500]
            step["body"] = str(raw.get("body") or raw.get("value") or target.get("body") or "")[:20_000]
        if operation == "inspect_app":
            step["max_elements"] = max(10, min(int(raw.get("max_elements") or 80), 200))
        if operation == "click_control":
            step["control"] = _clean_control(raw.get("control") or target.get("control") or target.get("label"))
        if operation == "type_text":
            step["control"] = _clean_control(raw.get("control") or target.get("control") or target.get("label"))
            value = str(raw.get("value") or target.get("value") or "")
            if not value:
                raise ValueError("computer_text_required")
            if re.search(r"password|passcode|secret|api[ _-]?key|token", step["control"], flags=re.IGNORECASE):
                raise ValueError("computer_sensitive_field_blocked")
            step["value"] = value[:20_000]
        if operation == "select_menu_item":
            step["menu"] = _clean_control(raw.get("menu") or target.get("menu"))
            step["item"] = _clean_control(raw.get("item") or target.get("item"))
        if operation == "press_key":
            key = str(raw.get("key") or target.get("key") or "").strip().lower()
            if len(key) == 1:
                if not key.isprintable():
                    raise ValueError("computer_key_not_allowed")
            elif key not in SAFE_KEYS:
                raise ValueError("computer_key_not_allowed")
            modifiers = [str(item).strip().lower() for item in (raw.get("modifiers") or target.get("modifiers") or [])]
            if any(item not in SAFE_MODIFIERS for item in modifiers):
                raise ValueError("computer_modifier_not_allowed")
            step["key"] = key
            step["modifiers"] = sorted(set(modifiers))
        if operation == "wait":
            step["seconds"] = max(0.1, min(float(raw.get("seconds") or target.get("seconds") or 1), 10.0))
        if operation == "verify_text":
            expected = str(raw.get("expected_text") or target.get("expected_text") or raw.get("value") or "").strip()
            if not expected:
                raise ValueError("computer_expected_text_required")
            step["expected_text"] = expected[:500]
        step["approval_required"] = _step_requires_approval(
            step,
            model_requested=bool(raw.get("approval_required")),
        )
        normalised.append(step)
    return normalised


class ComputerHarnessStore:
    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "computer_harness" / "state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value.setdefault("plans", {})
                value.setdefault("grants", {})
                value.setdefault("receipts", {})
                return value
        except (OSError, ValueError, TypeError):
            pass
        return {"plans": {}, "grants": {}, "receipts": {}}

    def _save(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _public(plan: Mapping[str, Any]) -> dict[str, Any]:
        return deepcopy(dict(plan))

    def _issue_grant(self, state: dict[str, Any], plan: dict[str, Any], now: int) -> str:
        grant_id = "computer_grant_" + uuid4().hex
        token = secrets.token_urlsafe(32)
        state["grants"][grant_id] = {
            "grant_id": grant_id,
            "plan_id": plan["plan_id"],
            "plan_hash": plan["plan_hash"],
            "token_hash": _hash(token),
            "issued_at": now,
            "expires_at": now + 300,
            "redeemed_at": None,
        }
        plan["grant_id"] = grant_id
        plan["execution_token"] = token
        return token

    def create_plan(self, *, proposal: Mapping[str, Any], provider: str, model: str,
                    workspace_id: str, requested_by: str = "aion_chat", now: int | None = None) -> dict[str, Any]:
        created_at = int(now if now is not None else time.time())
        steps = normalise_computer_steps(proposal.get("steps"))
        plan = {
            "schema_version": "aion.computer_plan.v1",
            "plan_id": "computer_plan_" + uuid4().hex,
            "workspace_id": workspace_id,
            "provider": str(provider or ""),
            "model": str(model or provider or ""),
            "provider_neutral": True,
            "requested_by": requested_by,
            "objective": str(proposal.get("objective") or "Operate an approved desktop app")[:500],
            "steps": steps,
            "approval_step_ids": [step["step_id"] for step in steps if step["approval_required"]],
            "state": "awaiting_user_approval" if any(step["approval_required"] for step in steps) else "ready",
            "auto_execute": not any(step["approval_required"] for step in steps),
            "created_at": created_at,
            "approved_at": None,
            "approval_hash": None,
            "grant_id": None,
            "plan_hash": "",
        }
        plan["plan_hash"] = _hash({key: value for key, value in plan.items() if key not in {"plan_hash", "grant_id"}})
        with self._lock:
            state = self._load()
            if plan["state"] == "ready":
                self._evaluate(plan, created_at, None)
                self._issue_grant(state, plan, created_at)
            state["plans"][plan["plan_id"]] = plan
            self._save(state)
        return self._public(plan)

    def _evaluate(self, plan: dict[str, Any], at: int, approval_hash: str | None) -> None:
        registry = create_capability_registry()
        evaluations = []
        for step in plan["steps"]:
            if step["approval_required"]:
                tool_name = "desktop_mutate_app"
            elif step["operation"] == "open_app":
                tool_name = "desktop_open_app"
            elif step["operation"] in WRITE_OPERATIONS:
                tool_name = "desktop_mutate_local"
            else:
                tool_name = "desktop_read_app"
            request = create_tool_call_request(
                mission_id=plan["plan_id"], mission_run_id=plan["plan_id"], step_id=step["step_id"],
                tool_name=tool_name, requested_by="aion_pilot", payload=step,
                approved_payload_hash=_hash(step) if step["approval_required"] else None,
                approval_hash=approval_hash if step["approval_required"] else None,
                approval_expires_at=at + 300 if step["approval_required"] else None,
            )
            evaluation = evaluate_tool_call(registry=registry, request=request, evaluation_time=at, caller="aion_pilot")
            if not evaluation["allowed"]:
                raise PermissionError("computer_plan_gateway_blocked:" + ",".join(evaluation["reasons"]))
            evaluations.append(evaluation)
        plan["gateway_evaluations"] = evaluations

    def approve_plan(self, *, plan_id: str, approved_step_ids: list[str], approved_by: str,
                     now: int | None = None) -> dict[str, Any]:
        approved_at = int(now if now is not None else time.time())
        with self._lock:
            state = self._load()
            plan = state["plans"].get(plan_id)
            if not isinstance(plan, dict):
                raise KeyError("computer_plan_not_found")
            expected = set(plan.get("approval_step_ids") or [])
            supplied = {str(value) for value in approved_step_ids}
            if supplied != expected:
                raise ValueError("exact_computer_step_approval_required")
            approval = {"plan_id": plan_id, "plan_hash": plan["plan_hash"], "approved_step_ids": sorted(supplied),
                        "approved_by": str(approved_by or "business_owner"), "approved_at": approved_at}
            approval_hash = _hash(approval)
            self._evaluate(plan, approved_at, approval_hash)
            plan.update({"state": "ready", "approved_at": approved_at, "approval_hash": approval_hash,
                         "approved_by": approval["approved_by"]})
            self._issue_grant(state, plan, approved_at)
            state["plans"][plan_id] = plan
            self._save(state)
            return self._public(plan)

    def redeem_grant(self, *, grant_id: str, execution_token: str, now: int | None = None) -> dict[str, Any]:
        redeemed_at = int(now if now is not None else time.time())
        with self._lock:
            state = self._load()
            grant = state["grants"].get(grant_id)
            if not isinstance(grant, dict):
                raise KeyError("computer_grant_not_found")
            if grant.get("redeemed_at") is not None:
                raise PermissionError("computer_grant_already_redeemed")
            if redeemed_at > int(grant.get("expires_at") or 0):
                raise PermissionError("computer_grant_expired")
            if not secrets.compare_digest(str(grant.get("token_hash") or ""), _hash(execution_token)):
                raise PermissionError("computer_grant_token_invalid")
            plan = state["plans"].get(grant["plan_id"])
            if not isinstance(plan, dict) or plan.get("state") != "ready":
                raise PermissionError("computer_plan_not_ready")
            grant["redeemed_at"] = redeemed_at
            plan["state"] = "executing"
            state["grants"][grant_id] = grant
            state["plans"][plan["plan_id"]] = plan
            self._save(state)
            return {"ok": True, "grant_id": grant_id, "plan_id": plan["plan_id"], "plan_hash": plan["plan_hash"],
                    "objective": plan["objective"], "steps": deepcopy(plan["steps"]),
                    "approved_step_ids": deepcopy(plan.get("approval_step_ids") or []),
                    "approval_payload_hash": plan.get("approval_hash") or "read_only_grant"}

    def record_receipt(self, *, grant_id: str, result: Mapping[str, Any], now: int | None = None) -> dict[str, Any]:
        completed_at = int(now if now is not None else time.time())
        with self._lock:
            state = self._load()
            grant = state["grants"].get(grant_id)
            if not isinstance(grant, dict) or grant.get("redeemed_at") is None:
                raise PermissionError("computer_grant_not_redeemed")
            plan = state["plans"].get(grant["plan_id"])
            if not isinstance(plan, dict):
                raise KeyError("computer_plan_not_found")
            envelopes = [create_capability_receipt(evaluation=evaluation, provider_response=dict(result),
                                                   evidence_hashes=[_hash(result)], rollback_available=False)
                         for evaluation in plan.get("gateway_evaluations") or []]
            receipt = {"schema_version": "aion.computer_execution_receipt.v1",
                       "receipt_id": "computer_receipt_" + uuid4().hex, "grant_id": grant_id,
                       "plan_id": plan["plan_id"], "plan_hash": plan["plan_hash"], "provider": plan["provider"],
                       "model": plan["model"], "provider_neutral": True, "completed_at": completed_at,
                       "ok": bool(result.get("ok")), "status": str(result.get("status") or "unknown"),
                       "result": deepcopy(dict(result)), "gateway_receipts": envelopes, "receipt_hash": ""}
            receipt["receipt_hash"] = _hash({key: value for key, value in receipt.items() if key != "receipt_hash"})
            state["receipts"][receipt["receipt_id"]] = receipt
            plan["state"] = "completed" if receipt["ok"] else "failed"
            plan["receipt_id"] = receipt["receipt_id"]
            state["plans"][plan["plan_id"]] = plan
            self._save(state)
            return deepcopy(receipt)

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._lock:
            plan = self._load()["plans"].get(plan_id)
            return self._public(plan) if isinstance(plan, dict) else None
