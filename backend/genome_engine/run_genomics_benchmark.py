from __future__ import annotations
from typing import Any, Dict, Union, List
import argparse
import json
import hashlib
from pathlib import Path

from .genome_resonance_engine import deterministic_run_id, run_sim_core
from .replay_bundle_writer import make_replay_bundle
from .artifacts_writer import write_artifacts, get_git_rev
from .genomics_scenarios import default_scenarios
from .genomics_metrics import checks as mk_checks
from .schema_validate import validate_or_raise


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _filter_trace(trace: Any, *, mode: str, stride: int, max_events: int) -> Any:
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

    # sampled (default)
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


def run_genomics_benchmark(config_path_or_obj: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(config_path_or_obj, str):
        with open(config_path_or_obj, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = dict(config_path_or_obj)

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

    # Trace size controls (default: sampled + capped)
    cfg.setdefault("trace_mode", "sampled")      # "full" or "sampled"
    cfg.setdefault("trace_stride", 8)            # keep every Nth event
    cfg.setdefault("trace_max_events", 4096)     # 0 means unlimited

    # Dataset provenance (required by schema now)
    dataset_path = str(cfg.get("dataset_path") or "")
    if not dataset_path:
        raise ValueError("GX1 config missing dataset_path")
    cfg.setdefault("dataset_id", Path(dataset_path).name)
    cfg.setdefault("dataset_sha256", _sha256_file(dataset_path))

    # Deterministic run_id AFTER all stable fields exist
    run_id = str(cfg.get("run_id") or deterministic_run_id(cfg))
    cfg["run_id"] = run_id

    core = run_sim_core(cfg)
    scen: Dict[str, Any] = core["scenario_summaries"]

    rho_matched = float(scen.get("matched_key", {}).get("rho_primary", 0.0))
    rho_mismatch = float(scen.get("mismatched_key", {}).get("rho_primary", 0.0))

    # IMPORTANT: crosstalk gate applies to multiplex scenarios only (mutation is a different test)
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
        "status": "OK" if all_pass else "FAIL",
        "summary": {
            **summary,
            "checks_pass": bool(all_pass),
            "checks_failed": int(sum(1 for x in checks if not x.get("pass"))),
        },
        "checks": checks,
        "scenario_summaries": scen,
    }

    repo_root = "/workspaces/COMDEX"
    phase_root = str(cfg["output_root"])
    git_rev = get_git_rev(repo_root)

    # Filter trace BEFORE replay digest + artifact write
    trace_out = _filter_trace(
        core.get("trace"),
        mode=str(cfg.get("trace_mode")),
        stride=int(cfg.get("trace_stride")),
        max_events=int(cfg.get("trace_max_events")),
    )

    replay = make_replay_bundle(
        config=cfg,
        metrics=metrics,
        trace=trace_out,
        git_rev=git_rev,
        run_id=run_id,
    )

    # Fail-fast contract validation (schemas)
    validate_or_raise("gx1_genome_benchmark_config.schema.json", cfg)
    validate_or_raise("gx1_genome_benchmark_metrics.schema.json", metrics)
    validate_or_raise("gx1_replay_bundle.schema.json", replay)

    info = write_artifacts(
        repo_root=repo_root,
        phase_root=phase_root,
        run_id=run_id,
        config=cfg,
        metrics=metrics,
        trace=trace_out,
        replay_bundle=replay,
    )

    return {
        "run_id": run_id,
        "phase_root": phase_root,
        "run_dir": info["run_dir"],
        "git_rev": git_rev,
        "status": metrics["status"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to GX1 config JSON")
    args = ap.parse_args()
    r = run_genomics_benchmark(args.config)
    print(f"✅ GX1 done: run_id={r['run_id']} status={r['status']}")
    print(f"   phase_root={r['phase_root']}")
    print(f"   run_dir={r['run_dir']}")


if __name__ == "__main__":
    main()
