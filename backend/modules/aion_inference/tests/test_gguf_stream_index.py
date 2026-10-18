import io
import struct

from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index


def _string(value: str) -> bytes:
    encoded = value.encode()
    return struct.pack("<Q", len(encoded)) + encoded


def test_indexes_seekable_non_file_stream():
    payload = bytearray(b"GGUF" + struct.pack("<IQQ", 3, 2, 2))
    payload.extend(_string("general.architecture") + struct.pack("<I", 8) + _string("tiny"))
    payload.extend(_string("general.alignment") + struct.pack("<II", 4, 32))
    for name, offset in (("first", 0), ("second", 32)):
        payload.extend(_string(name) + struct.pack("<I", 1) + struct.pack("<Q", 8))
        payload.extend(struct.pack("<IQ", 0, offset))
    while len(payload) % 32:
        payload.append(0)
    data_offset = len(payload)
    payload.extend(bytes(64))
    index = read_gguf_stream_index(
        io.BytesIO(payload), len(payload),
        {"general.architecture", "general.alignment"},
    )
    assert index["metadata"]["general.architecture"] == "tiny"
    assert index["data_offset"] == data_offset
    assert [item["byte_length"] for item in index["tensors"]] == [32, 32]


def test_retains_requested_string_array():
    payload = bytearray(b"GGUF" + struct.pack("<IQQ", 3, 1, 1))
    payload.extend(_string("tokenizer.ggml.tokens"))
    payload.extend(struct.pack("<IIQ", 9, 8, 3))
    payload.extend(_string("one") + _string("two") + _string("three"))
    payload.extend(_string("weight") + struct.pack("<I", 1) + struct.pack("<Q", 1))
    payload.extend(struct.pack("<IQ", 0, 0))
    while len(payload) % 32:
        payload.append(0)
    payload.extend(bytes(4))
    index = read_gguf_stream_index(
        io.BytesIO(payload), len(payload), {"tokenizer.ggml.tokens"},
    )
    assert index["metadata"]["tokenizer.ggml.tokens"] == ["one", "two", "three"]
