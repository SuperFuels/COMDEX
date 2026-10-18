"""Addressed layer/expert storage experiment with explicit claim boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any, Iterable, Mapping, Sequence


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class AddressedShard:
    shard_id: str
    kind: str
    layer_index: int
    expert_id: str | None
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ShardReadMeasurement:
    route: str
    shard_count: int
    bytes_read: int
    median_seconds: float
    p95_seconds: float
    aggregate_sha256: str
    all_shards_verified: bool


class AddressedShardExperiment:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = root / "shards.manifest.json"

    @staticmethod
    def _fixture_bytes(label: str, size: int) -> bytes:
        chunks: list[bytes] = []
        counter = 0
        remaining = size
        while remaining:
            block = hashlib.sha256(f"{label}:{counter}".encode()).digest()
            chunks.append(block[:remaining])
            remaining -= min(len(block), remaining)
            counter += 1
        return b"".join(chunks)

    def build_fixture(
        self,
        *,
        layer_count: int = 4,
        experts_per_layer: int = 4,
        common_bytes: int = 128 * 1024,
        expert_bytes: int = 256 * 1024,
    ) -> tuple[AddressedShard, ...]:
        if not 1 <= layer_count <= 64 or not 2 <= experts_per_layer <= 64:
            raise ValueError("fixture dimensions are outside the bounded experiment")
        if not 4096 <= common_bytes <= 16 * 1024 * 1024 or not 4096 <= expert_bytes <= 16 * 1024 * 1024:
            raise ValueError("fixture shard size is outside the bounded experiment")
        shards: list[AddressedShard] = []
        for layer in range(layer_count):
            definitions = [("common", None, common_bytes)] + [
                ("expert", f"e{expert}", expert_bytes) for expert in range(experts_per_layer)
            ]
            for kind, expert_id, size in definitions:
                shard_id = f"layer-{layer:03d}-{kind}" + (f"-{expert_id}" if expert_id else "")
                path = self.root / f"{shard_id}.bin"
                expected = self._fixture_bytes(shard_id, size)
                expected_hash = hashlib.sha256(expected).hexdigest()
                if path.exists():
                    if path.stat().st_size != size or _sha_file(path) != expected_hash:
                        raise RuntimeError(f"existing fixture shard failed identity check: {path}")
                else:
                    path.write_bytes(expected)
                shards.append(AddressedShard(shard_id, kind, layer, expert_id, str(path), size, expected_hash))
        payload = {
            "schema_version": "aion.addressed_shards.manifest.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": "synthetic storage-addressing fixture; not neural inference equivalence",
            "shards": [asdict(shard) for shard in shards],
        }
        self.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return tuple(shards)

    @staticmethod
    def select_experts(
        shards: Sequence[AddressedShard],
        selected_experts: Mapping[int, Iterable[str]],
    ) -> tuple[AddressedShard, ...]:
        selected = []
        requested = {layer: set(experts) for layer, experts in selected_experts.items()}
        for shard in shards:
            if shard.kind == "common" or shard.expert_id in requested.get(shard.layer_index, set()):
                selected.append(shard)
        layers = {shard.layer_index for shard in shards}
        covered = {shard.layer_index for shard in selected if shard.kind == "expert"}
        if covered != layers:
            raise ValueError("every layer requires at least one selected expert")
        return tuple(selected)

    @staticmethod
    def _read_once(shards: Sequence[AddressedShard]) -> tuple[int, str, bool]:
        aggregate = hashlib.sha256()
        total = 0
        verified = True
        for shard in shards:
            data = Path(shard.path).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            verified = verified and digest == shard.sha256 and len(data) == shard.size_bytes
            aggregate.update(shard.shard_id.encode())
            aggregate.update(bytes.fromhex(digest))
            total += len(data)
        return total, aggregate.hexdigest(), verified

    @classmethod
    def measure(cls, route: str, shards: Sequence[AddressedShard], *, iterations: int = 5) -> ShardReadMeasurement:
        if iterations < 1:
            raise ValueError("iterations must be positive")
        timings: list[float] = []
        final_bytes = 0
        final_digest = ""
        verified = True
        for _ in range(iterations):
            started = time.monotonic()
            final_bytes, final_digest, passed = cls._read_once(shards)
            timings.append(time.monotonic() - started)
            verified = verified and passed
        ordered = sorted(timings)
        p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
        return ShardReadMeasurement(
            route=route,
            shard_count=len(shards),
            bytes_read=final_bytes,
            median_seconds=statistics.median(timings),
            p95_seconds=ordered[p95_index],
            aggregate_sha256=final_digest,
            all_shards_verified=verified,
        )

    def run(
        self,
        *,
        layer_count: int = 4,
        experts_per_layer: int = 4,
        selected_per_layer: int = 1,
        common_bytes: int = 128 * 1024,
        expert_bytes: int = 256 * 1024,
        iterations: int = 5,
    ) -> Mapping[str, Any]:
        if not 1 <= selected_per_layer <= experts_per_layer:
            raise ValueError("selected expert count is invalid")
        shards = self.build_fixture(
            layer_count=layer_count,
            experts_per_layer=experts_per_layer,
            common_bytes=common_bytes,
            expert_bytes=expert_bytes,
        )
        selection = {layer: [f"e{expert}" for expert in range(selected_per_layer)] for layer in range(layer_count)}
        selected = self.select_experts(shards, selection)
        full = self.measure("all_experts", shards, iterations=iterations)
        addressed = self.measure("selected_experts", selected, iterations=iterations)
        return {
            "schema_version": "aion.addressed_shards.experiment.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "storage_root": str(self.root),
            "configuration": {
                "layer_count": layer_count,
                "experts_per_layer": experts_per_layer,
                "selected_per_layer": selected_per_layer,
                "common_bytes_per_layer": common_bytes,
                "expert_bytes_per_expert": expert_bytes,
                "iterations": iterations,
            },
            "full": asdict(full),
            "selected": asdict(addressed),
            "measured_byte_reduction_percent": (1.0 - addressed.bytes_read / full.bytes_read) * 100.0,
            "selection": selection,
            "claim_boundary": {
                "proven": "content-addressed selection reads and verifies fewer synthetic shard bytes",
                "not_proven": "model quality, router correctness, real MoE expert activation, or token throughput",
            },
        }
