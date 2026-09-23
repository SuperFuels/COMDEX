from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
from datetime import datetime, timezone

from .contracts_workflow_glyph import (
    WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION,
    WORKFLOW_SAVE_SCHEMA_VERSION,
    assert_safe_workflow_glyph,
)
from .workflow_glyph_compiler import build_canvas_layout, compile_workflow_graph_to_glyph


SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _safe_id(value: str, fallback: str) -> str:
    raw = str(value or fallback).strip() or fallback
    return SAFE_ID_RE.sub("-", raw).strip("-") or fallback


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WorkflowGlyphRepository:
    def __init__(self, runtime_root: Path | str = ".runtime/local_node") -> None:
        self.runtime_root = Path(runtime_root)

    def workflow_dir(self, business_container: str) -> Path:
        safe_business = _safe_id(business_container, "costa-conexion")
        return self.runtime_root / safe_business / "aion_workflows"

    def workflow_path(self, business_container: str, workflow_id: str) -> Path:
        safe_workflow_id = _safe_id(workflow_id, "workflow_draft_1")
        return self.workflow_dir(business_container) / f"{safe_workflow_id}.json"

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        workflow = payload.get("workflow") or {}
        compiled_glyph = payload.get("compiled_glyph") or {}
        graph = payload.get("graph") or {}

        business_container = (
            payload.get("business_container")
            or workflow.get("business_container")
            or compiled_glyph.get("workflow", {}).get("business_container")
            or "costa-conexion"
        )

        workflow_id = (
            payload.get("workflow_id")
            or workflow.get("workflow_id")
            or compiled_glyph.get("workflow", {}).get("workflow_id")
            or "workflow_draft_1"
        )

        now = utc_now_iso()

        if not compiled_glyph:
            compiled_glyph = compile_workflow_graph_to_glyph({
                **payload,
                "business_container": business_container,
                "workflow_id": workflow_id,
                "graph": graph,
            })

        assert_safe_workflow_glyph(compiled_glyph)

        canvas_layout = payload.get("canvas_layout")
        if not isinstance(canvas_layout, dict):
            canvas_layout = build_canvas_layout(graph)

        if canvas_layout.get("schema_version") != WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION:
            canvas_layout["schema_version"] = WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION
        canvas_layout.setdefault("coordinate_space", "absolute_canvas_px")

        record = {
            "schema_version": WORKFLOW_SAVE_SCHEMA_VERSION,
            "storage_scope": "business_container",
            "business_container": _safe_id(business_container, "costa-conexion"),
            "workflow_id": _safe_id(workflow_id, "workflow_draft_1"),
            "name": payload.get("name") or workflow.get("name") or compiled_glyph.get("workflow", {}).get("name") or "Untitled workflow 1",
            "status": payload.get("status") or workflow.get("status") or compiled_glyph.get("workflow", {}).get("status") or "draft",
            "graph": graph,
            "canvas_layout": canvas_layout,
            "compiled_glyph": compiled_glyph,
            "created_at": payload.get("created_at") or now,
            "updated_at": now,
        }

        path = self.workflow_path(record["business_container"], record["workflow_id"])
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

        return {
            "ok": True,
            "workflow_id": record["workflow_id"],
            "business_container": record["business_container"],
            "path": str(path),
            "updated_at": record["updated_at"],
        }

    def load(self, business_container: str, workflow_id: str) -> dict[str, Any] | None:
        path = self.workflow_path(business_container, workflow_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
