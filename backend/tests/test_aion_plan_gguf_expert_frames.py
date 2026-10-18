import importlib.util
import struct
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "aion_plan_gguf_expert_frames.py"
SPEC = importlib.util.spec_from_file_location("aion_plan_gguf_expert_frames", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _string(value: str) -> bytes:
    encoded = value.encode()
    return struct.pack("<Q", len(encoded)) + encoded


def _gguf(path: Path) -> int:
    tensors = [("blk.0.ffn_up_exps.weight", [4, 2], 0), ("output.weight", [8], 32)]
    payload = bytearray(b"GGUF" + struct.pack("<IQQ", 3, len(tensors), 1))
    payload.extend(_string("general.alignment") + struct.pack("<II", 4, 32))
    for name, dimensions, offset in tensors:
        payload.extend(_string(name) + struct.pack("<I", len(dimensions)))
        payload.extend(b"".join(struct.pack("<Q", item) for item in dimensions))
        payload.extend(struct.pack("<IQ", 0, offset))
    while len(payload) % 32:
        payload.append(0)
    payload.extend(bytes(48))
    path.write_bytes(payload)
    return len(payload)


def test_plan_is_gapless_and_expert_aligned(tmp_path):
    header = tmp_path / "tiny.gguf"
    size = _gguf(header)
    source = {"schema": "source", "revision": "abc", "shards": [{
        "name": "tiny.gguf", "url": "https://example.invalid/tiny.gguf",
        "size": size, "sha256": "0" * 64,
    }]}
    plan = MODULE.build_plan(source, [header], 8)
    expert = next(region for region in plan["shards"][0]["regions"]
                  if region["kind"] == "expert_tensor")
    assert [frame["raw_bytes"] for frame in expert["frames"]] == [16, 16]
    assert plan["expert_frames"] == 2
    assert plan["canonical_sha256"] == MODULE._canonical_hash(plan)
