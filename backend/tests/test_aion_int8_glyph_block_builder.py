import json

import torch

from backend.scripts.build_aion_int8_glyph_blocks import _block_metadata


def test_block_metadata_binds_shapes_and_offsets() -> None:
    input_weight = torch.empty((12, 4), dtype=torch.float16)
    output_weight = torch.empty((4, 6), dtype=torch.float16)
    metadata = _block_metadata(input_weight, output_weight)
    assert json.loads(metadata["input_shape"]) == [12, 4]
    assert json.loads(metadata["output_shape"]) == [4, 6]
    assert metadata["input_offset_elements"] == "0"
    assert metadata["output_offset_elements"] == "48"
