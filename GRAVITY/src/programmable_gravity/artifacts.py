from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


def run_hash_from_dict(d: Dict[str, Any], n: int = 7) -> str:
    blob = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:n]


def write_run_artifacts(
    *,
    base_dir: str,
    test_id: str,
    config: Dict[str, Any],
    controller: str,
    run_hash: str,
    run: Dict[str, Any],
    git_commit: Optional[str] = None,
) -> Path:
    """
    Writes audit artifacts:
      base_dir/<test_id>/<run_hash>/
        config.json
        metrics.csv
        S_final.npy, R_final.npy, R_target.npy
        plots/*.png
    """
    out_dir = Path(base_dir) / test_id / run_hash
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # config.json
    cfg = {
        "test_id": test_id,
        "run_hash": run_hash,
        "controller": controller,
        "config": config,
        "git_commit": git_commit,
    }
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")

    # arrays
    np.save(out_dir / "S_final.npy", run["S_final"])
    np.save(out_dir / "R_final.npy", run["R_final"])
    np.save(out_dir / "R_target.npy", run["R_target"])

    # metrics.csv
    mse_series = np.asarray(run["mse_series"], dtype=float)
    with open(out_dir / "metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "mse_R"])
        for i, v in enumerate(mse_series):
            w.writerow([i, float(v)])

    # plots (matplotlib only; no seaborn; no forced colors)
    import matplotlib.pyplot as plt

    def _save_im(arr: np.ndarray, path: Path, title: str):
        plt.figure()
        plt.imshow(arr, origin="lower")
        plt.title(title)
        plt.colorbar()
        plt.tight_layout()
        plt.savefig(path, dpi=140)
        plt.close()

    _save_im(run["R_target"], plots_dir / "R_target.png", "Target curvature proxy R_target")
    _save_im(run["R_final"], plots_dir / "R_final.png", "Final curvature proxy R_final")
    _save_im(run["S_final"], plots_dir / "S_final.png", "Final entropy proxy S_final")

    plt.figure()
    plt.plot(np.arange(len(mse_series)), mse_series)
    plt.title("Curvature MSE over time")
    plt.xlabel("step")
    plt.ylabel("mse_R")
    plt.tight_layout()
    plt.savefig(plots_dir / "metrics_over_time.png", dpi=140)
    plt.close()

    return out_dir
