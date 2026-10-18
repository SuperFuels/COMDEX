import numpy as np

from backend.modules.hexcore.explicit_visual_action_chunk_memory import (
    ActionChunkMemory, feature_weights, make_features,
)


def test_feature_contract_and_weights():
    feature = make_features(np.zeros((2, 18), np.float32), np.array([[64, 48], [32, 24]]), np.array([0, 125]))
    assert feature.shape == (2, 22)
    assert feature_weights((1, 2, 3, 4)).shape == (22,)


def test_chunk_memory_preserves_coherent_program():
    feature = np.array([[0, 0], [1, 1]], np.float32)
    chunks = np.array([[[0], [1], [2]], [[5], [6], [7]]], np.float32)
    memory = ActionChunkMemory(feature, chunks, np.ones(2), np.zeros(2), np.ones(2), 1)
    assert np.array_equal(memory.predict([[.1, .1]])[0, :, 0], [0, 1, 2])
