#!/usr/bin/env python3
"""Build a calibration-only plan of low-sensitivity fused Granite layers."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import time

import torch
from transformers import AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model
from backend.scripts.run_aion_storage_first_multiprompt import _generate, _validate_prompt_catalog


def _set_one(model, selected: int | None) -> None:
    for index, layer in enumerate(model.model.layers):
        layer.block_sparse_moe.experts.use_fused_metal_matvec = index == selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--prompt-manifest", type=Path, required=True)
    parser.add_argument("--calibration-families", type=int, default=4)
    parser.add_argument("--selected-layers", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(), "glyph_manifest": args.glyph_manifest.resolve(),
             "prompt_manifest": args.prompt_manifest.resolve()}
    output = args.output.resolve()
    if root not in paths["model"].parents or root not in paths["glyph_manifest"].parents or root not in output.parents:
        raise SystemExit("model, weights and evidence must remain on external storage")
    if output.exists() or not 1 <= args.selected_layers <= 32:
        raise SystemExit("refusing overwrite or invalid selected-layer count")
    prompt_document = json.loads(paths["prompt_manifest"].read_text())
    prompts = _validate_prompt_catalog(prompt_document)[:args.calibration_families]
    glyph = json.loads(paths["glyph_manifest"].read_text())
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    checkpoint_index = json.loads((paths["model"] / "model.safetensors.index.json").read_text())
    started = time.perf_counter()
    model, _ = _load_storage_first_model(paths["model"], checkpoint_index)
    for layer_index, layer in enumerate(model.model.layers):
        source_moe = layer.block_sparse_moe
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8GlyphMoE(
            source_moe, entries, root, _sha256, "mps", skip_empty_experts=True,
            prepare_fused_metal_matvec=True,
        )
        source_moe = None
        gc.collect()
    torch.mps.synchronize()
    controls = {}
    _set_one(model, None)
    for prompt in prompts:
        controls[prompt["family"]] = _generate(model, tokenizer, prompt["prompt"], 2)
    layer_reports = []
    for layer_index in range(32):
        _set_one(model, layer_index)
        family_errors = []
        token_exact = True
        for prompt in prompts:
            candidate = _generate(model, tokenizer, prompt["prompt"], 2)
            control = controls[prompt["family"]]
            token_exact = token_exact and candidate["token_ids"] == control["token_ids"]
            family_errors.append(float((candidate["scores"][-1] -
                                        control["scores"][-1]).abs().max()))
        layer_reports.append({"layer": layer_index,
                              "maximum_second_step_logit_error": max(family_errors),
                              "mean_family_error": sum(family_errors) / len(family_errors),
                              "calibration_token_ids_exact": token_exact})
    eligible = [item for item in layer_reports if item["calibration_token_ids_exact"]]
    selected = sorted(item["layer"] for item in sorted(
        eligible, key=lambda item: (item["maximum_second_step_logit_error"], item["layer"])
    )[:args.selected_layers])
    acceptance = {"all_32_layers_measured": len(layer_reports) == 32,
                  "selected_requested_layer_count": len(selected) == args.selected_layers,
                  "calibration_only_selection": True}
    report = {"schema_version": "aion.fused_layer_sensitivity_plan.v1",
              "track": "quality_gated_changed_kernel_not_bit_exact",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
              "calibration_families": [item["family"] for item in prompts],
              "selected_layer_count": args.selected_layers,
              "selected_layers": selected, "layers": layer_reports,
              "elapsed_seconds": time.perf_counter() - started,
              "acceptance": acceptance,
              "decision": ("FREEZE_FUSED_LAYER_HOLDOUT_PLAN" if all(acceptance.values())
                           else "STOP_LAYER_SELECTIVE_FUSION"),
              "claim_boundary": ("Layer selection uses only the first frozen prompt families and "
                                 "two-token calibration. No holdout speed or quality claim.")}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "selected_layers": selected, "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
