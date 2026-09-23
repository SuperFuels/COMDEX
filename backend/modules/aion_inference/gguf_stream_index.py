"""GGUF header indexing over any seekable AION byte source."""

from __future__ import annotations

import struct
from typing import Any, BinaryIO, Collection


_SCALARS = {
    0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
    6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d",
}
_STRING = 8
_ARRAY = 9


def _exact(handle: BinaryIO, count: int) -> bytes:
    value = handle.read(count)
    if len(value) != count:
        raise ValueError("truncated GGUF header")
    return value


def _scalar(handle: BinaryIO, fmt: str) -> Any:
    return struct.unpack(fmt, _exact(handle, struct.calcsize(fmt)))[0]


def _string(handle: BinaryIO) -> str:
    return _exact(handle, _scalar(handle, "<Q")).decode("utf-8")


def _value(handle: BinaryIO, kind: int, retain: bool) -> Any:
    if kind in _SCALARS:
        value = _scalar(handle, _SCALARS[kind])
        return value if retain else None
    if kind == _STRING:
        value = _string(handle)
        return value if retain else None
    if kind == _ARRAY:
        element = _scalar(handle, "<I")
        count = _scalar(handle, "<Q")
        if retain:
            return [_value(handle, element, True) for _ in range(count)]
        if element in _SCALARS:
            handle.seek(struct.calcsize(_SCALARS[element]) * count, 1)
        else:
            for _ in range(count):
                _value(handle, element, False)
        return None
    raise ValueError(f"unsupported GGUF metadata type {kind}")


def read_gguf_stream_index(handle: BinaryIO, file_size: int,
                           retained_keys: Collection[str] = ()) -> dict[str, Any]:
    """Read a GGUF index without requiring a filesystem-backed complete file."""
    handle.seek(0)
    if _exact(handle, 4) != b"GGUF":
        raise ValueError("not a GGUF stream")
    version = _scalar(handle, "<I")
    if version not in {2, 3}:
        raise ValueError(f"unsupported GGUF version {version}")
    tensor_count = _scalar(handle, "<Q")
    metadata_count = _scalar(handle, "<Q")
    retained = set(retained_keys)
    metadata: dict[str, Any] = {}
    for _ in range(metadata_count):
        key = _string(handle)
        kind = _scalar(handle, "<I")
        value = _value(handle, kind, key in retained)
        if key in retained:
            metadata[key] = value
    tensors = []
    for _ in range(tensor_count):
        name = _string(handle)
        dimensions = [_scalar(handle, "<Q") for _ in range(_scalar(handle, "<I"))]
        ggml_type = _scalar(handle, "<I")
        relative_offset = _scalar(handle, "<Q")
        tensors.append({"name": name, "dimensions": dimensions,
                        "ggml_type": ggml_type, "relative_offset": relative_offset})
    alignment = int(metadata.get("general.alignment") or 32)
    data_offset = (handle.tell() + alignment - 1) // alignment * alignment
    by_offset = sorted(tensors, key=lambda item: int(item["relative_offset"]))
    for index, tensor in enumerate(by_offset):
        next_offset = (int(by_offset[index + 1]["relative_offset"])
                       if index + 1 < len(by_offset) else file_size - data_offset)
        length = next_offset - int(tensor["relative_offset"])
        if length <= 0:
            raise ValueError(f"invalid tensor span for {tensor['name']}")
        tensor["absolute_offset"] = data_offset + int(tensor["relative_offset"])
        tensor["byte_length"] = length
    return {"version": version, "file_size": file_size, "data_offset": data_offset,
            "metadata": metadata, "tensors": tensors}
