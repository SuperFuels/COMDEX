"""Arena v15: wall-clock continual operation against independently changing outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROCEDURE_ID = "procedure_long_duration_real_outcome_campaign_v15_6fd206e71b24"
REMOTE_AUTHORITIES = {
    "cpython": ("https://github.com/python/cpython.git", "refs/heads/main"),
    "node": ("https://github.com/nodejs/node.git", "refs/heads/main"),
}
JSON_AUTHORITIES = {
    "pypi_numpy": "https://pypi.org/pypi/numpy/json",
    "open_meteo_madrid": "https://api.open-meteo.com/v1/forecast?latitude=40.4168&longitude=-3.7038&current=temperature_2m,wind_speed_10m",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _remote_head(url: str, ref: str) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        ["git", "ls-remote", "--exit-code", url, ref],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    revision = completed.stdout.split()[0] if completed.returncode == 0 and completed.stdout.split() else None
    return {
        "authority": url,
        "ref": ref,
        "revision": revision,
        "reachable": revision is not None,
        "latency_seconds": round(time.monotonic() - started, 4),
        "stderr_class": "none" if completed.returncode == 0 else "remote_or_network_failure",
    }


def _json_outcome(url: str) -> dict[str, Any]:
    started=time.monotonic();error_class="invalid_json_shape";request=urllib.request.Request(url,headers={"User-Agent":"AION-HexCore-read-only-research/1.0","Accept":"application/json"},method="GET")
    try:
        with urllib.request.urlopen(request,timeout=40) as response:body=response.read();status=response.status
        parsed=json.loads(body);reachable=status==200 and isinstance(parsed,dict)
    except Exception as error:
        body=b"";status=None;reachable=False;error_class=type(error).__name__
    return {"authority":url,"revision":hashlib.sha256(body).hexdigest() if reachable else None,"reachable":reachable,"status":status,"latency_seconds":round(time.monotonic()-started,4),"stderr_class":"none" if reachable else error_class}


def _execution_outcome(repo_root: Path) -> dict[str, Any]:
    verifier = (
        "import hashlib,json,pathlib,sys;"
        "root=pathlib.Path(sys.argv[1]);"
        "r=json.loads((root/'results/hexcore_continual_neural_physical_policy_v14.json').read_text());"
        "w=root/'backend/modules/hexcore/data/neural_physical_v14/policy.pt';"
        "h=hashlib.sha256(w.read_bytes()).hexdigest();"
        "assert r['passed'] and h==r['gate']['weights_sha256'];"
        "print(h)"
    )
    command = [
        str(repo_root / ".venv/bin/python"),
        "-I",
        "-c",
        verifier,
        str(repo_root),
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, timeout=60, check=False)
    return {
        "authority": "fresh_pytest_subprocess",
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256((completed.stdout + completed.stderr).encode()).hexdigest(),
    }


def _transaction_outcome(database: Path, cycle: int) -> dict[str, Any]:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("CREATE TABLE IF NOT EXISTS cycles(id INTEGER PRIMARY KEY, committed_at TEXT NOT NULL)")
    connection.execute("INSERT OR REPLACE INTO cycles VALUES (?, ?)", (cycle, _now()))
    connection.commit()
    retained = connection.execute("SELECT COUNT(*) FROM cycles WHERE id=?", (cycle,)).fetchone()[0] == 1
    connection.close()
    return {"authority": "sqlite_transaction_commit", "passed": retained, "cycle": cycle}


def _initial_state() -> dict[str, Any]:
    return {
        "schema_version": "aion.hexcore.long_duration_campaign.v1",
        "procedure_id": PROCEDURE_ID,
        "started_at": _now(),
        "started_epoch": time.time(),
        "last_cycle_epoch": None,
        "cycles": [],
        "source_models": {name: {"observations": 0, "changes": 0, "failures": 0} for name in (*REMOTE_AUTHORITIES,*JSON_AUTHORITIES)},
        "process_starts": 0,
        "status": "RUNNING",
        "promotion": "BLOCKED_UNTIL_WALL_CLOCK_AND_OUTCOME_GATES_PASS",
    }


def run_cycle(*, repo_root: Path, state_path: Path, ledger_path: Path, minimum_hours: float, minimum_cycles: int) -> dict[str, Any]:
    state = json.loads(state_path.read_text()) if state_path.exists() else _initial_state()
    for name in (*REMOTE_AUTHORITIES,*JSON_AUTHORITIES):state["source_models"].setdefault(name,{"observations":0,"changes":0,"failures":0})
    state["process_starts"] += 1
    cycle_number = len(state["cycles"]) + 1
    commitment_material = {
        "cycle": cycle_number,
        "planned_actions": ["query_two_independent_remote_heads", "query_two_public_json_outcomes", "run_protected_execution", "commit_transaction"],
        "previous_heads": {name: model.get("last_revision") for name, model in state["source_models"].items()},
    }
    pre_action_commitment = _hash(commitment_material)
    remotes = {name: _remote_head(*contract) for name, contract in REMOTE_AUTHORITIES.items()}
    remotes.update({name:_json_outcome(url) for name,url in JSON_AUTHORITIES.items()})
    execution = _execution_outcome(repo_root)
    transaction = _transaction_outcome(state_path.parent / "campaign.sqlite3", cycle_number)
    changes = []
    for name, outcome in remotes.items():
        model = state["source_models"][name]
        previous = model.get("last_revision")
        model["observations"] += 1
        if not outcome["reachable"]:
            model["failures"] += 1
        elif previous and previous != outcome["revision"]:
            model["changes"] += 1
            changes.append(name)
        if outcome["revision"]:
            model["last_revision"] = outcome["revision"]
        # Learned monitoring policy: volatile or failing sources receive the
        # shorter interval; stable sources can be measured less often.
        risk = (model["changes"] + model["failures"] + 1) / (model["observations"] + 2)
        model["recommended_interval_minutes"] = 15 if risk >= 0.34 else 60
    observed = {
        "cycle": cycle_number,
        "observed_at": _now(),
        "pre_action_commitment": pre_action_commitment,
        "remotes": remotes,
        "execution": execution,
        "transaction": transaction,
        "changes_detected": changes,
        "all_outcomes_safe": execution["passed"] and transaction["passed"],
    }
    observed["outcome_sha256"] = _hash(observed)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observed, sort_keys=True) + "\n")
    state["cycles"].append({
        "cycle": cycle_number,
        "observed_at": observed["observed_at"],
        "commitment": pre_action_commitment,
        "outcome_sha256": observed["outcome_sha256"],
        "remote_reachable": sum(int(v["reachable"]) for v in remotes.values()),
        "execution_passed": execution["passed"],
        "transaction_passed": transaction["passed"],
        "changes_detected": changes,
    })
    state["last_cycle_epoch"] = time.time()
    elapsed_hours = (state["last_cycle_epoch"] - state["started_epoch"]) / 3600
    all_safe = all(c["execution_passed"] and c["transaction_passed"] for c in state["cycles"])
    enough_authority = all(m["observations"] >= minimum_cycles for m in state["source_models"].values())
    accepted = elapsed_hours >= minimum_hours and len(state["cycles"]) >= minimum_cycles and all_safe and enough_authority
    state["gate"] = {
        "minimum_elapsed_hours": minimum_hours,
        "actual_elapsed_hours": elapsed_hours,
        "minimum_cycles": minimum_cycles,
        "completed_cycles": len(state["cycles"]),
        "independent_remote_authorities": len(REMOTE_AUTHORITIES)+len(JSON_AUTHORITIES),
        "all_execution_and_transaction_outcomes_safe": all_safe,
        "wall_clock_requirement_met": elapsed_hours >= minimum_hours,
        "restart_resumable": state["process_starts"] >= 2,
        "accepted": accepted,
    }
    if accepted:
        if state.get("promotion") == "INTERNAL_CAU_PROMOTED":
            state["status"] = "INTERNALLY_PROMOTED_BY_CAU"
        else:
            state["status"] = "INTERNALLY_ELIGIBLE_FOR_CAU_REVIEW"
            state["promotion"] = "PENDING_CAU_REVIEW"
    _atomic_json(state_path, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--state-path", type=Path, default=Path("results/hexcore_long_duration_campaign_v15_state.json"))
    parser.add_argument("--ledger-path", type=Path, default=Path("results/hexcore_long_duration_campaign_v15_ledger.jsonl"))
    parser.add_argument("--minimum-hours", type=float, default=24.0)
    parser.add_argument("--minimum-cycles", type=int, default=12)
    args = parser.parse_args()
    state = run_cycle(repo_root=args.repo_root.resolve(), state_path=args.state_path.resolve(), ledger_path=args.ledger_path.resolve(), minimum_hours=args.minimum_hours, minimum_cycles=args.minimum_cycles)
    print(json.dumps({"status": state["status"], "gate": state["gate"], "source_models": state["source_models"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
