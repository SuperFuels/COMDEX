from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.genome_engine.run_genomics_benchmark import run_genomics_benchmark


def _truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


APP_TITLE = "GX1 API (minimal)"
RUNS_ROOT = Path(os.getenv("GX1_RUNS_ROOT", "/tmp/gx1_uploads")).resolve()
RUNS_ROOT.mkdir(parents=True, exist_ok=True)

DEFAULT_OUTPUT_ROOT = os.getenv(
    "GX1_OUTPUT_ROOT",
    "/workspaces/COMDEX/docs/Artifacts/v0.4/P21_GX1",
)

# How much trace detail to return inline (UI-safe)
TRACE_PREVIEW_N = int(os.getenv("GX1_TRACE_PREVIEW_N", "64"))

app = FastAPI(title=APP_TITLE, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-only
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "gx1", "runs_root": str(RUNS_ROOT)}

# ✅ Alias so Vite can hit /api/gx1/health through the proxy
@app.get("/api/gx1/health")
def health_alias() -> Dict[str, Any]:
    return health()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _load_manifest(raw: bytes) -> Dict[str, Any]:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"manifest must be valid JSON: {e}")
    if not isinstance(obj, dict):
        raise HTTPException(status_code=400, detail="manifest must be a JSON object")
    return obj


def _normalize_exec(manifest: Dict[str, Any]) -> Dict[str, Any]:
    exec_cfg = manifest.get("exec") or {}
    if not isinstance(exec_cfg, dict):
        raise HTTPException(status_code=400, detail="manifest.exec must be an object")
    source = str(exec_cfg.get("source") or "SIM").upper()
    sqi_stage = str(exec_cfg.get("sqi_stage") or "off").lower()
    kg_write = _truthy(exec_cfg.get("kg_write", False))
    return {"source": source, "sqi_stage": sqi_stage, "kg_write": kg_write}


def _normalize_cfg(manifest: Dict[str, Any]) -> Dict[str, Any]:
    cfg = manifest.get("gx1_config") or manifest.get("config")
    if not isinstance(cfg, dict):
        raise HTTPException(status_code=400, detail="manifest must include gx1_config object")
    return dict(cfg)


def _trace_preview_from_metrics(metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a UI-safe preview from metrics.scenario_summaries[*].rho_trace
    without returning the full arrays.
    """
    if not isinstance(metrics, dict):
        return {"preview_n": TRACE_PREVIEW_N, "scenarios": {}}

    ss = metrics.get("scenario_summaries")
    if not isinstance(ss, dict):
        return {"preview_n": TRACE_PREVIEW_N, "scenarios": {}}

    out: Dict[str, Any] = {"preview_n": TRACE_PREVIEW_N, "scenarios": {}}

    for sid, s in ss.items():
        if not isinstance(s, dict):
            continue
        rt = s.get("rho_trace")
        if not isinstance(rt, list):
            continue

        # numeric-only (defensive)
        vals: List[float] = []
        for v in rt:
            try:
                vals.append(float(v))
            except Exception:
                pass

        n = len(vals)
        prev = vals[:TRACE_PREVIEW_N]
        out["scenarios"][sid] = {
            "n": n,
            "first": prev,
            "min": min(vals) if n else None,
            "max": max(vals) if n else None,
            "mean": (sum(vals) / n) if n else None,
        }

    return out


# ─────────────────────────────────────────────────────────────
# API: run
# ─────────────────────────────────────────────────────────────

@app.post("/api/gx1/run")
async def gx1_run(
    manifest: UploadFile = File(...),
    dataset: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Minimal GX1 upload contract:
      - manifest: JSON with `gx1_config` + optional `exec`
      - dataset: JSONL rows (needs seq/sequence)

    Response is UI-safe (no massive rho arrays).
    Full artifacts remain on disk for replay.
    """
    mf_raw = await manifest.read()
    ds_raw = await dataset.read()

    mf = _load_manifest(mf_raw)
    exec_cfg = _normalize_exec(mf)
    cfg = _normalize_cfg(mf)

    # Only SIM supported here (Mode B later)
    if exec_cfg["source"] != "SIM":
        raise HTTPException(status_code=400, detail="exec.source != SIM not supported in gx1_api_min")

    upload_id = uuid.uuid4().hex
    wdir = RUNS_ROOT / upload_id
    wdir.mkdir(parents=True, exist_ok=True)

    mf_path = wdir / "manifest.json"
    ds_path = wdir / "dataset.jsonl"
    mf_path.write_bytes(mf_raw)
    ds_path.write_bytes(ds_raw)

    # Rewrite paths
    cfg["dataset_path"] = str(ds_path)
    cfg["output_root"] = str(Path(DEFAULT_OUTPUT_ROOT).resolve())

    # SQI stage toggle
    stage = exec_cfg["sqi_stage"]
    if stage == "bundle":
        cfg["export_sqi_bundle"] = True
    elif stage == "fabric":
        cfg["sqi"] = dict(cfg.get("sqi") or {})
        cfg["sqi"]["enabled"] = True
        cfg["sqi"]["level"] = "fabric"
        cfg["sqi"]["kg_write"] = bool(exec_cfg["kg_write"])
    elif stage in {"off", "", "none"}:
        pass
    else:
        raise HTTPException(status_code=400, detail=f"Unknown exec.sqi_stage: {stage}")

    try:
        result = run_genomics_benchmark(cfg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GX1 run failed: {type(e).__name__}: {e}")

    metrics = result.get("metrics") if isinstance(result, dict) else None
    replay_bundle = result.get("replay_bundle") if isinstance(result, dict) else None
    exports = replay_bundle.get("exports") if isinstance(replay_bundle, dict) else None

    out: Dict[str, Any] = {
        "status": result.get("status", "UNKNOWN"),
        "run_id": result.get("run_id"),
        "git_rev": result.get("git_rev"),
        "phase_root": result.get("phase_root"),
        "run_dir": result.get("run_dir"),
        "trace_digest": (replay_bundle.get("trace_digest") if isinstance(replay_bundle, dict) else None),
        "metrics": metrics,
        "trace_preview": _trace_preview_from_metrics(metrics),
        "exports": exports,
        "staging_dir": str(wdir),
    }

    # Strip huge rho_trace arrays from HTTP response (remain on disk)
    if isinstance(out.get("metrics"), dict):
        ss = out["metrics"].get("scenario_summaries")
        if isinstance(ss, dict):
            for _sid, s in ss.items():
                if isinstance(s, dict) and "rho_trace" in s:
                    s.pop("rho_trace", None)

    return out


# ─────────────────────────────────────────────────────────────
# API: inspect + files
# ─────────────────────────────────────────────────────────────

def _safe_join(base: Path, rel: str) -> Path:
    rel = rel.lstrip("/").replace("..", "")
    p = (base / rel).resolve()
    if not str(p).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="invalid rel path")
    return p


def _read_text_if_exists(p: Path, max_bytes: int = 2_000_000) -> str:
    if not p.exists():
        return ""
    data = p.read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
    try:
        return data.decode("utf-8")
    except Exception:
        return data.decode("utf-8", errors="replace")


@app.get("/api/gx1/runs/{run_id}")
def gx1_run_info(run_id: str) -> Dict[str, Any]:
    out_root = Path(DEFAULT_OUTPUT_ROOT).resolve()
    run_dir = (out_root / "runs" / run_id).resolve()
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run_id not found")

    idx = run_dir / "ARTIFACTS_INDEX.md"
    sha = run_dir / "ARTIFACTS.sha256"
    cfg = run_dir / "CONFIG.json"
    metrics = run_dir / "METRICS.json"
    trace = run_dir / "TRACE.jsonl"
    replay = run_dir / "REPLAY_BUNDLE.json"
    ledger = run_dir / "LEDGER.jsonl"
    kgw = run_dir / "SQI_KG_WRITES.jsonl"

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "files": {
            "CONFIG.json": str(cfg) if cfg.exists() else "",
            "METRICS.json": str(metrics) if metrics.exists() else "",
            "TRACE.jsonl": str(trace) if trace.exists() else "",
            "REPLAY_BUNDLE.json": str(replay) if replay.exists() else "",
            "LEDGER.jsonl": str(ledger) if ledger.exists() else "",
            "SQI_KG_WRITES.jsonl": str(kgw) if kgw.exists() else "",
            "ARTIFACTS_INDEX.md": str(idx) if idx.exists() else "",
            "ARTIFACTS.sha256": str(sha) if sha.exists() else "",
        },
        "index_text": _read_text_if_exists(idx),
        "sha256_text": _read_text_if_exists(sha),
    }


@app.get("/api/gx1/runs/{run_id}/file")
def gx1_run_file(run_id: str, rel: str) -> FileResponse:
    out_root = Path(DEFAULT_OUTPUT_ROOT).resolve()
    run_dir = (out_root / "runs" / run_id).resolve()
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run_id not found")

    p = _safe_join(run_dir, rel)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    media_type = "application/octet-stream"
    if p.name.endswith(".json"):
        media_type = "application/json"
    elif p.name.endswith((".jsonl", ".sha256", ".md", ".txt")):
        media_type = "text/plain"

    return FileResponse(str(p), media_type=media_type, filename=p.name)


# ─────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────

def main() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "8090"))
    uvicorn.run("backend.gx1_api_min:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()