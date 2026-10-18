from backend.scripts.build_aion_int8_dynamic_banks import _layer_metadata


def test_layer_metadata_binds_shapes_and_quantization() -> None:
    result = _layer_metadata(3, [40, 1024, 1536], [40, 1536, 512])
    assert result["layer"] == "3"
    assert result["experts"] == "40"
    assert result["input_shape"] == "[40,1024,1536]"
    assert "int8" in result["quantization"]
