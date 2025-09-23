# backend/modules/lean/lean_report.py
"""
Lean Report Generator
─────────────────────────────────────────────
Render container injection/export reports in Markdown or JSON.

Goals:
• Single-source: both CLI + API call here.
• Always embed validation_errors + audit metadata.
• Support Markdown (human-readable) + JSON (machine-readable).
• Extensible: add HTML / rich later.

Usage:
    from backend.modules.lean.lean_report import render_report, save_report
"""

import json
import time
from typing import Any, Dict, List, Optional

from backend.modules.lean.lean_audit import (
    build_inject_event,
    build_export_event,
)


# ──────────────────────────────
# Internal helpers
# ──────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _short_preview(items: List[Any], max_items: int = 5) -> List[str]:
    """
    Truncate items into previews for reports.
    """
    previews: List[str] = []
    for i, it in enumerate(items):
        if i >= max_items:
            previews.append("…")
            break
        if isinstance(it, dict):
            previews.append(json.dumps(it, ensure_ascii=False)[:80])
        else:
            previews.append(str(it)[:80])
    return previews


# ──────────────────────────────
# Report rendering
# ──────────────────────────────

def render_report(
    container: Dict[str, Any],
    *,
    fmt: str = "md",
    kind: str = "lean.inject",
    container_path: Optional[str] = None,
    container_id: Optional[str] = None,
    lean_path: Optional[str] = None,
    validation_errors: Optional[List[Dict[str, Any]]] = None,
    origin: str = "CLI",
) -> str:
    """
    Render a container report in the requested format.

    Args:
        container: dict with core data (glyphs/logic/trees/etc.).
        fmt: "md" or "json".
        kind: "lean.inject" | "lean.export".
        validation_errors: structured errors, embedded in report.
    """
    glyphs = container.get("glyphs", [])
    num_items = len(glyphs) if isinstance(glyphs, list) else 1
    previews = _short_preview(glyphs)

    # Build a synthetic audit event to include in the report
    if kind == "lean.inject":
        audit_evt = build_inject_event(
            container_path=container_path or "?",
            container_id=container_id,
            lean_path=lean_path or "?",
            num_items=num_items,
            previews=previews,
            validation_errors=validation_errors,
            origin=origin,
        )
    else:
        audit_evt = build_export_event(
            out_path=container_path,
            container_id=container_id,
            container_type=container.get("engine"),
            lean_path=lean_path or "?",
            num_items=num_items,
            previews=previews,
            validation_errors=validation_errors,
            origin=origin,
        )

    # ── JSON Report ──────────────────────────
    if fmt == "json":
        return json.dumps(
            {
                "report_version": "v1",
                "kind": kind,
                "audit": audit_evt,
                "container": container,
            },
            ensure_ascii=False,
            indent=2,
        )

    # ── Markdown Report ──────────────────────
    elif fmt == "md":
        lines: List[str] = []
        lines.append(f"# Lean Report ({kind})")
        lines.append("")
        lines.append(f"- Generated: {_now_iso()}")
        lines.append(f"- Origin: {origin}")
        lines.append("")
        lines.append("## Audit Metadata")
        for k, v in audit_evt.items():
            if k in ("previews", "validation_errors"):
                continue
            lines.append(f"- **{k}**: {v}")
        lines.append("")
        lines.append("### Previews")
        for p in previews:
            lines.append(f"- `{p}`")
        lines.append("")
        lines.append("### Validation Errors")
        if validation_errors:
            for e in validation_errors:
                code = e.get("code", "?")
                msg = e.get("message", "")
                lines.append(f"- `{code}` {msg}")
        else:
            lines.append("- None ✅")
        lines.append("")
        lines.append("## Container Snapshot")
        lines.append("```json")
        lines.append(json.dumps(container, ensure_ascii=False, indent=2))
        lines.append("```")
        return "\n".join(lines)

    else:
        raise ValueError(f"Unsupported report format: {fmt}")


def save_report(
    container: Dict[str, Any],
    path: str,
    *,
    fmt: str = "md",
    kind: str = "lean.inject",
    container_path: Optional[str] = None,
    container_id: Optional[str] = None,
    lean_path: Optional[str] = None,
    validation_errors: Optional[List[Dict[str, Any]]] = None,
    origin: str = "CLI",
) -> None:
    """
    Save a rendered report to disk.
    """
    content = render_report(
        container,
        fmt=fmt,
        kind=kind,
        container_path=container_path,
        container_id=container_id,
        lean_path=lean_path,
        validation_errors=validation_errors,
        origin=origin,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)