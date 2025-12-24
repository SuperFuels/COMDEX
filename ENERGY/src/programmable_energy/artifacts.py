from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def write_run_artifacts(base_dir: str, test_id: str, run_hash: str, run: dict) -> Path:
    """
    Writes:
      ENERGY/artifacts/programmable_energy/PE01/<run_hash>/
        config.json
        metrics.csv
        final_phase.npy
        final_intensity.npy
        target_intensity.npy
        plots/
          intensity_final.png
          metrics_over_time.png
    """
    out_dir = Path(base_dir) / test_id / run_hash
    plots_dir = out_dir / "plots"
    ensure_dir(plots_dir)

    config_payload = {
        "test_id": run["test_id"],
        "controller": run["controller"],
        "run_hash": run["run_hash"],
        "config": run["config"],
    }
    (out_dir / "config.json").write_text(json.dumps(config_payload, indent=2, sort_keys=True))

    metrics = run["metrics"]
    header = ["step", "eta", "mse", "coherence", "S", "r_norm"]
    lines = [",".join(header)]
    for row in metrics:
        lines.append(",".join(str(row[h]) for h in header))
    (out_dir / "metrics.csv").write_text("\n".join(lines) + "\n")

    np.save(out_dir / "final_phase.npy", run["final_phase"])
    np.save(out_dir / "final_intensity.npy", run["final_intensity"])
    np.save(out_dir / "target_intensity.npy", run["target_intensity"])

    I_final = run["final_intensity"]
    I_target = run["target_intensity"]

    plt.figure()
    plt.imshow(I_target)
    plt.title("Target intensity (normalized)")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(plots_dir / "target_intensity.png", dpi=150)
    plt.close()

    plt.figure()
    plt.imshow(I_final)
    plt.title("Final intensity (normalized)")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(plots_dir / "intensity_final.png", dpi=150)
    plt.close()

    steps = [m["step"] for m in metrics]
    eta = [m["eta"] for m in metrics]
    mse = [m["mse"] for m in metrics]
    coh = [m["coherence"] for m in metrics]
    rnorm = [m["r_norm"] for m in metrics]

    plt.figure()
    plt.plot(steps, eta, label="eta (ROI efficiency)")
    plt.plot(steps, coh, label="coherence")
    plt.plot(steps, rnorm, label="r_norm (continuity residual)")
    plt.plot(steps, mse, label="mse (shape error)")
    plt.title("Metrics over time")
    plt.xlabel("step")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "metrics_over_time.png", dpi=150)
    plt.close()

    return out_dir
