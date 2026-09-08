"""Granite MoE backed by contiguous GPU-addressable INT8 layer banks."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from safetensors.torch import load_file
import torch
from torch import nn

from backend.scripts.run_aion_int8_dynamic_bank_moe_gate import _shader_source


@lru_cache(maxsize=1)
def _library():
    return torch.mps.compile_shader(_shader_source())


def load_bank_entry(manifest: dict[str, Any], layer: int, storage_root: Path,
                    verify_hash: Any) -> dict[str, Any]:
    entry = manifest["layers"][layer]
    if int(entry["layer"]) != layer:
        raise RuntimeError("dynamic bank layer ordering mismatch")
    path = Path(entry["path"]).resolve()
    if storage_root not in path.parents or verify_hash(path) != entry["sha256"]:
        raise RuntimeError(f"dynamic bank integrity failed: {path}")
    return entry


class Int8DynamicBankMoE(nn.Module):
    """Exact native fallback plus GPU-resident one-token dynamic dispatch."""

    def __init__(self, source_moe: nn.Module, entry: dict[str, Any], storage_root: Path,
                 verify_hash: Any, device: str = "mps",
                 use_dynamic_decode: bool = False) -> None:
        super().__init__()
        path = Path(entry["path"]).resolve()
        if storage_root not in path.parents or verify_hash(path) != entry["sha256"]:
            raise RuntimeError(f"dynamic bank integrity failed: {path}")
        tensors = load_file(path, device="cpu")
        for name in ("input_bank", "input_scale_bank", "output_bank", "output_scale_bank"):
            self.register_buffer(name, tensors[name].to(device), persistent=False)
        self.input_size = source_moe.input_size
        self.hidden_size = source_moe.hidden_size
        self.activation = source_moe.activation
        self.router = source_moe.router
        self.use_dynamic_decode = use_dynamic_decode
        self.register_buffer("dynamic_hidden", torch.empty(
            (8, self.input_bank.shape[1]), dtype=torch.float16, device=device), persistent=False)
        self.register_buffer("dynamic_output", torch.empty(
            (self.output_bank.shape[1],), dtype=torch.float16, device=device), persistent=False)

    @staticmethod
    def _native(values: torch.Tensor, expert_size: Any, bank: torch.Tensor,
                scales: torch.Tensor) -> torch.Tensor:
        pieces = values.split(expert_size, dim=0)
        outputs = []
        for index, piece in enumerate(pieces):
            if piece.shape[0] == 0:
                outputs.append(piece.new_empty((0, bank.shape[1])))
            else:
                outputs.append(torch._weight_int8pack_mm(piece, bank[index], scales[index]))
        return torch.cat(outputs, dim=0)

    def _dynamic(self, flattened: torch.Tensor) -> torch.Tensor:
        logits = self.router.layer(flattened).float()
        top_logits, top_indices = logits.topk(8, dim=1)
        gates = torch.softmax(top_logits, dim=1).type_as(flattened)
        top_indices, order = top_indices.sort(dim=1)
        gates = gates.gather(1, order)
        expert_indices = top_indices[0].to(torch.int32)
        library = _library()
        library.dyn_input(
            flattened, self.input_bank, self.input_scale_bank, expert_indices,
            self.dynamic_hidden, self.input_bank.shape[2], self.input_bank.shape[1],
            threads=(self.input_bank.shape[1] * 32, 8, 1), group_size=(32, 1, 1),
        )
        gate, projected = self.dynamic_hidden.chunk(2, dim=-1)
        activated = self.activation(gate) * projected
        library.dyn_output(
            activated, self.output_bank, self.output_scale_bank, expert_indices, gates[0],
            self.dynamic_output, self.output_bank.shape[2], self.output_bank.shape[1],
            threads=(self.output_bank.shape[1] * 32, 1, 1), group_size=(32, 1, 1),
        )
        return self.dynamic_output.view(1, 1, self.input_size)

    def forward(self, layer_input: torch.Tensor) -> torch.Tensor:
        batch, length, embedding = layer_input.size()
        flattened = layer_input.reshape(-1, embedding)
        if self.use_dynamic_decode and flattened.shape[0] == 1:
            return self._dynamic(flattened)
        _, batch_index, batch_gates, expert_size, _ = self.router(flattened)
        expert_inputs = flattened[batch_index]
        hidden = self._native(expert_inputs, expert_size, self.input_bank, self.input_scale_bank)
        gate, projected = hidden.chunk(2, dim=-1)
        hidden = self.activation(gate) * projected
        expert_outputs = self._native(hidden, expert_size, self.output_bank, self.output_scale_bank)
        expert_outputs = expert_outputs * batch_gates[:, None]
        zeros = torch.zeros((batch * length, self.input_size), dtype=expert_outputs.dtype,
                            device=expert_outputs.device)
        return zeros.index_add(0, batch_index, expert_outputs).view(batch, length, self.input_size)
