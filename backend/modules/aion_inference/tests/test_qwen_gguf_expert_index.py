import struct

from backend.modules.aion_inference.qwen_gguf_expert_index import build_expert_manifest


def _string(value: str) -> bytes:
    encoded = value.encode()
    return struct.pack("<Q", len(encoded)) + encoded


def _tiny_gguf(path):
    metadata = {
        "general.architecture": (8, "qwen3moe"),
        "qwen3moe.block_count": (4, 1),
        "qwen3moe.expert_count": (4, 128),
        "qwen3moe.expert_used_count": (4, 8),
    }
    names = [
        "blk.0.ffn_gate_exps.weight",
        "blk.0.ffn_up_exps.weight",
        "blk.0.ffn_down_exps.weight",
        "output_norm.weight",
    ]
    payload = bytearray(b"GGUF" + struct.pack("<IQQ", 3, len(names), len(metadata)))
    for key, (value_type, value) in metadata.items():
        payload += _string(key) + struct.pack("<I", value_type)
        payload += _string(value) if value_type == 8 else struct.pack("<I", value)
    offsets = [0, 1280, 2560, 3840]
    for name, offset in zip(names, offsets):
        payload += _string(name)
        payload += struct.pack("<IQQQI", 3, 2, 5, 128, 8)
        payload += struct.pack("<Q", offset)
    payload += b"\0" * ((32 - len(payload) % 32) % 32)
    payload += b"x" * 3872
    path.write_bytes(payload)


def test_builds_zero_copy_ranges_for_every_expert(tmp_path):
    model = tmp_path / "tiny.gguf"
    _tiny_gguf(model)
    manifest = build_expert_manifest(model, "a" * 64)

    assert manifest["layer_count"] == 1
    assert manifest["expert_count"] == 128
    assert manifest["logical_expert_instances"] == 128
    assert manifest["expert_tensor_bytes"] == 3840
    first = manifest["layers"][0]["experts"][0]
    second = manifest["layers"][0]["experts"][1]
    assert first["byte_length"] == 30
    assert second["ranges"]["gate"]["absolute_offset"] == (
        first["ranges"]["gate"]["absolute_offset"] + 10
    )
    assert len(manifest["canonical_sha256"]) == 64
