import os
import json
from backend.AION.validation.resonant_logic_kernel_tests import ResonantLogicKernelTests


def test_resonant_logic_kernel_tests(tmp_path):
    """
    Validates the Resonant Logic Kernel (D5+ Adaptive)
    ensuring invariance structure, adaptive tuning, and file output.
    """

    output_path = tmp_path / "kernel_report.jsonl"
    validator = ResonantLogicKernelTests(output_path=str(output_path))
    report = validator.run()

    # Check run status — must be either 'ok' or 'drift'
    assert report["status"] in ("ok", "drift"), f"RLK validator failed: {report}"
    assert 0.0 <= report["pass_rate"] <= 1.0

    # Verify adaptive loop executed at least once
    assert report["iterations"] >= 1
    assert isinstance(report["final_tolerance"], float)

    # File existence and readability
    assert os.path.exists(output_path)
    with open(output_path, "r") as f:
        lines = [json.loads(l) for l in f.readlines()]

    # Should contain iteration history and a final summary
    assert len(lines) >= 2, "Insufficient log entries written"

    first_entry = lines[0]
    summary = lines[-1]

    # Iteration entries must contain adaptive keys
    for key in ("iteration", "tolerance", "pass_rate"):
        assert key in first_entry, f"Missing iteration key: {key}"

    # Final summary structure
    for key in ("status", "pass_rate", "final_tolerance", "iterations", "target_rate"):
        assert key in summary, f"Missing summary key: {key}"

    print(f"\n✅ RLK-Adaptive summary: {report['status']} "
          f"(pass_rate={report['pass_rate']:.3f}, ε={report['final_tolerance']:.4f})")