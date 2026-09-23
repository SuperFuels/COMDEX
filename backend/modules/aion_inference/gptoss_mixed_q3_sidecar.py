"""Verified, non-resident access to precompiled mixed-Q3 expert sidecars."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path


class GptOssMixedQ3Sidecar:
    """Read Q3 gate/up plus exact down components without caching payloads."""

    _MAGIC = b"AIONQ3S1"
    _HEADER = struct.Struct("<8s6Q")
    _ORDER = tuple((projection, kind)
                   for projection in ("gate", "up", "down")
                   for kind in ("weight", "bias"))

    def __init__(self, manifest_path: Path, source_manifest_path: Path) -> None:
        self.manifest_path = manifest_path.resolve()
        self.root = self.manifest_path.parent
        self.manifest = json.loads(self.manifest_path.read_text())
        if (self.manifest.get("schema") != "aion.gptoss-mixed-q3-sidecar.v1"
                or self.manifest.get("status") != "COMPLETE_VERIFIED"):
            raise ValueError("mixed-Q3 sidecar is not complete and verified")
        source_sha = hashlib.sha256(source_manifest_path.resolve().read_bytes()).hexdigest()
        if source_sha != self.manifest.get("source_manifest_sha256"):
            raise ValueError("mixed-Q3 sidecar source manifest mismatch")
        body = dict(self.manifest)
        expected = body.pop("canonical_sha256", None)
        actual = hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode()).hexdigest()
        if expected != actual:
            raise ValueError("mixed-Q3 sidecar canonical hash mismatch")
        self._entries = {
            (int(entry["layer"]), int(entry["expert"])): entry
            for entry in self.manifest["entries"]
        }
        if len(self._entries) != len(self.manifest["entries"]):
            raise ValueError("duplicate mixed-Q3 sidecar entry")
        self.hits = 0
        self.misses = 0
        self.bytes_read = 0
        self.integrity_failures = 0

    def get(self, layer: int, expert: int) -> dict[str, dict[str, bytes]] | None:
        entry = self._entries.get((layer, expert))
        if entry is None:
            self.misses += 1
            return None
        path = self.root / entry["relative_path"]
        try:
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != entry["file_sha256"]:
                raise ValueError("sidecar file hash mismatch")
            if len(payload) < self._HEADER.size:
                raise ValueError("short sidecar header")
            magic, *lengths = self._HEADER.unpack_from(payload)
            if magic != self._MAGIC or self._HEADER.size + sum(lengths) != len(payload):
                raise ValueError("invalid sidecar frame")
            cursor = self._HEADER.size
            value: dict[str, dict[str, bytes]] = {}
            for (projection, kind), length, expected_hash in zip(
                    self._ORDER, lengths, entry["component_sha256"], strict=True):
                raw = payload[cursor:cursor + length]
                cursor += length
                if hashlib.sha256(raw).hexdigest() != expected_hash:
                    raise ValueError("sidecar component hash mismatch")
                value.setdefault(projection, {})[kind] = raw
        except (FileNotFoundError, KeyError, ValueError, struct.error):
            self.integrity_failures += 1
            self.misses += 1
            return None
        self.hits += 1
        self.bytes_read += len(payload)
        return value

    def metrics(self) -> dict[str, int | str]:
        return {
            "manifest": str(self.manifest_path),
            "entries": len(self._entries), "hits": self.hits,
            "misses": self.misses, "bytes_read": self.bytes_read,
            "integrity_failures": self.integrity_failures,
        }
