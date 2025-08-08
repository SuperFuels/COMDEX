# backend/routes/lean_inject.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any

from backend.modules.lean.lean_injector import (
    inject_theorems_into_container,
    load_container,
    save_container,
)
from backend.modules.lean.lean_exporter import build_container_from_lean
from backend.modules.lean.lean_inject_cli import CONTAINER_MAP  # reuse spec

router = APIRouter(prefix="/lean", tags=["lean"])

class InjectRequest(BaseModel):
    container_path: str = Field(..., description="Path to existing container JSON")
    lean_path: str = Field(..., description="Path to .lean file")
    overwrite: bool = False
    auto_clean: bool = True
    dedupe: bool = True
    preview: Literal["raw", "normalized"] = "raw"
    validate: bool = False

class ExportRequest(BaseModel):
    lean_path: str = Field(..., description="Path to .lean file")
    container_type: Literal["dc","hoberman","sec","exotic","symmetry","atom"] = "dc"
    preview: Literal["raw","normalized"] = "raw"
    pretty: bool = True
    out_path: Optional[str] = None

@router.post("/inject")
def api_inject(req: InjectRequest) -> Dict[str, Any]:
    try:
        container = load_container(req.container_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load container: {e}")

    # overwrite / cleanup
    from backend.modules.lean.lean_inject_cli import _guess_spec, _auto_clean, _dedupe_by_name, _rebuild_previews
    spec = _guess_spec(container)

    if req.overwrite:
        _auto_clean(container, spec)
        container[spec["glyph_field"]] = []
        container[spec["logic_field"]] = []
        container[spec["tree_field"]] = []
        container["previews"] = []
        container["dependencies"] = []

    try:
        container = inject_theorems_into_container(container, req.lean_path)
        if req.auto_clean:
            _auto_clean(container, spec)
        if req.dedupe:
            _dedupe_by_name(container, spec)

        _rebuild_previews(container, spec, req.preview)

        save_container(container, req.container_path)
        return {
            "ok": True,
            "container_path": req.container_path,
            "type": container.get("type"),
            "id": container.get("id"),
            "counts": {
                "logic": len(container.get(spec["logic_field"], [])),
                "glyphs": len(container.get(spec["glyph_field"], [])),
                "tree": len(container.get(spec["tree_field"], [])),
            },
            "previews": container.get("previews", [])[:6],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inject failed: {e}")

@router.post("/export")
def api_export(req: ExportRequest) -> Dict[str, Any]:
    try:
        container = build_container_from_lean(req.lean_path, req.container_type)

        # rebuild previews to honor selection
        from backend.modules.lean.lean_inject_cli import _rebuild_previews
        spec = CONTAINER_MAP[req.container_type]
        _rebuild_previews(container, spec, req.preview)

        if req.out_path:
            import json
            with open(req.out_path, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2 if req.pretty else None, ensure_ascii=False)

        return {
            "ok": True,
            "written": bool(req.out_path),
            "out_path": req.out_path,
            "type": container.get("type"),
            "id": container.get("id"),
            "counts": {
                "logic": len(container.get(spec["logic_field"], [])),
                "glyphs": len(container.get(spec["glyph_field"], [])),
                "tree": len(container.get(spec["tree_field"], [])),
            },
            "previews": container.get("previews", [])[:6],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")