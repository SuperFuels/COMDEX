#!/usr/bin/env python3
"""Verify locally reconstructed GPT-OSS tokenization against frozen evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_gguf_tokenizer import GptOssGGUFTokenizer


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    reference = json.loads(args.reference.read_text())
    expected = reference["input_token_ids"]
    tokenizer = GptOssGGUFTokenizer.from_warehouse(args.manifest)
    observed = tokenizer.harmony_user_prompt(args.prompt)
    report = {
        "schema": "aion.gptoss-120b-gguf-tokenizer-gate.v1",
        "status": "PASSED" if observed == expected else "FAILED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt": args.prompt,
        "expected_token_ids": expected,
        "observed_token_ids": observed,
        "exact_match": observed == expected,
        "warehouse_manifest_sha256": digest(args.manifest),
        "reference_sha256": digest(args.reference),
        "claim_boundary": (
            "This proves exact local tokenization of one frozen public prompt using only "
            "the vocabulary and merges read through the compressed SD warehouse. It enables "
            "new family capture but is not inference-speed or model-quality evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "exact_match": report["exact_match"],
                      "token_count": len(observed),
                      "canonical_sha256": report["canonical_sha256"]}, indent=2))
    return 0 if report["exact_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
