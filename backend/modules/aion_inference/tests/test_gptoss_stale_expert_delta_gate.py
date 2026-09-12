import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = (Path(__file__).parents[3] / "scripts" /
          "run_aion_gptoss_stale_expert_delta_gate.py")
SPEC = importlib.util.spec_from_file_location("aion_stale_delta", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_rms_norm_matches_declared_f32_formula():
    values = np.asarray([3.0, 4.0], dtype=np.float32)
    actual = MODULE.rms_norm(values, np.ones(2, dtype=np.float32))
    scale = np.float32(1.0 / np.sqrt(np.mean(values * values) + MODULE.EPSILON))
    np.testing.assert_array_equal(actual, values * scale)


def test_canonical_is_key_order_independent():
    assert MODULE.canonical({"a": 1, "b": 2}) == MODULE.canonical({"b": 2, "a": 1})
