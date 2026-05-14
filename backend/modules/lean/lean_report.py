# backend/modules/lean/lean_report.py
"""
Lean Report Generator
─────────────────────────────────────────────
Render container injection/export reports in Markdown, JSON, or (stub) HTML.

Fixes:
- No broken imports (no lean_to_expr / convert_lean_to_codexlang / symatics rewriter).
- Does NOT mutate the container in-place.
- Counts + previews come from actual logic entries when available.
- Always includes validation_errors + audit metadata.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.lean.lean_audit import build_inject_event, build_export_event


# ──────────────────────────────
# Internal helpers
# ──────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_validation_errors(errors: Any) -> List[Dict[str, str]]:
    """
    Ensure validation_errors are structured dicts with codes/messages.
    Backward compatible: if list of strings, wrap them.
    """
    out: List[Dict[str, str]] = []
    if isinstance(errors, list):
        for e in errors:
            if isinstance(e, dict):
                code = str(e.get("code", "E000"))
                msg = str(e.get("message", e))
                out.append({"code": code, "message": msg})
            else:
                out.append({"code": "E000", "message": str(e)})
    return out


def _pick_logic_field(container: Dict[str, Any]) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Prefer the real logic entries over glyph strings.
    """
    for fld in (
        "symbolic_logic",
        "expanded_logic",
        "hoberman_logic",
        "exotic_logic",
        "symmetric_logic",
        "axioms",
    ):
        v = container.get(fld)
        if isinstance(v, list) and v:
            # keep only dict entries; ignore stray strings
            return fld, [x for x in v if isinstance(x, dict)]
    return None, []


def _logic_preview(e: Dict[str, Any]) -> str:
    """
    Prefer normalized if present, else raw/logic.
    """
    codex = e.get("codexlang") or {}
    s = (
        (codex.get("normalized") if isinstance(codex, dict) else None)
        or e.get("logic_normalized")
        or e.get("logic")
        or e.get("logic_raw")
        or ""
    )
    return str(s).replace("\n", " ")[:220]


def _attach_report_normalized_logic(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Non-destructive: shallow-copy entries and populate logic_normalized
    from codexlang.normalized if available.
    """
    out: List[Dict[str, Any]] = []
    for e in entries:
        ee = dict(e)
        codex = ee.get("codexlang") if isinstance(ee.get("codexlang"), dict) else {}
        ee["logic_normalized"] = (
            (codex or {}).get("normalized")
            or ee.get("logic")
            or ee.get("logic_raw")
            or ""
        )
        out.append(ee)
    return out


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

    fmt: "md" | "json" | "html" (html = stub).
    kind: "lean.inject" | "lean.export".
    """
    v_errors = _normalize_validation_errors(validation_errors or container.get("validation_errors", []))

    logic_field, entries = _pick_logic_field(container)
    safe_entries = _attach_report_normalized_logic(entries)

    # item count + previews: logic entries preferred
    if safe_entries:
        num_items = len(safe_entries)
        previews: List[str] = []
        for e in safe_entries[:6]:
            sym = e.get("symbol", "⟦ ? ⟧")
            name = e.get("name", "unknown")
            previews.append(f"{sym} | {name} : {_logic_preview(e)}")
        if len(safe_entries) > 6:
            previews.append("...")
    else:
        # fallback: container previews, else glyphs, else none
        previews = []
        if isinstance(container.get("previews"), list) and container["previews"]:
            previews = [str(x)[:220] for x in container["previews"][:6]]
            if len(container["previews"]) > 6:
                previews.append("...")
            num_items = len(container["previews"])
        else:
            glyphs = container.get("glyphs")
            if isinstance(glyphs, list) and glyphs:
                previews = [str(x)[:220] for x in glyphs[:6]]
                if len(glyphs) > 6:
                    previews.append("...")
                num_items = len(glyphs)
            else:
                num_items = 0

    # audit metadata (always included)
    if kind == "lean.inject":
        audit_evt = build_inject_event(
            container_path=container_path or "?",
            container_id=container_id or container.get("id"),
            lean_path=lean_path or "?",
            num_items=num_items,
            previews=previews,
            validation_errors=v_errors,
            origin=origin,
        )
    else:
        audit_evt = build_export_event(
            out_path=container_path,
            container_id=container_id or container.get("id"),
            container_type=container.get("type"),
            lean_path=lean_path or "?",
            num_items=num_items,
            previews=previews,
            validation_errors=v_errors,
            origin=origin,
        )

    if fmt == "json":
        payload = {
            "report_version": "v1",
            "kind": kind,
            "generated_at": _now_iso(),
            "audit": audit_evt,
            "container_meta": {
                "type": container.get("type"),
                "id": container.get("id"),
                "logic_field": logic_field,
                "count": num_items,
            },
            "previews": previews,
            "validation_errors": v_errors,
            "validation_errors_version": "v1",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if fmt == "md":
        lines: List[str] = []
        lines.append(f"# Lean Report ({kind})")
        lines.append("")
        lines.append(f"- Generated: {_now_iso()}")
        lines.append(f"- Origin: {origin}")
        lines.append(f"- Container: `{container.get('id')}`  ({container.get('type')})")
        if logic_field:
            lines.append(f"- Logic field: `{logic_field}`  (count: {num_items})")
        else:
            lines.append(f"- Logic field: `(none)`  (fallback previews)")
        lines.append("")

        lines.append("## Audit Metadata")
        for k, v in audit_evt.items():
            if k in ("previews", "validation_errors"):
                continue
            lines.append(f"- **{k}**: {v}")
        lines.append("")

        lines.append("### Previews")
        if previews:
            for p in previews:
                lines.append(f"- `{p}`")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.append("### Validation Errors")
        if v_errors:
            for e in v_errors:
                lines.append(f"- `{e.get('code','?')}` {e.get('message','')}")
        else:
            lines.append("- None ✅")

        return "\n".join(lines)

    if fmt == "html":
        return (
            "<html><body><h1>Lean Report (HTML)</h1>"
            "<p>Stub only - full HTML/Mermaid/PNG support comes in Stage B.</p>"
            "</body></html>"
        )

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