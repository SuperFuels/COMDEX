"""Seekable, bounded access to a verified expert-frame GGUF warehouse."""

from __future__ import annotations

import bisect
import ctypes
import hashlib
import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any

from backend.modules.aion_inference.gptoss_expert_frame_store import _zstd


class ExpertFrameGGUFReader:
    """Expose one logical GGUF shard without materialising the complete file."""

    def __init__(self, manifest_path: Path, source_shard: str,
                 cache_bytes: int = 128 * 1024 * 1024) -> None:
        if cache_bytes < 0:
            raise ValueError("cache_bytes must be non-negative")
        self.manifest_path = manifest_path.resolve()
        self.root = self.manifest_path.parent
        self.manifest = json.loads(self.manifest_path.read_text())
        if (self.manifest.get("schema") != "aion.expert-frame-warehouse.v1"
                or self.manifest.get("status") != "COMPLETE_VERIFIED"):
            raise ValueError("expert-frame warehouse is not complete and verified")
        sources = {item["name"]: item for item in self.manifest["verified_sources"]}
        if source_shard not in sources:
            raise KeyError(f"unknown source shard {source_shard}")
        source = sources[source_shard]
        if source.get("expected_sha256") != source.get("verified_sha256"):
            raise ValueError("source shard hash is not verified")
        self.source_shard = source_shard
        self.size = int(source["size"])
        self.cache_bytes = cache_bytes
        self._position = 0
        self._zstd = _zstd()
        self._cache: OrderedDict[tuple[str, int], bytes] = OrderedDict()
        self._resident = 0
        self.cache_hits = 0
        self.frame_faults = 0
        self.compressed_bytes_read = 0
        self.raw_bytes_materialized = 0
        self.peak_resident_bytes = 0

        frames: list[dict[str, Any]] = []
        for region in self.manifest["regions"]:
            if region["source_shard"] != source_shard:
                continue
            region_start = int(region["source_offset"])
            for frame in region["frames"]:
                frames.append({
                    **frame,
                    "raw_offset": region_start + int(frame["relative_offset"]),
                    "pack_relative_path": region["pack_relative_path"],
                })
        frames.sort(key=lambda item: int(item["raw_offset"]))
        expected = 0
        for frame in frames:
            if int(frame["raw_offset"]) != expected:
                raise RuntimeError(f"expert-frame coverage gap at byte {expected}")
            expected += int(frame["raw_bytes"])
        if expected != self.size:
            raise RuntimeError(f"expert-frame coverage ends at {expected}, expected {self.size}")
        self._frames = frames
        self._starts = [int(item["raw_offset"]) for item in frames]

    def _decode(self, frame: dict[str, Any]) -> bytes:
        key = (str(frame["pack_relative_path"]), int(frame["encoded_offset"]))
        cached = self._cache.pop(key, None)
        if cached is not None:
            self.cache_hits += 1
            self._cache[key] = cached
            return cached
        path = self.root / frame["pack_relative_path"]
        with path.open("rb", buffering=0) as handle:
            encoded = os.pread(handle.fileno(), int(frame["compressed_bytes"]),
                               int(frame["encoded_offset"]))
        if len(encoded) != int(frame["compressed_bytes"]):
            raise RuntimeError(f"short expert-frame read: {path}")
        if hashlib.sha256(encoded).hexdigest() != frame["compressed_sha256"]:
            raise RuntimeError(f"compressed expert-frame hash mismatch: {path}")
        raw_size = int(frame["raw_bytes"])
        output = ctypes.create_string_buffer(raw_size)
        source = ctypes.create_string_buffer(encoded)
        result = self._zstd.ZSTD_decompress(output, raw_size, source, len(encoded))
        if self._zstd.ZSTD_isError(result) or int(result) != raw_size:
            raise RuntimeError(f"expert-frame decode failed: {path}")
        raw = output.raw
        if hashlib.sha256(raw).hexdigest() != frame["raw_sha256"]:
            raise RuntimeError(f"decoded expert-frame hash mismatch: {path}")
        self.frame_faults += 1
        self.compressed_bytes_read += len(encoded)
        self.raw_bytes_materialized += len(raw)
        if len(raw) <= self.cache_bytes:
            while self._cache and self._resident + len(raw) > self.cache_bytes:
                _, removed = self._cache.popitem(last=False)
                self._resident -= len(removed)
            self._cache[key] = raw
            self._resident += len(raw)
            self.peak_resident_bytes = max(self.peak_resident_bytes, self._resident)
        return raw

    def read_at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError("read lies outside source shard")
        if length == 0:
            return b""
        index = bisect.bisect_right(self._starts, offset) - 1
        if index < 0:
            raise RuntimeError("missing frame at source start")
        parts: list[bytes] = []
        position = offset
        remaining = length
        while remaining:
            if index >= len(self._frames):
                raise RuntimeError("expert-frame coverage ended during read")
            frame = self._frames[index]
            start = int(frame["raw_offset"])
            raw = self._decode(frame)
            within = position - start
            if within < 0 or within >= len(raw):
                raise RuntimeError("invalid expert-frame boundary")
            take = min(remaining, len(raw) - within)
            parts.append(raw[within:within + take])
            position += take
            remaining -= take
            index += 1
        return b"".join(parts)

    def read(self, length: int = -1) -> bytes:
        if length < 0:
            length = self.size - self._position
        length = min(length, self.size - self._position)
        value = self.read_at(self._position, length)
        self._position += len(value)
        return value

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            position = offset
        elif whence == 1:
            position = self._position + offset
        elif whence == 2:
            position = self.size + offset
        else:
            raise ValueError("invalid whence")
        if position < 0 or position > self.size:
            raise ValueError("seek lies outside source shard")
        self._position = position
        return position

    def tell(self) -> int:
        return self._position

    def metrics(self) -> dict[str, int | float]:
        accesses = self.cache_hits + self.frame_faults
        return {
            "cache_capacity_bytes": self.cache_bytes,
            "cache_resident_bytes": self._resident,
            "peak_resident_bytes": self.peak_resident_bytes,
            "cache_hits": self.cache_hits,
            "frame_faults": self.frame_faults,
            "cache_hit_rate": self.cache_hits / accesses if accesses else 0.0,
            "compressed_bytes_read": self.compressed_bytes_read,
            "raw_bytes_materialized": self.raw_bytes_materialized,
        }
