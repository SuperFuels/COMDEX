import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).parents[3] / "scripts" / "run_aion_gptoss_activation_column_sparsity_gate.py"
SPEC = importlib.util.spec_from_file_location("column_sparsity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_retain_largest_keeps_requested_magnitudes_and_reports_energy():
    values = np.asarray([1.0, -4.0, 2.0, 3.0], dtype=np.float32)
    masked, energy, coordinates = MODULE.retain_largest(values, .5)
    np.testing.assert_array_equal(masked, [0.0, -4.0, 0.0, 3.0])
    assert energy == 25.0 / 30.0
    assert set(coordinates) == {1, 3}


def test_retain_largest_can_select_physical_blocks():
    values = np.asarray([1.0, 1.0, 4.0, 0.0], dtype=np.float32)
    masked, energy, coordinates = MODULE.retain_largest(values, .5, block_size=2)
    np.testing.assert_array_equal(masked, [0.0, 0.0, 4.0, 0.0])
    assert energy == 16.0 / 18.0
    assert set(coordinates) == {2, 3}


def test_coordinate_plane_page_count_handles_cross_page_planes():
    touched, total = MODULE.coordinate_plane_pages(np.asarray([0, 1]), width=8,
                                                    page_size=4)
    assert touched == 2
    assert total == 8
