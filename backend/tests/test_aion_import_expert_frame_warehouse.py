import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "aion_import_expert_frame_warehouse.py"
SPEC = importlib.util.spec_from_file_location("aion_import_expert_frame_warehouse", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_region_pack_round_trip_and_receipt_validation(tmp_path):
    raw = (b"abcdefgh" * 1024) + (b"12345678" * 1024)
    raw_path = tmp_path / "raw.bin"
    raw_path.write_bytes(raw)
    pack = tmp_path / "region.zstpack"
    frames = [{"frame": 0, "relative_offset": 0, "raw_bytes": len(raw) // 2},
              {"frame": 1, "relative_offset": len(raw) // 2, "raw_bytes": len(raw) // 2}]
    packed = MODULE.pack_region(MODULE.Zstd(), raw_path, pack, frames, 3)
    assert len(packed) == 2
    assert sum(frame["compressed_bytes"] for frame in packed) == pack.stat().st_size
    receipt = {"pack_bytes": pack.stat().st_size,
               "pack_sha256": MODULE.sha256_path(pack)}
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    assert MODULE.receipt_valid(receipt_path, pack)


def test_canonical_hash_ignores_hash_field():
    payload = {"schema": "x", "value": 1}
    first = MODULE.canonical_hash(payload)
    payload["canonical_sha256"] = first
    assert MODULE.canonical_hash(payload) == first
