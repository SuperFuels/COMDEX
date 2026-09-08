from pathlib import Path

import pytest

from backend.modules.aion_inference.int8_dynamic_bank_moe import load_bank_entry


def test_load_bank_entry_rejects_wrong_order() -> None:
    with pytest.raises(RuntimeError, match="ordering"):
        load_bank_entry({"layers": [{"layer": 1}]}, 0, Path("/tmp"), lambda _: "")


def test_load_bank_entry_checks_hash(tmp_path: Path) -> None:
    path = tmp_path / "bank.safetensors"
    path.write_bytes(b"x")
    manifest = {"layers": [{"layer": 0, "path": str(path), "sha256": "ok"}]}
    assert load_bank_entry(manifest, 0, tmp_path.parent, lambda _: "ok")["path"] == str(path)
