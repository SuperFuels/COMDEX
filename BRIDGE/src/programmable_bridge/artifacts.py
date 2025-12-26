from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ARTIFACT_ROOT = Path("BRIDGE/artifacts/programmable_bridge")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_run_artifacts(*, test_id: str, run_hash: str, cfg: Any, run: Dict[str, Any]) -> Path:
    outdir = ARTIFACT_ROOT / test_id / run_hash
    _ensure_dir(outdir)

    # Keep run.json audit-small: exclude bulky optional payloads
    run_for_json = dict(run)
    for k in (
        "telemetry_lines",
        "telemetry",
        "psi_frames",
        "field_snaps",
    ):
        run_for_json.pop(k, None)

    # run.json
    (outdir / "run.json").write_text(json.dumps(run_for_json, indent=2, sort_keys=True))

    # config.json
    (outdir / "config.json").write_text(json.dumps(asdict(cfg), indent=2, sort_keys=True))

    # meta.json
    meta = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": run.get("controller"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))

    # metrics.csv (time series)
    ks = run.get("kappa_series", []) or []
    curls = run.get("curl_rms_series", []) or []
    curvs = run.get("curvature_series", []) or []
    norms = run.get("norm_series", []) or []

    n = max(len(ks), len(curls), len(curvs), len(norms))
    with (outdir / "metrics.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "kappa", "curl_rms", "curvature", "norm"])
        for i in range(n):
            w.writerow(
                [
                    i,
                    ks[i] if i < len(ks) else "",
                    curls[i] if i < len(curls) else "",
                    curvs[i] if i < len(curvs) else "",
                    norms[i] if i < len(norms) else "",
                ]
            )

    # --- Phase 0.1 (optional): telemetry.jsonl + field.npz for QFC replay ---
    # Never break audits; these are best-effort.
    try:
        import numpy as np

        # telemetry.jsonl
        if os.getenv("TESSARIS_EMIT_TELEMETRY", "1") == "1":
            telemetry_lines = run.get("telemetry_lines")

            if isinstance(telemetry_lines, list) and telemetry_lines:
                tele_path = outdir / "telemetry.jsonl"
                with tele_path.open("w", encoding="utf-8") as f:
                    for row in telemetry_lines:
                        f.write(json.dumps(row, sort_keys=True) + "\n")
            else:
                # synthesize from series if available
                if ks and curls and curvs and norms:
                    T = min(len(ks), len(curls), len(curvs), len(norms))
                    tele_path = outdir / "telemetry.jsonl"
                    with tele_path.open("w", encoding="utf-8") as f:
                        for t in range(T):
                            row = {
                                "t": int(t),
                                "kappa": float(ks[t]),
                                "curl_rms": float(curls[t]),
                                "curvature": float(curvs[t]),
                                "norm": float(norms[t]),
                            }
                            f.write(json.dumps(row, sort_keys=True) + "\n")

        # field.npz
        if os.getenv("TESSARIS_EMIT_FIELD", "1") == "1":
            psi_frames = run.get("psi_frames")

            # legacy support: list[(step:int, psi:ndarray)]
            field_snaps = run.get("field_snaps")
            if psi_frames is None and isinstance(field_snaps, list) and field_snaps:
                # convert to just frames (order preserved)
                psi_frames = [arr for (_, arr) in field_snaps]

            if isinstance(psi_frames, list) and psi_frames:
                psi_arr = np.stack(psi_frames, axis=0)  # (F,H,W) complex
                np.savez_compressed(
                    outdir / "field.npz",
                    psi_real=psi_arr.real.astype("float32"),
                    psi_imag=psi_arr.imag.astype("float32"),
                    kappa=np.asarray(ks, dtype="float32"),
                    curl_rms=np.asarray(curls, dtype="float32"),
                    curvature=np.asarray(curvs, dtype="float32"),
                    norm=np.asarray(norms, dtype="float32"),
                )

    except Exception:
        pass

    return outdir