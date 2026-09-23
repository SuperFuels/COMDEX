"""Bounded zero-copy-addressed reader for expert slices in a Qwen GGUF."""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any


class QwenExpertGlyphStore:
    """Read exact packed expert bytes through a strict byte-budgeted LRU."""

    def __init__(self, manifest_path: Path, capacity_bytes: int) -> None:
        if capacity_bytes < 0:
            raise ValueError("capacity_bytes must be non-negative")
        self.manifest_path = manifest_path.resolve()
        self.manifest = json.loads(self.manifest_path.read_text())
        if self.manifest.get("schema") != "aion.qwen3moe.gguf-expert-addresses.v1":
            raise ValueError("unsupported expert-address manifest")
        self.model_path = Path(self.manifest["source_path"]).resolve()
        if self.model_path.stat().st_size != int(self.manifest["source_bytes"]):
            raise RuntimeError("GGUF size differs from the bound expert manifest")
        self.capacity_bytes = capacity_bytes
        self._handle = self.model_path.open("rb", buffering=0)
        self._cache: OrderedDict[tuple[int, int], tuple[bytes, bytes, bytes]] = OrderedDict()
        self.resident_bytes = 0
        self.peak_resident_bytes = 0
        self.hits = 0
        self.faults = 0
        self.physical_bytes = 0
        self.evictions = 0

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "QwenExpertGlyphStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _entry(self, layer: int, expert: int) -> dict[str, Any]:
        entry = self.manifest["layers"][layer]["experts"][expert]
        if int(entry["expert"]) != expert:
            raise RuntimeError("expert manifest ordering mismatch")
        return entry

    def _read(self, entry: dict[str, Any]) -> tuple[bytes, bytes, bytes]:
        values = []
        for projection in ("gate", "up", "down"):
            address = entry["ranges"][projection]
            length = int(address["byte_length"])
            value = os.pread(self._handle.fileno(), length, int(address["absolute_offset"]))
            if len(value) != length:
                raise RuntimeError("short expert-range read")
            values.append(value)
            self.physical_bytes += length
        return values[0], values[1], values[2]

    def get(self, layer: int, expert: int) -> tuple[bytes, bytes, bytes]:
        key = (layer, expert)
        cached = self._cache.pop(key, None)
        if cached is not None:
            self.hits += 1
            self._cache[key] = cached
            return cached
        self.faults += 1
        entry = self._entry(layer, expert)
        value = self._read(entry)
        size = sum(len(part) for part in value)
        if size > self.capacity_bytes:
            return value
        while self._cache and self.resident_bytes + size > self.capacity_bytes:
            _, removed = self._cache.popitem(last=False)
            self.resident_bytes -= sum(len(part) for part in removed)
            self.evictions += 1
        self._cache[key] = value
        self.resident_bytes += size
        self.peak_resident_bytes = max(self.peak_resident_bytes, self.resident_bytes)
        return value

    def get_layer_route(self, layer: int, experts: list[int]) -> list[tuple[bytes, bytes, bytes]]:
        if len(set(experts)) != len(experts):
            raise ValueError("route must contain unique experts")
        return [self.get(layer, expert) for expert in experts]

    def metrics(self) -> dict[str, int | float]:
        accesses = self.hits + self.faults
        return {
            "capacity_bytes": self.capacity_bytes,
            "resident_bytes": self.resident_bytes,
            "peak_resident_bytes": self.peak_resident_bytes,
            "hits": self.hits,
            "faults": self.faults,
            "hit_rate": self.hits / accesses if accesses else 0.0,
            "physical_bytes": self.physical_bytes,
            "evictions": self.evictions,
        }
