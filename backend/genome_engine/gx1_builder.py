from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List

from .artifacts_writer import get_git_rev
from .genome_resonance_engine import deterministic_run_id, run_sim_core
from .genomics_metrics import checks as mk_checks
from .genomics_scenarios import default_scenarios
from .ledger_feed import build_ledger_exports, build_ledger_rows
from .replay_bundle_writer import make_replay_bundle
from .stable_json import stable_hash as _stable_hash
from .sqi_bundle import build_sqi_bundle


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

    Always preserves GX1 contract-critical events:
      - trace_kind in {"scenario_summary","rho_trace_eval_window","sqi_bundle","sqi_fabric_plan","sqi_fabric_result"}
      - event_type == "trace_meta"
    """
    if not isinstance(trace, list):
        return trace

    m = str(mode or "sampled")
    s = int(stride) if int(stride) > 0 else 1
    cap = int(max_events) if int(max_events) >= 0 else 0

    CRITICAL_KINDS = {
        "scenario_summary",
        "rho_trace_eval_window",
        "sqi_bundle",
        "sqi_fabric_plan",
        "sqi_fabric_result",
    }

    def _is_critical(ev: Any) -> bool:
        if not isinstance(ev, dict):
            return False
        tk = ev.get("trace_kind")
        if tk in CRITICAL_KINDS:
            return True
        if ev.get("event_type") == "trace_meta":
            return True
        return False

    def _dedup_key(ev: Dict[str, Any]) -> tuple:
        # Deterministic key for stable de-dupe
        return (
            str(ev.get("trace_kind", "")),
            str(ev.get("event_type", "")),
            str(ev.get("scenario_id", "")),
            int(ev.get("tick", -1)) if isinstance(ev.get("tick", -1), int) else -1,
            float(ev.get("t", -1.0)) if isinstance(ev.get("t", -1.0), (int, float)) else -1.0,
        )

    def _critical_rank(ev: Dict[str, Any]) -> int:
        tk = str(ev.get("trace_kind") or "")
        if tk == "scenario_summary":
            return 0
        if tk == "rho_trace_eval_window":
            return 1
        if tk == "sqi_bundle":
            return 2
        if tk == "sqi_fabric_plan":
            return 3
        if tk == "sqi_fabric_result":
            return 4
        return 9

    # Collect critical events from the original trace (deterministic ordering)
    critical = [ev for ev in trace if _is_critical(ev)]
    critical_sorted = sorted(
        (ev for ev in critical if isinstance(ev, dict)),
        key=lambda ev: (
            str(ev.get("scenario_id", "")),
            _critical_rank(ev),
            _dedup_key(ev),
        ),
    )

    if m == "full":
        out = trace if cap == 0 else trace[:cap]
    else:
        out: List[Any] = []
        for i, ev in enumerate(trace):
            if i % s != 0:
                continue
            out.append(ev)
            if cap and len(out) >= cap:
                break

    # De-dupe and force-include critical events
    seen: set[tuple] = set()
    out2: List[Any] = []
    for ev in out:
        if isinstance(ev, dict):
            k = _dedup_key(ev)
            if k in seen:
                continue
            seen.add(k)
        out2.append(ev)

    for ev in critical_sorted:
        k = _dedup_key(ev)
        if k in seen:
            continue
        seen.add(k)
        out2.append(ev)

    # Never allow an empty trace for schema sanity
    if not out2:
        out2 = [
            {
                "event_type": "trace_meta",
                "mode": m,
                "stride": s,
                "max_events": cap,
                "events_in": len(trace),
            }
        ]

    return out2


def _normalize_sqi_cfg(cfg: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
    """
    Normalizes SQI control knobs to match the config schema:
      - export_sqi_bundle: back-compat boolean
      - sqi: { enabled, level, executor, kg_write, plan_scope, max_jobs }

    Rules:
      - If sqi.enabled is set, it wins.
      - Else fall back to export_sqi_bundle.
      - Else default: sle/beam => enabled True (bundle), sim => enabled False.
    """
    sqi_in = cfg.get("sqi")
    sqi_cfg: Dict[str, Any] = dict(sqi_in or {})

    enabled_raw = sqi_cfg.get("enabled", None)
    if enabled_raw is None:
        if "export_sqi_bundle" in cfg:
            enabled = bool(cfg.get("export_sqi_bundle"))
        else:
            enabled = True if mode in ("sle", "beam") else False
    else:
        enabled = bool(enabled_raw)

    level_raw = sqi_cfg.get("level", None)
    if level_raw is None:
        level = "bundle" if enabled else "bundle"
    else:
        level = str(level_raw)

    # If not enabled, treat as off at runtime
    runtime_level = level if enabled else "off"

    # Keep only schema-allowed keys (additionalProperties=false)
    exec_raw = sqi_cfg.get("executor", None)
    executor = str(exec_raw or "local").lower()
    if executor not in ("local", "ucs"):
        executor = "local"

    out = {
        "enabled": enabled,
        "level": level if level in ("bundle", "fabric") else "bundle",
        "executor": executor,
        "kg_write": bool(sqi_cfg.get("kg_write", False)),
        "plan_scope": (
            str(sqi_cfg.get("plan_scope", "run"))
            if str(sqi_cfg.get("plan_scope", "run")) in ("run", "scenario")
            else "run"
        ),
        "max_jobs": int(sqi_cfg.get("max_jobs", 0)) if int(sqi_cfg.get("max_jobs", 0)) >= 0 else 0,
    }

    # Back-compat flag: keep it consistent with sqi.enabled for callers/tests
    cfg.setdefault("export_sqi_bundle", bool(out["enabled"]))

    # Persist normalized sqi cfg (schema-safe)
    cfg["sqi"] = {k: v for k, v in out.items() if not str(k).startswith("_")}

    # Provide runtime_level to caller (off/bundle/fabric)
    out["_runtime_level"] = runtime_level
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
    cfg.setdefault(
        "thresholds",
        {
            "warmup_ticks": 128,
            "eval_ticks": 512,
            "rho_matched_min": 0.80,
            "rho_mismatch_abs_max": 0.20,
            "crosstalk_max": 0.20,
            "coherence_mean_min": 0.80,
            "drift_mean_max": 0.08,
        },
    )
    cfg.setdefault("scenarios", default_scenarios())
    cfg.setdefault("output_root", "/workspaces/COMDEX/docs/Artifacts/v0.4/P21_GX1")

    cfg.setdefault("trace_mode", "sampled")      # "full" or "sampled"
    cfg.setdefault("trace_stride", 8)           # keep every Nth event
    cfg.setdefault("trace_max_events", 4096)    # 0 means unlimited

    dataset_path = str(cfg.get("dataset_path") or "")
    if not dataset_path:
        raise ValueError("GX1 config missing dataset_path")

    cfg.setdefault("dataset_id", Path(dataset_path).name)
    cfg.setdefault("dataset_sha256", sha256_file(dataset_path))

    run_id = str(cfg.get("run_id") or deterministic_run_id(cfg))
    cfg["run_id"] = run_id

    mode = str(cfg.get("mode") or "sim").lower()
    cfg["mode"] = mode

    # Normalize SQI knobs early so replay/config is schema-safe and deterministic
    sqi_cfg = _normalize_sqi_cfg(cfg, mode=mode)
    sqi_runtime_level = str(sqi_cfg.get("_runtime_level") or "off")  # off | bundle | fabric

    if mode == "sim":
        core = run_sim_core(cfg)
        scen: Dict[str, Any] = core["scenario_summaries"]
        trace_raw = list(core.get("trace") or [])

    elif mode in ("sle", "beam"):
        from .sle_adapter import SLEAdapter

        thr = dict(cfg.get("thresholds") or {})
        thr.setdefault("warmup_ticks", 128)
        thr.setdefault("eval_ticks", 512)

        adapter = SLEAdapter(seed=int(cfg["seed"]), dt=float(cfg.get("dt", 1 / 30)))
        out = adapter.run(scenarios=list(cfg.get("scenarios") or []), thresholds=thr)

        # Build scenario_summaries compatible with metrics logic + metrics schema.
        scen = {}
        for sid, s in (out.get("scenarios") or {}).items():
            eval_window = list(s.get("qscore_eval_window") or [])
            coherence_mean = float(s.get("coherence_mean", 0.0))

            scen[sid] = {
                "scenario_id": sid,
                "mode": str(s.get("mode", "")),
                "k": int(s.get("k", 1)),
                "rho_primary": coherence_mean,          # proxy for now
                "coherence_mean": coherence_mean,
                "drift_mean": float(0.0),
                "crosstalk_max": float(0.0),
                "rho_trace": [float(x) for x in eval_window],  # REQUIRED
            }

        trace_raw = list(out.get("trace") or [])
        scenarios_out = out.get("scenarios") or {}

        # (1) SQI bundle (GX1-local attachment point)
        if bool(cfg.get("export_sqi_bundle")) or bool(sqi_cfg.get("enabled")):
            bundles: List[Dict[str, Any]] = []
            for sid in sorted(scenarios_out.keys()):
                s = scenarios_out[sid] or {}
                eval_window = [float(x) for x in (s.get("qscore_eval_window") or [])]
                bundles.append(
                    build_sqi_bundle(
                        scenario_id=str(sid),
                        mode=str(s.get("mode", "")),
                        seed=int(cfg["seed"]),
                        qscore_series=eval_window,
                        trace_events=None,
                    )
                )
            trace_raw.extend(bundles)

        core = {"scenario_summaries": scen, "trace": trace_raw}

    else:
        raise NotImplementedError(
            f"GX1 build_gx1_payload unsupported mode {mode!r} (expected 'sim' or 'sle'/'beam')"
        )

    # ---- Metrics (unchanged contract-facing summary) ----
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

    # ---- (2) SQI fabric stage (Mode C as pipeline stage) ----
    # NOTE: only runs when sqi.enabled and sqi.level=="fabric"
    if sqi_runtime_level == "fabric":
        from .sqi_fabric_runner import build_sqi_fabric_plan, run_sqi_fabric_plan_local

        scope = str(cfg.get("sqi", {}).get("plan_scope") or "run")
        max_jobs = int(cfg.get("sqi", {}).get("max_jobs") or 0)

        plan = build_sqi_fabric_plan(
            run_id=run_id,
            seed=int(cfg["seed"]),
            scope=scope,
            scenario_summaries=scen,
            max_jobs=max_jobs,
        )

        executor = str(cfg.get("sqi", {}).get("executor") or "local").lower()
        if executor == "ucs":
            from .sqi_executor_ucs import run_sqi_fabric_plan_ucs

            result = run_sqi_fabric_plan_ucs(
                plan=plan,
                scenario_summaries=scen,
                kg_write=bool(cfg.get("sqi", {}).get("kg_write")),
            )
        else:
            result = run_sqi_fabric_plan_local(
                plan=plan,
                scenario_summaries=scen,
                kg_write=bool(cfg.get("sqi", {}).get("kg_write")),
            )

        # Append deterministic plan/result records
        trace_raw = list(core.get("trace") or [])
        trace_raw.append({"trace_kind": "sqi_fabric_plan", "plan": plan})
        trace_raw.append(
            {
                "trace_kind": "sqi_fabric_result",
                "result": result,
                # deterministic anchors for replay/audit (path is run-dir relative)
                "kg_writes_count": int(len(result.get("kg_writes") or [])),
                "kg_writes_path": "SQI_KG_WRITES.jsonl",
            }
        )
        core["trace"] = trace_raw

        # Optional: minimal, stable anchors (counts only)
        metrics["summary"]["sqi_executor"] = str(cfg.get("sqi", {}).get("executor") or "local")
        metrics["summary"]["sqi_fabric_plan_id"] = str(plan.get("plan_id", ""))
        metrics["summary"]["sqi_fabric_job_count"] = int(len(plan.get("jobs") or []))
        metrics["summary"]["sqi_fabric_kg_write_count"] = int(len(result.get("kg_writes") or []))

    # ---- Filter trace last (must preserve critical kinds) ----
    trace_out = filter_trace(
        core.get("trace"),
        mode=str(cfg.get("trace_mode")),
        stride=int(cfg.get("trace_stride")),
        max_events=int(cfg.get("trace_max_events")),
    )

    # ---- (3) LEDGER export (optional; deterministic) ----
    ledger_cfg = cfg.get("ledger") or {}
    ledger_enabled = bool(ledger_cfg.get("enabled", False))

    ledger_rows: List[Dict[str, Any]] = []
    ledger_exports: Dict[str, Any] = {"enabled": False, "ledger_path": "", "ledger_count": 0, "ledger_digest": ""}

    if ledger_enabled:
        ledger_rows = build_ledger_rows(
            run_id=run_id,
            seed=int(cfg["seed"]),
            mode=mode,
            scenario_summaries=scen,
            trace=trace_out,
        )
        # path SHOULD be run-dir relative
        ledger_exports = build_ledger_exports(rows=ledger_rows, ledger_path="LEDGER.jsonl")

    git_rev = get_git_rev("/workspaces/COMDEX")

    replay = make_replay_bundle(
        config=cfg,
        metrics=metrics,
        trace=trace_out,
        git_rev=git_rev,
        run_id=run_id,
        ledger=ledger_exports,
    )

    return {
        "config": cfg,
        "metrics": metrics,
        "trace": trace_out,
        "replay_bundle": replay,
        "ledger_rows": ledger_rows,
        "git_rev": git_rev,
        "run_id": run_id,
        "phase_root": str(cfg["output_root"]),
        "mode": mode,
    }


def stable_hash(obj: Any) -> str:
    """
    Back-compat wrapper.
    Use backend.genome_engine.stable_json.stable_hash as the single canonical helper.
    """
    return _stable_hash(obj)