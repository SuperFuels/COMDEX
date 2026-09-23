#!/usr/bin/env python3
"""Exercise the complete Semantic Gateway and bounded SQI beam collapse."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    LearnedAtomSheetStore,
    verify_proof_receipt,
    verify_trace_chain,
)


CASES = (
    ("exact_calculation", "What is 15% of 240?", (), "calculation_atomsheet", False),
    (
        "governed_workflow_fallback",
        "Prepare a customer quotation. Do not book or take payment; human review is required.",
        ("Policy: every quotation must receive human approval.", "Unrelated stock note."),
        "model_fallback",
        True,
    ),
    ("ambiguous_calculation", "Add 15 percent tax to 200 or 250.", (), "model_fallback", True),
    ("general_fallback", "Explain why leaves change colour.", (), "model_fallback", True),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", default="sqi-gateway-v1")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    experiment_root = root / "runtime-evidence" / args.run_id
    if (experiment_root / "trace.jsonl").exists() or (experiment_root / "replay.sqlite3").exists():
        raise SystemExit("run-id already exists; use a fresh run-id to preserve prior evidence")
    learning_root = root / "learning" / "falsification-runs" / "multifamily-v4-domain-bounds"
    runtime = AdaptiveInferenceRuntime(
        replay_path=experiment_root / "replay.sqlite3",
        trace_path=experiment_root / "trace.jsonl",
        learned_store=LearnedAtomSheetStore(learning_root / "learning.sqlite3", learning_root / "promoted"),
    )
    results = []
    for case_id, text, context, expected_beam, requires_model in CASES:
        result = runtime.route(text, context=context)
        receipt = result.proof_receipt
        results.append({
            "case_id": case_id,
            "input": text,
            "result": result.to_dict(),
            "checks": {
                "ten_pipeline_stages": len(receipt["semantic_gateway_pipeline"]) == 10,
                "parallel_beam_mode": receipt["sqi_beam_mode"] == "bounded_deterministic_parallel_candidates",
                "expected_collapse": receipt["route_collapse"]["selected_beam_id"] == expected_beam,
                "expected_model_requirement": result.model_call_required is requires_model,
                "collapse_event_emitted": receipt["beam_events"][-1]["type"] == "semantic_route_collapse",
                "constraints_preserved": all(item in (result.fallback_prompt or "") for item in (
                    ("BOOKING_PROHIBITED", "PAYMENT_PROHIBITED", "HUMAN_REVIEW_REQUIRED")
                    if case_id == "governed_workflow_fallback" else ()
                )),
            },
        })
    trace_path = experiment_root / "trace.jsonl"
    acceptance = {
        "all_case_checks_pass": all(all(case["checks"].values()) for case in results),
        "workflow_discovered_without_unauthorised_execution": (
            results[1]["result"]["proof_receipt"]["workflow_lookup"]["workflow_id"]
            == "aion.workflow.quotation.review.v1"
            and results[1]["result"]["proof_receipt"]["workflow_lookup"]["executor_bound"] is False
        ),
        "different_general_meanings_have_distinct_glyphs": (
            results[2]["result"]["glyph_address"] != results[3]["result"]["glyph_address"]
        ),
        "trace_events_written": len(trace_path.read_text(encoding="utf-8").splitlines()) == len(results),
        "all_proof_receipts_canonically_bound": all(
            verify_proof_receipt(case["result"]["proof_receipt"]) for case in results
        ),
        "trace_ancestry_chain_valid": verify_trace_chain(trace_path),
    }
    report = {
        "schema_version": "aion.sqi_semantic_gateway_experiment.v1",
        "storage_root": str(root),
        "pipeline": [
            "Public Intent Gateway", "Semantic Transformer", "Glyph Meaning Compiler",
            "SQI Candidate Beams", "Route Collapse", "Replay / AtomSheet / CodexCore / Model",
        ],
        "beam_claim_boundary": "Parallel bounded deterministic route candidates using BeamEventBus telemetry; not neural sampling and not a photonic measurement.",
        "cases": results,
        "trace_path": str(trace_path),
        "trace_sha256": _sha256(trace_path),
        "acceptance": acceptance,
    }
    output = args.output or root / "experiments" / f"{args.run_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "acceptance": acceptance}, indent=2))
    return 0 if all(acceptance.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
