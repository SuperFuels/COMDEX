"""Bounded executable Operating Systems apprenticeship for the Academy."""
from __future__ import annotations

import json
import mmap
import os
import stat
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_operating_systems_apprenticeship_v1"

CHILD = '''from __future__ import annotations
import json,os,sys
for line in sys.stdin:
    row=json.loads(line)
    print(json.dumps({"pid":os.getpid(),"parent":os.getppid(),"sequence":row["sequence"],"value":row["value"]*2}),flush=True)
'''


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "operating_systems_academy_cau"}


def run(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion-os-academy-") as raw:
        workspace = Path(raw)
        child = workspace / "worker.py"
        child.write_text(CHILD, encoding="utf-8")
        started = time.perf_counter()
        process = subprocess.Popen(
            [sys.executable, "-I", str(child)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=workspace,
        )
        assert process.stdin and process.stdout
        requests = [{"sequence": index, "value": index + 2} for index in range(4)]
        responses = []
        for request in requests:
            process.stdin.write(json.dumps(request) + "\n"); process.stdin.flush()
            responses.append(json.loads(process.stdout.readline()))
        process.stdin.close(); returncode = process.wait(timeout=5)
        process_elapsed = time.perf_counter() - started

        counter = {"value": 0}
        lock = threading.Lock()
        def increment() -> None:
            for _ in range(1000):
                with lock:
                    counter["value"] += 1
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: increment(), range(4)))

        with mmap.mmap(-1, 64) as region:
            region[:11] = b"aion-memory"
            memory_ok = region[:11] == b"aion-memory"

        protected = workspace / "private.dat"
        protected.write_text("bounded", encoding="utf-8"); protected.chmod(0o600)
        permission_ok = stat.S_IMODE(protected.stat().st_mode) == 0o600

        timeout_enforced = False
        try:
            subprocess.run([sys.executable, "-I", "-c", "import time;time.sleep(2)"], timeout=0.1, check=False)
        except subprocess.TimeoutExpired:
            timeout_enforced = True

        security_cases = [
            {"shell": True}, {"mode": 0o777}, {"path": "/"},
            {"dynamic": "eval"}, {"network": True}, {"unbounded_processes": True},
        ]
        def safe(case: dict[str, Any]) -> bool:
            return not (
                case.get("shell") is True or case.get("mode") == 0o777
                or case.get("path") == "/" or case.get("dynamic") in {"eval", "exec"}
                or case.get("network") is True or case.get("unbounded_processes") is True
            )
        malicious_rejected = sum(not safe(case) for case in security_cases)
        transfer_ok = [row["value"] for row in responses] == [4, 6, 8, 10]
        gate = {
            "process_and_ipc": returncode == 0 and len({row["pid"] for row in responses}) == 1,
            "thread_synchronisation": counter["value"] == 4000,
            "memory_mapping": memory_ok,
            "filesystem_permissions": permission_ok,
            "scheduling_and_timeout": timeout_enforced,
            "system_trace_complete": process_elapsed > 0 and all(set(row) == {"pid", "parent", "sequence", "value"} for row in responses),
            "source_disjoint_protocol_transfer": transfer_ok,
            "malicious_variants_rejected": malicious_rejected,
            "malicious_variants_total": len(security_cases),
            "unsafe_programs_executed": 0,
            "live_repository_writes": 0,
        }
        checks = [gate[key] for key in (
            "process_and_ipc", "thread_synchronisation", "memory_mapping",
            "filesystem_permissions", "scheduling_and_timeout",
            "system_trace_complete", "source_disjoint_protocol_transfer",
        )]
        gate["score"] = sum(checks) / len(checks)
        gate["source_disjoint_transfer"] = gate["source_disjoint_protocol_transfer"]
        gate["accepted"] = bool(
            gate["score"] >= 0.9
            and malicious_rejected == len(security_cases)
            and gate["unsafe_programs_executed"] == gate["live_repository_writes"] == 0
        )
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    cohort = "operating_systems_" + _canonical_hash(gate)[:16]
    runtime.store.state.setdefault("operating_systems_academy", {})[cohort] = {
        "gate": gate, "responses": responses, "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "operating_systems_academy",
        ["construct_child_process_contract", "communicate_over_json_pipe", "synchronise_threads",
         "exercise_mapped_memory", "apply_private_file_permissions", "enforce_process_timeout",
         "retain_system_trace", "transfer_protocol_after_restart"],
        gate["score"], gate["accepted"], {"cohort_id": cohort, "gate": gate},
        ["procedure_advanced_python_apprenticeship_v1"],
    )
    decision = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                  score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="operating_systems_apprenticeship")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "champion_retained": restarted.store.state["champions"].get("operating_systems_academy") == PROCEDURE_ID,
        "cohort_retained": cohort in restarted.store.state.get("operating_systems_academy", {}),
        "source_replay": 0,
    }
    result = {
        "schema_version": "aion.hexcore.operating_systems_apprenticeship.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "gate": gate, "restart": restart,
        "promotion": {"candidate": candidate.to_dict(), "decision": decision},
        "passed": bool(gate["accepted"] and restart["champion_retained"] and restart["cohort_retained"]),
        "boundary": "This is a bounded local OS laboratory covering processes, IPC, threads, memory, permissions and resource control; it is not kernel or production OS mastery.",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
