#!/usr/bin/env python3
"""Bind sparse GGUF tokenization to an exact prompt-token transformer run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--transformer-evidence", type=Path, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--chat-template", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--tool-source", type=Path,
        default=Path(__file__).parents[1] / "modules/aion_inference/native/gptoss_vocab_shell.cpp",
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")

    manifest = json.loads(args.manifest.read_text())
    transformer = json.loads(args.transformer_evidence.read_text())
    claimed_transformer_hash = transformer.get("canonical_sha256")
    transformer_body = dict(transformer)
    transformer_body.pop("canonical_sha256", None)
    transformer_hash_valid = claimed_transformer_hash == _canonical(transformer_body)

    with tempfile.TemporaryDirectory(prefix="aion-gptoss-vocab-receipt-") as name:
        root = Path(name)
        executable = root / "gptoss-vocab-shell"
        subprocess.run([
            "clang++", "-std=c++17", "-O3", "-I/opt/homebrew/include",
            str(args.tool_source), "-L/opt/homebrew/lib", "-lllama", "-lggml",
            "-lggml-base", "-ldl", "-o", str(executable),
        ], check=True)
        shells = []
        for source in manifest["verified_sources"]:
            reader = ExpertFrameGGUFReader(args.manifest, source["name"], 64 * 1024 * 1024)
            index = read_gguf_stream_index(reader, int(source["size"]))
            shell = root / source["name"]
            with shell.open("wb") as handle:
                handle.write(reader.read_at(0, int(index["data_offset"])))
                handle.truncate(int(source["size"]))
            shells.append(shell)
        physical_bytes = sum(path.stat().st_blocks * 512 for path in shells)
        logical_bytes = sum(path.stat().st_size for path in shells)

        token_text = subprocess.check_output([
            str(executable), str(shells[0]),
            "chat-tokenize" if args.chat_template else "tokenize", args.prompt,
        ], text=True).strip()
        token_ids = [int(value) for value in token_text.split(",") if value]
        response_sequences = [
            [int(item["generated_token_id"]) for item in run["tokens"][len(token_ids) - 1:]]
            for run in [transformer["run_a"], transformer["run_b"]]
        ]
        generated_ids = response_sequences[0]
        generated_id = generated_ids[-1]
        generated_text = subprocess.check_output([
            str(executable), str(shells[0]), "detokenize", *map(str, generated_ids),
        ], text=True).rstrip("\n")

    acceptance = {
        "warehouse_complete_verified": manifest.get("status") == "COMPLETE_VERIFIED",
        "transformer_evidence_hash_valid": transformer_hash_valid,
        "transformer_execution_passed": transformer.get("status") == "PASSED",
        "routes_repeatable": transformer.get("routes_repeatable") is True,
        "hidden_and_logits_bitwise_repeatable": (
            transformer.get("final_hidden_and_logits_bitwise_repeatable") is True
        ),
        "prompt_has_at_least_one_token": len(token_ids) >= 1,
        "transformer_input_matches_tokenizer": token_ids == transformer.get(
            "input_token_ids", [transformer.get("input_token_id")]
        ),
        "transformer_evaluated_complete_prompt": int(transformer.get("token_count", 0)) >= len(token_ids),
        "response_token_sequence_repeatable": response_sequences[0] == response_sequences[1],
        "physical_vocab_shell_under_32_mib": physical_bytes <= 32 * 1024 * 1024,
    }
    report = {
        "schema": "aion.gptoss-120b-prompt-sequence-receipt.v1",
        "status": "PASSED" if all(acceptance.values()) else "FAILED",
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "prompt": args.prompt,
        "model_declared_chat_template_applied": args.chat_template,
        "prompt_token_ids": token_ids,
        "generated_token_id": generated_id,
        "generated_token_ids": generated_ids,
        "generated_text": generated_text,
        "sparse_vocab_shell": {
            "logical_bytes": logical_bytes,
            "physical_bytes": physical_bytes,
            "physical_reduction_percent": 100.0 * (1.0 - physical_bytes / logical_bytes),
            "temporary_and_deleted_after_use": True,
        },
        "hashes": {
            "warehouse_manifest_sha256": _sha256(args.manifest),
            "transformer_evidence_sha256": _sha256(args.transformer_evidence),
            "transformer_canonical_sha256": claimed_transformer_hash,
            "vocab_tool_source_sha256": _sha256(args.tool_source),
        },
        "acceptance": acceptance,
        "claim_boundary": (
            "One real text prompt was tokenized from header-only sparse GGUF shells, teacher-"
            "forced through the complete custom 36-layer SD-backed transformer twice with KV "
            "history, and its response-side tokens were detokenized. This proves the prompt/"
            "vocabulary bridge and exact repeatability for this sequence; it is not chat-template "
            "quality beyond the declared mode or sustained throughput."
        ),
    }
    report["canonical_sha256"] = _canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "prompt_token_ids": token_ids,
        "generated_token_id": generated_id, "generated_text": generated_text,
        "physical_shell_bytes": physical_bytes,
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2))
    return 0 if report["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
