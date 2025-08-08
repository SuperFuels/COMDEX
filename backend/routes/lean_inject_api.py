# backend/routes/lean_inject_api.py
import os
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

# Use your existing logic helpers
from backend.modules.lean.lean_injector import load_container, save_container, inject_theorems_into_container
from backend.modules.lean.lean_utils import validate_logic_trees
from backend.modules.lean.lean_audit import audit_event, build_inject_event
from backend.modules.lean.lean_exporter import build_container_from_lean

router = APIRouter(prefix="/api/lean", tags=["Lean"])

@router.post("/inject")
async def inject(
    container_path: str = Form(...),
    overwrite: bool = Form(False),
    dedupe: bool = Form(False),
    auto_clean: bool = Form(True),
    validate: bool = Form(True),
    preview: Optional[str] = Form(None),            # "raw" | "normalized"
    lean_file: UploadFile = File(...),
):
    """
    Upload a .lean file + point at an existing container JSON path on the server.
    Mutates the container in place and returns a summary.
    """
    try:
        # 1) stash uploaded .lean to a temp path
        tmp_dir = "tmp/lean_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_lean_path = os.path.join(tmp_dir, lean_file.filename or "upload.lean")
        with open(tmp_lean_path, "wb") as f:
            f.write(await lean_file.read())

        # 2) run your existing injection logic
        before = load_container(container_path)
        after = inject_theorems_into_container(before, tmp_lean_path)

        # --- overwrite / dedupe / preview flags (same behavior as CLI) ---
        # overwrite: last occurrence wins by name
        if overwrite:
            # choose the best logic field
            logic_field = None
            for f in ("symbolic_logic","expanded_logic","hoberman_logic","exotic_logic","symmetric_logic","axioms"):
                if f in after:
                    logic_field = f
                    break
            items = after.get(logic_field, [])
            by_name = {}
            for it in items:
                by_name[it.get("name")] = it
            after[logic_field] = list(by_name.values())

        if dedupe:
            logic_field = None
            for f in ("symbolic_logic","expanded_logic","hoberman_logic","exotic_logic","symmetric_logic","axioms"):
                if f in after:
                    logic_field = f
                    break
            seen, unique = set(), []
            for it in after.get(logic_field, []):
                sig = (it.get("name"), it.get("symbol"), it.get("logic_raw") or it.get("logic"))
                if sig not in seen:
                    seen.add(sig)
                    unique.append(it)
            after[logic_field] = unique

        if preview:
            logic_field = None
            for f in ("symbolic_logic","expanded_logic","hoberman_logic","exotic_logic","symmetric_logic","axioms"):
                if f in after:
                    logic_field = f
                    break
            previews: List[str] = []
            for it in after.get(logic_field, []):
                name = it.get("name","unknown")
                sym  = it.get("symbol","⟦ ? ⟧")
                if preview == "raw":
                    logic = it.get("logic_raw") or it.get("codexlang",{}).get("logic") or it.get("logic") or "???"
                else:
                    logic = it.get("logic") or it.get("logic_raw") or it.get("codexlang",{}).get("logic") or "???"
                label = "Define" if "Definition" in sym else "Prove"
                previews.append(f"{sym} | {name} : {logic} → {label} ⟧")
            after["previews"] = previews

        # auto clean small cruft
        if auto_clean:
            for key in ("glyphs","previews"):
                if key in after and isinstance(after[key], list):
                    deduped, seen = [], set()
                    for x in after[key]:
                        if x not in seen:
                            seen.add(x); deduped.append(x)
                    after[key] = deduped
            if "dependencies" in after and not after["dependencies"]:
                del after["dependencies"]

        # validate
        validation_errors: List[str] = []
        if validate:
            validation_errors = validate_logic_trees(after)

        # 3) persist container
        save_container(after, container_path)

        # 4) audit (best-effort)
        try:
            logic_field = None
            for f in ("symbolic_logic","expanded_logic","hoberman_logic","exotic_logic","symmetric_logic","axioms"):
                if f in after:
                    logic_field = f
                    break
            previews = after.get("previews", [])
            audit_event(build_inject_event(
                container_path=container_path,
                container_id=after.get("id"),
                lean_path=tmp_lean_path,
                num_items=len(after.get(logic_field, [])),
                previews=previews,
                extra={"overwrite": overwrite, "dedupe": dedupe, "auto_clean": auto_clean}
            ))
        except Exception:
            pass

        # 5) response
        return JSONResponse({
            "ok": True,
            "container": {"type": after.get("type"), "id": after.get("id"), "path": container_path},
            "counts": {"entries": len(after.get(logic_field or "symbolic_logic", []))},
            "previews": after.get("previews", []),
            "validation_errors": validation_errors,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export")
async def export_container(
    container_type: str = Form("dc"),   # "dc" | "hoberman" | ...
    lean_file: UploadFile = File(...),
):
    """Build a brand-new container JSON from a .lean file and return it."""
    try:
        tmp_dir = "tmp/lean_uploads"
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_lean_path = os.path.join(tmp_dir, lean_file.filename or "upload.lean")
        with open(tmp_lean_path, "wb") as f:
            f.write(await lean_file.read())

        container = build_container_from_lean(tmp_lean_path, container_type)
        return JSONResponse({"ok": True, "container": container})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))