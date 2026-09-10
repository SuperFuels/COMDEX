"""Bounded, verified access to gpt-oss expert-aligned warehouse frames."""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import os
import re
import struct
import threading
import uuid
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
        self._protected: set[tuple[int, int]] = set()
        self._admission_allowlist: set[tuple[int, int]] | None = None
        self._resident = 0
        self._zstd = _zstd()
        self.hits = 0
        self.faults = 0
        self.evictions = 0
        self.compressed_bytes_read = 0
        self.raw_bytes_materialized = 0
        self.peak_resident_bytes = 0
        self.admission_bypasses = 0
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
        if (self._admission_allowlist is not None
                and cache_key not in self._admission_allowlist):
            self.admission_bypasses += 1
            return
        if size <= self.capacity_bytes:
            while self._cache and self._resident + size > self.capacity_bytes:
                victim = next((key for key in self._cache if key not in self._protected), None)
                if victim is None:
                    self.admission_bypasses += 1
                    return
                removed = self._cache.pop(victim)
                self._resident -= self._value_size(removed)
                self.evictions += 1
            self._cache[cache_key] = value
            self._resident += size
            self.peak_resident_bytes = max(self.peak_resident_bytes, self._resident)

    def protect(self, layer_experts: dict[str, list[int]]) -> None:
        """Pin an already-resident bounded pool; later misses remain transient."""
        requested = {(int(layer), expert) for layer, experts in layer_experts.items()
                     for expert in experts}
        missing = requested.difference(self._cache)
        if missing:
            raise ValueError(f"cannot protect {len(missing)} non-resident experts")
        self._protected = requested

    def set_admission_allowlist(self, layer_experts: dict[str, list[int]]) -> None:
        """Retain only pool members while still serving exact transient misses."""
        self._admission_allowlist = {
            (int(layer), expert) for layer, experts in layer_experts.items()
            for expert in experts}

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
            "protected_entries": len(self._protected),
            "admission_allowlist_entries": (
                len(self._admission_allowlist)
                if self._admission_allowlist is not None else 0),
            "admission_bypasses": self.admission_bypasses,
            "compressed_bytes_read": self.compressed_bytes_read,
            "raw_bytes_materialized": self.raw_bytes_materialized,
        }


class GptOssPersistentL2ExpertFrameStore(GptOssExpertFrameStore):
    """Exact RAM LRU backed by a bounded process-persistent internal-disk L2.

    The SD warehouse remains authoritative. A verified SD miss is serialized as
    one raw expert frame under a manifest-bound namespace. Later processes may
    reconstruct the six components from that file only after checking every
    original component hash from the warehouse manifest.
    """

    _MAGIC = b"AIONL2R1"
    _ORDER = tuple((projection, kind)
                   for projection in ("gate", "up", "down")
                   for kind in ("weight", "bias"))
    _HEADER = struct.Struct("<8s6Q")

    def __init__(self, manifest_path: Path, capacity_bytes: int,
                 l2_root: Path, l2_capacity_bytes: int) -> None:
        if l2_capacity_bytes < 0:
            raise ValueError("l2_capacity_bytes must be non-negative")
        super().__init__(manifest_path, capacity_bytes)
        manifest_sha = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        self.l2_root = l2_root.resolve() / manifest_sha
        self.l2_root.mkdir(parents=True, exist_ok=True)
        self.l2_capacity_bytes = l2_capacity_bytes
        self.l2_hits = 0
        self.l2_misses = 0
        self.l2_bytes_read = 0
        self.l2_bytes_written = 0
        self.l2_evictions = 0
        self.l2_integrity_failures = 0
        self.sd_fallbacks = 0
        self._l2_bypass: set[tuple[int, int]] = set()
        self._l2_lock = threading.Lock()

    def _l2_path(self, layer: int, expert: int) -> Path:
        return self.l2_root / f"layer-{layer:02d}-expert-{expert:03d}.aionraw"

    def _component_address(self, layer: int, expert: int,
                           projection: str, kind: str) -> dict[str, Any]:
        return self._addresses[(layer, expert, projection, kind)]

    def _read_l2(self, layer: int, expert: int) -> dict[str, dict[str, bytes]] | None:
        if (layer, expert) in self._l2_bypass:
            self.l2_misses += 1
            return None
        path = self._l2_path(layer, expert)
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            self.l2_misses += 1
            return None
        try:
            if len(payload) < self._HEADER.size:
                raise ValueError("short L2 header")
            magic, *lengths = self._HEADER.unpack_from(payload)
            if magic != self._MAGIC or self._HEADER.size + sum(lengths) != len(payload):
                raise ValueError("invalid L2 frame")
            cursor = self._HEADER.size
            value: dict[str, dict[str, bytes]] = {}
            for (projection, kind), length in zip(self._ORDER, lengths, strict=True):
                raw = payload[cursor:cursor + length]
                cursor += length
                address = self._component_address(layer, expert, projection, kind)
                if (length != int(address["raw_bytes"])
                        or hashlib.sha256(raw).hexdigest() != address["raw_sha256"]):
                    raise ValueError("L2 component hash mismatch")
                value.setdefault(projection, {})[kind] = raw
        except (KeyError, ValueError, struct.error):
            self.l2_integrity_failures += 1
            self.l2_misses += 1
            path.unlink(missing_ok=True)
            return None
        os.utime(path, None)
        self.l2_hits += 1
        self.l2_bytes_read += len(payload)
        with self._metrics_lock:
            self.raw_bytes_materialized += len(payload) - self._HEADER.size
        return value

    def _l2_files(self) -> list[Path]:
        return [path for path in self.l2_root.glob("*.aionraw") if path.is_file()]

    def _evict_l2_for(self, incoming: int) -> bool:
        files = self._l2_files()
        resident = sum(path.stat().st_size for path in files)
        if incoming > self.l2_capacity_bytes:
            return False
        for victim in sorted(files, key=lambda path: (path.stat().st_mtime_ns, path.name)):
            if resident + incoming <= self.l2_capacity_bytes:
                break
            size = victim.stat().st_size
            victim.unlink(missing_ok=True)
            resident -= size
            self.l2_evictions += 1
        return resident + incoming <= self.l2_capacity_bytes

    def _write_l2(self, layer: int, expert: int,
                  value: dict[str, dict[str, bytes]]) -> None:
        if (layer, expert) in self._l2_bypass:
            return
        components = [value[projection][kind] for projection, kind in self._ORDER]
        payload_size = self._HEADER.size + sum(map(len, components))
        with self._l2_lock:
            destination = self._l2_path(layer, expert)
            if destination.exists() or not self._evict_l2_for(payload_size):
                return
            temporary = destination.with_name(
                destination.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb", buffering=0) as handle:
                    handle.write(self._HEADER.pack(
                        self._MAGIC, *(len(component) for component in components)))
                    for component in components:
                        handle.write(component)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
                self.l2_bytes_written += payload_size
            finally:
                temporary.unlink(missing_ok=True)

    def _load_value(self, layer: int, expert: int) -> dict[str, dict[str, bytes]]:
        cached = self._read_l2(layer, expert)
        if cached is not None:
            return cached
        self.sd_fallbacks += 1
        value = super()._load_value(layer, expert)
        self._write_l2(layer, expert, value)
        return value

    def set_l2_bypass(self, layer_experts: dict[str, list[int]]) -> None:
        """Do not duplicate a separately resident/protected RAM pool in L2."""
        self._l2_bypass = {(int(layer), expert)
                           for layer, experts in layer_experts.items()
                           for expert in experts}

    def metrics(self) -> dict[str, int | float | str]:
        result = super().metrics()
        files = self._l2_files()
        return {
            **result,
            "cache_representation": "raw_hash_verified_internal_disk_l2",
            "l2_root": str(self.l2_root),
            "l2_capacity_bytes": self.l2_capacity_bytes,
            "l2_resident_bytes": sum(path.stat().st_size for path in files),
            "l2_entries": len(files),
            "l2_hits": self.l2_hits,
            "l2_misses": self.l2_misses,
            "l2_bytes_read": self.l2_bytes_read,
            "l2_bytes_written": self.l2_bytes_written,
            "l2_evictions": self.l2_evictions,
            "l2_integrity_failures": self.l2_integrity_failures,
            "sd_fallbacks": self.sd_fallbacks,
            "l2_bypass_entries": len(self._l2_bypass),
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
