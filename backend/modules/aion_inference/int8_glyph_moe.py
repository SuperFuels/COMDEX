"""Quality-gated Granite MoE modules backed by native Metal INT8 Glyph blocks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from safetensors.torch import load_file
import torch
from torch import nn


def fused_metal_shader_source() -> str:
    """Return the bounded eight-expert one-token INT8 Metal kernel."""
    parameters = ", ".join(
        f"device const char* w{i} [[buffer({1 + 2 * i})]], "
        f"device const half* s{i} [[buffer({2 + 2 * i})]]"
        for i in range(8)
    )
    cases = " ".join(
        f"case {i}: weight = w{i}; scale = s{i}; break;" for i in range(1, 8)
    )
    return f"""
#include <metal_stdlib>
using namespace metal;
kernel void fused8(
    device const half* input [[buffer(0)]], {parameters},
    device half* output [[buffer(17)]], constant uint& width [[buffer(18)]],
    constant uint& rows [[buffer(19)]],
    uint2 group [[threadgroup_position_in_grid]],
    uint lane [[thread_index_in_threadgroup]]) {{
  uint row = group.x;
  uint slot = group.y;
  device const char* weight = w0;
  device const half* scale = s0;
  switch (slot) {{ {cases} }}
  float value = 0.0f;
  uint weight_base = row * width;
  uint input_base = slot * width;
  for (uint column = lane; column < width; column += 32) {{
    value += float(input[input_base + column]) * float(weight[weight_base + column]);
  }}
  value = simd_sum(value);
  if (lane == 0) output[slot * rows + row] = half(value * float(scale[row]));
}}
"""


@lru_cache(maxsize=1)
def _fused_metal_kernel():
    return torch.mps.compile_shader(fused_metal_shader_source()).fused8


def _nonempty_splits(inputs: torch.Tensor, expert_size: Any
                     ) -> list[tuple[int, torch.Tensor]]:
    """Return routed expert views that contain at least one token."""
    return [(index, values) for index, values in
            enumerate(inputs.split(expert_size, dim=0)) if values.shape[0] > 0]


class Int8GlyphParallelExperts(nn.Module):
    """Parallel experts using one content-addressed packed block per expert."""

    def __init__(self, entries: list[dict[str, Any]], storage_root: Path,
                 verify_hash: Any, device: str = "mps",
                 skip_empty_experts: bool = True,
                 use_decode_arena: bool = False,
                 decode_arena_capacity: int = 0,
                 use_cached_weight_views: bool = False,
                 use_cached_empty_views: bool = False,
                 prepare_fused_metal_matvec: bool = False,
                 use_fused_metal_matvec: bool = False) -> None:
        super().__init__()
        if len(entries) != 40:
            raise ValueError("Granite requires exactly 40 expert blocks per layer")
        self.entries = entries
        self.skip_empty_experts = skip_empty_experts
        self.use_decode_arena = use_decode_arena
        self.decode_arena_capacity = decode_arena_capacity
        self.use_cached_weight_views = use_cached_weight_views
        self.use_cached_empty_views = use_cached_empty_views
        self.use_fused_metal_matvec = use_fused_metal_matvec
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
        self.register_buffer(
            "input_arena",
            torch.empty((decode_arena_capacity, int(entries[0]["input_shape"][0])),
                        dtype=torch.float16, device=device),
            persistent=False,
        )
        self.register_buffer(
            "output_arena",
            torch.empty((decode_arena_capacity, int(entries[0]["output_shape"][0])),
                        dtype=torch.float16, device=device),
            persistent=False,
        )
        self._cached_weight_views = [self._materialize_weights(index) for index in range(40)]
        input_widths = {int(entry["input_shape"][0]) for entry in entries}
        output_widths = {int(entry["output_shape"][0]) for entry in entries}
        if len(input_widths) != 1 or len(output_widths) != 1:
            raise ValueError("cached empty views require uniform expert widths")
        self.register_buffer(
            "input_empty", torch.empty((0, input_widths.pop()), dtype=torch.float16,
                                       device=device), persistent=False,
        )
        self.register_buffer(
            "output_empty", torch.empty((0, output_widths.pop()), dtype=torch.float16,
                                        device=device), persistent=False,
        )
        fused_capacity = 8 if prepare_fused_metal_matvec else 0
        self.register_buffer(
            "fused_input_output",
            torch.empty((fused_capacity, int(entries[0]["input_shape"][0])),
                        dtype=torch.float16, device=device), persistent=False,
        )
        self.register_buffer(
            "fused_output_output",
            torch.empty((fused_capacity, int(entries[0]["output_shape"][0])),
                        dtype=torch.float16, device=device), persistent=False,
        )

    def _finish(self, outputs: list[torch.Tensor], arena: torch.Tensor,
                total: int) -> torch.Tensor:
        if not self.use_decode_arena or total > self.decode_arena_capacity:
            return torch.cat(outputs, dim=0)
        offset = 0
        for output in outputs:
            count = output.shape[0]
            if count:
                arena[offset:offset + count].copy_(output)
                offset += count
        if offset != total:
            raise RuntimeError("decode arena routed-token coverage mismatch")
        return arena[:total]

    def _materialize_weights(self, index: int) -> tuple[torch.Tensor, torch.Tensor,
                                                         torch.Tensor, torch.Tensor]:
        entry = self.entries[index]
        block = getattr(self, f"block_{index}")
        offset = int(entry["output_offset_elements"])
        input_weight = block[:offset].view(entry["input_shape"])
        output_weight = block[offset:].view(entry["output_shape"])
        return (input_weight, getattr(self, f"input_scale_{index}"),
                output_weight, getattr(self, f"output_scale_{index}"))

    def _weights(self, index: int) -> tuple[torch.Tensor, torch.Tensor,
                                             torch.Tensor, torch.Tensor]:
        if self.use_cached_weight_views:
            return self._cached_weight_views[index]
        return self._materialize_weights(index)

    def _fused_projection(self, inputs: torch.Tensor, expert_size: Any,
                          output_projection: bool) -> torch.Tensor | None:
        if not self.use_fused_metal_matvec or inputs.shape[0] != 8:
            return None
        active = [index for index, size in enumerate(expert_size) if int(size) == 1]
        if len(active) != 8 or sum(int(size) for size in expert_size) != 8:
            return None
        pairs = []
        for index in active:
            input_weight, input_scale, output_weight, output_scale = self._weights(index)
            pairs.append((output_weight, output_scale) if output_projection else
                         (input_weight, input_scale))
        destination = self.fused_output_output if output_projection else self.fused_input_output
        arguments = []
        for weight, scale in pairs:
            arguments.extend((weight, scale))
        rows, width = pairs[0][0].shape
        _fused_metal_kernel()(inputs, *arguments, destination, width, rows,
                              threads=(rows * 32, 8, 1), group_size=(32, 1, 1))
        return destination

    def input_forward(self, inputs: torch.Tensor, expert_size: torch.Tensor) -> torch.Tensor:
        fused = self._fused_projection(inputs, expert_size, False)
        if fused is not None:
            return fused
        input_list = inputs.split(expert_size, dim=0)
        outputs = []
        for index, values in enumerate(input_list):
            if self.skip_empty_experts and values.shape[0] == 0:
                outputs.append(self.input_empty if self.use_cached_empty_views else
                               values.new_empty((0, int(self.entries[index]["input_shape"][0]))))
                continue
            input_weight, input_scale, _, _ = self._weights(index)
            outputs.append(torch._weight_int8pack_mm(values, input_weight, input_scale))
        return self._finish(outputs, self.input_arena, inputs.shape[0])

    def output_forward(self, inputs: torch.Tensor, expert_size: torch.Tensor) -> torch.Tensor:
        fused = self._fused_projection(inputs, expert_size, True)
        if fused is not None:
            return fused
        input_list = inputs.split(expert_size, dim=0)
        outputs = []
        for index, values in enumerate(input_list):
            if self.skip_empty_experts and values.shape[0] == 0:
                outputs.append(self.output_empty if self.use_cached_empty_views else
                               values.new_empty((0, int(self.entries[index]["output_shape"][0]))))
                continue
            _, _, output_weight, output_scale = self._weights(index)
            outputs.append(torch._weight_int8pack_mm(values, output_weight, output_scale))
        return self._finish(outputs, self.output_arena, inputs.shape[0])


class Int8GlyphMoE(nn.Module):
    """Granite-compatible MoE retaining the original learned router."""

    def __init__(self, source_moe: nn.Module, entries: list[dict[str, Any]],
                 storage_root: Path, verify_hash: Any, device: str = "mps",
                 skip_empty_experts: bool = True,
                 use_decode_arena: bool = False,
                 decode_arena_capacity: int = 0,
                 use_cached_weight_views: bool = False,
                 use_cached_empty_views: bool = False,
                 prepare_fused_metal_matvec: bool = False,
                 use_fused_metal_matvec: bool = False) -> None:
        super().__init__()
        self.input_size = source_moe.input_size
        self.hidden_size = source_moe.hidden_size
        self.activation = source_moe.activation
        self.router = source_moe.router
        self.experts = Int8GlyphParallelExperts(
            entries, storage_root, verify_hash, device, skip_empty_experts,
            use_decode_arena, decode_arena_capacity, use_cached_weight_views,
            use_cached_empty_views, prepare_fused_metal_matvec,
            use_fused_metal_matvec,
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
