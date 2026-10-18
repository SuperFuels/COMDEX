from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias


def test_predictive_feedback_uses_explicit_test_storage(tmp_path):
    model_path = tmp_path / "temporal_model.json"
    log_path = tmp_path / "predictive_transitions.jsonl"
    pb = PredictiveBias(
        events_path=tmp_path / "pal_events.jsonl",
        model_path=model_path,
        state_path=tmp_path / "predictive_bias_state.json",
        log_path=log_path,
    )
    sequence = ["Φ", "λ", "Ω", "Φ", "λ", "Ω", "Φ"]

    for symbol in sequence:
        pb.observe(symbol)

    predicted, probability = pb.predict_next("Φ")
    assert predicted == "λ"
    assert probability > 0
    assert pb.evaluate(predicted) == 1.0
    assert log_path.exists()
