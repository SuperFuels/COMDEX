"""Quality-gated Granite MoE modules backed by native Metal INT8 Glyph blocks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from safetensors.torch import load_file
import torch
from torch import nn


def _nonempty_splits(inputs: torch.Tensor, expert_size: Any
                     ) -> list[tuple[int, torch.Tensor]]:
    """Return routed expert views that contain at least one token."""
    return [(index, values) for index, values in
            enumerate(inputs.split(expert_size, dim=0)) if values.shape[0] > 0]


class Int8GlyphParallelExperts(nn.Module):
    """Parallel experts using one content-addressed packed block per expert."""

    def __init__(self, entries: list[dict[str, Any]], storage_root: Path,
                 verify_hash: Any, device: str = "mps",
                 skip_empty_experts: bool = True) -> None:
        super().__init__()
        if len(entries) != 40:
            raise ValueError("Granite requires exactly 40 expert blocks per layer")
        self.entries = entries
        self.skip_empty_experts = skip_empty_experts
        for index, entry in enumerate(entries):
            path = Path(entry["path"]).resolve()
            if storage_root not in path.parents or verify_hash(path) != entry["sha256"]:
                raise RuntimeError(f"Glyph block integrity failed: {path}")
            tensors = load_file(path, device="cpu")
            self.register_buffer(f"block_{index}", tensors["weight_block"].to(device),
                                 persistent=False)
            self.register_buffer(f"input_scale_{index}", tensors["input_scale"].to(device),
                                 persistent=False)
            self.register_buffer(f"output_scale_{index}", tensors["output_scale"].to(device),
                                 persistent=False)

    def _weights(self, index: int) -> tuple[torch.Tensor, torch.Tensor,
                                             torch.Tensor, torch.Tensor]:
        entry = self.entries[index]
        block = getattr(self, f"block_{index}")
        offset = int(entry["output_offset_elements"])
        input_weight = block[:offset].view(entry["input_shape"])
        output_weight = block[offset:].view(entry["output_shape"])
        return (input_weight, getattr(self, f"input_scale_{index}"),
                output_weight, getattr(self, f"output_scale_{index}"))

    def input_forward(self, inputs: torch.Tensor, expert_size: torch.Tensor) -> torch.Tensor:
        input_list = inputs.split(expert_size, dim=0)
        outputs = []
        for index, values in enumerate(input_list):
            if self.skip_empty_experts and values.shape[0] == 0:
                outputs.append(values.new_empty((0, int(self.entries[index]["input_shape"][0]))))
                continue
            input_weight, input_scale, _, _ = self._weights(index)
            outputs.append(torch._weight_int8pack_mm(values, input_weight, input_scale))
        return torch.cat(outputs, dim=0)

    def output_forward(self, inputs: torch.Tensor, expert_size: torch.Tensor) -> torch.Tensor:
        input_list = inputs.split(expert_size, dim=0)
        outputs = []
        for index, values in enumerate(input_list):
            if self.skip_empty_experts and values.shape[0] == 0:
                outputs.append(values.new_empty((0, int(self.entries[index]["output_shape"][0]))))
                continue
            _, _, output_weight, output_scale = self._weights(index)
            outputs.append(torch._weight_int8pack_mm(values, output_weight, output_scale))
        return torch.cat(outputs, dim=0)


class Int8GlyphMoE(nn.Module):
    """Granite-compatible MoE retaining the original learned router."""

    def __init__(self, source_moe: nn.Module, entries: list[dict[str, Any]],
                 storage_root: Path, verify_hash: Any, device: str = "mps",
                 skip_empty_experts: bool = True) -> None:
        super().__init__()
        self.input_size = source_moe.input_size
        self.hidden_size = source_moe.hidden_size
        self.activation = source_moe.activation
        self.router = source_moe.router
        self.experts = Int8GlyphParallelExperts(
            entries, storage_root, verify_hash, device, skip_empty_experts,
        )

    def forward(self, layer_input: torch.Tensor) -> torch.Tensor:
        batch, length, embedding = layer_input.size()
        flattened = layer_input.reshape(-1, embedding)
        _, batch_index, batch_gates, expert_size, _ = self.router(flattened)
        expert_inputs = flattened[batch_index]
        hidden = self.experts.input_forward(expert_inputs, expert_size)
        gate, projected = hidden.chunk(2, dim=-1)
        hidden = self.activation(gate) * projected
        expert_outputs = self.experts.output_forward(hidden, expert_size)
        expert_outputs = expert_outputs * batch_gates[:, None]
        zeros = torch.zeros((batch * length, self.input_size), dtype=expert_outputs.dtype,
                            device=expert_outputs.device)
        result = zeros.index_add(0, batch_index, expert_outputs)
        return result.view(batch, length, self.input_size)


def load_layer_entries(manifest: dict[str, Any], layer: int, storage_root: Path,
                       verify_hash: Any) -> list[dict[str, Any]]:
    layer_entry = manifest["layers"][layer]
    if int(layer_entry["layer"]) != layer:
        raise RuntimeError("Glyph manifest layer ordering mismatch")
    index_path = Path(layer_entry["index_path"]).resolve()
    if storage_root not in index_path.parents or verify_hash(index_path) != layer_entry["index_sha256"]:
        raise RuntimeError(f"Glyph layer {layer} index integrity failed")
    index = json.loads(index_path.read_text())
    entries = sorted(index["experts"], key=lambda item: int(item["expert"]))
    if [int(item["expert"]) for item in entries] != list(range(40)):
        raise RuntimeError(f"Glyph layer {layer} expert coverage failed")
    return entries
