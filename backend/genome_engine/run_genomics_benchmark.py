from __future__ import annotations

from typing import Any, Dict, Union
import argparse
import json
from pathlib import Path

from backend.utils.log_gate import tprint

from .gx1_builder import build_gx1_payload
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

    cfg = dict(payload["config"])
    _strip_internal_keys(cfg)

    run_id: str = payload["run_id"]
    git_rev: str = payload["git_rev"]
    phase_root: str = payload["phase_root"]

    metrics: Dict[str, Any] = dict(payload["metrics"])
    _strip_internal_keys(metrics)

    trace_out = payload["trace"]
    replay = payload["replay_bundle"]

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
    )

    return {
        "run_id": run_id,
        "phase_root": phase_root,
        "run_dir": info["run_dir"],
        "git_rev": git_rev,
        "status": metrics.get("status", "UNKNOWN"),
    }


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
    tprint(f"✅ GX1 done: run_id={r['run_id']} status={r['status']}")
    tprint(f"   phase_root={r['phase_root']}")
    tprint(f"   run_dir={r['run_dir']}")


if __name__ == "__main__":
    main()