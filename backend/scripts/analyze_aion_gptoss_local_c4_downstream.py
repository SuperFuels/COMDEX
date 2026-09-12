#!/usr/bin/env python3
"""Compare a local-C4 roll-forward with its unrestricted teacher trajectory."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    teacher = json.loads(args.teacher.read_text())
    candidate = json.loads(args.candidate.read_text())
    if teacher["token_count"] != candidate["token_count"]:
        raise SystemExit("teacher and candidate token counts differ")
    if not candidate.get("local_c4_cartridge_sha256"):
        raise SystemExit("candidate has no bound local C4 cartridge")

    ordered_routes = []
    route_sets = []
    top_experts = []
    layer_outputs = []
    token_differences = []
    second_token_differences = []
    applications = []
    chosen_logit_deltas = []
    second_logit_deltas = []
    margin_deltas = []
    normalized_dangers = []
    for position, (reference, changed) in enumerate(zip(
            teacher["run_a"]["tokens"], candidate["run_a"]["tokens"], strict=True)):
        if reference["generated_token_id"] != changed["generated_token_id"]:
            token_differences.append(position)
        if reference["output"]["second_token_id"] != changed["output"]["second_token_id"]:
            second_token_differences.append(position)
        chosen_logit_deltas.append(abs(
            reference["output"]["max_logit"] - changed["output"]["max_logit"]
        ))
        second_logit_deltas.append(abs(
            reference["output"]["second_logit"] - changed["output"]["second_logit"]
        ))
        margin_deltas.append(abs(
            reference["output"]["margin"] - changed["output"]["margin"]
        ))
        normalized_dangers.append(max(
            chosen_logit_deltas[-1], second_logit_deltas[-1]
        ) / max(abs(reference["output"]["margin"]), 1e-30))
        for layer, (original, altered) in enumerate(zip(
                reference["layers"], changed["layers"], strict=True)):
            address = {"position": position, "layer": layer}
            if altered.get("local_c4_applied"):
                applications.append({
                    **address,
                    "joint_cosine": altered["local_c4_joint_cosine"],
                })
            if original["route"] != altered["route"]:
                ordered_routes.append(address)
            if set(original["route"]) != set(altered["route"]):
                route_sets.append(address)
            if original["route"][0] != altered["route"][0]:
                top_experts.append(address)
            if original["output_sha256"] != altered["output_sha256"]:
                layer_outputs.append(address)

    token_stable = not token_differences and not second_token_differences
    trajectory_identical = not ordered_routes and not layer_outputs
    if not applications:
        raise SystemExit("candidate did not apply the local C4 cartridge")
    first_application_position = min(row["position"] for row in applications)
    downstream_dangers = normalized_dangers[first_application_position:]
    status = ("FULL_DOWNSTREAM_IDENTITY"
              if token_stable and trajectory_identical else
              "TOKEN_STABLE_DOWNSTREAM_DRIFT" if token_stable else
              "STOP_LOCAL_C4_DOWNSTREAM_DIVERGENCE")
    report = {
        "schema": "aion.gptoss-120b-local-c4-downstream-gate.v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_track": True,
        "positions": teacher["token_count"],
        "applications": applications,
        "application_calls_all_candidate_passes": candidate["local_c4_applied_calls"],
        "candidate_internally_repeatable": candidate[
            "final_hidden_and_logits_bitwise_repeatable"
        ],
        "token_differences": token_differences,
        "second_token_differences": second_token_differences,
        "ordered_route_differences": len(ordered_routes),
        "route_set_differences": len(route_sets),
        "top_expert_differences": len(top_experts),
        "layer_output_hash_differences": len(layer_outputs),
        "first_ordered_route_difference": ordered_routes[:1],
        "first_route_set_difference": route_sets[:1],
        "maximum_abs_chosen_logit_delta": max(chosen_logit_deltas),
        "p95_abs_chosen_logit_delta": float(np.percentile(chosen_logit_deltas, 95)),
        "maximum_abs_second_logit_delta": max(second_logit_deltas),
        "maximum_abs_margin_delta": max(margin_deltas),
        "p95_abs_margin_delta": float(np.percentile(margin_deltas, 95)),
        "downstream_normalized_margin_danger_p50": float(np.percentile(
            downstream_dangers, 50
        )),
        "downstream_normalized_margin_danger_p95": float(np.percentile(
            downstream_dangers, 95
        )),
        "downstream_normalized_margin_danger_max": max(downstream_dangers),
        "downstream_normalized_margin_danger_max_position": (
            first_application_position + int(np.argmax(downstream_dangers))
        ),
        "teacher_final_margin": teacher["run_a"]["output"]["margin"],
        "candidate_final_margin": candidate["run_a"]["output"]["margin"],
        "teacher_sha256": digest(args.teacher),
        "candidate_sha256": digest(args.candidate),
        "cartridge_sha256": candidate["local_c4_cartridge_sha256"],
        "claim_boundary": (
            "All reported downstream comparisons use pass A of separately repeatable "
            "teacher and candidate receipts. Identical token IDs do not imply identical "
            "hidden states, routes or logits. Full logit vectors were hash-bound but not "
            "retained, so scalar drift covers the recorded winning and runner-up logits. "
            "This gate does not establish semantic breadth or a speed improvement."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "positions", "applications", "token_differences",
        "ordered_route_differences", "route_set_differences",
        "top_expert_differences", "maximum_abs_chosen_logit_delta",
        "canonical_sha256",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
