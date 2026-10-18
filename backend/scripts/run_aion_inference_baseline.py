"""Run the Phase 0 AION inference truth baseline."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from backend.modules.aion_inference import (
    OllamaStreamingClient,
    collect_machine_inventory,
    collect_model_store_evidence,
    load_workloads,
    run_baseline,
)
from backend.modules.aion_inference.baseline import DEFAULT_WORKLOAD_PATH


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--workloads", type=Path, default=DEFAULT_WORKLOAD_PATH)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--storage-root", type=Path, default=os.getenv("AION_INFERENCE_STORAGE_ROOT"))
    parser.add_argument("--probe-storage", action="store_true")
    parser.add_argument("--model-store", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    cases = load_workloads(args.workloads)
    if args.case_ids:
        selected = set(args.case_ids)
        cases = [case for case in cases if case.case_id in selected]
        missing = sorted(selected - {case.case_id for case in cases})
        if missing:
            parser.error(f"unknown workload case(s): {', '.join(missing)}")

    machine = collect_machine_inventory(args.storage_root, probe_storage=args.probe_storage)
    machine["runtime_endpoint"] = args.base_url
    if args.model_store:
        machine["model_store"] = collect_model_store_evidence(args.model_store, args.model)

    report = run_baseline(
        model=args.model,
        cases=cases,
        client=OllamaStreamingClient(base_url=args.base_url),
        machine=machine,
        workload_manifest_bytes=args.workloads.read_bytes(),
    )
    rendered = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
