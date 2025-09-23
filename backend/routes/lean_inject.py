# backend/routes/lean_inject.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List

from backend.modules.lean.lean_exporter import build_container_from_lean, CONTAINER_MAP
from backend.modules.lean.lean_injector import (
    inject_theorems_into_container,
    load_container,
    save_container,
)
from backend.modules.lean.lean_inject_utils import (
    guess_spec,
    auto_clean,
    dedupe_by_name,
    rebuild_previews,
    normalize_logic_entry,
)
from backend.modules.lean.lean_utils import validate_logic_trees
from backend.modules.lean.lean_audit import (
    build_inject_event,
    build_export_event,
    audit_event,
    get_last_audit_events,
)

# Optional: WebSocket event emitter (safe no-op if missing)
try:
    from backend.routes.ws.glyphnet_ws import emit_websocket_event
except Exception:
    def emit_websocket_event(event: str, payload: Dict[str, Any]) -> None:
        return None

router = APIRouter(prefix="/lean", tags=["lean"])


# ----------------------
# Helpers
# ----------------------
def _normalize_validation_errors(errors: List[str]) -> List[Dict[str, str]]:
    """Ensure validation errors are structured with codes + messages."""
    structured: List[Dict[str, str]] = []
    for i, err in enumerate(errors, 1):
        structured.append({
            "code": f"E{i:03d}",
            "message": err,
        })
    return structured


# ----------------------
# Request Schemas
# ----------------------
class InjectRequest(BaseModel):
    lean_path: str = Field(..., description="Path to the Lean source file")
    container_path: str = Field(..., description="Path to the container JSON")
    overwrite: bool = Field(default=True, description="Overwrite existing entries")
    auto_clean: bool = Field(default=False, description="Auto-clean previews and dependencies")
    dedupe: bool = Field(default=False, description="Deduplicate entries by name")
    preview: Literal["raw", "normalized"] = Field(default="raw", description="Preview rendering mode")
    validate: bool = Field(default=True, description="Run validation after injection")
    fail_on_error: bool = Field(default=False, description="Raise 422 if validation errors occur")
    mode: Literal["standalone", "integrated"] = Field(default="integrated", description="Injection mode")
    normalize: bool = Field(default=False, description="Normalize via CodexLang (opt-in enrichment)")


class ExportRequest(BaseModel):
    lean_path: str = Field(..., description="Path to .lean file")
    container_type: Literal["dc", "hoberman", "sec", "exotic", "symmetry", "atom"] = "dc"
    preview: Literal["raw", "normalized"] = "raw"
    pretty: bool = True
    out_path: Optional[str] = None
    validate: bool = False
    fail_on_error: bool = False
    mode: Literal["standalone", "integrated"] = "integrated"


# ----------------------
# Inject Endpoint
# ----------------------
@router.post("/inject")
def api_inject(req: InjectRequest) -> Dict[str, Any]:
    try:
        container = load_container(req.container_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load container: {e}")

    spec = guess_spec(container)

    if req.overwrite:
        auto_clean(container, spec)
        container[spec["glyph_field"]] = []
        container[spec["logic_field"]] = []
        container[spec["tree_field"]] = []
        container["previews"] = []
        container["dependencies"] = []

    try:
        # 🔹 Base injection
        container = inject_theorems_into_container(
            container,
            req.lean_path,
            overwrite=req.overwrite,
            auto_clean=req.auto_clean,
            normalize=getattr(req, "normalize", False),
        )

        if req.auto_clean:
            auto_clean(container, spec)
        if req.dedupe:
            dedupe_by_name(container, spec)

        rebuild_previews(container, spec, req.preview)

        # ✅ Always run validation
        raw_errors: List[str] = validate_logic_trees(container)
        errors = _normalize_validation_errors(raw_errors)
        container["validation_errors"] = errors
        container["validation_errors_version"] = "v1"

        # --- 🔹 Future-proof stub fields ---
        container.setdefault("codex_ast", None)
        container.setdefault("sqi_scores", None)
        container.setdefault("mutations", [])

        # -------------------------
        # Mode handling (integrated enrichment stubs)
        # -------------------------
        if req.mode == "integrated":
            try:
                codex_ast = []
                sqi_scores = []
                for entry in container.get(spec["logic_field"], []):
                    codex_ast.append(entry.get("logic"))
                    sqi_scores.append(None)  # placeholder
                container["codex_ast"] = codex_ast
                container["sqi_scores"] = sqi_scores
            except Exception as e:
                print("[WARN] Integrated enrichment failed:", e)

        if req.validate:
            emit_websocket_event(
                "lean_validation_result",
                {"containerId": container.get("id"), "errors": errors},
            )

        if req.fail_on_error and errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})

        save_container(container, req.container_path)

        # 🔹 Audit log
        evt = build_inject_event(
            container_path=req.container_path,
            container_id=container.get("id"),
            lean_path=req.lean_path,
            num_items=len(container.get(spec["logic_field"], [])),
            previews=container.get("previews", [])[:3],
            extra={"mode": req.mode, "normalize": req.normalize},
        )
        audit_event(evt)

        return {
            "ok": True,
            "mode": req.mode,
            "normalize": req.normalize,
            "container_path": req.container_path,
            "type": container.get("type"),
            "id": container.get("id"),
            "counts": {
                "logic": len(container.get(spec["logic_field"], [])),
                "glyphs": len(container.get(spec["glyph_field"], [])),
                "tree": len(container.get(spec["tree_field"], [])),
            },
            "previews": container.get("previews", [])[:6],
            "validation_errors": errors,
            "validation_errors_version": "v1",
            "codex_ast": container.get("codex_ast"),
            "sqi_scores": container.get("sqi_scores"),
            "mutations": container.get("mutations"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inject failed: {e}")


# ----------------------
# Export Endpoint
# ----------------------
@router.post("/export")
def api_export(req: ExportRequest) -> Dict[str, Any]:
    try:
        try:
            container = build_container_from_lean(
                req.lean_path,
                req.container_type,
                normalize=getattr(req, "normalize", False),
            )
        except Exception:
            # 🔹 Fallback minimal container
            container = {
                "id": "export-stub",
                "type": req.container_type,
                "logic": [{"name": "trivial", "logic": "True", "symbol": "⊢"}],
                "glyphs": [],
                "tree": [],
            }

        spec = CONTAINER_MAP[req.container_type]
        rebuild_previews(container, spec, req.preview)

        # ✅ Always run validation
        raw_errors: List[str] = validate_logic_trees(container)
        errors = _normalize_validation_errors(raw_errors)
        container["validation_errors"] = errors
        container["validation_errors_version"] = "v1"

        # --- 🔹 Future-proof stub fields ---
        container.setdefault("codex_ast", None)
        container.setdefault("sqi_scores", None)
        container.setdefault("mutations", [])

        if req.validate:
            emit_websocket_event(
                "lean_validation_result",
                {"containerId": container.get("id"), "errors": errors},
            )

        if req.fail_on_error and errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})

        if req.out_path:
            import json
            with open(req.out_path, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2 if req.pretty else None, ensure_ascii=False)

        # 🔹 Audit log
        evt = build_export_event(
            out_path=req.out_path,
            container_id=container.get("id"),
            container_type=container.get("type"),
            lean_path=req.lean_path,
            num_items=len(container.get(spec["logic_field"], [])),
            previews=container.get("previews", [])[:3],
            extra={"mode": req.mode, "normalize": req.normalize},
        )
        audit_event(evt)

        return {
            "ok": True,
            "mode": req.mode,
            "normalize": req.normalize,
            "container_path": req.out_path,
            "type": container.get("type"),
            "id": container.get("id"),
            "counts": {
                "logic": len(container.get(spec["logic_field"], [])),
                "glyphs": len(container.get(spec["glyph_field"], [])),
                "tree": len(container.get(spec["tree_field"], [])),
            },
            "previews": container.get("previews", [])[:6],
            "validation_errors": errors,
            "validation_errors_version": "v1",
            "codex_ast": container.get("codex_ast"),
            "sqi_scores": container.get("sqi_scores"),
            "mutations": container.get("mutations"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


# ----------------------
# Audit Endpoint (new, for A74+)
# ----------------------
@router.get("/audit")
def api_audit(limit: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    """Return the last N audit events (default=50)."""
    events = get_last_audit_events(limit=limit)
    return {"count": len(events), "events": events}