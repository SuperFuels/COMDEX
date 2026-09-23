"""Acquire, run and register executors requested by the guided academy."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.hexcore.advanced_python_apprenticeship import run as run_advanced_python
from backend.modules.hexcore.guided_foundation_academy import GuidedFoundationAcademy
from backend.modules.hexcore.testing_debugging_academy_bridge import run as run_testing_debugging
from backend.modules.hexcore.academy_verified_evidence_bridge import run as run_evidence_bridge
from backend.modules.hexcore.operating_systems_apprenticeship import run as run_operating_systems
from backend.modules.hexcore.networking_apprenticeship import run as run_networking
from backend.modules.hexcore.distributed_systems_apprenticeship import run as run_distributed_systems


Runner = Callable[[Path, Path, Path], Mapping[str, Any]]


def _advanced(repo_root: Path, state_path: Path, result_path: Path) -> Mapping[str, Any]:
    del repo_root
    return run_advanced_python(state_path=state_path, result_path=result_path)


def _testing(repo_root: Path, state_path: Path, result_path: Path) -> Mapping[str, Any]:
    return run_testing_debugging(repo_root=repo_root, state_path=state_path, result_path=result_path)


def _operating_systems(repo_root: Path, state_path: Path, result_path: Path) -> Mapping[str, Any]:
    del repo_root
    return run_operating_systems(state_path=state_path, result_path=result_path)


def _networking(repo_root: Path, state_path: Path, result_path: Path) -> Mapping[str, Any]:
    del repo_root
    return run_networking(state_path=state_path, result_path=result_path)


def _distributed(repo_root: Path, state_path: Path, result_path: Path) -> Mapping[str, Any]:
    del repo_root
    return run_distributed_systems(state_path=state_path, result_path=result_path)


def _evidence(module_id: str) -> Runner:
    def execute(repo_root: Path, state_path: Path, result_path: Path) -> Mapping[str, Any]:
        return run_evidence_bridge(
            module_id=module_id, repo_root=repo_root,
            state_path=state_path, result_path=result_path,
        )
    return execute


RUNNERS: dict[str, Runner] = {
    "advanced_python": _advanced,
    "testing_debugging": _testing,
    "operating_systems": _operating_systems,
    "networking": _networking,
    "distributed_systems": _distributed,
    "software_engineering": _evidence("software_engineering"),
    "database_engineering": _evidence("database_engineering"),
    "rust_systems": _evidence("rust_systems"),
    "secure_engineering": _evidence("secure_engineering"),
    "architecture_operations": _evidence("architecture_operations"),
    "integrated_engineering_capstone": _evidence("integrated_engineering_capstone"),
}


class AcademyExecutorAcquisitionWorker:
    """Consumes open Academy requests and closes them only with verified receipts."""

    def __init__(self, *, repo_root: Path, academy_state_path: Path, state_path: Path) -> None:
        self.repo_root = repo_root
        self.academy_state_path = academy_state_path
        self.state_path = state_path
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "schema_version": "aion.hexcore.academy_executor_worker.v1",
            "attempts": [], "last_progress_at": None, "last_progress_epoch": None,
            "consecutive_no_progress": 0, "status": "ready",
        }

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
        json.loads(temporary.read_text(encoding="utf-8")); os.replace(temporary, self.state_path)

    def open_requests(self) -> list[dict[str, Any]]:
        academy = GuidedFoundationAcademy(repo_root=self.repo_root, state_path=self.academy_state_path)
        return [dict(row) for row in academy.state.get("executor_requests") or [] if row.get("status") == "open"]

    def step(self) -> dict[str, Any]:
        academy = GuidedFoundationAcademy(repo_root=self.repo_root, state_path=self.academy_state_path)
        requests = [row for row in academy.state.get("executor_requests") or [] if row.get("status") == "open"]
        runnable = next((row for row in requests if row.get("module_id") in RUNNERS), None)
        if runnable is None:
            self.state["consecutive_no_progress"] = int(self.state.get("consecutive_no_progress") or 0) + 1
            self.state["status"] = "blocked_no_verified_executor" if requests else "waiting_for_request"
            outcome = {
                "status": self.state["status"], "progressed": False,
                "open_requests": len(requests),
                "unsupported_modules": [row.get("module_id") for row in requests],
            }
            self._save()
            return outcome

        module_id = str(runnable["module_id"])
        result_path = self.repo_root / f"results/hexcore_{module_id}_academy.json"
        learning_path = self.repo_root / f"backend/modules/hexcore/data/{module_id}_academy/learning.json"
        started = time.time()
        try:
            result = dict(RUNNERS[module_id](self.repo_root, learning_path, result_path))
            passed = result.get("passed") is True and (result.get("gate") or {}).get("accepted") is True
            if not passed:
                status = "executor_rejected"
                receipt = None
            else:
                artifact_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
                receipt = academy.record_verified_module(
                    module_id=module_id,
                    procedure_id=str(result["procedure_id"]),
                    artifact=str(result_path.relative_to(self.repo_root)),
                    artifact_hash=artifact_hash,
                    score=float((result.get("gate") or {}).get("score", 1.0)),
                    transfer_verified=bool((result.get("gate") or {}).get("source_disjoint_transfer") is True),
                    restart_verified=bool(
                        (result.get("restart") or {}).get("champion_retained") is True
                        or (result.get("gate") or {}).get("restart_retention") is True
                    ),
                )
                passed = receipt.get("verified") is True
                status = "verified_and_registered" if passed else "receipt_rejected"
        except Exception as error:
            result = {"error": type(error).__name__, "detail": str(error)}
            receipt = None; passed = False; status = "executor_error"

        row = {
            "module_id": module_id, "request_id": runnable.get("request_id"),
            "status": status, "progressed": passed, "receipt": receipt,
            "result_path": str(result_path.relative_to(self.repo_root)),
            "duration_seconds": round(time.time() - started, 3),
            "recorded_epoch": time.time(),
        }
        if not passed:
            row["failure"] = result.get("error") or result.get("gate")
        self.state["attempts"].append(row)
        self.state["attempts"] = self.state["attempts"][-500:]
        if passed:
            self.state["last_progress_epoch"] = time.time()
            self.state["last_progress_at"] = row["recorded_epoch"]
            self.state["consecutive_no_progress"] = 0
            self.state["status"] = "progressed"
        else:
            self.state["consecutive_no_progress"] = int(self.state.get("consecutive_no_progress") or 0) + 1
            self.state["status"] = status
        self._save()
        return row

    def status(self) -> dict[str, Any]:
        last = float(self.state.get("last_progress_epoch") or 0.0)
        age = time.time() - last if last else None
        return {
            "status": self.state.get("status"),
            "attempts": len(self.state.get("attempts") or []),
            "consecutive_no_progress": int(self.state.get("consecutive_no_progress") or 0),
            "last_progress_age_seconds": age,
            "stalled": bool(
                int(self.state.get("consecutive_no_progress") or 0) >= 3
                or (age is not None and age > 1800 and self.open_requests())
            ),
            "supported_modules": sorted(RUNNERS),
        }
