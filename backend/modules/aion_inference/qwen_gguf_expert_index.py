"""Build zero-copy Glyph addresses for Qwen MoE experts inside a GGUF file."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, BinaryIO


_SCALAR_FORMATS = {
    0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
    6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d",
}
_STRING = 8
_ARRAY = 9
_EXPERT_TENSOR = re.compile(
    r"^blk\.(?P<layer>\d+)\.ffn_(?P<projection>down|gate|up)_exps\.weight$"
)


def _read_exact(handle: BinaryIO, count: int) -> bytes:
    value = handle.read(count)
    if len(value) != count:
        raise ValueError("truncated GGUF")
    return value


def _scalar(handle: BinaryIO, fmt: str) -> Any:
    return struct.unpack(fmt, _read_exact(handle, struct.calcsize(fmt)))[0]


def _string(handle: BinaryIO) -> str:
    length = _scalar(handle, "<Q")
    return _read_exact(handle, length).decode("utf-8")


def _value(handle: BinaryIO, value_type: int, retain: bool = True) -> Any:
    if value_type in _SCALAR_FORMATS:
        value = _scalar(handle, _SCALAR_FORMATS[value_type])
        return value if retain else None
    if value_type == _STRING:
        value = _string(handle)
        return value if retain else None
    if value_type == _ARRAY:
        element_type = _scalar(handle, "<I")
        count = _scalar(handle, "<Q")
        if element_type in _SCALAR_FORMATS:
            width = struct.calcsize(_SCALAR_FORMATS[element_type])
            handle.seek(width * count, 1)
        else:
            for _ in range(count):
                _value(handle, element_type, retain=False)
        return None
    raise ValueError(f"unsupported GGUF value type {value_type}")


def read_gguf_index(path: Path) -> dict[str, Any]:
    """Read metadata and tensor ranges without reading tensor payload bytes."""
    file_size = path.stat().st_size
    retained_keys = {
        "general.architecture", "general.name", "general.alignment",
        "qwen3moe.block_count", "qwen3moe.expert_count",
        "qwen3moe.expert_used_count", "qwen3next.block_count",
        "qwen3next.expert_count", "qwen3next.expert_used_count",
    }
    with path.open("rb") as handle:
        if _read_exact(handle, 4) != b"GGUF":
            raise ValueError("not a GGUF file")
        version = _scalar(handle, "<I")
        if version not in {2, 3}:
            raise ValueError(f"unsupported GGUF version {version}")
        tensor_count = _scalar(handle, "<Q")
        kv_count = _scalar(handle, "<Q")
        metadata: dict[str, Any] = {}
        for _ in range(kv_count):
            key = _string(handle)
            value_type = _scalar(handle, "<I")
            value = _value(handle, value_type, retain=key in retained_keys)
            if key in retained_keys:
                metadata[key] = value
        tensors = []
        for _ in range(tensor_count):
            name = _string(handle)
            dimensions = [_scalar(handle, "<Q") for _ in range(_scalar(handle, "<I"))]
            ggml_type = _scalar(handle, "<I")
            offset = _scalar(handle, "<Q")
            tensors.append({
                "name": name,
                "dimensions": dimensions,
                "ggml_type": ggml_type,
                "relative_offset": offset,
            })
        alignment = int(metadata.get("general.alignment") or 32)
        data_offset = (handle.tell() + alignment - 1) // alignment * alignment

    by_offset = sorted(tensors, key=lambda item: int(item["relative_offset"]))
    for index, tensor in enumerate(by_offset):
        next_offset = (int(by_offset[index + 1]["relative_offset"])
                       if index + 1 < len(by_offset) else file_size - data_offset)
        byte_length = next_offset - int(tensor["relative_offset"])
        if byte_length <= 0:
            raise ValueError(f"invalid tensor span for {tensor['name']}")
        tensor["absolute_offset"] = data_offset + int(tensor["relative_offset"])
        tensor["byte_length"] = byte_length
    return {
        "version": version,
        "file_size": file_size,
        "data_offset": data_offset,
        "metadata": metadata,
        "tensors": tensors,
    }


def build_expert_manifest(path: Path, model_sha256: str) -> dict[str, Any]:
    """Describe each expert as three exact byte ranges in the original GGUF."""
    index = read_gguf_index(path)
    metadata = index["metadata"]
    architecture = str(metadata.get("general.architecture") or "")
    if architecture == "qwen3next":
        family = "qwen3next"
    elif architecture == "qwen3moe":
        family = "qwen3moe"
    else:
        raise ValueError(f"unsupported Qwen MoE architecture: {architecture or 'missing'}")
    expert_count = int(metadata.get(f"{family}.expert_count") or 0)
    layer_count = int(metadata.get(f"{family}.block_count") or 0)
    if expert_count <= 0 or layer_count <= 0:
        raise ValueError("GGUF is missing Qwen MoE layer/expert metadata")

    layers: dict[int, dict[str, dict[str, Any]]] = {}
    expert_bytes = 0
    for tensor in index["tensors"]:
        match = _EXPERT_TENSOR.match(tensor["name"])
        if not match:
            continue
        byte_length = int(tensor["byte_length"])
        if byte_length % expert_count:
            raise ValueError(f"expert tensor is not evenly sliceable: {tensor['name']}")
        projection = match.group("projection")
        layer = int(match.group("layer"))
        layers.setdefault(layer, {})[projection] = tensor
        expert_bytes += byte_length

    if sorted(layers) != list(range(layer_count)):
        raise ValueError("expert layer coverage mismatch")
    expected = {"down", "gate", "up"}
    manifest_layers = []
    for layer in range(layer_count):
        projections = layers[layer]
        if set(projections) != expected:
            raise ValueError(f"layer {layer} projection coverage mismatch")
        experts = []
        for expert in range(expert_count):
            ranges = {}
            total = 0
            for projection in ("gate", "up", "down"):
                tensor = projections[projection]
                stride = int(tensor["byte_length"]) // expert_count
                ranges[projection] = {
                    "tensor": tensor["name"],
                    "absolute_offset": int(tensor["absolute_offset"]) + expert * stride,
                    "byte_length": stride,
                    "ggml_type": int(tensor["ggml_type"]),
                    "tensor_dimensions": tensor["dimensions"],
                }
                total += stride
            experts.append({
                "expert": expert,
                "glyph": f"qwen3moe/layer/{layer:02d}/expert/{expert:03d}",
                "byte_length": total,
                "ranges": ranges,
            })
        manifest_layers.append({"layer": layer, "experts": experts})

    manifest = {
        "schema": "aion.qwen3moe.gguf-expert-addresses.v1",
        "source_path": str(path.resolve()),
        "source_sha256": model_sha256,
        "source_bytes": int(index["file_size"]),
        "gguf_version": int(index["version"]),
        "gguf_data_offset": int(index["data_offset"]),
        "architecture": metadata.get("general.architecture"),
        "model_name": metadata.get("general.name"),
        "layer_count": layer_count,
        "expert_count": expert_count,
        "experts_used_per_token": int(metadata.get(f"{family}.expert_used_count") or 0),
        "expert_tensor_bytes": expert_bytes,
        "logical_expert_instances": layer_count * expert_count,
        "layers": manifest_layers,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model-sha256", required=True)
    args = parser.parse_args()
    manifest = build_expert_manifest(args.model, args.model_sha256)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "canonical_sha256": manifest["canonical_sha256"],
        "layers": manifest["layer_count"],
        "experts_per_layer": manifest["expert_count"],
        "expert_tensor_bytes": manifest["expert_tensor_bytes"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
