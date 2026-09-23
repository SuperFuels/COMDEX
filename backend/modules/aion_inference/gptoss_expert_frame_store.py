"""Bounded, verified access to gpt-oss expert-aligned warehouse frames."""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
import mmap
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
        self._l2_protected: set[tuple[int, int]] = set()
        self._l2_two_touch_admission = False
        self._l2_admission_touches = 2
        self._l2_probation: dict[tuple[int, int], int] = {}
        self.l2_admission_bypasses = 0
        self.l2_admission_promotions = 0
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

    @staticmethod
    def _l2_file_key(path: Path) -> tuple[int, int] | None:
        match = re.fullmatch(r"layer-(\d+)-expert-(\d+)\.aionraw", path.name)
        return ((int(match.group(1)), int(match.group(2))) if match else None)

    def _l2_evictable_files(self, files: list[Path]) -> list[Path]:
        """Return LRU victims without sacrificing an active exact cartridge."""
        return sorted(
            (path for path in files if self._l2_file_key(path) not in self._l2_protected),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
        )

    def _evict_l2_for(self, incoming: int) -> bool:
        files = self._l2_files()
        resident = sum(path.stat().st_size for path in files)
        if incoming > self.l2_capacity_bytes:
            return False
        for victim in self._l2_evictable_files(files):
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
            if destination.exists():
                return
            if not self._should_admit_l2((layer, expert)):
                return
            if not self._evict_l2_for(payload_size):
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

    def set_l2_protected(self, layer_experts: dict[str, list[int]]) -> None:
        """Protect an exact core/cartridge from L2 eviction without prefetching it."""
        protected = {(int(layer), int(expert))
                     for layer, experts in layer_experts.items()
                     for expert in experts}
        if protected & self._l2_bypass:
            raise ValueError("an L2 expert cannot be both protected and bypassed")
        self._l2_protected = protected

    def set_l2_two_touch_admission(self, enabled: bool = True,
                                   required_touches: int = 2) -> None:
        """Admit non-cartridge exceptions only after a repeated demand.

        A long sequential route can otherwise fill the small unprotected tail
        of a family cartridge with one-use experts, evicting exceptions just
        before their next reuse.  Protected entries remain immediately
        admissible; exact first-touch exceptions are served transiently from
        the authoritative SD warehouse.
        """
        if required_touches < 2:
            raise ValueError("L2 exception admission requires at least two touches")
        self._l2_two_touch_admission = enabled
        self._l2_admission_touches = required_touches
        if not enabled:
            self._l2_probation.clear()

    def _should_admit_l2(self, cache_key: tuple[int, int]) -> bool:
        if (not self._l2_two_touch_admission
                or cache_key in self._l2_protected):
            return True
        touches = self._l2_probation.get(cache_key, 0) + 1
        if touches >= self._l2_admission_touches:
            self._l2_probation.pop(cache_key, None)
            self.l2_admission_promotions += 1
            return True
        self._l2_probation[cache_key] = touches
        self.l2_admission_bypasses += 1
        return False

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
            "l2_protected_entries": len(self._l2_protected),
            "l2_protected_resident_entries": sum(
                self._l2_file_key(path) in self._l2_protected for path in files),
            "l2_two_touch_admission": self._l2_two_touch_admission,
            "l2_admission_required_touches": self._l2_admission_touches,
            "l2_probation_entries": len(self._l2_probation),
            "l2_admission_bypasses": self.l2_admission_bypasses,
            "l2_admission_promotions": self.l2_admission_promotions,
        }


class GptOssMappedPersistentL2ExpertFrameStore(GptOssPersistentL2ExpertFrameStore):
    """Expose verified L2 frame components as mmap-backed packed-weight views.

    The first access in a process verifies every component exactly. The
    resulting private mapping is then a process-lifetime verified snapshot,
    matching the trust boundary of the raw RAM L1. A new process revalidates
    the frame. AION modifies frames only by atomic replacement, so a path
    replacement cannot alter an already admitted mapping. The returned views
    retain the mapping for as long as native calculation can reference it.
    """

    def __init__(self, manifest_path: Path, capacity_bytes: int,
                 l2_root: Path, l2_capacity_bytes: int) -> None:
        super().__init__(manifest_path, capacity_bytes, l2_root, l2_capacity_bytes)
        self._verified_l2: dict[tuple[int, int], tuple[int, int, int, int, int]] = {}
        self._mapped_values: OrderedDict[
            tuple[int, int],
            tuple[tuple[int, int, int, int, int], dict[str, dict[str, memoryview]]],
        ] = OrderedDict()
        self.mapped_l2_hits = 0
        self.mapped_l2_view_reuses = 0
        self.mapped_l2_logical_bytes = 0
        self.l2_verification_passes = 0
        self.l2_verification_reuses = 0
        self.l2_verification_bytes = 0
        self.mapped_l2_willneed_calls = 0

    @staticmethod
    def _file_signature(stat_result: os.stat_result) -> tuple[int, int, int, int, int]:
        return (stat_result.st_dev, stat_result.st_ino, stat_result.st_size,
                stat_result.st_mtime_ns, stat_result.st_ctime_ns)

    def _read_l2(self, layer: int, expert: int) -> dict[str, dict[str, memoryview]] | None:
        cache_key = (layer, expert)
        if cache_key in self._l2_bypass:
            self.l2_misses += 1
            return None
        path = self._l2_path(layer, expert)
        mapped = self._mapped_values.pop(cache_key, None)
        if mapped is not None:
            self._mapped_values[cache_key] = mapped
            logical_bytes = self._HEADER.size + sum(
                len(component) for projection in mapped[1].values()
                for component in projection.values())
            self.l2_hits += 1
            self.mapped_l2_hits += 1
            self.mapped_l2_view_reuses += 1
            self.l2_verification_reuses += 1
            self.l2_bytes_read += logical_bytes
            self.mapped_l2_logical_bytes += logical_bytes
            return mapped[1]
        try:
            with path.open("rb", buffering=0) as handle:
                signature = self._file_signature(os.fstat(handle.fileno()))
                mapping = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_COPY)
                mapping.madvise(mmap.MADV_SEQUENTIAL)
        except FileNotFoundError:
            self.l2_misses += 1
            return None
        value: dict[str, dict[str, memoryview]] = {}
        try:
            if len(mapping) < self._HEADER.size:
                raise ValueError("short mapped L2 header")
            magic, *lengths = self._HEADER.unpack_from(mapping)
            if magic != self._MAGIC or self._HEADER.size + sum(lengths) != len(mapping):
                raise ValueError("invalid mapped L2 frame")
            verify_components = self._verified_l2.get(cache_key) != signature
            cursor = self._HEADER.size
            for (projection, kind), length in zip(self._ORDER, lengths, strict=True):
                raw = memoryview(mapping)[cursor:cursor + length]
                cursor += length
                address = self._component_address(layer, expert, projection, kind)
                if length != int(address["raw_bytes"]):
                    raise ValueError("mapped L2 component length mismatch")
                if (verify_components
                        and hashlib.sha256(raw).hexdigest() != address["raw_sha256"]):
                    raise ValueError("mapped L2 component hash mismatch")
                value.setdefault(projection, {})[kind] = raw
            if verify_components:
                self.l2_verification_passes += 1
                self.l2_verification_bytes += len(mapping) - self._HEADER.size
            else:
                self.l2_verification_reuses += 1
        except (KeyError, ValueError, struct.error):
            self.l2_integrity_failures += 1
            self.l2_misses += 1
            self._verified_l2.pop(cache_key, None)
            value.clear()
            if "raw" in locals():
                raw.release()
            mapping.close()
            path.unlink(missing_ok=True)
            return None
        os.utime(path, None)
        signature = self._file_signature(path.stat())
        self._verified_l2[cache_key] = signature
        self._mapped_values[cache_key] = (signature, value)
        self.l2_hits += 1
        self.mapped_l2_hits += 1
        self.l2_bytes_read += len(mapping)
        self.mapped_l2_logical_bytes += len(mapping)
        return value

    def metrics(self) -> dict[str, int | float | str]:
        return {
            **super().metrics(),
            "cache_representation": "direct_mapped_hash_verified_internal_disk_l2",
            "mapped_l2_hits": self.mapped_l2_hits,
            "mapped_l2_open_views": len(self._mapped_values),
            "mapped_l2_view_reuses": self.mapped_l2_view_reuses,
            "mapped_l2_logical_bytes": self.mapped_l2_logical_bytes,
            "l2_verification_passes": self.l2_verification_passes,
            "l2_verification_reuses": self.l2_verification_reuses,
            "l2_verification_bytes": self.l2_verification_bytes,
            "mapped_l2_willneed_calls": self.mapped_l2_willneed_calls,
        }

    def advise_route_willneed(self, values: list[dict[str, dict[str, Any]]]) -> None:
        """Ask the kernel to begin paging mapped route experts before compute."""
        mappings: dict[int, mmap.mmap] = {}
        for value in values:
            for projection in ("gate", "up", "down"):
                for kind in ("weight", "bias"):
                    component = value[projection][kind]
                    if isinstance(component, memoryview) and isinstance(component.obj, mmap.mmap):
                        mappings[id(component.obj)] = component.obj
        for mapping in mappings.values():
            mapping.madvise(mmap.MADV_WILLNEED)
        self.mapped_l2_willneed_calls += len(mappings)

    def get_layer_route_parallel(self, layer: int, experts: list[int],
                                 workers: int = 4) -> list[dict[str, dict[str, Any]]]:
        """Avoid constructing a fault pool when every requested view is open."""
        if workers < 1:
            raise ValueError("workers must be positive")
        if len(experts) != len(set(experts)):
            raise ValueError("route must contain unique experts")
        keys = [(layer, expert) for expert in experts]
        if all(key in self._cache or key in self._mapped_values for key in keys):
            return [self.get(layer, expert) for expert in experts]
        return super().get_layer_route_parallel(layer, experts, workers)

    def _evict_l2_for(self, incoming: int) -> bool:
        files = self._l2_files()
        resident = sum(path.stat().st_size for path in files)
        if incoming > self.l2_capacity_bytes:
            return False
        for victim in self._l2_evictable_files(files):
            if resident + incoming <= self.l2_capacity_bytes:
                break
            key = self._l2_file_key(victim)
            if key is not None:
                # Dropping our references is safe even if a currently executing
                # route still owns views; those views keep the old mapping alive
                # until native execution returns.
                self._mapped_values.pop(key, None)
                self._verified_l2.pop(key, None)
            size = victim.stat().st_size
            victim.unlink(missing_ok=True)
            resident -= size
            self.l2_evictions += 1
        return resident + incoming <= self.l2_capacity_bytes

    def set_l2_bypass(self, layer_experts: dict[str, list[int]]) -> None:
        super().set_l2_bypass(layer_experts)
        for key in self._l2_bypass:
            self._mapped_values.pop(key, None)
            self._verified_l2.pop(key, None)


class GptOssPinnedVerifiedPersistentL2ExpertFrameStore(
        GptOssPersistentL2ExpertFrameStore):
    """Bulk-read L2 frames while hashing each immutable frame once per process.

    AION writes L2 frames by atomic replacement and never mutates an admitted
    frame in place. Consequently, a frame that passed all six manifest hashes
    can use the same process-lifetime trust epoch as an admitted RAM-cache
    value. A new process has an empty epoch and verifies the frame again. This
    retains the copied representation that avoids demand paging during native
    calculation while removing repeated SHA-256 work from stable reuse.
    """

    def __init__(self, manifest_path: Path, capacity_bytes: int,
                 l2_root: Path, l2_capacity_bytes: int) -> None:
        super().__init__(manifest_path, capacity_bytes, l2_root, l2_capacity_bytes)
        self._verified_l2: set[tuple[int, int]] = set()
        self.l2_verification_passes = 0
        self.l2_verification_reuses = 0
        self.l2_verification_bytes = 0

    def _read_l2(self, layer: int, expert: int) -> dict[str, dict[str, bytes]] | None:
        cache_key = (layer, expert)
        if cache_key in self._l2_bypass:
            self.l2_misses += 1
            return None
        path = self._l2_path(layer, expert)
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            self.l2_misses += 1
            self._verified_l2.discard(cache_key)
            return None
        verify_components = cache_key not in self._verified_l2
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
                if length != int(address["raw_bytes"]):
                    raise ValueError("L2 component length mismatch")
                if (verify_components
                        and hashlib.sha256(raw).hexdigest() != address["raw_sha256"]):
                    raise ValueError("L2 component hash mismatch")
                value.setdefault(projection, {})[kind] = raw
        except (KeyError, ValueError, struct.error):
            self.l2_integrity_failures += 1
            self.l2_misses += 1
            self._verified_l2.discard(cache_key)
            path.unlink(missing_ok=True)
            return None
        if verify_components:
            self._verified_l2.add(cache_key)
            self.l2_verification_passes += 1
            self.l2_verification_bytes += len(payload) - self._HEADER.size
        else:
            self.l2_verification_reuses += 1
        os.utime(path, None)
        self.l2_hits += 1
        self.l2_bytes_read += len(payload)
        with self._metrics_lock:
            self.raw_bytes_materialized += len(payload) - self._HEADER.size
        return value

    def _evict_l2_for(self, incoming: int) -> bool:
        before = set(self._l2_files())
        accepted = super()._evict_l2_for(incoming)
        after = set(self._l2_files())
        for victim in before - after:
            match = re.fullmatch(r"layer-(\d+)-expert-(\d+)\.aionraw", victim.name)
            if match:
                self._verified_l2.discard((int(match.group(1)), int(match.group(2))))
        return accepted

    def metrics(self) -> dict[str, int | float | str]:
        return {
            **super().metrics(),
            "cache_representation": "bulk_copied_process_verified_internal_disk_l2",
            "l2_verified_epoch_entries": len(self._verified_l2),
            "l2_verification_passes": self.l2_verification_passes,
            "l2_verification_reuses": self.l2_verification_reuses,
            "l2_verification_bytes": self.l2_verification_bytes,
        }


class GptOssReusableArenaPersistentL2ExpertFrameStore(
        GptOssPinnedVerifiedPersistentL2ExpertFrameStore):
    """Read transient four-expert routes directly into reusable resident arenas.

    The ordinary copied L2 path first allocates a whole-file ``bytes`` object
    and then copies each of its six slices into another ``bytes`` object. This
    variant performs one ``preadv`` into each preallocated expert slot and
    exposes component memoryviews to the existing packed native kernel. The
    read dirties/touches every destination page before calculation, avoiding
    the deferred page-fault behaviour of file-backed mmap.
    """

    def __init__(self, manifest_path: Path, capacity_bytes: int,
                 l2_root: Path, l2_capacity_bytes: int) -> None:
        super().__init__(manifest_path, capacity_bytes, l2_root, l2_capacity_bytes)
        largest = max(
            self._HEADER.size + sum(int(self._component_address(layer, expert, p, k)["raw_bytes"])
                                    for p, k in self._ORDER)
            for layer, expert in {(key[0], key[1]) for key in self._addresses}
        )
        self._route_arenas = [bytearray(largest) for _ in range(4)]
        self.route_arena_capacity_bytes = largest * len(self._route_arenas)
        self.route_arena_reads = 0
        self.route_arena_bytes_read = 0
        self._route_arena_l1_allowlist: set[tuple[int, int]] = set()
        self.route_arena_l1_admissions = 0
        self.route_arena_l1_admission_bytes = 0
        self.partial_l2_read_calls = 0
        self.partial_l2_bytes_read = 0

    def set_route_arena_l1_allowlist(
            self, layer_experts: dict[str, list[int]]) -> None:
        """Admit only a measured hot subset from transient arenas into durable L1."""
        self._route_arena_l1_allowlist = {
            (int(layer), int(expert))
            for layer, experts in layer_experts.items() for expert in experts
        }

    def maybe_admit_route_arena_l1(self, layer: int, expert: int, value):
        """Copy an allowlisted transient arena value into durable bounded L1."""
        cache_key = (layer, expert)
        if cache_key not in self._route_arena_l1_allowlist:
            return value
        stable = {
            projection: {
                kind: bytes(component)
                for kind, component in components.items()
            }
            for projection, components in value.items()
        }
        before = self._resident
        self._retain(cache_key, stable)
        if self._resident > before:
            self.route_arena_l1_admissions += 1
            self.route_arena_l1_admission_bytes += self._resident - before
        return stable

    def _read_l2_into_slot(self, layer: int, expert: int, slot: int):
        cache_key = (layer, expert)
        if cache_key in self._l2_bypass:
            self.l2_misses += 1
            return None
        path = self._l2_path(layer, expert)
        try:
            size = path.stat().st_size
            arena = self._route_arenas[slot]
            if size > len(arena):
                raise ValueError("L2 frame exceeds route arena")
            with path.open("rb", buffering=0) as handle:
                written = os.preadv(handle.fileno(), [memoryview(arena)[:size]], 0)
        except FileNotFoundError:
            self.l2_misses += 1
            self._verified_l2.discard(cache_key)
            return None
        if written != size:
            raise RuntimeError("short reusable-arena L2 read")
        frame = memoryview(arena)[:size]
        verify_components = cache_key not in self._verified_l2
        try:
            if size < self._HEADER.size:
                raise ValueError("short L2 header")
            magic, *lengths = self._HEADER.unpack_from(frame)
            if magic != self._MAGIC or self._HEADER.size + sum(lengths) != size:
                raise ValueError("invalid L2 frame")
            cursor = self._HEADER.size
            value: dict[str, dict[str, memoryview]] = {}
            for (projection, kind), length in zip(self._ORDER, lengths, strict=True):
                raw = frame[cursor:cursor + length]
                cursor += length
                address = self._component_address(layer, expert, projection, kind)
                if length != int(address["raw_bytes"]):
                    raise ValueError("L2 component length mismatch")
                if (verify_components
                        and hashlib.sha256(raw).hexdigest() != address["raw_sha256"]):
                    raise ValueError("L2 component hash mismatch")
                value.setdefault(projection, {})[kind] = raw
        except (KeyError, ValueError, struct.error):
            self.l2_integrity_failures += 1
            self.l2_misses += 1
            self._verified_l2.discard(cache_key)
            path.unlink(missing_ok=True)
            return None
        if verify_components:
            self._verified_l2.add(cache_key)
            self.l2_verification_passes += 1
            self.l2_verification_bytes += size - self._HEADER.size
        else:
            self.l2_verification_reuses += 1
        self.l2_hits += 1
        self.l2_bytes_read += size
        self.route_arena_reads += 1
        self.route_arena_bytes_read += size
        with self._metrics_lock:
            self.raw_bytes_materialized += size - self._HEADER.size
        return value

    def read_verified_l2_component_group_into_slot(
            self, layer: int, expert: int, slot: int,
            component_indices: tuple[int, ...]):
        """Read selected components into their normal arena offsets.

        Partial reads are permitted only after this process has verified every
        component of the immutable L2 frame once.  This retains the existing
        integrity boundary while allowing gate/up calculation to overlap the
        later down-projection read.
        """
        cache_key = (layer, expert)
        if cache_key not in self._verified_l2:
            raise ValueError("partial L2 read requires process-verified frame")
        if not component_indices or any(index < 0 or index >= len(self._ORDER)
                                        for index in component_indices):
            raise ValueError("invalid partial L2 component selection")
        path = self._l2_path(layer, expert)
        arena = self._route_arenas[slot]
        try:
            with path.open("rb", buffering=0) as handle:
                header = os.pread(handle.fileno(), self._HEADER.size, 0)
                if len(header) != self._HEADER.size:
                    raise ValueError("short L2 header")
                magic, *lengths = self._HEADER.unpack(header)
                if magic != self._MAGIC:
                    raise ValueError("invalid L2 frame")
                offsets = []
                cursor = self._HEADER.size
                for length in lengths:
                    offsets.append(cursor)
                    cursor += length
                if cursor != path.stat().st_size:
                    raise ValueError("invalid L2 frame size")
                value: dict[str, dict[str, memoryview]] = {}
                bytes_read = len(header)
                for index in component_indices:
                    projection, kind = self._ORDER[index]
                    length = lengths[index]
                    offset = offsets[index]
                    address = self._component_address(layer, expert, projection, kind)
                    if length != int(address["raw_bytes"]):
                        raise ValueError("L2 component length mismatch")
                    target = memoryview(arena)[offset:offset + length]
                    written = os.preadv(handle.fileno(), [target], offset)
                    if written != length:
                        raise RuntimeError("short partial reusable-arena L2 read")
                    value.setdefault(projection, {})[kind] = target
                    bytes_read += written
        except (FileNotFoundError, KeyError, ValueError, struct.error):
            self.l2_integrity_failures += 1
            raise
        self.partial_l2_read_calls += 1
        self.partial_l2_bytes_read += bytes_read
        self.l2_bytes_read += bytes_read
        self.route_arena_bytes_read += bytes_read
        with self._metrics_lock:
            self.raw_bytes_materialized += bytes_read - self._HEADER.size
        return value

    def get_layer_route_parallel(self, layer: int, experts: list[int],
                                 workers: int = 4):
        if workers < 1:
            raise ValueError("workers must be positive")
        if len(experts) != len(set(experts)):
            raise ValueError("route must contain unique experts")
        # Protected-pool startup can request dozens of experts. It is a
        # one-time admission operation whose values must outlive a layer call,
        # so retain the ordinary verified copied loader for that case.
        if len(experts) > len(self._route_arenas):
            return super().get_layer_route_parallel(layer, experts, workers)
        results = [None] * len(experts)
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
            def load(item):
                position, expert = item
                value = self._read_l2_into_slot(layer, expert, position)
                if value is not None:
                    return value
                self.sd_fallbacks += 1
                value = GptOssExpertFrameStore._load_value(self, layer, expert)
                self._write_l2(layer, expert, value)
                return value
            with ThreadPoolExecutor(max_workers=min(workers, len(missing)),
                                    thread_name_prefix="aion-gptoss-l2-arena") as pool:
                loaded = list(pool.map(load, missing))
            for (position, expert), value in zip(missing, loaded, strict=True):
                value = self.maybe_admit_route_arena_l1(layer, expert, value)
                results[position] = value
        if any(value is None for value in results):
            raise RuntimeError("reusable-arena route remained incomplete")
        return results

    def metrics(self) -> dict[str, int | float | str]:
        return {
            **super().metrics(),
            "cache_representation": "bulk_preadv_process_verified_reusable_route_arena",
            "route_arena_capacity_bytes": self.route_arena_capacity_bytes,
            "route_arena_reads": self.route_arena_reads,
            "route_arena_bytes_read": self.route_arena_bytes_read,
            "route_arena_l1_allowlist_entries": len(
                self._route_arena_l1_allowlist),
            "route_arena_l1_admissions": self.route_arena_l1_admissions,
            "route_arena_l1_admission_bytes": self.route_arena_l1_admission_bytes,
            "partial_l2_read_calls": self.partial_l2_read_calls,
            "partial_l2_bytes_read": self.partial_l2_bytes_read,
        }


def ctypes_component_pointer_array(
        blobs: list[bytes | bytearray | memoryview],
) -> tuple[list[Any], Any]:
    """Build native pointers without copying writable mapped component views."""
    references: list[Any] = []
    addresses: list[int] = []
    for blob in blobs:
        if isinstance(blob, bytes):
            reference = ctypes.c_char_p(blob)
            address = ctypes.cast(reference, ctypes.c_void_p).value
        else:
            reference = (ctypes.c_ubyte * len(blob)).from_buffer(blob)
            address = ctypes.addressof(reference)
        if address is None:
            raise RuntimeError("component buffer has no native address")
        references.append(reference)
        addresses.append(address)
    return references, (ctypes.c_void_p * len(addresses))(*addresses)


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
