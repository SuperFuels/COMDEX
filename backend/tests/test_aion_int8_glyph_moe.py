from pathlib import Path

import pytest

from backend.modules.aion_inference.int8_glyph_moe import load_layer_entries


def test_load_layer_entries_rejects_wrong_layer_order() -> None:
    with pytest.raises(RuntimeError, match="ordering"):
        load_layer_entries({"layers": [{"layer": 1}]}, 0, Path("/tmp"), lambda _: "")


def test_load_layer_entries_rejects_missing_experts(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text('{"experts": []}')
    manifest = {"layers": [{"layer": 0, "index_path": str(index),
                            "index_sha256": "ok"}]}
    with pytest.raises(RuntimeError, match="coverage"):
        load_layer_entries(manifest, 0, tmp_path.parent, lambda _: "ok")
