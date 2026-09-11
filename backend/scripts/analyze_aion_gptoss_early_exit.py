#!/usr/bin/env python3
"""Summarise diagnostic intermediate-head agreement without changing inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--family", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--thresholds", default="0.25,0.5,1,2,4,8")
    args = parser.parse_args()
    if len(args.input) != len(args.family):
        raise SystemExit("each input requires one family label")
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    thresholds = [float(value) for value in args.thresholds.split(",")]
    families = []
    aggregate: dict[int, list[tuple[bool, float]]] = {}
    for path, family in zip(args.input, args.family):
        source = json.loads(path.read_text())
        runs = [source["run_a"], source["run_b"], *source.get("additional_runs", [])]
        prompt_positions = len(source["input_token_ids"])
        observations: dict[int, list[tuple[bool, float]]] = {}
        for run in runs:
            for token in run["tokens"]:
                if token["position"] < prompt_positions:
                    continue
                for layer in token["layers"]:
                    diagnostic = layer.get("early_exit_diagnostic")
                    if diagnostic is None:
                        continue
                    row = (
                        diagnostic["argmax_token_id"] == token["generated_token_id"],
                        diagnostic["margin"],
                    )
                    observations.setdefault(layer["layer"], []).append(row)
                    aggregate.setdefault(layer["layer"], []).append(row)

        def summarise(rows: list[tuple[bool, float]]) -> dict:
            gates = []
            for threshold in thresholds:
                accepted = [match for match, margin in rows if margin >= threshold]
                gates.append(
                    {
                        "margin_threshold": threshold,
                        "accepted_observations": len(accepted),
                        "matching_observations": sum(accepted),
                        "precision": sum(accepted) / len(accepted) if accepted else None,
                    }
                )
            return {
                "observations": len(rows),
                "matching_observations": sum(match for match, _ in rows),
                "unconditional_agreement": sum(match for match, _ in rows) / len(rows),
                "confidence_gates": gates,
            }

        families.append(
            {
                "family": family,
                "source_path": str(path.resolve()),
                "source_canonical_sha256": source["canonical_sha256"],
                "prompt_positions": prompt_positions,
                "continuation_observations_per_pass": source["token_count"] - prompt_positions,
                "passes": source["passes"],
                "layers": {str(layer): summarise(rows) for layer, rows in sorted(observations.items())},
            }
        )
    report = {
        "schema": "aion.gptoss-120b-early-exit-diagnostic-receipt.v1",
        "status": "DIAGNOSTIC_ONLY",
        "families": families,
        "aggregate_layers": {str(layer): summarise(rows) for layer, rows in sorted(aggregate.items())},
        "claim_boundary": (
            "Intermediate hidden states were projected through the original final norm and output head and compared with the final full-depth argmax. "
            "The authoritative 36-layer path was not changed. Repeated observations from the same deterministic sequence establish repeatability, not independent statistical confidence. "
            "Early emission would not remove the need to build skipped-layer KV state for later tokens; therefore this receipt is not throughput evidence."
        ),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"canonical_sha256": report["canonical_sha256"], "status": report["status"]}))


if __name__ == "__main__":
    main()
