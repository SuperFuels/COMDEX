import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_aion_gptoss_partial_expert_io_gate.py"
SPEC = importlib.util.spec_from_file_location("run_aion_gptoss_partial_expert_io_gate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_addresses_require_six_components_and_ignore_appledouble(tmp_path):
    receipt_dir = tmp_path / "receipts" / "shard-01"
    receipt_dir.mkdir(parents=True)
    index = 0
    for projection in ("gate", "up", "down"):
        for kind in ("weight", "bias"):
            payload = {
                "region_name": f"blk.0.ffn_{projection}_exps.{kind}",
                "pack_relative_path": f"pack-{index}",
                "frames": [{"expert": 0, "raw_bytes": index + 1}],
            }
            (receipt_dir / f"region-{index}.json").write_text(json.dumps(payload))
            index += 1
    (receipt_dir / "._region-0.json").write_bytes(b"\x00\xffnot-json")
    found = MODULE.addresses(tmp_path, 0, 0)
    assert len(found) == 6
    assert {(item["projection"], item["kind"]) for item in found} == {
        (projection, kind) for projection in ("gate", "up", "down")
        for kind in ("weight", "bias")
    }
