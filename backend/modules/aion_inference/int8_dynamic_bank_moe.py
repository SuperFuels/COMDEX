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


PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS = frozenset({19, 21, 22})
PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS = 32
PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS = 8


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

    PREFILL_TOKEN_CAPACITY = 512

    def __init__(self, source_moe: nn.Module, entry: dict[str, Any], storage_root: Path,
                 verify_hash: Any, device: str = "mps",
                 use_dynamic_decode: bool = False,
                 use_fused_router: bool = False,
                 use_fused_prefill_router: bool = False,
                 use_fused_projection_pipeline: bool = False) -> None:
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
        self.use_fused_router = use_fused_router
        self.use_fused_prefill_router = use_fused_prefill_router
        self.use_fused_projection_pipeline = use_fused_projection_pipeline
        self.projection_pipeline_decode_tokens: int | None = None
        self.router_fallback_after_tokens: int | None = None
        self.decode_step = 0
        self.route_audit: dict[str, Any] | None = None
        self.register_buffer("dynamic_hidden", torch.empty(
            (8, self.input_bank.shape[1]), dtype=torch.float16, device=device), persistent=False)
        self.register_buffer("dynamic_output", torch.empty(
            (self.output_bank.shape[1],), dtype=torch.float16, device=device), persistent=False)
        self.register_buffer("dynamic_activated", torch.empty(
            (8, self.input_bank.shape[1] // 2), dtype=torch.float16, device=device),
            persistent=False)
        self.register_buffer("dynamic_expert_indices", torch.empty(
            (8,), dtype=torch.int32, device=device), persistent=False)
        self.register_buffer("dynamic_gates", torch.empty(
            (8,), dtype=torch.float16, device=device), persistent=False)
        assignments = self.PREFILL_TOKEN_CAPACITY * 8
        self.register_buffer("prefill_expert_indices", torch.empty(
            (assignments,), dtype=torch.int32, device=device), persistent=False)
        self.register_buffer("prefill_gates", torch.empty(
            (assignments,), dtype=torch.float16, device=device), persistent=False)
        self.register_buffer("prefill_counts", torch.empty(
            (40,), dtype=torch.int32, device=device), persistent=False)
        self.register_buffer("prefill_batch_index", torch.empty(
            (assignments,), dtype=torch.int32, device=device), persistent=False)
        self.register_buffer("prefill_batch_gates", torch.empty(
            (assignments,), dtype=torch.float16, device=device), persistent=False)

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
        library = _library()
        fast_router_enabled = (
            self.use_fused_router and
            (self.router_fallback_after_tokens is None or
             self.decode_step < self.router_fallback_after_tokens)
        )
        if fast_router_enabled:
            logits = self.router.layer(flattened).float()
            library.select_decode(
                logits, self.dynamic_expert_indices, self.dynamic_gates,
                self.router.layer.weight.shape[0], threads=(1, 1, 1), group_size=(1, 1, 1))
            expert_indices = self.dynamic_expert_indices
            gates = self.dynamic_gates
            if self.route_audit is not None:
                top_logits, reference_indices = logits.topk(8, dim=1)
                reference_gates = torch.softmax(top_logits, dim=1).type_as(flattened)
                reference_indices, order = reference_indices.sort(dim=1)
                reference_gates = reference_gates.gather(1, order)[0]
                torch.mps.synchronize()
                audit = self.route_audit
                audit["calls"] += 1
                if not torch.equal(reference_indices[0].to(torch.int32).cpu(),
                                   expert_indices.cpu()):
                    audit["expert_index_mismatches"] += 1
                error = float((reference_gates.float() - gates.float()).abs().max().cpu())
                audit["maximum_gate_error"] = max(audit["maximum_gate_error"], error)
        else:
            logits = self.router.layer(flattened).float()
            top_logits, top_indices = logits.topk(8, dim=1)
            gates_2d = torch.softmax(top_logits, dim=1).type_as(flattened)
            top_indices, order = top_indices.sort(dim=1)
            gates = gates_2d.gather(1, order)[0]
            expert_indices = top_indices[0].to(torch.int32)
        fused_projection_enabled = (
            self.use_fused_projection_pipeline and
            (self.projection_pipeline_decode_tokens is None or
             self.decode_step < self.projection_pipeline_decode_tokens)
        )
        if fused_projection_enabled:
            library.dyn_input_silu(
                flattened, self.input_bank, self.input_scale_bank, expert_indices,
                self.dynamic_activated, self.input_bank.shape[2], self.input_bank.shape[1],
                threads=((self.input_bank.shape[1] // 2) * 32, 8, 1),
                group_size=(32, 1, 1),
            )
            library.dyn_output_parallel(
                self.dynamic_activated, self.output_bank, self.output_scale_bank,
                expert_indices, gates, self.dynamic_output, self.output_bank.shape[2],
                self.output_bank.shape[1], threads=(self.output_bank.shape[1] * 32, 8, 1),
                group_size=(32, 8, 1),
            )
        else:
            library.dyn_input(
                flattened, self.input_bank, self.input_scale_bank, expert_indices,
                self.dynamic_hidden, self.input_bank.shape[2], self.input_bank.shape[1],
                threads=(self.input_bank.shape[1] * 32, 8, 1), group_size=(32, 1, 1),
            )
            gate, projected = self.dynamic_hidden.chunk(2, dim=-1)
            activated = self.activation(gate) * projected
            library.dyn_output(
                activated, self.output_bank, self.output_scale_bank, expert_indices, gates,
                self.dynamic_output, self.output_bank.shape[2], self.output_bank.shape[1],
                threads=(self.output_bank.shape[1] * 32, 1, 1), group_size=(32, 1, 1),
            )
        self.decode_step += 1
        return self.dynamic_output.view(1, 1, self.input_size)

    def _fused_prefill_route(self, flattened: torch.Tensor):
        tokens = flattened.shape[0]
        assignments = tokens * 8
        library = _library()
        logits = self.router.layer(flattened).float()
        top_logits, top_indices = logits.topk(8, dim=1)
        top_gates = torch.softmax(top_logits, dim=1).type_as(flattened)
        flat_indices = top_indices.flatten()
        flat_gates = top_gates.flatten()
        library.group_count_exact(
            flat_indices, flat_gates, self.prefill_counts,
            self.prefill_batch_index, self.prefill_batch_gates, assignments,
            threads=(64, 1, 1), group_size=(64, 1, 1))
        expert_size = self.prefill_counts.tolist()
        return (self.prefill_batch_index[:assignments],
                self.prefill_batch_gates[:assignments], expert_size)

    def forward(self, layer_input: torch.Tensor) -> torch.Tensor:
        batch, length, embedding = layer_input.size()
        flattened = layer_input.reshape(-1, embedding)
        if self.use_dynamic_decode and flattened.shape[0] == 1:
            return self._dynamic(flattened)
        self.decode_step = 0
        if self.use_fused_prefill_router and flattened.shape[0] <= self.PREFILL_TOKEN_CAPACITY:
            batch_index, batch_gates, expert_size = self._fused_prefill_route(flattened)
        else:
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
