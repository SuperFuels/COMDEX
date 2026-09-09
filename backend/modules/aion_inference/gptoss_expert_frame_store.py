"""Bounded, verified access to gpt-oss expert-aligned warehouse frames."""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import os
import re
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


_EXPERT = re.compile(
    r"^blk\.(?P<layer>\d+)\.ffn_(?P<projection>down|gate|up)_exps\.(?P<kind>weight|bias)$"
)


def _zstd() -> ctypes.CDLL:
    path = ctypes.util.find_library("zstd")
    if not path:
        raise RuntimeError("system libzstd is unavailable")
    library = ctypes.CDLL(path)
    library.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                         ctypes.c_void_p, ctypes.c_size_t]
    library.ZSTD_decompress.restype = ctypes.c_size_t
    library.ZSTD_isError.argtypes = [ctypes.c_size_t]
    library.ZSTD_isError.restype = ctypes.c_uint
    return library


class GptOssExpertFrameStore:
    """Read one exact Q4/MXFP4 expert through a strict raw-byte LRU."""

    def __init__(self, manifest_path: Path, capacity_bytes: int) -> None:
        if capacity_bytes < 0:
            raise ValueError("capacity_bytes must be non-negative")
        self.manifest_path = manifest_path.resolve()
        self.root = self.manifest_path.parent
        self.manifest = json.loads(self.manifest_path.read_text())
        if (self.manifest.get("schema") != "aion.expert-frame-warehouse.v1"
                or self.manifest.get("status") != "COMPLETE_VERIFIED"):
            raise ValueError("expert warehouse is not complete and verified")
        self._addresses: dict[tuple[int, int, str, str], dict[str, Any]] = {}
        for region in self.manifest["regions"]:
            match = _EXPERT.match(region["region_name"])
            if not match:
                continue
            for frame in region["frames"]:
                expert = int(frame["expert"])
                key = (int(match.group("layer")), expert,
                       match.group("projection"), match.group("kind"))
                if key in self._addresses:
                    raise RuntimeError(f"duplicate expert address {key}")
                self._addresses[key] = {
                    "pack_relative_path": region["pack_relative_path"], **frame,
                }
        if not self._addresses:
            raise RuntimeError("warehouse contains no expert frames")
        self.capacity_bytes = capacity_bytes
        self._cache: OrderedDict[tuple[int, int], dict[str, dict[str, bytes]]] = OrderedDict()
        self._resident = 0
        self._zstd = _zstd()
        self.hits = 0
        self.faults = 0
        self.evictions = 0
        self.compressed_bytes_read = 0
        self.raw_bytes_materialized = 0
        self.peak_resident_bytes = 0
        self._metrics_lock = threading.Lock()

    def _component(self, layer: int, expert: int, projection: str, kind: str) -> bytes:
        key = (layer, expert, projection, kind)
        if key not in self._addresses:
            raise KeyError(f"missing expert component {key}")
        address = self._addresses[key]
        path = self.root / address["pack_relative_path"]
        with path.open("rb", buffering=0) as handle:
            encoded = os.pread(handle.fileno(), int(address["compressed_bytes"]),
                               int(address["encoded_offset"]))
        if len(encoded) != int(address["compressed_bytes"]):
            raise RuntimeError(f"short expert-frame read: {path}")
        if hashlib.sha256(encoded).hexdigest() != address["compressed_sha256"]:
            raise RuntimeError(f"compressed expert-frame hash mismatch: {path}")
        raw_size = int(address["raw_bytes"])
        target = ctypes.create_string_buffer(raw_size)
        source = ctypes.create_string_buffer(encoded)
        result = self._zstd.ZSTD_decompress(target, raw_size, source, len(encoded))
        if self._zstd.ZSTD_isError(result) or int(result) != raw_size:
            raise RuntimeError(f"expert-frame decode failed: {path}")
        raw = target.raw
        if hashlib.sha256(raw).hexdigest() != address["raw_sha256"]:
            raise RuntimeError(f"decoded expert-frame hash mismatch: {path}")
        with self._metrics_lock:
            self.compressed_bytes_read += len(encoded)
            self.raw_bytes_materialized += len(raw)
        return raw

    def _load_value(self, layer: int, expert: int) -> dict[str, dict[str, bytes]]:
        return {
            projection: {
                kind: self._component(layer, expert, projection, kind)
                for kind in ("weight", "bias")
            }
            for projection in ("gate", "up", "down")
        }

    @staticmethod
    def _value_size(value: dict[str, dict[str, bytes]]) -> int:
        return sum(len(component) for projection in value.values()
                   for component in projection.values())

    def _retain(self, cache_key: tuple[int, int],
                value: dict[str, dict[str, bytes]]) -> None:
        size = self._value_size(value)
        if size <= self.capacity_bytes:
            while self._cache and self._resident + size > self.capacity_bytes:
                _, removed = self._cache.popitem(last=False)
                self._resident -= self._value_size(removed)
                self.evictions += 1
            self._cache[cache_key] = value
            self._resident += size
            self.peak_resident_bytes = max(self.peak_resident_bytes, self._resident)

    def get(self, layer: int, expert: int) -> dict[str, dict[str, bytes]]:
        cache_key = (layer, expert)
        cached = self._cache.pop(cache_key, None)
        if cached is not None:
            self.hits += 1
            self._cache[cache_key] = cached
            return cached
        self.faults += 1
        value = self._load_value(layer, expert)
        self._retain(cache_key, value)
        return value

    def get_layer_route(self, layer: int, experts: list[int]) -> list[dict[str, dict[str, bytes]]]:
        if len(experts) != len(set(experts)):
            raise ValueError("route must contain unique experts")
        return [self.get(layer, expert) for expert in experts]

    def get_layer_route_parallel(self, layer: int, experts: list[int],
                                 workers: int = 4) -> list[dict[str, dict[str, bytes]]]:
        """Fault missing experts concurrently, then retain them deterministically."""
        if workers < 1:
            raise ValueError("workers must be positive")
        if len(experts) != len(set(experts)):
            raise ValueError("route must contain unique experts")
        results: list[dict[str, dict[str, bytes]] | None] = [None] * len(experts)
        missing: list[tuple[int, int]] = []
        for position, expert in enumerate(experts):
            cache_key = (layer, expert)
            cached = self._cache.pop(cache_key, None)
            if cached is None:
                self.faults += 1
                missing.append((position, expert))
            else:
                self.hits += 1
                self._cache[cache_key] = cached
                results[position] = cached
        if missing:
            with ThreadPoolExecutor(max_workers=min(workers, len(missing)),
                                    thread_name_prefix="aion-gptoss-expert") as pool:
                loaded = list(pool.map(lambda item: self._load_value(layer, item[1]), missing))
            for (position, expert), value in zip(missing, loaded, strict=True):
                self._retain((layer, expert), value)
                results[position] = value
        if any(value is None for value in results):
            raise RuntimeError("parallel expert route remained incomplete")
        return [value for value in results if value is not None]

    def metrics(self) -> dict[str, int | float]:
        accesses = self.hits + self.faults
        return {
            "capacity_bytes": self.capacity_bytes,
            "resident_bytes": self._resident,
            "peak_resident_bytes": self.peak_resident_bytes,
            "hits": self.hits, "faults": self.faults,
            "hit_rate": self.hits / accesses if accesses else 0.0,
            "evictions": self.evictions,
            "compressed_bytes_read": self.compressed_bytes_read,
            "raw_bytes_materialized": self.raw_bytes_materialized,
        }
