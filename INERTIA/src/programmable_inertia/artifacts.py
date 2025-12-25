from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np


def run_hash_from_dict(meta: Mapping[str, Any]) -> str:
    blob = json.dumps(meta, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:7]


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
    out_dir = Path(base_dir) / test_id / run_hash
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = dict(config)
    cfg.setdefault("created_utc", _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z")

    meta = {
        "test_id": test_id,
        "controller": controller,
        "git_commit": git_commit,
        "config": cfg,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))

    # small run.json (numbers + a couple keys)
    run_json = {k: run[k] for k in run.keys() if k not in ("v_series", "a_series", "alpha_series")}
    (out_dir / "run.json").write_text(json.dumps(run_json, indent=2, sort_keys=True))

    # arrays
    if "v_series" in run:
        np.save(out_dir / "v_series.npy", np.asarray(run["v_series"], dtype=float))
    if "a_series" in run:
        np.save(out_dir / "a_series.npy", np.asarray(run["a_series"], dtype=float))
    if "alpha_series" in run:
        np.save(out_dir / "alpha_series.npy", np.asarray(run["alpha_series"], dtype=float))

    # metrics.csv
    v = np.asarray(run.get("v_series", []), dtype=float)
    a = np.asarray(run.get("a_series", []), dtype=float)
    al = np.asarray(run.get("alpha_series", []), dtype=float)
    n = int(min(len(v), len(a), len(al)))

    with open(out_dir / "metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "alpha", "v", "a"])
        for i in range(n):
            w.writerow([i, float(al[i]), float(v[i]), float(a[i])])

    # config snapshot for quick diffing
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True))

    return out_dir
