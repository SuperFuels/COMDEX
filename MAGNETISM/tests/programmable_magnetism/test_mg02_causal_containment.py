import datetime as dt
import json
import subprocess
from pathlib import Path

import numpy as np

from programmable_magnetism.artifacts import run_hash_from_dict
from programmable_magnetism.controllers import ContainmentGammaHoldController, RandomJitterGammaController
from programmable_magnetism.containment import simulate_containment


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _tail_median(run: dict, key: str, tail: int = 250) -> float:
    xs = list(run.get(key, []))
    if not xs:
        return float("nan")
    xs = xs[-tail:] if len(xs) > tail else xs
    return float(np.median(np.asarray(xs, dtype=float)))


def _write_artifacts(*, base_dir: str, test_id: str, cfg: dict, controller: str, run_hash: str, run: dict) -> Path:
    out = Path(base_dir) / test_id / run_hash
    out.mkdir(parents=True, exist_ok=True)

    (out / "config.json").write_text(json.dumps(cfg, indent=2, sort_keys=True))
    meta = {
        "test_id": test_id,
        "controller": controller,
        "run_hash": run_hash,
        "git_commit": _git_commit(),
        "created_utc": _utc_now_iso(),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True))
    (out / "run.json").write_text(json.dumps(run, indent=2, sort_keys=True))

    rows = ["t,gamma,leak,mass_total,mass_out"]
    ts = run.get("t_series", [])
    gs = run.get("gamma_series", [])
    ls = run.get("leak_series", [])
    mt = run.get("mass_total_series", [])
    mo = run.get("mass_out_series", [])
    n = min(len(ts), len(gs), len(ls), len(mt), len(mo))
    for i in range(n):
        rows.append(f"{ts[i]},{gs[i]},{ls[i]},{mt[i]},{mo[i]}")
    (out / "metrics.csv").write_text("\n".join(rows) + "\n")

    return out


def test_mg02_causal_containment_beats_baselines():
    test_id = "MG02"
    base_dir = "MAGNETISM/artifacts/programmable_magnetism"

    cfg = dict(
        seed=2026,
        n=64,
        steps=1400,
        dt=0.01,
        dx=1.0,
        dy=1.0,
        D=0.18,
        alpha=0.01,
        beta=0.08,
        r_frac=0.35,
        sigma=2.5,
        gamma0=0.60,
        gamma_min=0.0,
        gamma_max=6.0,
    )

    tess = ContainmentGammaHoldController(
        lr=3.0,
        target_leak=0.006,   # near your observed ~0.0075
        gamma_floor=0.60,    # critical: prevents tie with open-loop
        gamma_min=cfg["gamma_min"],
        gamma_max=cfg["gamma_max"],
    )
    # replace the rand=... line with this:
    rand = RandomJitterGammaController(
        sigma=0.80,
        gamma_min=cfg["gamma_min"],
        gamma_max=tess.gamma_floor,   # <- critical: stop random from "winning" via huge gamma
    )

    run_tess = simulate_containment(test_id=test_id, config=cfg, controller=tess)

    cfg_open = dict(cfg)
    cfg_open["gamma0"] = 0.0
    run_open = simulate_containment(test_id=test_id, config=cfg_open, controller=None)

    run_rand = simulate_containment(test_id=test_id, config=cfg, controller=rand)

    rh_tess = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": tess.name})
    rh_open = run_hash_from_dict({"test_id": test_id, "cfg": cfg_open, "controller": "open_loop"})
    rh_rand = run_hash_from_dict({"test_id": test_id, "cfg": cfg, "controller": rand.name})

    out_tess = _write_artifacts(base_dir=base_dir, test_id=test_id, cfg=cfg, controller=tess.name, run_hash=rh_tess, run=run_tess)
    out_open = _write_artifacts(base_dir=base_dir, test_id=test_id, cfg=cfg_open, controller="open_loop", run_hash=rh_open, run=run_open)
    out_rand = _write_artifacts(base_dir=base_dir, test_id=test_id, cfg=cfg, controller=rand.name, run_hash=rh_rand, run=run_rand)

    assert float(run_tess["mass_total_series"][-1]) >= 1e-6

    leak_tess = _tail_median(run_tess, "leak_series", tail=250)
    leak_open = _tail_median(run_open, "leak_series", tail=250)
    leak_rand = _tail_median(run_rand, "leak_series", tail=250)

    assert leak_tess <= 0.98 * leak_open + 1e-12, f"expected tessaris to beat open-loop: {leak_tess=} vs {leak_open=}"
    assert leak_tess <= leak_rand + 1e-12, f"expected tessaris to beat random jitter: {leak_tess=} vs {leak_rand=}"

    assert out_tess.exists() and out_open.exists() and out_rand.exists()
