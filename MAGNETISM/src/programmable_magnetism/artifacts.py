from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_hash_from_dict(d: Mapping[str, Any]) -> str:
    payload = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:7]


def _emit_telemetry_and_field(out: Path, run: Mapping[str, Any]) -> None:
    emit_tel = os.getenv("TESSARIS_EMIT_TELEMETRY", "1") == "1"
    emit_fld = os.getenv("TESSARIS_EMIT_FIELD", "1") == "1"
    if not (emit_tel or emit_fld):
        return

    ts = run.get("t_series", []) or []
    ks = run.get("kappa_series", []) or []
    ae = run.get("ang_err_series", []) or []
    bm = run.get("bmag_series", []) or []

    # MG02
    lg = run.get("leakage_series", []) or []
    sp = run.get("spread_series", []) or []

    # MG01
    b0 = run.get("b0_series", []) or []
    b1 = run.get("b1_series", []) or []

    # MG02 mode
    if len(sp) > 0:
        T = min(len(ts), len(ks), len(ae), len(bm), len(lg), len(sp))
        if T <= 0:
            return

        if emit_tel:
            with (out / "telemetry.jsonl").open("w", encoding="utf-8") as f:
                for i in range(T):
                    row = {
                        "t": float(ts[i]) if i < len(ts) else float(i),
                        "kappa": float(ks[i]),
                        "ang_err": float(ae[i]),
                        "bmag": float(bm[i]),
                        "leakage": float(lg[i]),
                        "spread": float(sp[i]),
                    }
                    f.write(json.dumps(row, sort_keys=True) + "\n")

        if emit_fld:
            field = np.stack(
                [
                    np.asarray(ks[:T], dtype=np.float32),
                    np.asarray(ae[:T], dtype=np.float32),
                    np.asarray(bm[:T], dtype=np.float32),
                    np.asarray(lg[:T], dtype=np.float32),
                    np.asarray(sp[:T], dtype=np.float32),
                ],
                axis=1,
            )  # (T,5)
            frame_steps = np.arange(T, dtype=np.int32)
            t_arr = np.asarray(ts[:T], dtype=np.float32) if len(ts) >= T else frame_steps.astype(np.float32)
            np.savez_compressed(out / "field.npz", frame_steps=frame_steps, t=t_arr, field=field)
        return

    # MG01 mode
    if len(b0) > 0:
        T = min(len(ts), len(ks), len(b0), len(b1), len(bm), len(ae))
        if T <= 0:
            return

        if emit_tel:
            with (out / "telemetry.jsonl").open("w", encoding="utf-8") as f:
                for i in range(T):
                    row = {
                        "t": float(ts[i]) if i < len(ts) else float(i),
                        "kappa": float(ks[i]),
                        "b0": float(b0[i]),
                        "b1": float(b1[i]),
                        "bmag": float(bm[i]),
                        "ang_err": float(ae[i]),
                    }
                    f.write(json.dumps(row, sort_keys=True) + "\n")

        if emit_fld:
            field = np.stack(
                [
                    np.asarray(ks[:T], dtype=np.float32),
                    np.asarray(b0[:T], dtype=np.float32),
                    np.asarray(b1[:T], dtype=np.float32),
                    np.asarray(bm[:T], dtype=np.float32),
                    np.asarray(ae[:T], dtype=np.float32),
                ],
                axis=1,
            )  # (T,5)
            frame_steps = np.arange(T, dtype=np.int32)
            t_arr = np.asarray(ts[:T], dtype=np.float32) if len(ts) >= T else frame_steps.astype(np.float32)
            np.savez_compressed(out / "field.npz", frame_steps=frame_steps, t=t_arr, field=field)
        return


def write_run_artifacts(
    *,
    base_dir: str,
    test_id: str,
    config: Mapping[str, Any],
    controller: str,
    run_hash: str,
    run: Mapping[str, Any],
    git_commit: str | None = None,
) -> Path:
    out = Path(base_dir) / test_id / run_hash
    out.mkdir(parents=True, exist_ok=True)

    (out / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    meta = {
        "test_id": test_id,
        "controller": controller,
        "run_hash": run_hash,
        "git_commit": git_commit,
        "created_utc": _utc_now_iso(),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    run_for_json = dict(run)
    run_for_json.setdefault("test_id", test_id)
    run_for_json.setdefault("run_hash", run_hash)
    run_for_json.setdefault("controller", controller)
    (out / "run.json").write_text(json.dumps(run_for_json, indent=2, sort_keys=True), encoding="utf-8")

    rows = ["t,kappa,b0,b1,bmag,ang_err"]
    ts = run_for_json.get("t_series", []) or []
    ks = run_for_json.get("kappa_series", []) or []
    b0 = run_for_json.get("b0_series", []) or []
    b1 = run_for_json.get("b1_series", []) or []
    bm = run_for_json.get("bmag_series", []) or []
    ae = run_for_json.get("ang_err_series", []) or []

    n = min(len(ts), len(ks), len(b0), len(b1), len(bm), len(ae))
    for i in range(n):
        rows.append(f"{ts[i]},{ks[i]},{b0[i]},{b1[i]},{bm[i]},{ae[i]}")
    (out / "metrics.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    _emit_telemetry_and_field(out, run_for_json)
    return out


def write_run_artifacts_mg02(
    *,
    base_dir: str,
    test_id: str,
    config: Mapping[str, Any],
    controller: str,
    run_hash: str,
    run: Mapping[str, Any],
    git_commit: str | None = None,
) -> Path:
    out = Path(base_dir) / test_id / run_hash
    out.mkdir(parents=True, exist_ok=True)

    (out / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    meta = {
        "test_id": test_id,
        "controller": controller,
        "run_hash": run_hash,
        "git_commit": git_commit,
        "created_utc": _utc_now_iso(),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    run_for_json = dict(run)
    run_for_json.setdefault("test_id", test_id)
    run_for_json.setdefault("run_hash", run_hash)
    run_for_json.setdefault("controller", controller)
    (out / "run.json").write_text(json.dumps(run_for_json, indent=2, sort_keys=True), encoding="utf-8")

    rows = ["t,kappa,ang_err,bmag,leakage,spread"]
    ts = run_for_json.get("t_series", []) or []
    ks = run_for_json.get("kappa_series", []) or []
    ae = run_for_json.get("ang_err_series", []) or []
    bm = run_for_json.get("bmag_series", []) or []
    lg = run_for_json.get("leakage_series", []) or []
    sp = run_for_json.get("spread_series", []) or []

    n = min(len(ts), len(ks), len(ae), len(bm), len(lg), len(sp))
    for i in range(n):
        rows.append(f"{ts[i]},{ks[i]},{ae[i]},{bm[i]},{lg[i]},{sp[i]}")
    (out / "metrics.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    _emit_telemetry_and_field(out, run_for_json)
    return out