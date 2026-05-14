from __future__ import annotations

from typing import Any, Dict, Union
import argparse
import json
from pathlib import Path

from backend.utils.log_gate import tprint

from .gx1_builder import build_gx1_payload
from .sqi_kg_writes_writer import extract_sqi_kg_writes, write_sqi_kg_writes_jsonl
from .schema_validate import validate_or_raise
from .artifacts_writer import write_artifacts


_INTERNAL_KEYS = ("mode", "stride", "max_events")

# Canonical example config path (avoid "path/to/config.json" confusion)
_EXAMPLE_CFG = "/workspaces/COMDEX/backend/genome_engine/examples/gx1_config.json"


def _strip_internal_keys(d: Dict[str, Any]) -> None:
    # Builder/internal trace controls MUST NOT leak into exported schema objects.
    for k in _INTERNAL_KEYS:
        d.pop(k, None)


def run_genomics_benchmark(config_path_or_obj: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(config_path_or_obj, str):
        cfg_path = Path(config_path_or_obj)
        if not cfg_path.exists():
            raise FileNotFoundError(
                f"GX1 config not found: {cfg_path}\n\n"
                f"Try the repo example config:\n"
                f"  {_EXAMPLE_CFG}\n\n"
                f"Example command:\n"
                f"  cd /workspaces/COMDEX && \\\n"
                f"  TESSARIS_TEST_QUIET=1 TESSARIS_DETERMINISTIC_TIME=1 PYTHONPATH=/workspaces/COMDEX \\\n"
                f"  python -m backend.genome_engine.run_genomics_benchmark --config {_EXAMPLE_CFG}\n"
            )
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg: Dict[str, Any] = json.load(f)
    else:
        cfg = dict(config_path_or_obj)

    payload = build_gx1_payload(cfg)

    # Use canonical post-build config for schema + export decisions
    cfg = dict(payload["config"])
    _strip_internal_keys(cfg)

    # --- SQI fabric: optional server-free KG write-intents artifact (JSONL) ---
    # This stage is intentionally "artifact-only" (no live KG, no UCS hub, no servers).
    sqi_cfg0 = dict(cfg.get("sqi") or {})
    sqi_level = str(sqi_cfg0.get("level") or ("bundle" if bool(cfg.get("export_sqi_bundle")) else "off"))
    sqi_enabled = bool(cfg.get("export_sqi_bundle")) or bool(sqi_cfg0.get("enabled"))
    kg_write = bool(sqi_cfg0.get("kg_write", False))

    if sqi_enabled and sqi_level == "fabric" and kg_write:
        kg_writes = extract_sqi_kg_writes(payload.get("trace"))
        out_path = Path(payload["phase_root"]) / "runs" / payload["run_id"] / "SQI_KG_WRITES.jsonl"
        info = write_sqi_kg_writes_jsonl(out_path, kg_writes)

        # Add light audit anchors into replay bundle (only if enabled).
        rb = payload.get("replay_bundle")
        if isinstance(rb, dict):
            exports = rb.setdefault("exports", {})
            sqi_exp = exports.setdefault("sqi", {})
            sqi_exp["kg_writes_count"] = int(info["count"])
            sqi_exp["kg_writes_digest"] = str(info["sha256"])
            sqi_exp["kg_writes_path"] = f"runs/{payload['run_id']}/SQI_KG_WRITES.jsonl"

    run_id: str = payload["run_id"]
    git_rev: str = payload["git_rev"]
    phase_root: str = payload["phase_root"]

    metrics: Dict[str, Any] = dict(payload["metrics"])
    _strip_internal_keys(metrics)

    trace_out = payload["trace"]
    replay = payload["replay_bundle"]

    # --- schema hygiene: never validate/serialize builder-internal sqi keys ---
    if isinstance(cfg.get("sqi"), dict):
        cfg["sqi"] = {k: v for k, v in cfg["sqi"].items() if not str(k).startswith("_")}

    # ---- SQI config normalization (must happen before schema validation) ----
    sqi_cfg = dict(cfg.get("sqi") or {})
    if isinstance(sqi_cfg, dict):
        # internal runtime hint must never hit schema validation
        sqi_cfg.pop("_runtime_level", None)
        if sqi_cfg:
            cfg["sqi"] = sqi_cfg
        else:
            cfg.pop("sqi", None)

    # Fail-fast contract validation (schemas)
    validate_or_raise("gx1_genome_benchmark_config.schema.json", cfg)
    validate_or_raise("gx1_genome_benchmark_metrics.schema.json", metrics)
    validate_or_raise("gx1_replay_bundle.schema.json", replay)

    repo_root = str(Path(__file__).resolve().parents[2])

    info = write_artifacts(
        repo_root=repo_root,
        phase_root=phase_root,
        run_id=run_id,
        config=cfg,
        metrics=metrics,
        trace=trace_out,
        replay_bundle=replay,
        ledger_rows=payload.get("ledger_rows"),
    )

    # ✅ Return payload surfaces + artifact locations (tests expect metrics/trace/replay_bundle)
    out: Dict[str, Any] = dict(payload)
    if isinstance(info, dict):
        out.update(info)

    out["status"] = metrics.get("status", "UNKNOWN")
    out["run_id"] = run_id
    out["git_rev"] = git_rev
    out["phase_root"] = phase_root
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run GX1 deterministic genomics benchmark (SIM).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Recommended example:\n"
            f"  cd /workspaces/COMDEX && \\\n"
            f"  TESSARIS_TEST_QUIET=1 TESSARIS_DETERMINISTIC_TIME=1 PYTHONPATH=/workspaces/COMDEX \\\n"
            f"  python -m backend.genome_engine.run_genomics_benchmark --config {_EXAMPLE_CFG}\n"
        ),
    )
    ap.add_argument(
        "--config",
        required=True,
        help=f"Path to GX1 config JSON (try: {_EXAMPLE_CFG})",
    )
    args = ap.parse_args()

    r = run_genomics_benchmark(args.config)

    # Use gated prints so tests/CI can suppress noise via TESSARIS_TEST_QUIET=1.
    tprint(f"✅ GX1 done: run_id={r['run_id']} status={r.get('status','UNKNOWN')}")
    tprint(f"   phase_root={r['phase_root']}")
    tprint(f"   run_dir={r.get('run_dir','')}")


if __name__ == "__main__":
    main()
