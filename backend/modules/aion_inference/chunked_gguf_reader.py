"""Bounded random access over an AION chunk-compressed GGUF warehouse."""

from __future__ import annotations

import ctypes
import ctypes.util
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any


def _zstd_library() -> ctypes.CDLL:
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


class ChunkedGGUFReader:
    """Expose one source shard as a seekable, hash-verifying byte stream."""

    def __init__(self, manifest_path: Path, source_shard: str,
                 cache_bytes: int = 128 * 1024 * 1024) -> None:
        if cache_bytes < 0:
            raise ValueError("cache_bytes must be non-negative")
        self.manifest_path = manifest_path.resolve()
        self.root = self.manifest_path.parent
        self.manifest = json.loads(self.manifest_path.read_text())
        if (self.manifest.get("schema") != "aion.chunked-gguf-warehouse.v1"
                or self.manifest.get("status") != "COMPLETE_VERIFIED"):
            raise ValueError("warehouse manifest is not complete and verified")
        sources = {item["name"]: item for item in self.manifest["source_shards"]}
        if source_shard not in sources:
            raise KeyError(f"unknown source shard {source_shard}")
        self.source = sources[source_shard]
        self.size = int(self.source["size"])
        self.chunk_size = int(self.manifest["chunk_size_bytes"])
        self.receipts = {
            int(item["chunk_index"]): item for item in self.manifest["chunks"]
            if item["source_shard"] == source_shard
        }
        expected_chunks = (self.size + self.chunk_size - 1) // self.chunk_size
        if sorted(self.receipts) != list(range(expected_chunks)):
            raise RuntimeError("chunk coverage is incomplete")
        self.cache_bytes = cache_bytes
        self._cache: OrderedDict[int, bytes] = OrderedDict()
        self._resident = 0
        self._position = 0
        self._zstd = _zstd_library()
        self.cache_hits = 0
        self.chunk_faults = 0
        self.compressed_bytes_read = 0
        self.raw_bytes_materialized = 0

    def _decode(self, index: int) -> bytes:
        cached = self._cache.pop(index, None)
        if cached is not None:
            self.cache_hits += 1
            self._cache[index] = cached
            return cached
        receipt = self.receipts[index]
        path = self.root / receipt["relative_path"]
        encoded = path.read_bytes()
        if hashlib.sha256(encoded).hexdigest() != receipt["compressed_sha256"]:
            raise RuntimeError(f"compressed chunk hash mismatch: {path}")
        raw_size = int(receipt["raw_bytes"])
        output = ctypes.create_string_buffer(raw_size)
        source = ctypes.create_string_buffer(encoded)
        result = self._zstd.ZSTD_decompress(output, raw_size, source, len(encoded))
        if self._zstd.ZSTD_isError(result) or int(result) != raw_size:
            raise RuntimeError(f"zstd chunk decode failed: {path}")
        raw = output.raw
        if hashlib.sha256(raw).hexdigest() != receipt["raw_sha256"]:
            raise RuntimeError(f"raw chunk hash mismatch: {path}")
        self.chunk_faults += 1
        self.compressed_bytes_read += len(encoded)
        self.raw_bytes_materialized += len(raw)
        if len(raw) <= self.cache_bytes:
            while self._cache and self._resident + len(raw) > self.cache_bytes:
                _, removed = self._cache.popitem(last=False)
                self._resident -= len(removed)
            self._cache[index] = raw
            self._resident += len(raw)
        return raw

    def read_at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError("read lies outside source shard")
        parts = []
        remaining = length
        position = offset
        while remaining:
            index, within = divmod(position, self.chunk_size)
            raw = self._decode(index)
            take = min(remaining, len(raw) - within)
            if take <= 0:
                raise RuntimeError("invalid chunk boundary")
            parts.append(raw[within:within + take])
            position += take
            remaining -= take
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

    def metrics(self) -> dict[str, Any]:
        accesses = self.cache_hits + self.chunk_faults
        return {
            "cache_capacity_bytes": self.cache_bytes,
            "cache_resident_bytes": self._resident,
            "cache_hits": self.cache_hits,
            "chunk_faults": self.chunk_faults,
            "cache_hit_rate": self.cache_hits / accesses if accesses else 0.0,
            "compressed_bytes_read": self.compressed_bytes_read,
            "raw_bytes_materialized": self.raw_bytes_materialized,
        }
