from backend.modules.glyphwave.core.beam_logger import log_beam_prediction

if __name__ == "__main__":
    result = log_beam_prediction({
        "source": {"id": "glyph_1"},
        "target": {"id": "glyph_2"},
        "sqi_score": 0.92,
        "innovation_score": 0.81,
        "container_id": "container_xyz",
        "tags": ["mutation", "rewrite"]
    })

    print("Logged Beam:")
    print(result)