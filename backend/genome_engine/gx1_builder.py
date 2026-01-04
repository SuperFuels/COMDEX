from __future__ import annotations

from typing import Any, Dict, List
import json
import hashlib
from pathlib import Path

from .genome_resonance_engine import deterministic_run_id, run_sim_core
from .replay_bundle_writer import make_replay_bundle
from .genomics_scenarios import default_scenarios
from .genomics_metrics import checks as mk_checks
from .artifacts_writer import get_git_rev


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def filter_trace(trace: Any, *, mode: str, stride: int, max_events: int) -> Any:
    """
    Deterministic size control for TRACE payload.
      - mode=full: keep all events (optionally capped)
      - mode=sampled: keep every Nth event (optionally capped)
    If trace isn't a list, it is returned unchanged.
    """
    if not isinstance(trace, list):
        return trace

    m = str(mode or "sampled")
    s = int(stride) if int(stride) > 0 else 1
    cap = int(max_events) if int(max_events) >= 0 else 0

    if m == "full":
        return trace if cap == 0 else trace[:cap]

    out: List[Any] = []
    for i, ev in enumerate(trace):
        if i % s != 0:
            continue
        out.append(ev)
        if cap and len(out) >= cap:
            break

    # Never allow an empty trace for schema sanity; add deterministic meta line.
    if not out:
        out = [{
            "event_type": "trace_meta",
            "mode": m,
            "stride": s,
            "max_events": cap,
            "events_in": len(trace),
        }]

    return out


def build_gx1_payload(cfg_in: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure GX1 build step:
      config -> core -> metrics -> filtered trace -> replay bundle
    No disk writes here (artifact writer lives in the runner).
    """
    cfg: Dict[str, Any] = dict(cfg_in)

    cfg.setdefault("schemaVersion", "GX1_CONFIG_V0")
    cfg.setdefault("objective_id", "P21_GX1_GENOMICS_BENCH_V0")
    cfg.setdefault("seed", 1337)
    cfg.setdefault("created_utc", "0000-00-00T00:00:00Z")
    cfg.setdefault("mapping_id", "GX1_MAP_V1")
    cfg.setdefault("chip_mode", "ONEHOT4")
    cfg.setdefault("dt", 0.01)
    cfg.setdefault("steps", 2048)
    cfg.setdefault("thresholds", {
        "warmup_ticks": 128,
        "eval_ticks": 512,
        "rho_matched_min": 0.80,
        "rho_mismatch_abs_max": 0.20,
        "crosstalk_max": 0.20,
        "coherence_mean_min": 0.80,
        "drift_mean_max": 0.08,
    })
    cfg.setdefault("scenarios", default_scenarios())
    cfg.setdefault("output_root", "/workspaces/COMDEX/docs/Artifacts/v0.4/P21_GX1")

    cfg.setdefault("trace_mode", "sampled")      # "full" or "sampled"
    cfg.setdefault("trace_stride", 8)            # keep every Nth event
    cfg.setdefault("trace_max_events", 4096)     # 0 means unlimited

    dataset_path = str(cfg.get("dataset_path") or "")
    if not dataset_path:
        raise ValueError("GX1 config missing dataset_path")

    cfg.setdefault("dataset_id", Path(dataset_path).name)
    cfg.setdefault("dataset_sha256", sha256_file(dataset_path))

    run_id = str(cfg.get("run_id") or deterministic_run_id(cfg))
    cfg["run_id"] = run_id

    mode = str(cfg.get("mode") or "sim").lower()
    if mode != "sim":
        raise NotImplementedError(f"build_gx1_payload only supports mode='sim' for now (got {mode!r})")
    cfg["mode"] = mode

    core = run_sim_core(cfg)
    scen: Dict[str, Any] = core["scenario_summaries"]

    rho_matched = float(scen.get("matched_key", {}).get("rho_primary", 0.0))
    rho_mismatch = float(scen.get("mismatched_key", {}).get("rho_primary", 0.0))

    multiplex_vals = [
        float(v.get("crosstalk_max", 0.0))
        for v in scen.values()
        if str(v.get("mode", "")) == "multiplex"
    ]
    crosstalk_max = max(multiplex_vals) if multiplex_vals else 0.0

    coherence_mean = float(scen.get("matched_key", {}).get("coherence_mean", 0.0))
    drift_mean = float(scen.get("matched_key", {}).get("drift_mean", 0.0))

    summary = {
        "rho_matched": rho_matched,
        "rho_mismatch": rho_mismatch,
        "crosstalk_max": crosstalk_max,
        "coherence_mean": coherence_mean,
        "drift_mean": drift_mean,
    }

    checks = mk_checks(cfg["thresholds"], summary)
    all_pass = all(bool(x.get("pass")) for x in checks) if checks else False

    metrics = {
        "schemaVersion": "GX1_METRICS_V0",
        "objective_id": cfg["objective_id"],
        "run_id": run_id,
        "seed": int(cfg["seed"]),
        "mode": mode,
        "status": "OK" if all_pass else "FAIL",
        "summary": {
            **summary,
            "checks_pass": bool(all_pass),
            "checks_failed": int(sum(1 for x in checks if not x.get("pass"))),
        },
        "checks": checks,
        "scenario_summaries": scen,
    }

    trace_out = filter_trace(
        core.get("trace"),
        mode=str(cfg.get("trace_mode")),
        stride=int(cfg.get("trace_stride")),
        max_events=int(cfg.get("trace_max_events")),
    )

    git_rev = get_git_rev("/workspaces/COMDEX")

    replay = make_replay_bundle(
        config=cfg,
        metrics=metrics,
        trace=trace_out,
        git_rev=git_rev,
        run_id=run_id,
    )

    return {
        "config": cfg,
        "metrics": metrics,
        "trace": trace_out,
        "replay_bundle": replay,
        "git_rev": git_rev,
        "run_id": run_id,
        "phase_root": str(cfg["output_root"]),
        "mode": mode,
    }


def stable_hash(obj: Any) -> str:
    """
    Simple stable hash for comparisons. (Not the contract hash; just for tests/verification.)
    """
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
