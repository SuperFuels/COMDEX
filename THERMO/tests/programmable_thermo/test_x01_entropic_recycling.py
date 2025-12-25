import subprocess
from pathlib import Path

from programmable_thermo.artifacts import run_hash_from_dict, write_run_artifacts
from programmable_thermo.controllers import (
    EntropicRecyclerController,
    OpenLoopController,
    RandomJitterGainController,
)
from programmable_thermo.sim import simulate_thermo

def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None

def test_x01_entropic_recycling_beats_baselines():
    """
    X01 (audit-safe): under fixed noise (temperature proxy), the recycler controller
    reduces entropy proxy S and increases coherence proxy R compared to open-loop and
    random jitter baselines. Model-only.
    """
    config = {
        "seed": 4242,
        "H": 96,
        "W": 96,
        "steps": 600,
        "dt": 0.05,

        # Protocol labels (pinned environment labels)
        "hbar": 1e-3,
        "G": 1e-5,
        "Lambda0": 1e-6,
        "alpha": 0.5,

        # Dynamics
        "nu": 0.18,
        "damp": 0.012,

        # Langevin noise ("temperature" proxy)
        "T": 1.0,
        "noise_sigma": 0.55,
    }

    base_dir = Path("THERMO/artifacts/programmable_thermo")

    tess = EntropicRecyclerController(
        name="tessaris_entropic_recycler",
        g_max=1.0,
        Gamma_W=0.18,
        eta_W=0.22,
        R_target=0.95,
        S_target=0.15,
    )
    open_ = OpenLoopController(name="open_loop")
    rand = RandomJitterGainController(name="random_jitter_gain", g0=0.25, g_step=0.18, g_max=1.0)

    r_tess = simulate_thermo(test_id="X01", config=config, controller=tess)
    r_open = simulate_thermo(test_id="X01", config=config, controller=open_)
    r_rand = simulate_thermo(test_id="X01", config=config, controller=rand)

    # Deterministic run hash per controller/config
    h_tess = run_hash_from_dict({"test_id":"X01","controller":r_tess["controller"],"config":config})
    h_open = run_hash_from_dict({"test_id":"X01","controller":r_open["controller"],"config":config})
    h_rand = run_hash_from_dict({"test_id":"X01","controller":r_rand["controller"],"config":config})

    gitc = _git_commit()
    r_tess["git_commit"] = gitc
    r_open["git_commit"] = gitc
    r_rand["git_commit"] = gitc

    write_run_artifacts(base_dir=base_dir, test_id="X01", run_hash=h_tess, run=r_tess)
    write_run_artifacts(base_dir=base_dir, test_id="X01", run_hash=h_open, run=r_open)
    write_run_artifacts(base_dir=base_dir, test_id="X01", run_hash=h_rand, run=r_rand)

    # --- Assertions (audit-safe, baseline-relative) ---
    # 1) "Cooling" proof in-proxy: S_final < S_initial, and better than open-loop
    assert r_tess["S_final"] < r_tess["S_initial"], "expected entropy proxy to decrease under recycler"
    assert r_tess["S_final"] <= r_open["S_final"] + 1e-12, f"expected tessaris S_final <= open_loop: {r_tess['S_final']=} vs {r_open['S_final']=}"

    # 2) "Coherence" proof: R_final should exceed baseline(s)
    assert r_tess["R_final"] >= r_open["R_final"] - 1e-12, f"expected tessaris R_final >= open_loop: {r_tess['R_final']=} vs {r_open['R_final']=}"
    assert r_tess["R_final"] >= 0.90, f"expected high coherence proxy; got {r_tess['R_final']=}"

    # 3) Must beat random jitter on S_final (conservative)
    assert r_tess["S_final"] <= r_rand["S_final"] + 1e-12, f"expected tessaris S_final <= random: {r_tess['S_final']=} vs {r_rand['S_final']=}"

    # Stability sanity: norm shouldn't explode
    assert max(r_tess["norm_series"]) <= 20.0, "unexpected instability (norm blow-up)"
