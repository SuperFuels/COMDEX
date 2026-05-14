import os
import json
import math
from backend.AION.validation.piS_phase_closure_validator import PiSPhaseClosureValidator

def test_piS_phase_closure_validator(tmp_path):
    log_path = tmp_path / "phase_state_events.jsonl"
    output_path = tmp_path / "piS_closure_report.jsonl"

    # ✅ Create φ-values summing exactly to 2π (closure)
    phi_values = [math.pi / 4] * 8  # 8 * (π/4) = 2π

    with open(log_path, "w") as f:
        for φ in phi_values:
            f.write(json.dumps({"phi": φ}) + "\n")

    validator = PiSPhaseClosureValidator(
        input_path=str(log_path),
        output_path=str(output_path),
        tolerance=0.05
    )
    report = validator.run()

    # ✅ Expect closure maintained
    assert report["status"] == "ok", f"Unexpected status: {report}"
    assert report["Δφs"] <= 0.05, f"Δφs too large: {report['Δφs']}"
    assert os.path.exists(output_path)

    # ✅ Ensure report logged properly
    with open(output_path, "r") as f:
        lines = [json.loads(l) for l in f.readlines()]
    assert len(lines) >= 1
    assert "Δφs" in lines[-1]