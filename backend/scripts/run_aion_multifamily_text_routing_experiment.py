#!/usr/bin/env python3
"""Measure ordinary-English routing into the promoted multi-family cohort."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path
import statistics
import time

from backend.modules.aion_inference.learned_atomsheets import LearnedAtomSheetStore


def _display(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _percent_cases(label: str, operation: str):
    builders = {
        "markup": (
            lambda a, b: f"Apply {b}% markup to {a}",
            lambda a, b: f"Mark up {a} by {b} percent",
            lambda a, b: f"What is {a} with a {b}% markup?",
        ),
        "discount": (
            lambda a, b: f"Apply {b}% discount to {a}",
            lambda a, b: f"Take {b} percent off {a}",
            lambda a, b: f"Discount {a} by {b}%",
            lambda a, b: f"What is {a} with a {b}% discount?",
        ),
        "tax": (
            lambda a, b: f"Add {b}% sales tax to {a}",
            lambda a, b: f"What is {a} plus {b} percent tax?",
            lambda a, b: f"Total price including {b}% tax on {a}",
        ),
    }[label]
    for i in range(25):
        a, b = Decimal(110 + 7 * i), Decimal(3 + i)
        result = a * (Decimal("1") + b / 100) if operation == "increase" else a * (Decimal("1") - b / 100)
        yield builders[i % len(builders)](_display(a), _display(b)), _display(result)


def _valid_cases():
    yield from _percent_cases("markup", "increase")
    yield from _percent_cases("discount", "decrease")
    yield from _percent_cases("tax", "increase")
    labour_builders = (
        lambda rate, hours: f"{rate} per hour for {hours} hours",
        lambda rate, hours: f"Labour cost for {hours} hours at {rate} per hour",
    )
    for i in range(25):
        rate, hours = Decimal(18 + i), Decimal(2 + i)
        yield labour_builders[i % 2](_display(rate), _display(hours)), _display(rate * hours)


def _invalid_cases():
    patterns = (
        "Apply {p}% markup to {a} and also 5% tax",
        "Take {p}% off {a} and then pay the invoice",
        "Add {p}% tax to {a} and then email the customer",
        "Work for {h} hours at {r} per hour and then book the job",
        "Apply {p}% discount to {a} or {b}",
        "Add {p}% tax to {a} or {b}",
        "The year is 2026; mark up {a} by {p}%",
        "Discount {a} by {p}% and add tax",
        "Apply {p}% markup and discount to {a}",
        "Take {over}% off {a}",
        "Add {over}% tax to {a}",
        "Apply {over}% markup to {a}",
        "Take {p}% off -{a}",
        "Add {p}% tax to 0",
        "-{r} per hour for {h} hours",
        "{r} per hour for 0 hours",
        "Use {r} and {h} to find labour cost",
        "Apply a discount to {a}",
    )
    for i in range(25):
        values = {"p": 5 + i, "over": 101 + i, "a": 100 + i, "b": 200 + i,
                  "r": 20 + i, "h": 2 + i}
        for pattern in patterns:
            yield pattern.format(**values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", default="multifamily-v4-domain-bounds")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.expanduser().resolve()
    learning_root = root / "learning" / "falsification-runs" / args.run_id
    if not (learning_root / "learning.sqlite3").is_file():
        raise SystemExit(f"promoted learning cohort is missing: {learning_root}")
    store = LearnedAtomSheetStore(learning_root / "learning.sqlite3", learning_root / "promoted")
    status = dict(store.status())
    if status["promoted_atomsheets"] != 4:
        raise SystemExit(f"expected four promoted AtomSheets, found {status['promoted_atomsheets']}")

    valid_results, durations = [], []
    for prompt, expected in _valid_cases():
        started = time.perf_counter_ns()
        result = store.route_text(prompt)
        durations.append(time.perf_counter_ns() - started)
        passed = result.route == "verified_learned_atomsheet" and result.answer == expected and not result.model_call_required
        valid_results.append({"prompt": prompt, "expected": expected, "actual": result.answer,
                              "intent": result.intent, "route": result.route, "passed": passed})

    invalid_results = []
    for prompt in _invalid_cases():
        result = store.route_text(prompt)
        invalid_results.append({"prompt": prompt, "route": result.route,
                                "reason": result.proof_receipt.get("gate_reason"),
                                "false_bypass": result.route != "full_model"})

    sorted_durations = sorted(durations)
    acceptance = {
        "all_valid_phrasings_exact": all(item["passed"] for item in valid_results),
        "zero_invalid_false_bypasses": not any(item["false_bypass"] for item in invalid_results),
        "all_routes_avoided_model": all(item["route"] == "verified_learned_atomsheet" for item in valid_results),
    }
    report = {
        "schema_version": "aion.multifamily_text_routing_experiment.v1",
        "storage_root": str(root), "learning_run_id": args.run_id,
        "promoted_contracts": {
            intent: store.promoted(intent)["contract_sha256"]
            for intent in ("CALCULATE_MARKED_UP_PRICE", "CALCULATE_DISCOUNTED_PRICE",
                           "CALCULATE_PRICE_WITH_TAX", "CALCULATE_LABOUR_COST")
        },
        "valid": {"case_count": len(valid_results), "pass_count": sum(item["passed"] for item in valid_results),
                  "results": valid_results},
        "invalid": {"case_count": len(invalid_results),
                    "false_bypass_count": sum(item["false_bypass"] for item in invalid_results),
                    "results": invalid_results},
        "latency": {"median_ms": statistics.median(durations) / 1_000_000,
                    "p95_ms": sorted_durations[int(len(sorted_durations) * .95) - 1] / 1_000_000},
        "acceptance": acceptance, "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": "This tests a bounded English grammar over four promoted arithmetic intents, not unrestricted language understanding.",
    }
    output = args.output or root / "experiments" / "multifamily-text-routing-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "valid": f"{report['valid']['pass_count']}/{report['valid']['case_count']}",
                      "invalid_cases": report["invalid"]["case_count"],
                      "false_bypasses": report["invalid"]["false_bypass_count"],
                      "median_ms": report["latency"]["median_ms"], "p95_ms": report["latency"]["p95_ms"]}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
