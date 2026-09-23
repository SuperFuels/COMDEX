import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = (Path(__file__).parents[3] / "scripts" /
          "analyze_aion_q3_weight_residual_structure.py")
SPEC = importlib.util.spec_from_file_location("aion_q3_residual", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_cumulative_fraction_reports_concentrated_energy():
    values = np.asarray([90.0, 5.0, 3.0, 2.0])
    result = MODULE.cumulative_fraction(values, (.25, .5, 1.0))
    assert result["0.25"] == 0.9
    assert result["0.5"] == 0.95
    assert result["1.0"] == 1.0


def test_cumulative_fraction_handles_zero_residual():
    result = MODULE.cumulative_fraction(np.zeros(10), (.1, 1.0))
    assert result == {"0.1": 1.0, "1.0": 1.0}
