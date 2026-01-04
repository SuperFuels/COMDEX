from __future__ import annotations
from typing import Any, Dict, Union, List
import argparse
import json
from pathlib import Path

from .gx1_builder import build_gx1_payload
from .replay_bundle_writer import make_replay_bundle
from .artifacts_writer import write_artifacts, get_git_rev
from .genomics_scenarios import default_scenarios
from .genomics_metrics import checks as mk_checks
from .schema_validate import validate_or_raise
 



def run_genomics_benchmark(config_path_or_obj: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(config_path_or_obj, str):
        with open(config_path_or_obj, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = dict(config_path_or_obj)

    payload = build_gx1_payload(cfg)

    cfg = payload["config"]


    # builder-internal trace controls are not part of the config schema


    cfg.pop("mode", None)


    cfg.pop("stride", None)


    cfg.pop("max_events", None)
    run_id = payload["run_id"]
    git_rev = payload["git_rev"]
    phase_root = payload["phase_root"]
    metrics = payload["metrics"]

    # builder-internal trace controls are not part of the metrics schema

    metrics.pop("mode", None)

    metrics.pop("stride", None)

    metrics.pop("max_events", None)
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
