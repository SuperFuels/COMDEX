#!/usr/bin/env python3
"""Build the family-disjoint capture plan for local fourth-expert corrections."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_gguf_tokenizer import GptOssGGUFTokenizer


PROMPTS = {
    "arithmetic": [
        "A shop sold 18 items at 7 euros each. What was the total revenue?",
        "A bill of 240 euros is reduced by 15 percent. What is the new total?",
        "Three boxes contain 24 parts each. Seven parts are removed. How many remain?",
        "A worker completes 9 orders per hour for 6 hours. How many orders are completed?",
        "A 480 euro cost is shared equally by 12 people. How much does each person pay?",
        "A product costs 80 euros and has a 25 percent markup. What is its selling price?",
    ],
    "extraction": [
        "Extract the company, amount and due date: Northwind owes 4,200 euros by 18 June.",
        "Extract the person, city and meeting time: Elena meets Marco in Valencia at 14:30.",
        "Extract the product, quantity and price: The order contains 36 blue mugs at 8 euros each.",
        "Extract the supplier and delivery date: Cedar Foods will deliver on 7 October.",
        "Extract the customer, invoice number and status: Rivera Ltd, invoice 814, remains unpaid.",
        "Extract the project, owner and deadline: Project Aurora is owned by Priya and due Friday.",
    ],
    "reasoning": [
        "Every copper key opens the blue door. This key is copper. What follows?",
        "All fragile parcels require careful handling. This parcel is fragile. What follows?",
        "No closed shop is serving customers. The shop is closed. What follows?",
        "Every approved request has a reference number. This request is approved. What follows?",
        "All refrigerated goods must remain cold. These goods are refrigerated. What follows?",
        "Every trained operator may use the machine. Lina is a trained operator. What follows?",
    ],
    "business": [
        "Give three practical steps a small cafe can take to reduce food waste.",
        "Suggest three ways a local plumber can reduce missed appointments.",
        "List three low-cost actions a small retailer can use to improve repeat sales.",
        "Give three steps a freelance designer can take to improve invoice collection.",
        "Suggest three practical ways a bakery can shorten customer waiting time.",
        "List three actions a small repair shop can use to reduce parts shortages.",
    ],
    "explanation": [
        "Explain in one sentence why wet roads can be slippery.",
        "Explain in one sentence why plants need sunlight.",
        "Explain in one sentence why metal expands when heated.",
        "Explain in one sentence why passwords should be unique.",
        "Explain in one sentence why ice floats on water.",
        "Explain in one sentence why regular backups are useful.",
    ],
    "writing": [
        "Write a polite one-sentence reminder that a payment is overdue.",
        "Write a friendly one-sentence confirmation of a meeting tomorrow morning.",
        "Write a concise one-sentence apology for a delayed delivery.",
        "Write a professional one-sentence request for missing account details.",
        "Write a warm one-sentence thank-you message for a customer referral.",
        "Write a clear one-sentence notice that office hours have changed.",
    ],
}

SPLITS = ("training", "training", "training", "training", "selection", "holdout")


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--continuation-tokens", type=int, default=16)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.continuation_tokens < 8:
        raise SystemExit("at least eight continuation tokens are required")

    tokenizer = GptOssGGUFTokenizer.from_warehouse(args.manifest)
    rows = []
    for family, prompts in PROMPTS.items():
        if len(prompts) != len(SPLITS):
            raise RuntimeError(f"split mismatch for {family}")
        for prompt_index, (prompt, split) in enumerate(zip(prompts, SPLITS, strict=True)):
            token_ids = tokenizer.harmony_user_prompt(prompt)
            token_count = len(token_ids) + args.continuation_tokens
            rows.append({
                "capture_id": f"c4_{family}_{prompt_index + 1:02d}",
                "family": family,
                "split": split,
                "public_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "input_token_ids": token_ids,
                "prompt_token_count": len(token_ids),
                "token_count": token_count,
                "capture_positions": list(range(3, token_count)),
                "capture_layers": list(range(36)),
            })

    split_counts = {
        split: sum(row["split"] == split for row in rows)
        for split in sorted(set(SPLITS))
    }
    report = {
        "schema": "aion.gptoss-120b-c4-coverage-corpus.v1",
        "status": "READY_FOR_AUTHENTIC_TEACHER_CAPTURE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "rows": rows,
        "families": sorted(PROMPTS),
        "split_counts": split_counts,
        "continuation_tokens_per_prompt": args.continuation_tokens,
        "contains_personal_or_customer_data": False,
        "prompt_text_stored_in_artifact": False,
        "warehouse_manifest_sha256": hashlib.sha256(
            args.manifest.read_bytes()
        ).hexdigest(),
        "promotion_contract": {
            "maximum_correction_fraction_of_original_e4": 0.25,
            "maximum_local_output_relative_l2": 0.02,
            "requires_downstream_route_stability": True,
            "requires_downstream_logit_and_token_stability": True,
            "requires_exact_e4_fallback": True,
            "minimum_full_generation_control_tokens_per_second": 7.0,
        },
        "claim_boundary": (
            "This artifact freezes public generic prompts and disjoint training, selection "
            "and holdout assignments before teacher capture. It contains only prompt hashes "
            "and token IDs. It is a coverage plan, not correction accuracy, model quality or "
            "tokens-per-second evidence."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "prompts": len(rows),
        "families": len(PROMPTS),
        "split_counts": split_counts,
        "planned_layer_positions": sum(
            len(row["capture_positions"]) * len(row["capture_layers"])
            for row in rows
        ),
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
