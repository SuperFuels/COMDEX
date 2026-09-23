# backend/photon_algebra/tests/haev_test_H3_arrow_of_time_emergence.py
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Minimal embedded dual-field bounce simulator (model-only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class H3Config:
    alpha: float = 0.7
    beta: float = 0.08
    Lambda_base: float = 0.0035
    kappa: float = 0.065
    omega0: float = 0.18
    xi: float = 0.015
    delta: float = 0.05
    noise: float = 0.0006
    rho_c: float = 1.0
    g_couple: float = 0.015
    kp: float = 0.2
    ki: float = 0.005
    kd: float = 0.04
    T: int = 12000
    dt: float = 0.002
    cycles: int = 4


class DualFieldBounce:
    @staticmethod
    def simulate(params: dict[str, float], dt: float, T: int, seed: int = 0, cycles: int = 4) -> dict[str, Any]:
        """
        Model-only proxy dynamics with symmetric zero-mean perturbations
        so seed robustness can be tested.
        """
        rng = np.random.default_rng(seed)

        t = np.arange(0, T * dt, dt, dtype=float)

        # Base symmetric proxy fields
        phi = np.sin(0.01 * t) * np.exp(-0.0001 * t)
        psi = np.cos(0.01 * t) * np.exp(-0.0001 * t)

        # Symmetric perturbation
        noise_sigma = float(params.get("noise", 0.0))
        if noise_sigma > 0.0:
            phi = phi + rng.normal(0.0, noise_sigma, size=phi.shape)
            psi = psi + rng.normal(0.0, noise_sigma, size=psi.shape)

        cycle_indices = np.array_split(np.arange(len(t)), cycles)
        return {
            "t": t,
            "phi": phi,
            "psi": psi,
            "cycles": cycles,
            "cycle_indices": cycle_indices,
        }


dualfield_bounce = DualFieldBounce


# ---------------------------------------------------------------------------
# Core metrics
# ---------------------------------------------------------------------------

def entropy(field: np.ndarray) -> float:
    prob = np.abs(field) ** 2
    denom = float(np.sum(prob))
    if denom <= 0.0:
        return 0.0
    prob = prob / denom
    return float(-np.sum(prob * np.log(prob + 1e-12)))


def build_params(cfg: H3Config) -> dict[str, float]:
    return {
        "alpha": cfg.alpha,
        "beta": cfg.beta,
        "Lambda_base": cfg.Lambda_base,
        "kappa": cfg.kappa,
        "omega0": cfg.omega0,
        "xi": cfg.xi,
        "delta": cfg.delta,
        "noise": cfg.noise,
        "rho_c": cfg.rho_c,
        "g_couple": cfg.g_couple,
        "kp": cfg.kp,
        "ki": cfg.ki,
        "kd": cfg.kd,
    }


def run_h3(seed: int, cfg: H3Config) -> dict[str, Any]:
    params = build_params(cfg)

    results = dualfield_bounce.simulate(
        params=params,
        dt=cfg.dt,
        T=cfg.T,
        seed=seed,
        cycles=cfg.cycles,
    )

    phi = results["phi"]
    psi = results["psi"]
    num_cycles = int(results["cycles"])

    s_total: list[float] = []
    i_mutual: list[float] = []

    for cycle in range(num_cycles):
        idx = results["cycle_indices"][cycle]
        s_v = entropy(phi[idx])
        s_h = entropy(psi[idx])
        s_t = entropy(phi[idx] + psi[idx])
        s_total.append(s_t)
        i_mutual.append(s_v + s_h - s_t)

    s_total_arr = np.array(s_total, dtype=float)
    i_mutual_arr = np.array(i_mutual, dtype=float)

    entropy_drift = np.diff(s_total_arr) if len(s_total_arr) >= 2 else np.array([0.0], dtype=float)
    drift_mean = float(np.mean(entropy_drift)) if len(entropy_drift) else 0.0
    arrow_direction = "Forward" if drift_mean > 0.0 else "None"

    metrics = {
        "entropy_cycle_mean": float(np.mean(s_total_arr)) if len(s_total_arr) else 0.0,
        "entropy_drift_mean": drift_mean,
        "mutual_information_asymmetry": (
            float(np.mean(np.abs(np.diff(i_mutual_arr))))
            if len(i_mutual_arr) >= 2
            else 0.0
        ),
        "arrow_direction": arrow_direction,
        "cycles": int(num_cycles),
    }

    return {
        "seed": int(seed),
        "constants": params,
        "metrics": metrics,
        "series": {
            "S_total": s_total_arr.tolist(),
            "I_mutual": i_mutual_arr.tolist(),
            "entropy_drift": entropy_drift.tolist(),
        },
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

KNOWLEDGE_DIR = "backend/modules/knowledge"
DEFAULT_PLOT_PATH = os.path.join(KNOWLEDGE_DIR, "HAEV_H3_EntropyPerCycle.png")
DEFAULT_JSON_PATH = os.path.join(KNOWLEDGE_DIR, "H3_arrow_of_time_emergence.json")
DEFAULT_SWEEP_JSON_PATH = os.path.join(KNOWLEDGE_DIR, "H3_arrow_of_time_seed_sweep.json")


def ensure_dirs() -> None:
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)


def save_single_run_artifacts(run: dict[str, Any], plot_path: str, json_path: str) -> None:
    ensure_dirs()

    s_total = np.array(run["series"]["S_total"], dtype=float)

    plt.figure()
    plt.plot(s_total, marker="o", label="Total Entropy")
    plt.xlabel("Cycle index")
    plt.ylabel("Entropy")
    plt.title("Entropy per Cycle (H3 Arrow of Time)")
    plt.legend()
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()

    output = {
        "constants": run["constants"],
        "metrics": run["metrics"],
        "classification": (
            "⏳ Emergent Arrow of Time Detected"
            if run["metrics"]["arrow_direction"] == "Forward"
            else "⚪ No Directional Bias"
        ),
        "files": {"entropy_plot": plot_path},
        "seed": run["seed"],
        "timestamp": run["timestamp"],
        "test_id": "H3",
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Plot saved    -> {plot_path}")
    print(f"✅ Results saved -> {json_path}")


def summarise_sweep(runs: list[dict[str, Any]]) -> dict[str, Any]:
    drift_vals = np.array([r["metrics"]["entropy_drift_mean"] for r in runs], dtype=float)
    asym_vals = np.array([r["metrics"]["mutual_information_asymmetry"] for r in runs], dtype=float)
    cycle_means = np.array([r["metrics"]["entropy_cycle_mean"] for r in runs], dtype=float)
    forward_count = int(sum(1 for r in runs if r["metrics"]["arrow_direction"] == "Forward"))

    return {
        "test_id": "H3",
        "runs": len(runs),
        "forward_count": forward_count,
        "forward_fraction": (forward_count / len(runs)) if runs else 0.0,
        "entropy_drift_mean_mean": float(np.mean(drift_vals)) if len(drift_vals) else 0.0,
        "entropy_drift_mean_std": float(np.std(drift_vals)) if len(drift_vals) else 0.0,
        "mutual_information_asymmetry_mean": float(np.mean(asym_vals)) if len(asym_vals) else 0.0,
        "mutual_information_asymmetry_std": float(np.std(asym_vals)) if len(asym_vals) else 0.0,
        "entropy_cycle_mean_mean": float(np.mean(cycle_means)) if len(cycle_means) else 0.0,
        "entropy_cycle_mean_std": float(np.std(cycle_means)) if len(cycle_means) else 0.0,
        "per_seed": [
            {
                "seed": r["seed"],
                "entropy_drift_mean": r["metrics"]["entropy_drift_mean"],
                "mutual_information_asymmetry": r["metrics"]["mutual_information_asymmetry"],
                "entropy_cycle_mean": r["metrics"]["entropy_cycle_mean"],
                "arrow_direction": r["metrics"]["arrow_direction"],
            }
            for r in runs
        ],
        "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
    }


def save_sweep_json(summary: dict[str, Any], json_path: str) -> None:
    ensure_dirs()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Seed sweep saved -> {json_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="H3 / HAEV emergent arrow-of-time proxy test with single-run and seed-sweep modes."
    )
    parser.add_argument("--seed", type=int, default=0, help="Seed for single-run mode.")
    parser.add_argument(
        "--seed-sweep",
        type=int,
        default=0,
        help="If > 0, run seeds 0..N-1 and summarize robustness.",
    )
    parser.add_argument("--plot-path", default=DEFAULT_PLOT_PATH, help="Path for single-run plot output.")
    parser.add_argument("--json-path", default=DEFAULT_JSON_PATH, help="Path for single-run JSON output.")
    parser.add_argument(
        "--sweep-json-path",
        default=DEFAULT_SWEEP_JSON_PATH,
        help="Path for seed-sweep JSON output.",
    )
    parser.add_argument("--T", type=int, default=12000, help="Number of time steps scale parameter.")
    parser.add_argument("--dt", type=float, default=0.002, help="Time step.")
    parser.add_argument("--cycles", type=int, default=4, help="Number of cycle partitions.")
    parser.add_argument("--noise", type=float, default=0.0006, help="Symmetric perturbation sigma.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = H3Config(T=args.T, dt=args.dt, cycles=args.cycles, noise=args.noise)

    if args.seed_sweep > 0:
        runs = [run_h3(seed=s, cfg=cfg) for s in range(args.seed_sweep)]
        summary = summarise_sweep(runs)

        print("=== H3 - Emergent Arrow of Time (Seed Sweep) ===")
        print(f"Runs: {summary['runs']}")
        print(f"Forward count: {summary['forward_count']}/{summary['runs']}")
        print(f"Forward fraction: {summary['forward_fraction']:.3f}")
        print(f"Mean entropy drift: {summary['entropy_drift_mean_mean']:.6e}")
        print(f"Std entropy drift:  {summary['entropy_drift_mean_std']:.6e}")
        print(f"Mean MI asymmetry:  {summary['mutual_information_asymmetry_mean']:.6e}")
        print(f"Std MI asymmetry:   {summary['mutual_information_asymmetry_std']:.6e}")

        save_sweep_json(summary, args.sweep_json_path)
        return

    run = run_h3(seed=args.seed, cfg=cfg)
    metrics = run["metrics"]

    print("=== H3 - Emergent Arrow of Time ===")
    print(f"Seed: {run['seed']}")
    print(f"Entropy drift mean: {metrics['entropy_drift_mean']:.4e}")
    print(f"Mutual info asymmetry: {metrics['mutual_information_asymmetry']:.4e}")
    print(f"-> {metrics['arrow_direction']} Arrow Detected")

    save_single_run_artifacts(run, args.plot_path, args.json_path)


if __name__ == "__main__":
    main()