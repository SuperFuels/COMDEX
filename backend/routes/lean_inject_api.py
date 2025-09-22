# backend/routes/lean_inject_api.py
import os
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# Existing helpers
from backend.modules.lean.lean_injector import load_container, save_container, inject_theorems_into_container
from backend.modules.lean.lean_utils import validate_logic_trees
from backend.modules.lean.lean_audit import audit_event, build_inject_event, build_export_event
from backend.modules.lean.lean_exporter import build_container_from_lean

router = APIRouter(prefix="/api/lean", tags=["Lean"])


def _integrated_hooks(container: dict) -> None:
    """Extra processing in integrated mode (Codex/SQI)."""
    # TODO: plug in CodexLangRewriter, SQI scoring, registry, mutation hooks
    print("[ℹ️] Integrated mode: Codex/SQI hooks would run here.")


@router.post("/inject")
async def inject(
    container_path: str = Form(...),
    overwrite: bool = Form(False),
    dedupe: bool = Form(False),
    auto_clean: bool = Form(True),
    validate: bool = Form(True),
    fail_on_error: bool = Form(False),
    preview: Optional[str] = Form(None),  # "raw" | "normalized"
    mode: str = Form("integrated"),       # 🟢 new mode field
    log_audit: bool = Form(False),
    ghx_out: Optional[str] = Form(None),
    ghx_bundle: Optional[str] = Form(None),
    lean_file: UploadFile = File(...),
):
    """
    Upload a .lean file + mutate an existing container.
    Supports standalone or integrated mode.
    """
    try:
        # 1) Save upload to tmp
        tmp_dir = "tmp/lean_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_lean_path = os.path.join(tmp_dir, lean_file.filename or "upload.lean")
        with open(tmp_lean_path, "wb") as f:
            f.write(await lean_file.read())

        # 2) Inject
        before = load_container(container_path)
        after = inject_theorems_into_container(before, tmp_lean_path)

        # --- overwrite / dedupe / preview ---
        logic_field = next((f for f in (
            "symbolic_logic", "expanded_logic", "hoberman_logic",
            "exotic_logic", "symmetric_logic", "axioms"
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

        # 3) Validate
        validation_errors: List[str] = validate_logic_trees(after)
        after["validation_errors"] = validation_errors
        after["validation_errors_version"] = "v1"

        if fail_on_error and validation_errors:
            raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

        # 4) Mode-specific
        if mode == "integrated":
            _integrated_hooks(after)
        else:
            print("[ℹ️] Standalone mode: skipping Codex/SQI integration.")

        # 5) Save
        save_container(after, container_path)

        # 6) Audit (optional)
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

        # 7) GHX (optional)
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

        # 8) Response
        return JSONResponse({
            "ok": True,
            "container": {"type": after.get("type"), "id": after.get("id"), "path": container_path},
            "counts": {"entries": len(after.get(logic_field or "symbolic_logic", []))},
            "previews": after.get("previews", []),
            "validation_errors": validation_errors,
            "mode": mode,
        })
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
    """Build a new container from a .lean file."""
    try:
        tmp_dir = "tmp/lean_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_lean_path = os.path.join(tmp_dir, lean_file.filename or "upload.lean")
        with open(tmp_lean_path, "wb") as f:
            f.write(await lean_file.read())

        container = build_container_from_lean(tmp_lean_path, container_type)

        # ✅ Validation
        validation_errors: List[str] = validate_logic_trees(container)
        container["validation_errors"] = validation_errors
        container["validation_errors_version"] = "v1"

        if fail_on_error and validation_errors:
            raise HTTPException(status_code=422, detail={"validation_errors": validation_errors})

        # 🟢 Mode
        if mode == "integrated":
            _integrated_hooks(container)
        else:
            print("[ℹ️] Standalone mode: skipping Codex/SQI integration.")

        # 📝 Audit
        if log_audit:
            try:
                audit_event(build_export_event(
                    container_type=container_type,
                    container_id=container.get("id"),
                    lean_path=tmp_lean_path,
                    num_items=len(container.get("symbolic_logic", [])),
                    previews=container.get("previews", []),
                    extra={"mode": mode},
                ))
                print("[📝] Audit event logged")
            except Exception as e:
                print(f"[⚠️] Audit logging failed: {e}")

        # 📦 GHX
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

        return JSONResponse({
            "ok": True,
            "container": container,
            "validation_errors": validation_errors,
            "mode": mode,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))