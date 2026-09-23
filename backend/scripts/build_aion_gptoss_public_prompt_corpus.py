#!/usr/bin/env python3
"""Create a prompt-free-on-disk token corpus using the SD-native tokenizer."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_gguf_tokenizer import GptOssGGUFTokenizer


PROMPTS = {
    "public_explanation_rain": "Explain in one sentence why rain falls from clouds.",
    "public_business_waste": "List three practical ways a small shop can reduce waste.",
    "public_reasoning_boxes": "If every red box is heavy and this box is red, what follows?",
    "public_writing_invoice": "Write a polite one-sentence reminder about an unpaid invoice.",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    tokenizer = GptOssGGUFTokenizer.from_warehouse(args.manifest)
    families = []
    for family, prompt in PROMPTS.items():
        token_ids = tokenizer.harmony_user_prompt(prompt)
        families.append({
            "family_id": family,
            "public_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "input_token_ids": token_ids,
            "prompt_token_count": len(token_ids),
            "capture_positions": list(range(3, len(token_ids) - 3)),
            "capture_layers": [12],
        })
    report = {
        "schema": "aion.gptoss-120b-public-prompt-token-corpus.v1",
        "status": "READY_FOR_TEACHER_CAPTURE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "families": families,
        "contains_personal_or_customer_data": False,
        "prompt_text_stored": False,
        "warehouse_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "claim_boundary": (
            "Prompt strings are fixed public/generic test material embedded in this source "
            "file; the emitted corpus retains only hashes and token IDs. This is tokenizer "
            "and capture planning evidence, not model quality or speed evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"],
                      "families": [(row["family_id"], row["prompt_token_count"])
                                   for row in families],
                      "canonical_sha256": report["canonical_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
