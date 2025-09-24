# backend/routes/lean_inject_api.py

import os
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from fastapi.responses import JSONResponse
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from backend.modules.lean.lean_injector import load_container, save_container, inject_theorems_into_container
from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors
from backend.modules.lean.lean_audit import audit_event, build_inject_event, build_export_event, get_last_audit_events
from backend.modules.lean.lean_exporter import build_container_from_lean, CONTAINER_MAP
from backend.modules.lean.lean_inject_utils import guess_spec, auto_clean, dedupe_by_name, rebuild_previews, normalize_logic_entry

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

def _integrated_hooks(container: dict) -> None:
    """Extra processing in integrated mode (Codex/SQI)."""
    # TODO: plug in CodexLangRewriter, SQI scoring, registry, mutation hooks
    print("[ℹ️] Integrated mode: Codex/SQI hooks would run here.")


from fastapi import Request
from fastapi.responses import PlainTextResponse, FileResponse
from backend.modules.lean.lean_proofviz import mermaid_for_dependencies, png_for_dependencies
from backend.modules.lean.lean_report import render_report

# Optional: WebSocket emitter (safe no-op fallback)
try:
    from backend.routes.ws.glyphnet_ws import emit_websocket_event
except Exception:
    def emit_websocket_event(event: str, payload: dict) -> None:
        return None


@router.post("/inject")
async def inject(
    request: Request,
    container_path: str = Form(...),
    overwrite: bool = Form(False),
    dedupe: bool = Form(False),
    auto_clean: bool = Form(True),
    validate: bool = Form(True),
    fail_on_error: bool = Form(False),
    preview: Optional[str] = Form(None),  # "raw" | "normalized"
    mode: str = Form("integrated"),       # "integrated" | "standalone"
    log_audit: bool = Form(False),
    ghx_out: Optional[str] = Form(None),
    ghx_bundle: Optional[str] = Form(None),
    lean_file: UploadFile = File(...),
):
    """
    Upload a .lean file + mutate an existing container.
    Features:
    - Multipart upload (container_path + .lean file).
    - Overwrite, dedupe, auto_clean, preview.
    - Validation with structured errors.
    - Fail-on-error returns HTTP 422 with validation_errors.
    - Integrated mode stubs: codex_ast, sqi_scores, mutations.
    - GHX packet dumping (optional).
    - Audit logging (optional).
    - Extra preview endpoints (?preview=mermaid|png).
    - Report rendering (?report=md|json).
    - WebSocket emit for validation.
    """
    try:
        # 1) Save upload to tmp
        tmp_dir = "tmp/lean_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_lean_path = os.path.join(tmp_dir, lean_file.filename or "upload.lean")
        with open(tmp_lean_path, "wb") as f:
            f.write(await lean_file.read())

        # 2) Load container + inject
        before = load_container(container_path)
        after = inject_theorems_into_container(before, tmp_lean_path)

        # --- overwrite / dedupe ---
        logic_field = next((f for f in (
            "symbolic_logic", "expanded_logic", "hoberman_logic",
            "exotic_logic", "symmetric_logic", "axioms", "logic"
        ) if f in after), None)

        if overwrite and logic_field:
            by_name = {it.get("name"): it for it in after.get(logic_field, [])}
            after[logic_field] = list(by_name.values())

        if dedupe and logic_field:
            seen, unique = set(), []
            for it in after.get(logic_field, []):
                sig = (it.get("name"), it.get("symbol"), it.get("logic_raw") or it.get("logic"))
                if sig not in seen:
                    seen.add(sig)
                    unique.append(it)
            after[logic_field] = unique

        # --- preview list (raw/normalized) ---
        if preview and logic_field:
            previews: List[str] = []
            for it in after.get(logic_field, []):
                name = it.get("name", "unknown")
                sym = it.get("symbol", "⟦ ? ⟧")
                if preview == "raw":
                    logic_str = it.get("logic_raw") or it.get("codexlang", {}).get("logic") or it.get("logic") or "???"
                else:
                    logic_str = it.get("logic") or it.get("logic_raw") or it.get("codexlang", {}).get("logic") or "???"
                label = "Define" if "Definition" in sym else "Prove"
                previews.append(f"{sym} | {name} : {logic_str} → {label} ⟧")
            after["previews"] = previews

        if auto_clean:
            for key in ("glyphs", "previews"):
                if key in after and isinstance(after[key], list):
                    after[key] = list(dict.fromkeys(after[key]))
            if "dependencies" in after and not after["dependencies"]:
                del after["dependencies"]

        # 3) Validation
        raw_errors: List = validate_logic_trees(after)
        errors = normalize_validation_errors(raw_errors)
        after["validation_errors"] = errors
        after["validation_errors_version"] = "v1"

        # --- structured errors for compatibility ---
        structured_errors = [
            {"code": f"E{i+1:03d}", "message": e.get("message", str(e))}
            if isinstance(e, dict) else {"code": f"E{i+1:03d}", "message": str(e)}
            for i, e in enumerate(errors)
        ]
        after["validation_errors"] = structured_errors

        if validate:
            emit_websocket_event(
                "lean_validation_result",
                {"containerId": after.get("id"), "errors": structured_errors},
            )

        if fail_on_error and structured_errors:
            raise HTTPException(status_code=422, detail={"validation_errors": structured_errors})

        # 4) Mode-specific fields
        after.setdefault("codex_ast", None)
        after.setdefault("sqi_scores", None)
        after.setdefault("mutations", [])
        if mode == "integrated" and logic_field:
            try:
                codex_ast = []
                sqi_scores = []
                for entry in after.get(logic_field, []):
                    codex_ast.append(entry.get("logic"))
                    sqi_scores.append(None)
                after["codex_ast"] = codex_ast
                after["sqi_scores"] = sqi_scores
            except Exception as e:
                print("[WARN] Integrated enrichment failed:", e)
        else:
            print("[ℹ️] Standalone mode: skipping Codex/SQI integration.")

        # 5) Preview overrides via query (?preview=mermaid|png)
        qp_preview = request.query_params.get("preview")
        if qp_preview == "mermaid":
            mmd = mermaid_for_dependencies(after)
            return PlainTextResponse(mmd, media_type="text/plain")
        elif qp_preview == "png":
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.close()
            ok, msg = png_for_dependencies(after, tmp.name)
            if ok:
                return FileResponse(tmp.name, media_type="image/png", filename="preview.png")
            else:
                return PlainTextResponse(f"⚠️ PNG generation failed: {msg}", media_type="text/plain")

        # 6) Report mode via query (?report=md|json)
        report_fmt = request.query_params.get("report") if request else None
        if report_fmt in ("md", "json"):
            report = render_report(
                after,
                fmt=report_fmt,
                kind="lean.inject",
                container_path=container_path,
                container_id=after.get("id"),
                lean_path=tmp_lean_path,
                validation_errors=structured_errors,
                origin="API",
            )
            media_type = "application/json" if report_fmt == "json" else "text/markdown"
            return PlainTextResponse(report, media_type=media_type)

        # 7) Save + Audit + GHX
        save_container(after, container_path)

        if log_audit:
            try:
                audit_event(build_inject_event(
                    container_path=container_path,
                    container_id=after.get("id"),
                    lean_path=tmp_lean_path,
                    num_items=len(after.get(logic_field, [])) if logic_field else 0,
                    previews=after.get("previews", []),
                    extra={"overwrite": overwrite, "dedupe": dedupe, "auto_clean": auto_clean, "mode": mode},
                ))
                print("[📝] Audit event logged")
            except Exception as e:
                print(f"[⚠️] Audit logging failed: {e}")

        if ghx_out:
            try:
                from backend.modules.lean.lean_ghx import dump_packets
                dump_packets(after, ghx_out)
                print(f"[📦] Wrote GHX packets → {ghx_out}")
            except Exception as e:
                print(f"[⚠️] GHX packet dump failed: {e}")

        if ghx_bundle:
            try:
                from backend.modules.lean.lean_ghx import bundle_packets
                bundle_packets(after, ghx_bundle)
                print(f"[📦] Wrote GHX bundle → {ghx_bundle}")
            except Exception as e:
                print(f"[⚠️] GHX bundle failed: {e}")

        # 8) Response (JSON)
        return {
            "ok": True,
            "container": {"type": after.get("type"), "id": after.get("id"), "path": container_path},
            "counts": {"entries": len(after.get(logic_field or "symbolic_logic", []))},
            "previews": after.get("previews", [])[:6],
            "validation_errors": structured_errors,
            "mode": mode,
            "codex_ast": after.get("codex_ast"),
            "sqi_scores": after.get("sqi_scores"),
            "mutations": after.get("mutations"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export")
async def export_container(
    container_type: str = Form("dc"),
    validate: bool = Form(True),
    fail_on_error: bool = Form(False),
    mode: str = Form("integrated"),
    log_audit: bool = Form(False),
    ghx_out: Optional[str] = Form(None),
    ghx_bundle: Optional[str] = Form(None),
    lean_file: UploadFile = File(...),
):
    """
    Build a new container from a .lean file.

    Features:
    - Multipart upload (lean_file).
    - Builds container from Lean source.
    - Auto preview rebuild.
    - Validation with structured errors.
    - Fail-on-error returns HTTP 422 with validation_errors.
    - Integrated mode stubs: codex_ast, sqi_scores, mutations.
    - GHX packet dumping (optional).
    - Audit logging (optional).
    - JSON response with counts, previews, validation, stubs.
    """
    try:
        # 1) Save upload to tmp
        tmp_dir = "tmp/lean_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_lean_path = os.path.join(tmp_dir, lean_file.filename or "upload.lean")
        with open(tmp_lean_path, "wb") as f:
            f.write(await lean_file.read())

        # 2) Build container
        try:
            container = build_container_from_lean(tmp_lean_path, container_type)
        except Exception:
            # 🔹 Fallback minimal container
            container = {
                "id": "export-stub",
                "type": container_type,
                "logic": [{"name": "trivial", "logic": "True", "symbol": "⊢"}],
                "glyphs": [],
                "tree": [],
            }

        # --- preview rebuild (if spec available) ---
        try:
            from backend.modules.lean.lean_inject_utils import rebuild_previews, CONTAINER_MAP
            spec = CONTAINER_MAP.get(container_type)
            if spec:
                rebuild_previews(container, spec, "raw")
        except Exception as e:
            print("[WARN] Failed to rebuild previews:", e)

        # 3) Validation
        raw_errors: List[str] = validate_logic_trees(container)
        errors = normalize_validation_errors(raw_errors)
        structured_errors = [
            {"code": f"E{i+1:03d}", "message": e.get("message", str(e))}
            if isinstance(e, dict) else {"code": f"E{i+1:03d}", "message": str(e)}
            for i, e in enumerate(errors)
        ]
        container["validation_errors"] = structured_errors
        container["validation_errors_version"] = "v1"

        if validate:
            emit_websocket_event(
                "lean_validation_result",
                {"containerId": container.get("id"), "errors": structured_errors},
            )

        if fail_on_error and structured_errors:
            raise HTTPException(status_code=422, detail={"validation_errors": structured_errors})

        # 4) Mode-specific fields
        container.setdefault("codex_ast", None)
        container.setdefault("sqi_scores", None)
        container.setdefault("mutations", [])
        if mode == "integrated":
            try:
                codex_ast = []
                sqi_scores = []
                for entry in container.get("logic", []):
                    codex_ast.append(entry.get("logic"))
                    sqi_scores.append(None)
                container["codex_ast"] = codex_ast
                container["sqi_scores"] = sqi_scores
            except Exception as e:
                print("[WARN] Integrated enrichment failed:", e)
        else:
            print("[ℹ️] Standalone mode: skipping Codex/SQI integration.")

        # 5) Audit log
        if log_audit:
            try:
                audit_event(build_export_event(
                    container_type=container_type,
                    container_id=container.get("id"),
                    lean_path=tmp_lean_path,
                    num_items=len(container.get("logic", [])),
                    previews=container.get("previews", []),
                    extra={"mode": mode},
                ))
                print("[📝] Audit event logged")
            except Exception as e:
                print(f"[⚠️] Audit logging failed: {e}")

        # 6) GHX export (optional)
        if ghx_out:
            try:
                from backend.modules.lean.lean_ghx import dump_packets
                dump_packets(container, ghx_out)
                print(f"[📦] Wrote GHX packets → {ghx_out}")
            except Exception as e:
                print(f"[⚠️] GHX packet dump failed: {e}")

        if ghx_bundle:
            try:
                from backend.modules.lean.lean_ghx import bundle_packets
                bundle_packets(container, ghx_bundle)
                print(f"[📦] Wrote GHX bundle → {ghx_bundle}")
            except Exception as e:
                print(f"[⚠️] GHX bundle failed: {e}")

        # 7) Response
        return {
            "ok": True,
            "container": container,
            "validation_errors": structured_errors,
            "mode": mode,
            "codex_ast": container.get("codex_ast"),
            "sqi_scores": container.get("sqi_scores"),
            "mutations": container.get("mutations"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))