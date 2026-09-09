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


class GptOssCompressedExpertFrameStore(GptOssExpertFrameStore):
    """Retain verified compressed frames; expand only the live layer route."""

    def __init__(self, manifest_path: Path, capacity_bytes: int,
                 freeze_when_full: bool = False) -> None:
        super().__init__(manifest_path, 0)
        self.capacity_bytes = capacity_bytes
        self._encoded_cache: OrderedDict[tuple[int, int], dict[str, dict[str, tuple[bytes, dict[str, Any]]]]] = OrderedDict()
        self._cache_lock = threading.Lock()
        self.freeze_when_full = freeze_when_full
        self.admission_bypasses = 0

    def _read_encoded(self, layer: int, expert: int, projection: str,
                      kind: str) -> tuple[bytes, dict[str, Any]]:
        address = self._addresses[(layer, expert, projection, kind)]
        path = self.root / address["pack_relative_path"]
        with path.open("rb", buffering=0) as handle:
            encoded = os.pread(handle.fileno(), int(address["compressed_bytes"]),
                               int(address["encoded_offset"]))
        if (len(encoded) != int(address["compressed_bytes"])
                or hashlib.sha256(encoded).hexdigest() != address["compressed_sha256"]):
            raise RuntimeError(f"compressed expert-frame integrity failure: {path}")
        with self._metrics_lock:
            self.compressed_bytes_read += len(encoded)
        return encoded, address

    def _load_encoded(self, layer: int, expert: int):
        return {projection: {kind: self._read_encoded(layer, expert, projection, kind)
                             for kind in ("weight", "bias")}
                for projection in ("gate", "up", "down")}

    def _decode_encoded(self, value):
        result = {}
        for projection, components in value.items():
            result[projection] = {}
            for kind, (encoded, address) in components.items():
                raw_size = int(address["raw_bytes"])
                target = ctypes.create_string_buffer(raw_size)
                source = ctypes.create_string_buffer(encoded)
                decoded_size = self._zstd.ZSTD_decompress(target, raw_size, source, len(encoded))
                if self._zstd.ZSTD_isError(decoded_size) or int(decoded_size) != raw_size:
                    raise RuntimeError("cached expert-frame decode failed")
                raw = target.raw
                if hashlib.sha256(raw).hexdigest() != address["raw_sha256"]:
                    raise RuntimeError("cached expert-frame raw hash mismatch")
                result[projection][kind] = raw
                with self._metrics_lock:
                    self.raw_bytes_materialized += len(raw)
        return result

    @staticmethod
    def _encoded_size(value) -> int:
        return sum(len(encoded) for components in value.values()
                   for encoded, _ in components.values())

    def _retain_encoded(self, key, value) -> None:
        size = self._encoded_size(value)
        if size > self.capacity_bytes:
            return
        if (self.freeze_when_full and self._encoded_cache
                and self._resident + size > self.capacity_bytes):
            self.admission_bypasses += 1
            return
        while self._encoded_cache and self._resident + size > self.capacity_bytes:
            _, removed = self._encoded_cache.popitem(last=False)
            self._resident -= self._encoded_size(removed)
            self.evictions += 1
        self._encoded_cache[key] = value
        self._resident += size
        self.peak_resident_bytes = max(self.peak_resident_bytes, self._resident)

    def get(self, layer: int, expert: int) -> dict[str, dict[str, bytes]]:
        key = (layer, expert)
        with self._cache_lock:
            encoded = self._encoded_cache.pop(key, None)
            if encoded is not None:
                self.hits += 1
                self._encoded_cache[key] = encoded
        if encoded is None:
            self.faults += 1
            encoded = self._load_encoded(layer, expert)
            with self._cache_lock:
                self._retain_encoded(key, encoded)
        return self._decode_encoded(encoded)

    def get_layer_route_parallel(self, layer: int, experts: list[int],
                                 workers: int = 4) -> list[dict[str, dict[str, bytes]]]:
        if workers < 1:
            raise ValueError("workers must be positive")
        if len(experts) != len(set(experts)):
            raise ValueError("route must contain unique experts")
        with ThreadPoolExecutor(max_workers=min(workers, len(experts)),
                                thread_name_prefix="aion-gptoss-compressed") as pool:
            return list(pool.map(lambda expert: self.get(layer, expert), experts))

    def metrics(self) -> dict[str, int | float]:
        result = super().metrics()
        result["cache_representation"] = "verified_compressed_frames"
        result["freeze_when_full"] = self.freeze_when_full
        result["admission_bypasses"] = self.admission_bypasses
        return result


class GptOssTieredExpertFrameStore:
    """Keep the last route per layer raw and older candidates compressed."""

    def __init__(self, manifest_path: Path, capacity_bytes: int) -> None:
        if capacity_bytes < 3 * 1024 * 1024 * 1024:
            raise ValueError("tiered store requires the declared 3 GiB ceiling")
        self.capacity_bytes = capacity_bytes
        self.compressed = GptOssCompressedExpertFrameStore(
            manifest_path, 1250 * 1024 * 1024, freeze_when_full=True)
        self._raw_layers: dict[int, dict[int, dict[str, dict[str, bytes]]]] = {}
        self.raw_hits = 0
        self.route_calls = 0

    def get_layer_route_parallel(self, layer: int, experts: list[int],
                                 workers: int = 4) -> list[dict[str, dict[str, bytes]]]:
        if len(experts) != len(set(experts)):
            raise ValueError("route must contain unique experts")
        previous = self._raw_layers.get(layer, {})
        result: list[dict[str, dict[str, bytes]] | None] = []
        missing = []
        for expert in experts:
            value = previous.get(expert)
            if value is not None:
                self.raw_hits += 1
            else:
                missing.append(expert)
            result.append(value)
        if missing:
            loaded = self.compressed.get_layer_route_parallel(layer, missing, workers)
            iterator = iter(loaded)
            result = [next(iterator) if value is None else value for value in result]
        resolved = [value for value in result if value is not None]
        self._raw_layers[layer] = dict(zip(experts, resolved, strict=True))
        self.route_calls += 1
        return resolved

    def metrics(self) -> dict[str, int | float | str]:
        underlying = self.compressed.metrics()
        raw_bytes = sum(GptOssExpertFrameStore._value_size(value)
                        for layer in self._raw_layers.values() for value in layer.values())
        return {**underlying, "capacity_bytes": self.capacity_bytes,
                "cache_representation": "per-layer-raw-route-plus-compressed-history",
                "raw_route_hits": self.raw_hits, "route_calls": self.route_calls,
                "raw_route_resident_bytes": raw_bytes,
                "resident_bytes": raw_bytes + int(underlying["resident_bytes"]),
                "peak_resident_bytes": raw_bytes + int(underlying["peak_resident_bytes"])}
