#!/usr/bin/env python3
"""Run learning, context, and addressed-shard experiments on external storage."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import uuid

from backend.modules.aion_inference.glyph_context import GlyphContextDictionary
from backend.modules.aion_inference.learned_atomsheets import LearnedAtomSheetStore, VerifiedModelOutcome
from backend.modules.aion_inference.shard_selection import AddressedShardExperiment


MARKUP_CASES = (("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7"), ("150", "12"), ("64", "37.5"), ("200", "10"), ("300", "10"), ("500", "20"), ("90", "10"), ("60", "25"), ("120", "50"), ("250", "8"), ("1000", "5"), ("40", "15"), ("320", "25"), ("75", "20"), ("600", "12"))
CONTEXT = (
    "Policy: every quotation must receive human approval.",
    "Do not take payment without a second confirmation.",
    "Customer asked for a patio quotation and supplied dimensions.",
)


def _ollama_numeric(base_url: str, model: str, cost: str, markup: str) -> tuple[str, dict]:
    prompt = f"A product costs {cost}. Apply a {markup} percent markup. Return only the final numeric price with no currency, words, or working."
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "think": False,
        "options": {"temperature": 0, "seed": 0, "num_predict": 32},
    }).encode()
    request = urllib.request.Request(base_url.rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        event = json.loads(response.read())
    text = str(event.get("response", "")).strip()
    match = re.fullmatch(r"\s*([-+]?\d[\d,]*(?:\.\d+)?)\s*", text)
    if not match:
        raise ValueError(f"model did not obey numeric-only response contract: {text!r}")
    return match.group(1).replace(",", ""), event


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--context-repetitions", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.storage_root.expanduser().resolve()
    store = LearnedAtomSheetStore(root / "learning" / "blind-v1" / "learning.sqlite3", root / "learning" / "blind-v1" / "promoted")
    outcomes, last_decision = [], None
    for index, (cost, markup) in enumerate(MARKUP_CASES):
        response_text, event, verified, parsed, detail = "", {}, False, "0", ""
        verifier_id = "decimal-forward-v1" if index % 2 == 0 else "decimal-inverse-v1"
        try:
            parsed, event = _ollama_numeric(args.base_url, args.model, cost, markup)
            response_text = str(event.get("response", ""))
            result, cost_value, markup_value = Decimal(parsed), Decimal(cost), Decimal(markup)
            if index % 2:
                verified = result * Decimal("100") == cost_value * (Decimal("100") + markup_value)
            else:
                verified = result == cost_value * (Decimal("1") + markup_value / Decimal("100"))
            detail = "exact_decimal_match" if verified else "independent_decimal_mismatch"
        except (ValueError, InvalidOperation, OSError) as exc:
            detail = f"model_or_parse_error:{type(exc).__name__}"
            response_text = response_text or detail
        last_decision = store.observe(VerifiedModelOutcome(
            intent="CALCULATE_MARKED_UP_PRICE", inputs={"cost": cost, "markup_percent": markup}, result=parsed,
            verifier_id=verifier_id, model_id=args.model, response_sha256=hashlib.sha256(response_text.encode()).hexdigest(),
            verifier_passed=verified,
        ))
        outcomes.append({
            "cost": cost, "markup_percent": markup, "model_response": response_text, "parsed_result": parsed,
            "verifier_id": verifier_id, "verifier_passed": verified, "verification_detail": detail,
            "prompt_tokens": event.get("prompt_eval_count"), "output_tokens": event.get("eval_count"),
            "load_duration_ns": event.get("load_duration"), "eval_duration_ns": event.get("eval_duration"),
        })

    learned_execution = store.execute("CALCULATE_MARKED_UP_PRICE", {"cost": "225", "markup_percent": "16"})
    adversarial_prompts = (
        "Apply 16% markup to 225 and also 5% tax",
        "Apply 16% markup to 225 and then send an invoice",
        "Apply 16% markup to -225",
        "Apply 16% markup to 0",
        "Apply a markup to 225",
        "Apply 16% markup to 225 or 250",
        "The year is 2026; apply 16% markup to 225",
    )
    adversarial_results = [
        {"prompt": prompt, "route": (result := store.route_text(prompt)).route, "reason": result.proof_receipt.get("gate_reason")}
        for prompt in adversarial_prompts
    ]
    context_run_id = uuid.uuid4().hex
    sender = GlyphContextDictionary(root / "glyph-context" / "runs" / context_run_id / "sender.sqlite3")
    receiver = GlyphContextDictionary(root / "glyph-context" / "runs" / context_run_id / "receiver.sqlite3")
    first_packet = sender.encode(CONTEXT, receiver_known_slots=receiver.known_slots())
    exact, packets = receiver.decode(first_packet) == CONTEXT, [first_packet]
    for _ in range(args.context_repetitions - 1):
        packet = sender.encode(CONTEXT, receiver_known_slots=receiver.known_slots())
        exact = exact and receiver.decode(packet) == CONTEXT
        packets.append(packet)
    context_summary = dict(sender.transmission_summary(packets))
    context_summary.update({"exact_reconstruction_passed": exact, "policy_passages_per_packet": 2, "first_packet_definitions": len(first_packet.definitions)})
    shard_report = AddressedShardExperiment(root / "shard-experiments" / "synthetic-moe-v1").run(
        layer_count=8, experts_per_layer=8, selected_per_layer=2, common_bytes=128 * 1024,
        expert_bytes=256 * 1024, iterations=7,
    )
    report = {
        "schema_version": "aion.learning_context_shards.experiment.v1", "storage_root": str(root), "model": args.model,
        "learning": {"blind_formula_prompting": True, "outcomes": outcomes, "verified_outcome_count_this_run": sum(item["verifier_passed"] for item in outcomes), "rejected_outcome_count_this_run": sum(not item["verifier_passed"] for item in outcomes), "decision": last_decision.to_dict() if last_decision else None, "unseen_execution": learned_execution.to_dict(), "adversarial_results": adversarial_results, "false_bypass_count": sum(item["route"] != "full_model" for item in adversarial_results), "status": store.status()},
        "glyph_context": context_summary, "addressed_shards": shard_report,
        "claim_boundary": {
            "learning": "promotion requires model outputs plus independent exact verification; model output alone is never proof",
            "context": "exact repeated transport compression, not yet tokenizer/KV-cache compression",
            "shards": "synthetic addressed storage read, not neural MoE output equivalence",
        },
    }
    output = args.output or root / "experiments" / "learning-context-shards-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report["learning"]["status"], "glyph_context": context_summary, "shard_byte_reduction_percent": shard_report["measured_byte_reduction_percent"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
