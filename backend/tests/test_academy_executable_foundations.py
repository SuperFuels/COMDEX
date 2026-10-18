from pathlib import Path

from backend.modules.hexcore.advanced_python_apprenticeship import run as run_advanced_python
from backend.modules.hexcore.distributed_systems_apprenticeship import run as run_distributed
from backend.modules.hexcore.networking_apprenticeship import run as run_networking
from backend.modules.hexcore.operating_systems_apprenticeship import run as run_operating_systems


def _paths(tmp_path: Path, name: str) -> tuple[Path, Path]:
    return tmp_path / name / "learning.json", tmp_path / f"{name}.json"


def test_advanced_python_executor_passes_real_private_package(tmp_path: Path) -> None:
    state, result = _paths(tmp_path, "advanced_python")
    outcome = run_advanced_python(state_path=state, result_path=result)
    assert outcome["passed"] is True
    assert outcome["gate"]["score"] >= 0.90
    assert outcome["gate"]["malicious_variants_rejected"] == outcome["gate"]["malicious_variants_total"]


def test_operating_systems_executor_passes_isolated_process_lab(tmp_path: Path) -> None:
    state, result = _paths(tmp_path, "operating_systems")
    outcome = run_operating_systems(state_path=state, result_path=result)
    assert outcome["passed"] is True
    assert outcome["gate"]["live_repository_writes"] == 0


def test_networking_executor_passes_loopback_protocol_lab(tmp_path: Path) -> None:
    state, result = _paths(tmp_path, "networking")
    outcome = run_networking(state_path=state, result_path=result)
    assert outcome["passed"] is True
    assert outcome["gate"]["routing_loopback_isolation"] is True
    assert outcome["gate"]["tls_safe_default"] is True


def test_distributed_executor_rejects_minority_and_converges(tmp_path: Path) -> None:
    state, result = _paths(tmp_path, "distributed")
    outcome = run_distributed(state_path=state, result_path=result)
    assert outcome["passed"] is True
    assert outcome["gate"]["consensus_quorum"] is True
    assert outcome["gate"]["recovery_and_convergence"] is True
    assert outcome["gate"]["malicious_variants_rejected"] == 6
