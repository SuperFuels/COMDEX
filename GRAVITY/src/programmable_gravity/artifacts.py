from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def run_hash_from_dict(meta: Mapping[str, Any], n: int = 7) -> str:
    h = hashlib.sha256(_json_dumps(meta).encode("utf-8")).hexdigest()
    return h[:n]


def _as_dict(x: Any) -> dict:
    if isinstance(x, Mapping):
        return dict(x)
    return {"value": x}


def _save_npy(out_dir: Path, name: str, arr: Any) -> None:
    if arr is None:
        return
    a = np.asarray(arr)
    np.save(out_dir / name, a)


def _write_metrics_csv(out_dir: Path, run: Mapping[str, Any]) -> None:
    """
    Writes a simple metrics.csv.
    Priority:
      1) run["metrics_rows"] : list[dict]
      2) run["mse_series"]   : list/array
      3) scalars in run      : single row
    """
    p = out_dir / "metrics.csv"

    if "metrics_rows" in run and isinstance(run["metrics_rows"], list) and run["metrics_rows"]:
        rows = run["metrics_rows"]
        # union keys (stable order)
        keys = []
        seen = set()
        for r in rows:
            if isinstance(r, Mapping):
                for k in r.keys():
                    if k not in seen:
                        seen.add(k)
                        keys.append(k)
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(keys)
            for r in rows:
                w.writerow([r.get(k, "") for k in keys])
        return

    if "mse_series" in run:
        series = np.asarray(run["mse_series"], dtype=float).reshape(-1)
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "mse"])
            for t, mse in enumerate(series.tolist()):
                w.writerow([t, float(mse)])
        return

    # fallback: write one row of numeric scalars (so "last col" parsing still works)
    scalars = {k: v for k, v in run.items() if isinstance(v, (int, float)) and np.isfinite(v)}
    if not scalars:
        with p.open("w", newline="") as f:
            csv.writer(f).writerow(["note"])
            csv.writer(f).writerow(["no_metrics"])
        return

    keys = sorted(scalars.keys())
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        w.writerow([scalars[k] for k in keys])


def write_run_artifacts(
    *,
    base_dir: str | Path,
    test_id: str,
    config: Mapping[str, Any] | Any,
    controller: str | None,
    run_hash: str,
    run: Mapping[str, Any],
    git_commit: str | None = None,
    **_: Any,
) -> Path:
    out_dir = Path(base_dir) / str(test_id) / str(run_hash)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = _as_dict(config)
    cfg.setdefault("test_id", test_id)
    cfg.setdefault("controller", controller)
    cfg.setdefault("git_commit", git_commit)
    cfg.setdefault("run_hash", run_hash)
    cfg.setdefault("created_utc", _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds") + "Z")

    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")

    # Save a compact run.json of scalars (avoid huge arrays)
    summary: dict[str, Any] = {}
    for k, v in run.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            summary[k] = v
    (out_dir / "run.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    # Arrays (tolerant keys)
    if "S_final" in run:
        _save_npy(out_dir, "S_final.npy", run["S_final"])
    elif "S" in run:
        _save_npy(out_dir, "S_final.npy", run["S"])

    if "R_final" in run:
        _save_npy(out_dir, "R_final.npy", run["R_final"])
    if "R_target" in run:
        _save_npy(out_dir, "R_target.npy", run["R_target"])

    _write_metrics_csv(out_dir, run)

    return out_dir
