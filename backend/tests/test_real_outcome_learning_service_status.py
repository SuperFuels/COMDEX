import json

from backend.AION.system.aion_real_outcome_learning_service import (
    _is_benign_child_log_line,
    _write_service_status,
)


def test_real_outcome_service_publishes_atomic_phase_heartbeat(tmp_path):
    path = tmp_path / "results/status.json"
    _write_service_status(path, cycle=7, phase="cross_domain_consequence_repair")
    row = json.loads(path.read_text())
    assert row["status"] == "running"
    assert row["cycle"] == 7
    assert row["phase"] == "cross_domain_consequence_repair"
    assert row["pid"] > 0
    assert row["updated_at"] > 0
    assert not path.with_suffix(".json.tmp").exists()


def test_known_macos_allocator_shutdown_noise_is_filtered_only_when_exact():
    assert _is_benign_child_log_line(
        "Python(42) MallocStackLogging: can't turn off malloc stack logging because it was not enabled."
    ) is True
    assert _is_benign_child_log_line("RuntimeError: allocator failed") is False
