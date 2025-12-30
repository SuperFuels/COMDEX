#!/usr/bin/env python3
"""
Vol IV executable evidence runner (reference implementation).

Scene:  VOL4_COHERENCE_PHASE_LOCK
Metric: phase coherence -> information
  r = |mean(exp(i*phi))|
  C_phi_final := r
  D_phi_final := 1 - r
  I_final     := 1 - D_phi_final = r

Writes:
  docs/Artifacts/VolIV/ledger/VOLIV_LINT_PROOF.log
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO = Path("/workspaces/COMDEX")

DEFAULT_SCENE = REPO / "docs/Artifacts/VolIV/qfc/VOL4_COHERENCE_PHASE_LOCK.scene.json"
DEFAULT_THRESHOLDS = REPO / "docs/Artifacts/VolIV/build/VOLIV_ACCEPTANCE_THRESHOLDS.yaml"
DEFAULT_OUT_LOG = REPO / "docs/Artifacts/VolIV/ledger/VOLIV_LINT_PROOF.log"
DEFAULT_OUT_METRICS = REPO / "docs/Artifacts/VolIV/ledger/VOLIV_METRICS.json"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def try_git_commit(repo: Path) -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo))
        return out.decode("utf-8").strip()
    except Exception:
        return None


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_thresholds_yaml_minimal(path: Path) -> Dict[str, Any]:
    """
    Minimal YAML reader for simple key/value + one-level nesting.
    If PyYAML exists, we use it; otherwise parse a tiny subset.
    """
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        data: Dict[str, Any] = {}
        stack: list[Tuple[int, Dict[str, Any]]] = [(0, data)]
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, val = [x.strip() for x in line.lstrip().split(":", 1)]
            # descend/ascend based on indent
            while stack and indent < stack[-1][0]:
                stack.pop()
            cur = stack[-1][1]
            if val == "":
                cur[key] = {}
                stack.append((indent + 2, cur[key]))
            else:
                # best-effort scalar parse
                if val.lower() in ("true", "false"):
                    cur[key] = (val.lower() == "true")
                else:
                    try:
                        if "." in val or "e" in val.lower():
                            cur[key] = float(val)
                        else:
                            cur[key] = int(val)
                    except Exception:
                        cur[key] = val.strip('"').strip("'")
        return data


@dataclass
class Thresholds:
    i_final_min: float = 0.95
    d_phi_final_max: float = 0.05
    within_steps: int = 1000

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Thresholds":
        # allow either flat keys or nested structure
        def pick(*keys: str, default: Any) -> Any:
            cur: Any = d
            for k in keys:
                if not isinstance(cur, dict) or k not in cur:
                    return default
                cur = cur[k]
            return cur

        return Thresholds(
            i_final_min=float(pick("pass", "I_final_min", default=pick("I_final_min", default=0.95))),
            d_phi_final_max=float(pick("pass", "D_phi_final_max", default=pick("D_phi_final_max", default=0.05))),
            within_steps=int(pick("pass", "within_steps", default=pick("within_steps", default=1000))),
        )


def order_parameter(phases) -> float:
    # r = |mean(exp(i*phi))|
    re = 0.0
    im = 0.0
    n = len(phases)
    for phi in phases:
        re += math.cos(phi)
        im += math.sin(phi)
    re /= n
    im /= n
    return math.sqrt(re * re + im * im)


def run_phase_lock_sim(
    n: int,
    steps: int,
    dt_step: float,
    k_couple: float,
    seed: int,
) -> Tuple[int, float, float, float]:
    """
    Deterministic Kuramoto-style global coupling (no noise after seeding).
    """
    import random

    rnd = random.Random(seed)

    # Initial random phases in [-pi, pi)
    phases = [rnd.uniform(-math.pi, math.pi) for _ in range(n)]

    # Deterministic natural frequencies: small fixed spread derived from seed
    # (keeps run reproducible and not "all identical" trivial locking)
    rnd2 = random.Random(seed + 1337)
    omegas = [rnd2.uniform(-0.5, 0.5) for _ in range(n)]

    # Iterate
    pass_step = None
    for t in range(1, steps + 1):
        r = order_parameter(phases)
        # mean phase angle psi
        # compute via atan2(mean(sin), mean(cos))
        re = sum(math.cos(p) for p in phases) / n
        im = sum(math.sin(p) for p in phases) / n
        psi = math.atan2(im, re)

        # Update phases (Euler)
        new_phases = []
        for i, phi in enumerate(phases):
            dphi = omegas[i] + k_couple * r * math.sin(psi - phi)
            phi2 = phi + dt_step * dphi
            # keep bounded
            if phi2 >= math.pi:
                phi2 -= 2 * math.pi
            elif phi2 < -math.pi:
                phi2 += 2 * math.pi
            new_phases.append(phi2)
        phases = new_phases

        r = order_parameter(phases)
        d_phi = 1.0 - r
        i_val = 1.0 - d_phi  # equals r

        # stop early if we’ve met typical thresholds; actual PASS evaluated outside
        if pass_step is None and (i_val >= 0.95 and d_phi <= 0.05):
            pass_step = t
            # keep running to end? usually no; we can stop for speed and record steps.
            break

    final_r = order_parameter(phases)
    final_d = 1.0 - final_r
    final_i = final_r
    return (pass_step or steps, final_r, final_d, final_i)


def write_log(
    out_log: Path,
    lock_id: str,
    scene_name: str,
    status: str,
    steps: int,
    c_phi: float,
    d_phi: float,
    i_val: float,
    thresholds: Thresholds,
    cmdline: str,
    commit: Optional[str],
) -> None:
    out_log.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# VOLIV_LINT_PROOF.log")
    lines.append("# Evidence log for Volume IV scene + metric thresholds.")
    lines.append("")
    lines.append(f"TIMESTAMP_UTC: {utc_now_iso()}")
    lines.append(f"LOCK_ID: {lock_id}")
    lines.append(f"SCENE: {scene_name}")
    lines.append(f"STATUS: {status}")
    lines.append("")
    lines.append("RUN_METADATA:")
    lines.append(f"  python: {sys.version.split()[0]}")
    lines.append(f"  platform: {platform.platform()}")
    if commit:
        lines.append(f"  git_commit: {commit}")
    else:
        lines.append("  git_commit: null")
    lines.append(f"  command: {cmdline}")
    lines.append("")
    lines.append("METRICS:")
    lines.append(f"  steps: {steps}")
    lines.append(f"  C_phi_final: {c_phi:.8f}")
    lines.append(f"  D_phi_final: {d_phi:.8f}")
    lines.append(f"  I_final: {i_val:.8f}")
    lines.append("")
    lines.append("PASS_CONDITION (from VOLIV_ACCEPTANCE_THRESHOLDS.yaml):")
    lines.append(f"  I_final >= {thresholds.i_final_min}")
    lines.append(f"  D_phi_final <= {thresholds.d_phi_final_max}")
    lines.append(f"  within_steps <= {thresholds.within_steps}")
    lines.append("")
    out_log.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", type=str, default=str(DEFAULT_SCENE))
    ap.add_argument("--thresholds", type=str, default=str(DEFAULT_THRESHOLDS))
    ap.add_argument("--out-log", type=str, default=str(DEFAULT_OUT_LOG))
    ap.add_argument("--out-metrics", type=str, default=str(DEFAULT_OUT_METRICS))
    ap.add_argument("--seed", type=int, default=0)

    # Simulation knobs (defaults are reasonable for quick locking)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--dt", type=float, default=0.05)
    ap.add_argument("--k", type=float, default=2.5)

    args = ap.parse_args()

    scene_path = Path(args.scene)
    thr_path = Path(args.thresholds)
    out_log = Path(args.out_log)
    out_metrics = Path(args.out_metrics)

    if not scene_path.exists():
        print(f"[ERROR] Missing scene: {scene_path}", file=sys.stderr)
        return 2

    scene = load_json(scene_path)
    scene_name = scene.get("scene", "VOL4_COHERENCE_PHASE_LOCK")

    # thresholds
    if thr_path.exists():
        thr_raw = load_thresholds_yaml_minimal(thr_path)
    else:
        thr_raw = {}
    thresholds = Thresholds.from_dict(thr_raw)

    # run sim
    used_steps, c_phi, d_phi, i_val = run_phase_lock_sim(
        n=args.n,
        steps=min(args.steps, thresholds.within_steps),
        dt_step=args.dt,
        k_couple=args.k,
        seed=args.seed,
    )

    passed = (i_val >= thresholds.i_final_min) and (d_phi <= thresholds.d_phi_final_max) and (used_steps <= thresholds.within_steps)
    status = "PASS" if passed else "FAIL"

    # metrics json (nice to keep machine-readable)
    out_metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics_payload = {
        "timestamp_utc": utc_now_iso(),
        "lock_id": scene.get("lock_id", "VolIV-INFO-COHERENCE-v0.1"),
        "scene": scene_name,
        "seed": args.seed,
        "params": {"n": args.n, "steps_cap": thresholds.within_steps, "dt": args.dt, "k": args.k},
        "metrics": {
            "steps": used_steps,
            "C_phi_final": c_phi,
            "D_phi_final": d_phi,
            "I_final": i_val,
        },
        "thresholds": {
            "I_final_min": thresholds.i_final_min,
            "D_phi_final_max": thresholds.d_phi_final_max,
            "within_steps": thresholds.within_steps,
        },
        "status": status,
    }
    out_metrics.write_text(json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8")

    # write lint proof log
    lock_id = scene.get("lock_id", "VolIV-INFO-COHERENCE-v0.1")
    commit = try_git_commit(REPO)
    cmdline = " ".join([sys.executable] + sys.argv)
    write_log(
        out_log=out_log,
        lock_id=lock_id,
        scene_name=scene_name,
        status=status,
        steps=used_steps,
        c_phi=c_phi,
        d_phi=d_phi,
        i_val=i_val,
        thresholds=thresholds,
        cmdline=cmdline,
        commit=commit,
    )

    print(f"[{status}] wrote: {out_log}")
    print(f"        wrote: {out_metrics}")
    print(f"        steps={used_steps} C_phi={c_phi:.6f} D_phi={d_phi:.6f} I={i_val:.6f}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())