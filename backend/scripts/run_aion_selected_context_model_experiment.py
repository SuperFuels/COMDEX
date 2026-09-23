#!/usr/bin/env python3
"""Paired Qwen test of full versus policy-preserving selected context."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import urllib.request

from backend.modules.aion_inference.adaptive_runtime import ContextSelector


SCHEMA = {
    "type": "object",
    "properties": {
        "width": {"type": "number"}, "length": {"type": "number"},
        "booking_allowed": {"type": "boolean"}, "payment_allowed": {"type": "boolean"},
        "human_review_required": {"type": "boolean"},
    },
    "required": ["width", "length", "booking_allowed", "payment_allowed", "human_review_required"],
    "additionalProperties": False,
}

POLICIES = (
    "Policy: every patio quotation must receive human approval before release.",
    "Payment is prohibited during patio quotation preparation.",
    "Never book patio installation while preparing a quotation.",
)

DISTRACTORS = (
    "The warehouse inventory review covers spare screws, packaging tape, protective gloves and cleaning supplies.",
    "An unrelated office note says the upstairs coffee machine is blue and will be serviced next quarter.",
    "Archived landscaping records discuss hedge trimming, tree surveys and irrigation maintenance from prior years.",
    "The marketing team is comparing newsletter layouts, photography styles and seasonal campaign headlines.",
    "A supplier catalogue lists timber stains, fence panels, garden lighting and several decorative stone finishes.",
    "Historic customer feedback mentions driveway cleaning, window repairs and indoor painting projects.",
    "The vehicle log records fuel checks, tyre inspections and routine servicing for the delivery van.",
    "A training memo describes telephone etiquette, document naming and general office filing conventions.",
    "The canteen order includes tea, coffee, fruit, biscuits and reusable cups for the weekly meeting.",
    "An old project calendar contains landscaping appointments that are unrelated to the current customer request.",
)


def _generate(base_url: str, model: str, query: str, context: tuple[str, ...]) -> tuple[dict, dict]:
    prompt = (
        "Use only the supplied context. Return width and length as numbers and the three policy decisions.\n"
        f"REQUEST: {query}\nCONTEXT:\n- " + "\n- ".join(context)
    )
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "think": False, "format": SCHEMA,
        "options": {"temperature": 0, "seed": 0, "num_predict": 80},
    }).encode()
    request = urllib.request.Request(base_url.rstrip("/") + "/api/generate", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        event = json.loads(response.read())
    return json.loads(str(event["response"])), event


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--cases", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.storage_root.expanduser().resolve()
    selector = ContextSelector()
    results = []
    for index in range(args.cases):
        width, length = 3 + index, 5 + index * 2
        fact = f"Current customer patio dimensions are exactly {width} metres wide and {length} metres long."
        context = (fact, *POLICIES, *DISTRACTORS)
        query = "Extract the current patio width and length and decide booking, payment and human-review policy."
        selection = selector.select(query, context, max_bytes=320)
        expected = {"width": width, "length": length, "booking_allowed": False,
                    "payment_allowed": False, "human_review_required": True}
        full_answer, full_event = _generate(args.base_url, args.model, query, context)
        selected_answer, selected_event = _generate(args.base_url, args.model, query, selection.selected)
        full_tokens, selected_tokens = int(full_event["prompt_eval_count"]), int(selected_event["prompt_eval_count"])
        results.append({
            "case": index + 1, "expected": expected, "full_answer": full_answer,
            "selected_answer": selected_answer, "full_correct": full_answer == expected,
            "selected_correct": selected_answer == expected,
            "answers_equivalent": full_answer == selected_answer,
            "full_prompt_tokens": full_tokens, "selected_prompt_tokens": selected_tokens,
            "token_reduction_percent": (1 - selected_tokens / full_tokens) * 100,
            "original_context_bytes": selection.original_utf8_bytes,
            "selected_context_bytes": selection.selected_utf8_bytes,
            "policy_passages_preserved": selection.policy_passages_preserved,
            "selected_context": selection.selected,
        })
    reductions = [item["token_reduction_percent"] for item in results]
    acceptance = {
        "all_full_answers_correct": all(item["full_correct"] for item in results),
        "all_selected_answers_correct": all(item["selected_correct"] for item in results),
        "all_answers_equivalent": all(item["answers_equivalent"] for item in results),
        "all_policies_preserved": all(item["policy_passages_preserved"] == 3 for item in results),
        "prompt_tokens_reduced_every_case": all(item["selected_prompt_tokens"] < item["full_prompt_tokens"] for item in results),
    }
    report = {
        "schema_version": "aion.selected_context_model_experiment.v1",
        "storage_root": str(root), "model": args.model, "case_count": len(results),
        "results": results,
        "summary": {"median_token_reduction_percent": statistics.median(reductions),
                    "minimum_token_reduction_percent": min(reductions),
                    "full_correct": sum(item["full_correct"] for item in results),
                    "selected_correct": sum(item["selected_correct"] for item in results)},
        "acceptance": acceptance, "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": "This measures real Qwen prompt-token reduction from policy-preserving context selection. Glyph dictionary transport and neural KV-cache compression remain separate claims.",
    }
    output = args.output or root / "experiments" / "selected-context-model-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "summary": report["summary"], "acceptance": acceptance}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
