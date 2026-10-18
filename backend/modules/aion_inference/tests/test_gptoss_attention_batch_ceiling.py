import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "scripts" / "analyze_aion_gptoss_attention_batch_ceiling.py"
SPEC = importlib.util.spec_from_file_location("attention_ceiling", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_summarize_run_calculates_optimistic_ceiling():
    run = {
        "mode": "union",
        "wall_seconds": 10.0,
        "all_positions_bitwise_exact": True,
        "layers": [
            {"attention_ms_total": 200.0, "moe_ms_total": 300.0,
             "expert_load_seconds": 8.0},
            {"attention_ms_total": 300.0, "moe_ms_total": 200.0,
             "expert_load_seconds": 1.0},
        ],
        "positions": [{"output_ms": 50.0}, {"output_ms": 50.0}],
    }
    result = MODULE.summarize_run(run)
    assert result["measured_attention_seconds"] == 0.5
    assert result["measured_moe_seconds"] == 0.5
    assert result["measured_expert_delivery_seconds"] == 9.0
    assert result["measured_output_seconds"] == 0.1
    assert result["optimistic_speedup_if_attention_were_free"] == 10.0 / 9.5
    assert result["optimistic_speedup_if_attention_and_moe_were_free"] == 10.0 / 9.0
