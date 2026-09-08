#!/usr/bin/env python3
"""Rank Granite layers by real-activation sensitivity to INT8 Glyph experts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS, _chat_tokens


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    source = json.loads(paths["source_manifest"].read_text())
    glyph = json.loads(paths["glyph_manifest"].read_text())
    if not all(source["integrity"].values()) or not all(glyph["integrity"].values()):
        raise RuntimeError("manifest integrity failed")
    if glyph["source_manifest_sha256"] != _sha256(paths["source_manifest"]):
        raise RuntimeError("Glyph/source binding failed")
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    torch.mps.synchronize()

    captured_inputs: list[list[torch.Tensor]] = [[] for _ in range(32)]
    captured_outputs: list[list[torch.Tensor]] = [[] for _ in range(32)]
    handles = []
    for layer_index, layer in enumerate(model.model.layers):
        handles.append(layer.block_sparse_moe.register_forward_pre_hook(
            lambda _module, values, index=layer_index:
                captured_inputs[index].append(values[0].detach().cpu())
        ))
        handles.append(layer.block_sparse_moe.register_forward_hook(
            lambda _module, _values, result, index=layer_index:
                captured_outputs[index].append(result.detach().cpu())
        ))
    with torch.inference_mode():
        for prompt in PROMPTS:
            model(**_chat_tokens(tokenizer, prompt["prompt"]), use_cache=False)
            torch.mps.synchronize()
    for handle in handles:
        handle.remove()
    if any(len(values) != len(PROMPTS) for values in captured_inputs + captured_outputs):
        raise RuntimeError("activation capture coverage failed")

    layers = []
    started = time.perf_counter()
    for layer_index, layer in enumerate(model.model.layers):
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        candidate = Int8GlyphMoE(layer.block_sparse_moe, entries, root, _sha256, "mps").eval()
        prompt_metrics = []
        with torch.inference_mode():
            for prompt, value, expected in zip(
                PROMPTS, captured_inputs[layer_index], captured_outputs[layer_index], strict=True,
            ):
                actual = candidate(value.to("mps")).detach().float().cpu()
                expected_float = expected.float()
                difference = actual - expected_float
                rmse = float(difference.square().mean().sqrt().item())
                signal_rms = float(expected_float.square().mean().sqrt().item())
                prompt_metrics.append({
                    "family": prompt["family"], "maximum_error": float(difference.abs().max()),
                    "mean_absolute_error": float(difference.abs().mean()), "rmse": rmse,
                    "signal_rms": signal_rms,
                    "normalized_rmse": rmse / max(signal_rms, 1e-12),
                })
        layers.append({
            "layer": layer_index, "prompt_metrics": prompt_metrics,
            "mean_normalized_rmse": statistics.mean(x["normalized_rmse"] for x in prompt_metrics),
            "maximum_error": max(x["maximum_error"] for x in prompt_metrics),
        })
        del candidate
        torch.mps.empty_cache()
    ranking = sorted(layers, key=lambda item: item["mean_normalized_rmse"], reverse=True)
    report = {
        "schema_version": "aion.int8_layer_sensitivity.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {"source_manifest": _sha256(paths["source_manifest"]),
                   "glyph_manifest": _sha256(paths["glyph_manifest"])},
        "prompt_families": [item["family"] for item in PROMPTS],
        "method": "one packed layer at a time on captured real FP16 prefill activations",
        "layers": layers,
        "ranking": [{"rank": rank, "layer": item["layer"],
                     "mean_normalized_rmse": item["mean_normalized_rmse"]}
                    for rank, item in enumerate(ranking, start=1)],
        "recommended_two_fp16_layers": [item["layer"] for item in ranking[:2]],
        "seconds": time.perf_counter() - started,
        "claim_boundary": (
            "Four-prompt prefill activation sensitivity diagnostic. Ranking does not itself "
            "prove generation quality; the recommended hybrid requires a frozen long gate."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output),
                      "recommended_two_fp16_layers": report["recommended_two_fp16_layers"],
                      "top_five": report["ranking"][:5],
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
