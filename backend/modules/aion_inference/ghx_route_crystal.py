"""Fast GHX route-crystal selection for governed Shadow Expert experiments.

This module deliberately does not substitute a predicted expert output.  It
turns a router activation and its four gated expert IDs into a cheap similarity
query over verified route prototypes.  A separately validated calculator may
use the returned neighbours; exact expert execution remains the fallback.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROUTER_WIDTH = 2880
EXPERT_COUNT = 128


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class RouteSelection:
    prototype_indices: tuple[int, ...]
    scores: tuple[float, ...]
    score_margin: float
    observed_expert_fraction: float


class GhxRouteCrystalSelector:
    """Hash-verified, allocation-light selector over route prototypes."""

    def __init__(self, router_prototypes: np.ndarray, route_glyphs: np.ndarray,
                 route_weight: float) -> None:
        if router_prototypes.ndim != 2 or router_prototypes.shape[1] != ROUTER_WIDTH:
            raise ValueError("invalid router prototype shape")
        if route_glyphs.shape != (router_prototypes.shape[0], EXPERT_COUNT):
            raise ValueError("invalid route glyph shape")
        self.router_prototypes = np.asarray(router_prototypes, dtype=np.float32)
        self.route_glyphs = np.asarray(route_glyphs, dtype=np.float32)
        self.route_weight = float(route_weight)
        self.observed_experts = np.any(self.route_glyphs != 0, axis=0)

    @classmethod
    def from_cartridge(cls, cartridge: Path) -> "GhxRouteCrystalSelector":
        receipt_path = cartridge / "cartridge.json"
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("schema") != "aion.ghx-route-crystal-cartridge.v1":
            raise ValueError("unsupported GHX route cartridge")
        for name, expected in receipt["files"].items():
            if _sha256(cartridge / name) != expected:
                raise ValueError(f"GHX route cartridge hash mismatch: {name}")
        prototype_shape = (-1, ROUTER_WIDTH)
        route_shape = (-1, EXPERT_COUNT)
        routers = np.fromfile(cartridge / "router-prototypes-f32.bin", dtype="<f4").reshape(
            prototype_shape)
        routes = np.fromfile(cartridge / "route-glyphs-f32.bin", dtype="<f4").reshape(
            route_shape)
        return cls(routers, routes, receipt["configuration"]["route_weight"])

    def select(self, router: np.ndarray, experts: list[int], gates: list[float],
               top_k: int = 3) -> RouteSelection:
        if len(experts) != len(gates) or not experts:
            raise ValueError("experts and gates must have equal non-zero length")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        router_value = np.asarray(router, dtype=np.float32).reshape(-1)
        if router_value.size != ROUTER_WIDTH:
            raise ValueError("router width mismatch")
        norm = float(np.linalg.norm(router_value))
        if not np.isfinite(norm) or norm == 0:
            raise ValueError("router must be finite and non-zero")
        router_value = router_value / norm
        route = np.zeros(EXPERT_COUNT, dtype=np.float32)
        for expert, gate in zip(experts, gates):
            if expert < 0 or expert >= EXPERT_COUNT:
                raise ValueError("expert ID outside route vocabulary")
            route[expert] = float(gate)
        scores = (self.router_prototypes @ router_value +
                  self.route_weight * (self.route_glyphs @ route))
        count = min(top_k, scores.size)
        order = np.argsort(scores, kind="stable")[-count:][::-1]
        margin = float(scores[order[0]] - scores[order[1]]) if count > 1 else float("inf")
        coverage = float(np.mean(self.observed_experts[np.asarray(experts, dtype=np.int64)]))
        return RouteSelection(
            prototype_indices=tuple(int(value) for value in order),
            scores=tuple(float(scores[value]) for value in order),
            score_margin=margin,
            observed_expert_fraction=coverage,
        )

