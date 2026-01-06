from __future__ import annotations

from typing import Any, Dict, Optional
import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from .run_genomics_benchmark import run_genomics_benchmark


def _repo_root() -> Path:
    # .../backend/genome_engine/web_gx1_upload.py -> repo root is 2 levels up
    return Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json_upload(up: UploadFile) -> Dict[str, Any]:
    raw = up.file.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in {up.filename}: {e}")


def _exec_mode_from_manifest(manifest: Dict[str, Any]) -> str:
    exec_cfg = manifest.get("exec") or {}
    src = str(exec_cfg.get("source") or "SIM").upper()
    if src == "SIM":
        return "sim"
    if src in ("SLE", "BEAM"):
        return "sle"
    # default safe
    return "sim"


def _apply_exec_to_cfg(cfg: Dict[str, Any], manifest: Dict[str, Any]) -> None:
    exec_cfg = manifest.get("exec") or {}

    # internal builder controls (they get stripped from exported schemas by your runner)
    cfg["mode"] = _exec_mode_from_manifest(manifest)

    # SQI stage toggle surface (matches your runner behavior)
    sqi_stage = str(exec_cfg.get("sqi_stage") or "off").lower()
    kg_write = bool(exec_cfg.get("kg_write", False))

    if sqi_stage == "off":
        # nothing
        return

    if sqi_stage == "bundle":
        cfg["export_sqi_bundle"] = True
        return

    if sqi_stage == "fabric":
        # drive the same path your runner expects
        cfg.setdefault("sqi", {})
        if not isinstance(cfg["sqi"], dict):
            cfg["sqi"] = {}
        cfg["sqi"]["enabled"] = True
        cfg["sqi"]["level"] = "fabric"
        cfg["sqi"]["kg_write"] = bool(kg_write)
        return


def build_fastapi_router() -> APIRouter:
    router = APIRouter()

    @router.post("/gx1/run", response_model=None)
    async def gx1_run(
        manifest: UploadFile = File(...),
        dataset: UploadFile = File(...),
    ) -> Dict[str, Any]:
        # --- stage workspace ---
        rr = _repo_root()
        stage_root = rr / ".runtime" / "gx1_uploads"
        stage_root.mkdir(parents=True, exist_ok=True)

        upload_id = uuid.uuid4().hex[:12]
        run_stage = stage_root / upload_id
        run_stage.mkdir(parents=True, exist_ok=True)

        # --- read uploads ---
        m = _read_json_upload(manifest)
        gx1_cfg = dict(m.get("gx1_config") or {})
        if not gx1_cfg:
            raise HTTPException(status_code=400, detail="manifest.gx1_config missing")

        # write dataset to staged file
        ds_path = run_stage / "dataset.jsonl"
        with ds_path.open("wb") as f:
            f.write(dataset.file.read())

        if ds_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="dataset upload is empty")

        # rewrite dataset_path/output_root for server-runner
        gx1_cfg["dataset_path"] = str(ds_path)

        # output_root: keep it server-managed (deterministic evidence tree)
        default_out = rr / "docs" / "Artifacts" / "v0.4" / "P21_GX1"
        out_root = Path(os.getenv("GX1_OUTPUT_ROOT", str(default_out)))
        gx1_cfg["output_root"] = str(out_root)

        # apply exec (SIM/SLE + SQI toggles)
        _apply_exec_to_cfg(gx1_cfg, m)

        # run
        try:
            r = run_genomics_benchmark(gx1_cfg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"GX1 run failed: {e}")

        # add upload anchors (helpful in UI)
        r.setdefault("upload", {})
        r["upload"]["upload_id"] = upload_id
        r["upload"]["dataset_path"] = str(ds_path)
        r["upload"]["dataset_sha256"] = _sha256_file(ds_path)

        return r

    return router
