from backend.modules.aion_prediction.temporal_coherence_memory import (
    TemporalCoherenceMemory,
)


def test_temporal_coherence_memory_learns_without_repository_writes(tmp_path):
    tcm = TemporalCoherenceMemory(
        buffer_path=tmp_path / "temporal_buffer.jsonl",
        model_path=tmp_path / "temporal_model.json",
    )
    sequence = ["Φ", "λ", "Ω", "Φ", "λ", "Ω", "Φ", "λ", "Ω"]

    for index in range(len(sequence) - 1):
        current, following = sequence[index], sequence[index + 1]
        tcm.update_sequence(current)
        tcm.update_markov(current, following)

    tcm.update_sequence("Φ")
    assert tcm.predict_next() == "λ"
    assert (tmp_path / "temporal_buffer.jsonl").exists()
    assert (tmp_path / "temporal_model.json").exists()
