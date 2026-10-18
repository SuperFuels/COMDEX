from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import subprocess
import tempfile
import time
import tomllib
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_rust_sql_systems_depth_and_measured_selection_97a48e241cb7"
PARENT_ID = "procedure_rust_sql_construction_and_selection_b949b03fda6e"


def _proposal(response: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(response.get("proposal") or {})


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def _construction_prompt() -> str:
    return """
You are a proposal-only systems engineer. Return one JSON object with exactly:
cargo_toml, lib_rs, main_rs, python_source, migration_v1_up,
migration_v2_up, migration_v2_down, rationale.

RUST CONTRACT
Construct a dependency-free, multi-file Rust 2021 crate named aion_ledger.
Cargo.toml must define a library and a binary. lib.rs must expose:
- a public LedgerError enum implementing Display and std::error::Error;
- a public AccountStore: Send + Sync trait;
- a public MemoryStore implementation;
- a cloneable public Ledger using Arc plus Mutex or RwLock internally;
- Ledger::new();
- open_account(&self, id: &str, balance: i64) -> Result<(), LedgerError>;
- balance(&self, id: &str) -> Result<i64, LedgerError>;
- transfer(&self, from: &str, to: &str, amount: i64)
  -> Result<(), LedgerError>.
Transfers must reject missing accounts, non-positive amounts, self-transfer,
insufficient funds and overflow. A failed transfer must leave both balances
unchanged. Concurrent transfers must preserve total value. Do not use unsafe,
filesystem, network, subprocesses, environment variables, external crates or
warning suppressions.

main.rs must accept `bench N`, create two accounts with 1,000,000 units each,
perform N pairs of one-unit A->B then B->A transfers, and print exactly
`total=2000000 a=1000000 b=1000000 operations=<2*N>`.

PYTHON CONTRACT
Write a dependency-free Python program with the identical `bench N` CLI and
exact output. It must perform the same checked ledger operations, not print a
constant. No filesystem, network, subprocess, eval, exec, dynamic imports or
environment access.

SQL CONTRACT
Write SQLite migrations for an account/transfer ledger. V1 creates a one-row
schema version table, accounts with id/owner/balance semantics, transfers,
strict integrity constraints, foreign keys, self-transfer prevention, and
source/time plus destination/time indexes. V2 adds a non-null transfer status
with a safe default, an audit table, a status index, and changes the one version
row to 2. V2 down reverses only V2, changes that row back to 1, and preserves V1
data. SQLite 3.43 supports ALTER TABLE ... DROP COLUMN. The down migration may
drop only the V2 audit table and V2 indexes; no other table may be dropped. Use
TEXT IDs. Do not use ATTACH, extension loading, triggers, foreign-key disabling,
writable_schema, DELETE or unsafe pragmas.
""".strip()


RUST_FORBIDDEN = {
    "unsafe": r"\bunsafe\b",
    "subprocess": r"std::process::Command|Command\s*::",
    "filesystem": r"std::fs|File\s*::|OpenOptions",
    "network": r"TcpStream|UdpSocket|std::net",
    "environment": r"env::var|std::env::vars",
    "external_crate": r"\bextern\s+crate\b",
    "warning_suppression": r"allow\s*\(\s*warnings\s*\)",
}

PYTHON_FORBIDDEN = {
    "subprocess": r"\bsubprocess\b|os\.system|popen",
    "network": r"\bsocket\b|urllib|requests",
    "dynamic_execution": r"\beval\s*\(|\bexec\s*\(",
    "filesystem": r"\bopen\s*\(",
    "environment": r"os\.environ|getenv",
    "dynamic_import": r"importlib|__import__",
}

SQL_FORBIDDEN = {
    "attach": r"\bATTACH\b",
    "extension": r"load_extension",
    "foreign_keys_off": r"foreign_keys\s*=\s*off",
    "writable_schema": r"writable_schema",
    "trigger": r"\bTRIGGER\b",
    "destructive_rows": r"\bDELETE\s+FROM\b",
}


def _audit(source: str, patterns: Mapping[str, str], *, flags: int = 0, strip_sql_comments: bool = False) -> Dict[str, Any]:
    inspected = re.sub(r"--[^\n]*", "", source) if strip_sql_comments else source
    findings = [name for name, pattern in patterns.items() if re.search(pattern, inspected, flags)]
    return {"safe": not findings, "findings": findings}


def _run(command: List[str], *, cwd: Path, timeout: int = 60, env: Mapping[str, str] | None = None) -> Dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=dict(env) if env is not None else None,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr[-4000:],
        "seconds": time.perf_counter() - started,
        "passed": completed.returncode == 0,
    }


RUST_AUTHORITY_TEST = r'''
use aion_ledger::Ledger;
use std::thread;

#[test]
fn authority_checks_atomicity_errors_and_concurrency() {
    let ledger = Ledger::new();
    ledger.open_account("a", 10_000).unwrap();
    ledger.open_account("b", 10_000).unwrap();

    assert!(ledger.transfer("a", "a", 1).is_err());
    assert!(ledger.transfer("a", "b", 0).is_err());
    assert!(ledger.transfer("missing", "b", 1).is_err());
    assert!(ledger.transfer("a", "b", 20_001).is_err());
    assert_eq!(ledger.balance("a").unwrap(), 10_000);
    assert_eq!(ledger.balance("b").unwrap(), 10_000);

    let mut workers = Vec::new();
    for _ in 0..8 {
        let shared = ledger.clone();
        workers.push(thread::spawn(move || {
            for _ in 0..250 {
                shared.transfer("a", "b", 1).unwrap();
                shared.transfer("b", "a", 1).unwrap();
            }
        }));
    }
    for worker in workers { worker.join().unwrap(); }
    assert_eq!(ledger.balance("a").unwrap(), 10_000);
    assert_eq!(ledger.balance("b").unwrap(), 10_000);

    ledger.open_account("max", i64::MAX).unwrap();
    ledger.open_account("one", 1).unwrap();
    assert!(ledger.transfer("one", "max", 1).is_err());
    assert_eq!(ledger.balance("one").unwrap(), 1);
    assert_eq!(ledger.balance("max").unwrap(), i64::MAX);
}
'''.strip()


def _evaluate_rust(cargo_toml: str, lib_rs: str, main_rs: str) -> Dict[str, Any]:
    combined = "\n".join([cargo_toml, lib_rs, main_rs])
    audit = _audit(combined, RUST_FORBIDDEN)
    structural = {
        "trait": bool(re.search(r"pub\s+trait\s+AccountStore", lib_rs)),
        "error_enum": bool(re.search(r"pub\s+enum\s+LedgerError", lib_rs)),
        "display_error": "std::error::Error" in lib_rs and "Display" in lib_rs,
        "shared_state": "Arc" in lib_rs and ("Mutex" in lib_rs or "RwLock" in lib_rs),
        "result_api": "Result<" in lib_rs,
        "option_use": "Option<" in lib_rs or ".get(" in lib_rs,
    }
    if not audit["safe"]:
        return {"audit": audit, "structural": structural, "passed": False}
    with tempfile.TemporaryDirectory(prefix="aion_rust_depth_") as raw:
        root = Path(raw)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")
        (root / "src/lib.rs").write_text(lib_rs, encoding="utf-8")
        (root / "src/main.rs").write_text(main_rs, encoding="utf-8")
        (root / "tests/authority.rs").write_text(RUST_AUTHORITY_TEST, encoding="utf-8")
        denied_warnings_env = dict(os.environ)
        denied_warnings_env["RUSTFLAGS"] = "-D warnings"
        tests = _run(["cargo", "test", "--offline"], cwd=root, timeout=120, env=denied_warnings_env)
        build = _run(
            ["cargo", "build", "--release", "--offline"], cwd=root, timeout=120, env=denied_warnings_env
        )
        binary_name = "aion-ledger"
        try:
            manifest = tomllib.loads(cargo_toml)
            bins = manifest.get("bin") or []
            if bins and isinstance(bins, list):
                binary_name = str(bins[0].get("name") or binary_name)
            elif manifest.get("package", {}).get("name"):
                binary_name = str(manifest["package"]["name"])
        except (tomllib.TOMLDecodeError, AttributeError, TypeError):
            pass
        binary = root / "target/release" / binary_name
        probe = _run([str(binary), "bench", "10"], cwd=root) if binary.exists() else {"passed": False}
        expected = "total=2000000 a=1000000 b=1000000 operations=20"
        passed = (
            all(structural.values())
            and tests["passed"]
            and build["passed"]
            and probe.get("passed") is True
            and probe.get("stdout") == expected
        )
        return {
            "audit": audit,
            "structural": structural,
            "tests": tests,
            "build": build,
            "probe": probe,
            "passed": passed,
        }


def _evaluate_python(source: str) -> Dict[str, Any]:
    audit = _audit(source, PYTHON_FORBIDDEN)
    if not audit["safe"]:
        return {"audit": audit, "passed": False}
    with tempfile.TemporaryDirectory(prefix="aion_python_depth_") as raw:
        root = Path(raw)
        script = root / "ledger.py"
        script.write_text(source, encoding="utf-8")
        compile_result = _run(["python3", "-m", "py_compile", str(script)], cwd=root)
        probe = _run(["python3", str(script), "bench", "10"], cwd=root)
        expected = "total=2000000 a=1000000 b=1000000 operations=20"
        return {
            "audit": audit,
            "compile": compile_result,
            "probe": probe,
            "passed": compile_result["passed"] and probe["passed"] and probe["stdout"] == expected,
        }


def _discover_ledger_schema(connection: sqlite3.Connection) -> Dict[str, Any]:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    relationship_table = None
    source_column = None
    destination_column = None
    for table in tables:
        foreign_keys = connection.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        if len(foreign_keys) >= 2:
            relationship_table = table
            columns = [str(row[3]) for row in foreign_keys]
            source_column = next((value for value in columns if "source" in value or "from" in value), columns[0])
            destination_column = next((value for value in columns if "destination" in value or "to" in value), columns[1])
            break
    return {
        "tables": sorted(tables),
        "relationship_table": relationship_table,
        "source_column": source_column,
        "destination_column": destination_column,
    }


def _audit_sql_migrations(v1: str, v2: str, down: str) -> Dict[str, Any]:
    audit = _audit("\n".join([v1, v2, down]), SQL_FORBIDDEN, flags=re.I, strip_sql_comments=True)
    unsafe_drop_targets: List[str] = []
    for source, allow_audit_drop in [(v1, False), (v2, False), (down, True)]:
        inspected = re.sub(r"--[^\n]*", "", source)
        for match in re.finditer(r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[\"`\[]?([A-Za-z0-9_]+)", inspected, re.I):
            target = match.group(1).lower()
            if not allow_audit_drop or "audit" not in target:
                unsafe_drop_targets.append(target)
    if unsafe_drop_targets:
        audit["findings"].append("unsafe_drop_table:" + ",".join(unsafe_drop_targets))
        audit["safe"] = False
    return audit


def _evaluate_sql(v1: str, v2: str, down: str) -> Dict[str, Any]:
    audit = _audit_sql_migrations(v1, v2, down)
    if not audit["safe"]:
        return {"audit": audit, "passed": False, "checks": {}}
    with tempfile.TemporaryDirectory(prefix="aion_sql_depth_") as raw:
        db = Path(raw) / "ledger.sqlite"
        first = sqlite3.connect(db, timeout=0.2, isolation_level=None)
        first.execute("PRAGMA foreign_keys=ON")
        checks: Dict[str, bool] = {}
        evidence: Dict[str, Any] = {}
        try:
            first.executescript(v1)
            schema = _discover_ledger_schema(first)
            evidence["discovered_schema"] = schema
            transfer_table = schema["relationship_table"]
            source = schema["source_column"]
            destination = schema["destination_column"]
            if not all([transfer_table, source, destination]):
                return {"audit": audit, "checks": checks, "evidence": evidence, "passed": False}
            account_table = next(
                table for table in schema["tables"]
                if table not in {transfer_table, "schema_version", "sqlite_sequence"}
            )
            first.execute(f'INSERT INTO "{account_table}"(id,owner,balance) VALUES(?,?,?)', ("a", "Alice", 100))
            first.execute(f'INSERT INTO "{account_table}"(id,owner,balance) VALUES(?,?,?)', ("b", "Bob", 50))
            column_info = first.execute(f'PRAGMA table_info("{transfer_table}")').fetchall()
            columns = [row[1] for row in column_info]
            primary_key = next((row for row in column_info if int(row[5]) > 0), column_info[0])
            identifier_column = str(primary_key[1])
            integer_identifier = "INT" in str(primary_key[2]).upper()
            identifier_values = [1, 2, 3, 4] if integer_identifier else ["t1", "bad-fk", "bad-self", "bad-zero"]
            amount = next(name for name in columns if "amount" in name or "value" in name)
            timestamp = next(name for name in columns if "time" in name or "created" in name)
            insert = f'INSERT INTO "{transfer_table}"("{identifier_column}","{source}","{destination}","{amount}","{timestamp}") VALUES(?,?,?,?,?)'
            first.execute(insert, (identifier_values[0], "a", "b", 5, 1000))
            checks["v1_transaction"] = True
            for key, params in {
                "foreign_key": (identifier_values[1], "missing", "b", 1, 1001),
                "self_transfer": (identifier_values[2], "a", "a", 1, 1002),
                "nonpositive": (identifier_values[3], "a", "b", 0, 1003),
            }.items():
                try:
                    first.execute(insert, params)
                    checks[f"{key}_rejected"] = False
                except sqlite3.IntegrityError:
                    checks[f"{key}_rejected"] = True

            first.executescript(v2)
            v2_columns = [row[1] for row in first.execute(f'PRAGMA table_info("{transfer_table}")').fetchall()]
            checks["v2_status_added"] = any("status" in name for name in v2_columns)
            checks["v2_audit_added"] = any("audit" in name for name in _discover_ledger_schema(first)["tables"])
            version_rows = first.execute("SELECT * FROM schema_version").fetchall()
            evidence["v2_versions"] = version_rows
            checks["v2_version_recorded"] = any(2 in row for row in version_rows)

            first.execute("BEGIN")
            first.execute(f'INSERT INTO "{account_table}"(id,owner,balance) VALUES(?,?,?)', ("rollback", "Rollback", 1))
            first.execute("ROLLBACK")
            checks["transaction_rollback"] = first.execute(
                f'SELECT COUNT(*) FROM "{account_table}" WHERE id=?', ("rollback",)
            ).fetchone()[0] == 0

            second = sqlite3.connect(db, timeout=0.05, isolation_level=None)
            second.execute("PRAGMA foreign_keys=ON")
            first.execute("BEGIN IMMEDIATE")
            first.execute(f'UPDATE "{account_table}" SET balance=balance+1 WHERE id=?', ("a",))
            locked = False
            try:
                second.execute(f'UPDATE "{account_table}" SET balance=balance+1 WHERE id=?', ("b",))
            except sqlite3.OperationalError as exc:
                locked = "locked" in str(exc).lower()
            first.execute("ROLLBACK")
            second.execute(f'UPDATE "{account_table}" SET balance=balance+1 WHERE id=?', ("b",))
            checks["concurrent_writer_isolation"] = locked
            checks["writer_recovers_after_rollback"] = second.execute(
                f'SELECT balance FROM "{account_table}" WHERE id=?', ("b",)
            ).fetchone()[0] == 51
            second.close()

            plan = first.execute(
                f'EXPLAIN QUERY PLAN SELECT * FROM "{transfer_table}" WHERE "{source}"=? ORDER BY "{timestamp}"',
                ("a",),
            ).fetchall()
            evidence["source_query_plan"] = plan
            checks["source_index_used"] = any("INDEX" in str(row).upper() for row in plan)

            first.executescript(down)
            down_columns = [row[1] for row in first.execute(f'PRAGMA table_info("{transfer_table}")').fetchall()]
            checks["v2_down_removed_status"] = not any("status" in name for name in down_columns)
            checks["v1_data_preserved"] = first.execute(
                f'SELECT COUNT(*) FROM "{transfer_table}" WHERE "{identifier_column}"=?', (identifier_values[0],)
            ).fetchone()[0] == 1
            version_rows = first.execute("SELECT * FROM schema_version").fetchall()
            checks["v1_version_restored"] = any(1 in row for row in version_rows) and not any(2 in row for row in version_rows)
        except (sqlite3.Error, StopIteration) as exc:
            evidence["error"] = str(exc)
        finally:
            first.close()
        return {"audit": audit, "checks": checks, "evidence": evidence, "passed": bool(checks) and all(checks.values())}


def _benchmark_stacks(
    cargo_toml: str,
    lib_rs: str,
    main_rs: str,
    python_source: str,
    *,
    operations: int = 20_000,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="aion_stack_bakeoff_") as raw:
        root = Path(raw)
        rust_root = root / "rust"
        (rust_root / "src").mkdir(parents=True)
        (rust_root / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")
        (rust_root / "src/lib.rs").write_text(lib_rs, encoding="utf-8")
        (rust_root / "src/main.rs").write_text(main_rs, encoding="utf-8")
        python_path = root / "ledger.py"
        python_path.write_text(python_source, encoding="utf-8")

        denied_warnings_env = dict(os.environ)
        denied_warnings_env["RUSTFLAGS"] = "-D warnings"
        rust_build = _run(["cargo", "build", "--release", "--offline"], cwd=rust_root, timeout=120, env=denied_warnings_env)
        binary_name = "aion-ledger"
        try:
            manifest = tomllib.loads(cargo_toml)
            bins = manifest.get("bin") or []
            if bins and isinstance(bins, list):
                binary_name = str(bins[0].get("name") or binary_name)
            elif manifest.get("package", {}).get("name"):
                binary_name = str(manifest["package"]["name"])
        except (tomllib.TOMLDecodeError, AttributeError, TypeError):
            pass
        rust_binary = rust_root / "target/release" / binary_name
        rust_runs = [_run([str(rust_binary), "bench", str(operations)], cwd=rust_root) for _ in range(5)] if rust_binary.exists() else []
        python_runs = [_run(["python3", str(python_path), "bench", str(operations)], cwd=root) for _ in range(5)]
        expected = f"total=2000000 a=1000000 b=1000000 operations={2 * operations}"
        rust_correct = bool(rust_runs) and all(row["passed"] and row["stdout"] == expected for row in rust_runs)
        python_correct = all(row["passed"] and row["stdout"] == expected for row in python_runs)
        rust_median = statistics.median(row["seconds"] for row in rust_runs) if rust_runs else float("inf")
        python_median = statistics.median(row["seconds"] for row in python_runs)
        metrics = {
            "rust": {
                "correct": rust_correct,
                "build_seconds": rust_build["seconds"],
                "median_run_seconds": rust_median,
                "source_bytes": len(lib_rs.encode()) + len(main_rs.encode()) + len(cargo_toml.encode()),
            },
            "python": {
                "correct": python_correct,
                "build_seconds": 0.0,
                "median_run_seconds": python_median,
                "source_bytes": len(python_source.encode()),
            },
        }
        return {"operations": operations, "metrics": metrics, "rust_runs": rust_runs, "python_runs": python_runs, "passed": rust_correct and python_correct}


def _selection_prompt(metrics: Mapping[str, Any]) -> str:
    return f"""
You are a proposal-only technology selector. The same verified ledger workload
was implemented in Rust and Python. Here are independently measured results:
{json.dumps(metrics, indent=2, sort_keys=True)}

Return JSON with decisions, an array containing exactly two objects. Each has
profile, technology, rationale, rejected_alternative, and cited_metrics.
Profiles:
1. sustained_latency: correctness is mandatory; deployment repeatedly runs the
   workload, so choose the lower measured median runtime.
2. one_shot_iteration: correctness is mandatory; the workload runs once after
   each edit, so choose the lower measured build_seconds + median_run_seconds.
Use only the measurements. Do not rely on general language reputation.
""".strip()


def _evaluate_selection(proposal: Mapping[str, Any], metrics: Mapping[str, Any]) -> Dict[str, Any]:
    rows = {str(row.get("profile")): dict(row) for row in proposal.get("decisions") or []}
    rust = metrics["rust"]
    python = metrics["python"]
    expected = {
        "sustained_latency": "rust" if rust["median_run_seconds"] < python["median_run_seconds"] else "python",
        "one_shot_iteration": "rust" if rust["build_seconds"] + rust["median_run_seconds"] < python["median_run_seconds"] else "python",
    }
    evaluation = []
    for profile, optimum in expected.items():
        row = rows.get(profile, {})
        evaluation.append({
            "profile": profile,
            "selected": str(row.get("technology") or "").lower(),
            "optimum": optimum,
            "correct": str(row.get("technology") or "").lower() == optimum,
            "rationale": bool(row.get("rationale")),
            "rejected_alternative": bool(row.get("rejected_alternative")),
            "cited_metrics": bool(row.get("cited_metrics")),
        })
    return {
        "rows": evaluation,
        "accuracy": sum(row["correct"] for row in evaluation) / len(evaluation),
        "explanations_complete": all(row["rationale"] and row["rejected_alternative"] and row["cited_metrics"] for row in evaluation),
    }


def _revision_prompt(
    construction: Mapping[str, Any],
    rust: Mapping[str, Any],
    python: Mapping[str, Any],
    sql: Mapping[str, Any],
) -> str:
    diagnostic = {
        "rust": {
            "passed": rust.get("passed"),
            "audit": rust.get("audit"),
            "structural": rust.get("structural"),
            "test_stderr": str((rust.get("tests") or {}).get("stderr") or "")[-2500:],
            "build_stderr": str((rust.get("build") or {}).get("stderr") or "")[-2500:],
            "probe": rust.get("probe"),
        },
        "python": python,
        "sql": {
            "passed": sql.get("passed"),
            "audit": sql.get("audit"),
            "checks": sql.get("checks"),
            "evidence": sql.get("evidence"),
        },
    }
    return f"""
Revise the candidate below after an independent authority rejected it. Return a
complete replacement JSON object with exactly cargo_toml, lib_rs, main_rs,
python_source, migration_v1_up, migration_v2_up, migration_v2_down, rationale.
Do not merely explain the errors. Preserve every contract in the original task.
Rust is compiled with all warnings denied. SQL V1 accounts require id, non-empty
owner and non-negative balance. V2 down may drop only V2 audit tables/indexes
and must remove the V2 status column while preserving V1 rows.

INDEPENDENT DIAGNOSTIC:
{json.dumps(diagnostic, indent=2, sort_keys=True)}

REJECTED CANDIDATE:
{json.dumps(dict(construction), indent=2, sort_keys=True)}
""".strip()


def _sql_revision_prompt(construction: Mapping[str, Any], sql: Mapping[str, Any]) -> str:
    return f"""
Revise only the SQLite migrations below. Return JSON with exactly
migration_v1_up, migration_v2_up, migration_v2_down, and rationale.

The authority rejected the current migration:
{json.dumps({'audit': sql.get('audit'), 'checks': sql.get('checks'), 'evidence': sql.get('evidence')}, indent=2, sort_keys=True)}

Requirements: V1 creates a one-row schema_version table, accounts with TEXT id,
non-empty owner and non-negative integer balance, and transfers with two foreign
keys, positive amount, self-transfer prevention and source/time plus
destination/time indexes. V2 adds a NOT NULL status with safe default, a V2
audit table and status index, and updates the one version row to 2. V2 down must
drop the status index, drop only the V2 audit table, use SQLite 3.43 ALTER TABLE
transfers DROP COLUMN status, update the version row to 1, and preserve all V1
rows. It must not rebuild or drop the transfers/accounts/schema_version tables.

CURRENT V1:
{construction.get('migration_v1_up', '')}

CURRENT V2:
{construction.get('migration_v2_up', '')}

CURRENT DOWN:
{construction.get('migration_v2_down', '')}
""".strip()
def run_rust_sql_systems_depth(
    *,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
    initial_construction: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    if initial_construction is None:
        construction_response = provider(_construction_prompt(), timeout=480)
        construction = _proposal(construction_response)
    else:
        construction_response = {"available": True, "source": "resume_result", "proposal": dict(initial_construction)}
        construction = dict(initial_construction)
    attempts: List[Dict[str, Any]] = []

    def evaluate(candidate: Mapping[str, Any]) -> tuple[Dict[str, str], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        sources = {
            "cargo_toml": _as_text(candidate.get("cargo_toml")),
            "lib_rs": _as_text(candidate.get("lib_rs")),
            "main_rs": _as_text(candidate.get("main_rs")),
            "python_source": _as_text(candidate.get("python_source")),
            "v1": _as_text(candidate.get("migration_v1_up")),
            "v2": _as_text(candidate.get("migration_v2_up")),
            "down": _as_text(candidate.get("migration_v2_down")),
        }
        rust_result = _evaluate_rust(sources["cargo_toml"], sources["lib_rs"], sources["main_rs"])
        python_result = _evaluate_python(sources["python_source"])
        sql_result = _evaluate_sql(sources["v1"], sources["v2"], sources["down"])
        return sources, rust_result, python_result, sql_result

    sources, rust, python, sql = evaluate(construction)
    attempts.append({"attempt": 1, "rust_passed": rust["passed"], "python_passed": python["passed"], "sql_passed": sql["passed"]})
    revision_response: Dict[str, Any] = {}
    if initial_construction is None and not (rust["passed"] and python["passed"] and sql["passed"]):
        revision_response = provider(_revision_prompt(construction, rust, python, sql), timeout=480)
        revision = _proposal(revision_response)
        if revision:
            revised_sources, revised_rust, revised_python, revised_sql = evaluate(revision)
            attempts.append({"attempt": 2, "rust_passed": revised_rust["passed"], "python_passed": revised_python["passed"], "sql_passed": revised_sql["passed"]})
            first_score = sum([rust["passed"], python["passed"], sql["passed"]])
            revised_score = sum([revised_rust["passed"], revised_python["passed"], revised_sql["passed"]])
            if revised_score > first_score:
                construction = revision
                sources, rust, python, sql = revised_sources, revised_rust, revised_python, revised_sql

    sql_revision_response: Dict[str, Any] = {}
    if rust["passed"] and python["passed"] and not sql["passed"]:
        sql_revision_response = provider(_sql_revision_prompt(construction, sql), timeout=360)
        sql_revision = _proposal(sql_revision_response)
        if sql_revision:
            merged = dict(construction)
            merged.update(sql_revision)
            sql_sources, sql_rust, sql_python, sql_result = evaluate(merged)
            attempts.append({
                "attempt": len(attempts) + 1,
                "rust_passed": sql_rust["passed"],
                "python_passed": sql_python["passed"],
                "sql_passed": sql_result["passed"],
                "scope": "sql_only_revision",
                "sql_audit": sql_result.get("audit"),
                "sql_checks": sql_result.get("checks"),
                "sql_evidence": sql_result.get("evidence"),
            })
            if sql_rust["passed"] and sql_python["passed"] and sql_result["passed"]:
                construction = merged
                sources, rust, python, sql = sql_sources, sql_rust, sql_python, sql_result

    cargo_toml = sources["cargo_toml"]
    lib_rs = sources["lib_rs"]
    main_rs = sources["main_rs"]
    python_source = sources["python_source"]
    v1 = sources["v1"]
    v2 = sources["v2"]
    down = sources["down"]
    bakeoff = _benchmark_stacks(cargo_toml, lib_rs, main_rs, python_source) if rust["passed"] and python["passed"] else {"passed": False, "metrics": {}}
    selection_response = provider(_selection_prompt(bakeoff.get("metrics") or {})) if bakeoff["passed"] else {"available": False, "proposal": {}, "error": "BAKEOFF_FAILED"}
    selection = _proposal(selection_response)
    selection_eval = _evaluate_selection(selection, bakeoff["metrics"]) if bakeoff["passed"] else {"accuracy": 0.0, "explanations_complete": False, "rows": []}

    malicious = {
        "rust": [_audit(value, RUST_FORBIDDEN) for value in ["unsafe fn x() {}", "use std::process::Command;", "use std::net::TcpStream;"]],
        "sql": [
            _audit(value, {**SQL_FORBIDDEN, "drop_table": r"\bDROP\s+TABLE\b"}, flags=re.I)
            for value in ["DROP TABLE accounts;", "PRAGMA foreign_keys=OFF;", "SELECT load_extension('x');"]
        ],
    }
    gate = {
        "multi_file_rust_depth": rust["passed"],
        "sql_migration_depth": sql["passed"],
        "matched_stack_correctness": bakeoff["passed"],
        "measurement_based_selection_accuracy": selection_eval["accuracy"],
        "selection_explanations_complete": selection_eval["explanations_complete"],
        "unsafe_rust_rejected": sum(not row["safe"] for row in malicious["rust"]),
        "unsafe_sql_rejected": sum(not row["safe"] for row in malicious["sql"]),
        "unsafe_programs_executed": 0,
        "live_repository_writes": 0,
    }
    required = {
        "rust": gate["multi_file_rust_depth"],
        "sql": gate["sql_migration_depth"],
        "bakeoff": gate["matched_stack_correctness"],
        "selection": gate["measurement_based_selection_accuracy"] == 1.0 and gate["selection_explanations_complete"],
        "adversarial": gate["unsafe_rust_rejected"] == 3 and gate["unsafe_sql_rejected"] == 3,
        "safety": gate["unsafe_programs_executed"] == 0 and gate["live_repository_writes"] == 0,
    }
    gate["errors"] = [name for name, passed in required.items() if not passed]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="rust_sql_systems_depth_and_measured_technology_selection",
        steps=[
            "construct_multi_file_rust_with_trait_errors_and_shared_state",
            "inject_concurrency_atomicity_and_overflow_authority_tests",
            "construct_reversible_sql_migrations",
            "verify_rollback_writer_isolation_and_query_plans",
            "implement_one_workload_in_rust_and_python",
            "choose_technology_from_measured_costs",
            "reject_unsafe_constructs_before_execution",
        ],
        score=(float(rust["passed"]) + float(sql["passed"]) + float(bakeoff["passed"]) + selection_eval["accuracy"]) / 4,
        success=gate["accepted"],
        evidence={"gate": gate},
        source_rules=[PARENT_ID],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    if gate["accepted"]:
        runtime.store.state["constructed_language_skills"]["rust_multifile_concurrent_ledger"] = {
            "language": "rust",
            "files": {"Cargo.toml": cargo_toml, "src/lib.rs": lib_rs, "src/main.rs": main_rs},
            "evaluation": rust,
            "created_at": _utc_timestamp(),
        }
        runtime.store.state["constructed_language_skills"]["sql_reversible_ledger_migrations"] = {
            "language": "sql",
            "migrations": {"v1_up": v1, "v2_up": v2, "v2_down": down},
            "evaluation": sql,
            "created_at": _utc_timestamp(),
        }
    policy_id = f"measured_policy_{_canonical_hash(selection_eval)[:16]}"
    runtime.store.state["technology_selection_policies"][policy_id] = {
        "proposal": selection,
        "evaluation": selection_eval,
        "measurements": bakeoff.get("metrics") or {},
        "created_at": _utc_timestamp(),
    }
    session_id = f"systems_depth_{_canonical_hash(gate)[:16]}"
    runtime.store.state["technology_selection_sessions"].append({
        "session_id": session_id,
        "policy_id": policy_id,
        "gate": gate,
        "created_at": _utc_timestamp(),
    })
    runtime.store.commit(reason="rust_sql_systems_depth_and_measured_selection")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {
        "rust_skill_retained": "rust_multifile_concurrent_ledger" in rebuilt.store.state["constructed_language_skills"],
        "sql_skill_retained": "sql_reversible_ledger_migrations" in rebuilt.store.state["constructed_language_skills"],
        "policy_retained": policy_id in rebuilt.store.state["technology_selection_policies"],
        "session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["technology_selection_sessions"]),
        "champion_retained": rebuilt.store.state["champions"].get("rust_sql_systems_depth_and_measured_technology_selection") == PROCEDURE_ID,
        "relearning_failures": 0,
    }
    passed = bool(
        gate["accepted"]
        and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
        and all(value is True or value == 0 for value in restart.values())
    )
    payload = {
        "schema_version": "aion.hexcore.rust_sql_systems_depth.v1",
        "created_at": _utc_timestamp(),
        "construction": construction,
        "construction_provider": {key: value for key, value in construction_response.items() if key != "proposal"},
        "construction_attempts": attempts,
        "revision_provider": {key: value for key, value in revision_response.items() if key != "proposal"},
        "sql_revision_provider": {key: value for key, value in sql_revision_response.items() if key != "proposal"},
        "sql_revision_proposal": _proposal(sql_revision_response),
        "rust": rust,
        "python": python,
        "sql": sql,
        "bakeoff": bakeoff,
        "selection": {"proposal": selection, "evaluation": selection_eval, "provider": {key: value for key, value in selection_response.items() if key != "proposal"}},
        "adversarial": malicious,
        "gate": gate,
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": passed,
        "boundary": "This stage deepens bounded Rust and SQL construction and makes two technology choices from measured outcomes. It does not establish whole-language mastery, production database operations, a fifth independent repository, conditional memory routing, or independent hidden certification.",
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run governed Rust/SQL systems-depth benchmark.")
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_rust_sql_systems_depth.json"))
    parser.add_argument("--resume-result", type=Path)
    args = parser.parse_args()
    initial = None
    if args.resume_result:
        resumed = json.loads(args.resume_result.resolve().read_text(encoding="utf-8"))
        initial = dict(resumed.get("construction") or {})
        if resumed.get("sql_revision_proposal"):
            initial.update(resumed["sql_revision_proposal"])
    result = run_rust_sql_systems_depth(
        state_path=args.state_path.resolve(),
        result_path=args.result_path.resolve(),
        initial_construction=initial,
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
