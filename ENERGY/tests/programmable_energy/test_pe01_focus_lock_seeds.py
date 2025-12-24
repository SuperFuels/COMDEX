TARGET_SIGMA = 6.0


import csv

def _read_eta_series(metrics_csv):
    """Return eta time-series from metrics.csv (assumes step,eta,... per row)."""
    etas = []
    with open(metrics_csv, newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                # typical: step, eta, mse, ...
                float(row[1])
            except Exception:
                continue
            etas.append(float(row[1]))
    if not etas:
        raise AssertionError(f"No eta rows found in {metrics_csv}")
    import numpy as np
    return np.asarray(etas, dtype=float)

import os
import csv
import inspect
from pathlib import Path

import numpy as np

from programmable_energy.field import make_input_field
from programmable_energy.controllers import PEConfig, TessarisGSController, target_focus_intensity, simulate_pe
from programmable_energy.artifacts import write_run_artifacts

ART_ROOT = Path("ENERGY/artifacts/programmable_energy/PE01_SEEDS")


def _call_with_supported_kwargs(fn, **kwargs):
    sig = inspect.signature(fn)
    filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return fn(**filtered)


def _make_controller(cfg):
    """
    Construct TessarisGSController robustly across constructor signatures.

    We introspect the __init__ signature and pass only parameters it accepts.
    This avoids brittle guessing when the controller API evolves.
    """
    import inspect
    from programmable_energy.controllers import TessarisGSController

    sig = inspect.signature(TessarisGSController)
    params = sig.parameters

    # Map common config values (only used if the controller accepts them)
    mapping = {
        "cfg": cfg,
        "config": cfg,
        "pe_config": cfg,
        "N": getattr(cfg, "N", None),
        "n": getattr(cfg, "N", None),
        "size": getattr(cfg, "N", None),
        "steps": getattr(cfg, "steps", None),
        "T": getattr(cfg, "steps", None),
        "roi_radius": getattr(cfg, "roi_radius", None),
        "drift_sigma": getattr(cfg, "drift_sigma", None),
        "tups_version": getattr(cfg, "tups_version", None),
        # controller knobs (if present)
        "max_phase_step": 0.25,
        "dphi_max": 0.25,
        "phase_step_max": 0.25,
    }

    # Build positional args for required positional parameters (if any)
    args = []
    kwargs = {}

    for p in params.values():
        if p.name == "self":
            continue

        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            if p.default is inspect._empty:
                # Required positional: supply if we can
                if p.name in mapping and mapping[p.name] is not None:
                    args.append(mapping[p.name])
                else:
                    # If a required param is unknown, we can't safely build it
                    # Let TypeError surface so we can see the missing name.
                    pass
            else:
                # Optional positional-or-kw: pass as kw if available
                if p.name in mapping and mapping[p.name] is not None:
                    kwargs[p.name] = mapping[p.name]
        elif p.kind in (p.KEYWORD_ONLY,):
            if p.name in mapping and mapping[p.name] is not None:
                kwargs[p.name] = mapping[p.name]

    # Filter out any kwargs the signature won't accept (safety)
    accepted = set(params.keys())
    kwargs = {k: v for k, v in kwargs.items() if k in accepted}

    try:
        return TessarisGSController(*args, **kwargs)
    except TypeError as e:
        # Last-resort fallbacks for very simple constructors
        try:
            c = TessarisGSController()
            if hasattr(c, "max_phase_step"):
                setattr(c, "max_phase_step", 0.25)
            return c
        except Exception:
            raise RuntimeError(f"Could not construct TessarisGSController. Original error: {e}") from e


def _run_seed(seed: int) -> tuple[Path, float, float]:
    ART_ROOT.mkdir(parents=True, exist_ok=True)

    cfg = PEConfig(
        N=256,
        steps=60,
        seed=seed,
        drift_sigma=1e-3,
        roi_radius=10,
        tups_version="TUPS_V1.2",
    )

    U_in = make_input_field(cfg.N, seed=cfg.seed)

    # tolerate signature: target_focus_intensity(N, sigma=...)
    try:
        target_I = target_focus_intensity(cfg.N, sigma=TARGET_SIGMA)
    except TypeError:
        target_I = target_focus_intensity(cfg.N)

    ctrl = _make_controller(cfg)

    # Run simulation (tolerate simulate_pe signature via kwargs filtering)
    run = _call_with_supported_kwargs(
        simulate_pe,
        test_id="PE01_SEEDS",
        config=cfg,
        controller=ctrl,
        U_in=U_in,
        U0=U_in,
        target_I=target_I,
        target_intensity=target_I,
    )

    # Write artifacts (tolerate write_run_artifacts signature)
    res = _call_with_supported_kwargs(
        write_run_artifacts,
        base_dir="ENERGY/artifacts/programmable_energy/PE01_SEEDS",
        run_hash=run["run_hash"],
        test_id="PE01_SEEDS",
        config=cfg,
        controller=ctrl,
        run=run,
        target_I=target_I,
        target_intensity=target_I,
    )

    # Determine output dir:
    out_dir = None
    if isinstance(res, (str, Path)):
        out_dir = Path(res)
    elif isinstance(res, tuple) and res:
        # common patterns: (out_dir, meta) or (meta, out_dir)
        for item in res:
            if isinstance(item, (str, Path)) and str(item).startswith("ENERGY/"):
                out_dir = Path(item)
                break
            if isinstance(item, dict) and "out_dir" in item:
                out_dir = Path(item["out_dir"])
                break
    elif isinstance(res, dict) and "out_dir" in res:
        out_dir = Path(res["out_dir"])

    if out_dir is None:
        # fallback: assume the writer created a newest folder under ART_ROOT
        out_dir = _latest_run_dir()

    metrics_csv = out_dir / "metrics.csv"
    assert metrics_csv.exists(), f"Missing metrics.csv at {metrics_csv}"

    eta = _read_eta_series(metrics_csv)
    eta_final = float(eta[-1])
    eta_last20 = eta[-20:]
    std_last20 = float(np.std(eta_last20))

    # Sanity: expected files exist
    for fname in ("config.json", "final_intensity.npy", "final_phase.npy", "target_intensity.npy"):
        assert (out_dir / fname).exists(), f"Missing {fname} in {out_dir}"
    assert (out_dir / "plots" / "metrics_over_time.png").exists(), f"Missing plots in {out_dir}"

    return out_dir, eta_final, std_last20


def test_pe01_focus_lock_is_robust_across_seeds():
    # Use fewer seeds in CI if needed.
    seeds = [1, 2, 3] if os.getenv("CI") else [1, 2, 3, 4, 5]

    floor_eta_final = 0.74
    ceil_std_last20 = 0.005

    failures = []
    for s in seeds:
        out_dir, eta_final, std_last20 = _run_seed(s)
        if not (eta_final >= floor_eta_final and std_last20 <= ceil_std_last20):
            failures.append(
                f"seed={s} eta_final={eta_final:.6f} std_last20={std_last20:.6f} out={out_dir}"
            )

    assert not failures, "PE01 robustness failures:\n" + "\n".join(failures)
