from backend.modules.glyphwave.core.coherence_optimizer import DynamicCoherenceOptimizer

def test_coherence_optimizer_basic():
    optimizer = DynamicCoherenceOptimizer(target_coherence=0.8)
    wave_state = {"wave": [0.1, 0.2, 0.3]}
    result = optimizer.optimize_if_needed(wave_state)
    assert result is True