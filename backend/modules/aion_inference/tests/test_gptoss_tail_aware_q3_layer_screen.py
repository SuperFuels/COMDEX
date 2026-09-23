import importlib.util
from pathlib import Path


SCRIPT = (Path(__file__).parents[3] / "scripts" /
          "run_aion_gptoss_tail_aware_q3_layer_screen.py")
SPEC = importlib.util.spec_from_file_location("aion_tail_q3", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_canonical_is_key_order_independent():
    assert MODULE.canonical({"x": 1, "y": 2}) == MODULE.canonical({"y": 2, "x": 1})
