#!/usr/bin/env python3
"""Blind, multi-family falsification of learned AtomSheet promotion.

All model calls go to the explicitly supplied local Ollama endpoint. Model
answers enter quarantine and count toward promotion only after exact Decimal
verification. The report is written to external experiment storage.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from typing import Callable, Mapping

from backend.modules.aion_inference.learned_atomsheets import LearnedAtomSheetStore, VerifiedModelOutcome


NumericRule = Callable[[Decimal, Decimal], Decimal]


@dataclass(frozen=True)
class Family:
    intent: str
    fields: tuple[str, str]
    expected_template: str
    prompt: str
    rule: NumericRule
    cases: tuple[tuple[str, str], ...]


CASES = (
    ("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"),
    ("12", "50"), ("400", "7"), ("150", "12"), ("64", "25"),
    ("200", "5"), ("300", "30"), ("500", "8"), ("90", "40"),
    ("60", "15"), ("120", "20"), ("250", "4"), ("1000", "3"),
    ("40", "35"), ("320", "10"), ("75", "16"), ("600", "12"),
)

FAMILIES = (
    Family(
        "CALCULATE_MARKED_UP_PRICE", ("cost", "markup_percent"),
        "increase_a_percent_b.v1",
        "A product costs {a}. Apply a {b} percent markup. Return only the final numeric price with no currency, words, or working.",
        lambda a, b: a * (Decimal("1") + b / Decimal("100")), CASES,
    ),
    Family(
        "CALCULATE_DISCOUNTED_PRICE", ("cost", "discount_percent"),
        "decrease_a_percent_b.v1",
        "An item costs {a}. Apply a {b} percent discount. Return only the final numeric price with no currency, words, or working.",
        lambda a, b: a * (Decimal("1") - b / Decimal("100")), CASES,
    ),
    Family(
        "CALCULATE_PRICE_WITH_TAX", ("subtotal", "tax_percent"),
        "increase_a_percent_b.v1",
        "The pre-tax price is {a} and the sales tax rate is {b} percent. What is the total price including tax? Return only the final numeric total.",
        lambda a, b: a * (Decimal("1") + b / Decimal("100")), CASES,
    ),
    Family(
        "CALCULATE_LABOUR_COST", ("hourly_rate", "hours"),
        "product2.v1",
        "A worker charges {a} per hour and works {b} hours. Return only the final numeric labour cost with no currency, words, or working.",
        lambda a, b: a * b,
        (("20", "3"), ("25", "8"), ("18", "5"), ("40", "6"),
         ("32", "7"), ("50", "4"), ("15", "12"), ("28", "9"),
         ("60", "2"), ("35", "10"), ("22", "11"), ("45", "5"),
         ("30", "13"), ("55", "6"), ("24", "15"), ("80", "3"),
         ("16", "20"), ("42", "8"), ("70", "7"), ("27", "14")),
    ),
)

STRICT_NUMBER = re.compile(r"\s*([-+]?\d[\d,]*(?:\.\d+)?)\s*")


def _display(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _model_answer(
    base_url: str, model: str, prompt: str, *, structured_output: bool,
) -> tuple[str, Mapping[str, object]]:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "think": False,
        **({"format": {"type": "object", "properties": {"answer": {"type": "number"}},
                       "required": ["answer"], "additionalProperties": False}}
           if structured_output else {}),
        "options": {"temperature": 0, "seed": 0, "num_predict": 32},
    }).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        event = json.loads(response.read())
    raw = str(event.get("response", ""))
    if structured_output:
        envelope = json.loads(raw)
        if set(envelope) != {"answer"} or isinstance(envelope["answer"], bool):
            raise ValueError(f"invalid_structured_model_response:{raw!r}")
        return str(envelope["answer"]), event
    match = STRICT_NUMBER.fullmatch(raw)
    if not match:
        raise ValueError(f"non_numeric_model_response:{raw!r}")
    return match.group(1).replace(",", ""), event


def _run_family(
    store: LearnedAtomSheetStore, family: Family, base_url: str, model: str,
    *, structured_output: bool,
) -> dict:
    outcomes = []
    for index, (a, b) in enumerate(family.cases):
        prompt = family.prompt.format(a=a, b=b)
        raw, parsed, event, passed, detail = "", "0", {}, False, ""
        try:
            parsed, event = _model_answer(base_url, model, prompt, structured_output=structured_output)
            raw = str(event.get("response", ""))
            passed = Decimal(parsed) == family.rule(Decimal(a), Decimal(b))
            detail = "exact_decimal_match" if passed else "independent_decimal_mismatch"
        except (ValueError, InvalidOperation, OSError) as exc:
            raw = raw or f"{type(exc).__name__}:{exc}"
            detail = f"model_or_parse_error:{type(exc).__name__}"
        verifier = "decimal-forward-v1" if index % 2 == 0 else "decimal-recomputed-v1"
        decision = store.observe(VerifiedModelOutcome(
            intent=family.intent,
            inputs={family.fields[0]: a, family.fields[1]: b}, result=parsed,
            verifier_id=verifier, model_id=model,
            response_sha256=hashlib.sha256(raw.encode()).hexdigest(), verifier_passed=passed,
        ))
        outcomes.append({
            "prompt": prompt,
            "inputs": {family.fields[0]: a, family.fields[1]: b},
            "model_response": raw, "parsed_result": parsed,
            "verifier_id": verifier, "verifier_passed": passed,
            "verification_detail": detail,
            "prompt_tokens": event.get("prompt_eval_count"),
            "output_tokens": event.get("eval_count"),
            "load_duration_ns": event.get("load_duration"),
            "eval_duration_ns": event.get("eval_duration"),
            "decision_status_after_observation": decision.status,
        })

    decision = store.evaluate(family.intent)
    sheet = store.promoted(family.intent)
    unseen = []
    for i in range(1, 26):
        a = Decimal(137 + i * 11)
        b = Decimal(2 + i)
        inputs = {family.fields[0]: _display(a), family.fields[1]: _display(b)}
        execution = store.execute(family.intent, inputs)
        expected = _display(family.rule(a, b))
        unseen.append({
            "inputs": inputs, "expected": expected, "actual": execution.answer,
            "route": execution.route,
            "passed": execution.answer == expected and not execution.model_call_required,
        })
    return {
        "intent": family.intent, "formula_hidden_from_learner": True,
        "expected_template": family.expected_template,
        "actual_template": sheet.get("operator_template_id") if sheet else None,
        "model_attempts": len(outcomes),
        "strict_verified_answers": sum(item["verifier_passed"] for item in outcomes),
        "rejected_answers": sum(not item["verifier_passed"] for item in outcomes),
        "decision": decision.to_dict(), "outcomes": outcomes,
        "unseen_cases": unseen,
        "unseen_pass_count": sum(item["passed"] for item in unseen),
    }


def _adversarial_structured(store: LearnedAtomSheetStore) -> list[dict]:
    results = []
    for family in FAMILIES:
        f1, f2 = family.fields
        attacks = []
        for i in range(1, 31):
            attacks.extend((
                {f1: str(-i), f2: str(i)},
                {f1: "0", f2: str(i)},
                {f1: str(i), f2: str(-i)},
                {f1: str(i), f2: "0"},
                {f1: str(10**12 + i), f2: str(i)},
                {f1: str(i), f2: str(10**12 + i)},
            ))
            if f2.endswith("_percent"):
                attacks.append({f1: str(100 + i), f2: str(100 + i)})
        attacks.extend(({f1: "10"}, {f1: "10", f2: "2", "unexpected": "3"}))
        for inputs in attacks:
            execution = store.execute(family.intent, inputs)
            results.append({
                "intent": family.intent, "inputs": inputs, "route": execution.route,
                "reason": execution.proof_receipt.get("gate_reason"),
                "false_bypass": execution.route != "full_model",
            })
    for i in range(25):
        execution = store.execute(f"UNKNOWN_INTENT_{i}", {"a": "1", "b": "2"})
        results.append({"intent": f"UNKNOWN_INTENT_{i}", "route": execution.route,
                        "reason": execution.proof_receipt.get("gate_reason"),
                        "false_bypass": execution.route != "full_model"})
    return results


def _adversarial_language(store: LearnedAtomSheetStore) -> list[dict]:
    patterns = (
        "Apply {p}% markup to {c} and also 5% tax",
        "Apply {p}% markup to {c} and then send an invoice",
        "Apply {p}% markup to -{c}",
        "Apply {p}% markup to 0",
        "Apply a markup to {c}",
        "Apply {p}% markup to {c} or 250",
        "The year is 2026; apply {p}% markup to {c}",
    )
    results = []
    for i in range(1, 21):
        for pattern in patterns:
            prompt = pattern.format(p=5 + i, c=100 + i)
            execution = store.route_text(prompt)
            results.append({"prompt": prompt, "route": execution.route,
                            "reason": execution.proof_receipt.get("gate_reason"),
                            "false_bypass": execution.route != "full_model"})
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", default="multifamily-v1")
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--structured-output", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.expanduser().resolve()
    run_root = root / "learning" / "falsification-runs" / args.run_id
    if (run_root / "learning.sqlite3").exists():
        raise SystemExit(f"refusing to contaminate an existing run: {run_root}")
    store = LearnedAtomSheetStore(run_root / "learning.sqlite3", run_root / "promoted")
    families = [
        _run_family(store, family, args.base_url, args.model, structured_output=args.structured_output)
        for family in FAMILIES
    ]
    structured = _adversarial_structured(store)
    language = _adversarial_language(store)
    false_bypasses = sum(item["false_bypass"] for item in structured + language)
    acceptance = {
        "all_four_promoted": all(item["decision"]["status"] == "promoted" for item in families),
        "all_templates_correct": all(item["actual_template"] == item["expected_template"] for item in families),
        "all_100_unseen_cases_passed": all(item["unseen_pass_count"] == 25 for item in families),
        "zero_false_bypasses": false_bypasses == 0,
    }
    report = {
        "schema_version": "aion.multifamily_falsification.v1",
        "storage_root": str(root), "run_root": str(run_root), "model": args.model,
        "method": {
            "blind_prompts": True,
            "response_contract": "single-number JSON object" if args.structured_output else "bare number",
            "model_output_is_never_proof": True,
            "independent_verification": "exact Decimal recomputation",
            "promotion_gates": {"minimum_verified_observations": 6, "distinct_inputs": 6,
                                "independent_verifier_ids": 2, "holdout_observations": 2,
                                "unique_audited_operator_required": True},
        },
        "families": families,
        "adversarial": {
            "structured_case_count": len(structured), "language_case_count": len(language),
            "false_bypass_count": false_bypasses,
            "structured_results": structured, "language_results": language,
        },
        "acceptance": acceptance,
        "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": "Tests exact arithmetic AtomSheet induction and guarded replay only; it does not prove arbitrary reasoning, tokenizer/KV compression, or neural expert equivalence.",
    }
    output = args.output or root / "experiments" / "multifamily-falsification-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "result": report["result"], "acceptance": acceptance,
        "families": [{"intent": item["intent"], "verified": item["strict_verified_answers"],
                      "promoted": item["decision"]["status"], "template": item["actual_template"],
                      "unseen_pass": item["unseen_pass_count"]} for item in families],
        "adversarial_cases": len(structured) + len(language), "false_bypasses": false_bypasses,
    }, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
