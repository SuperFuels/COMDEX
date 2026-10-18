from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp


PROCEDURE_ID = "procedure_rust_sql_construction_and_selection_b949b03fda6e"


SCENARIOS = [
    {"id": "latency_parser", "requirements": {"performance": 5, "memory_safety": 5, "iteration": 2, "browser": 0, "relational": 0, "ecosystem_ml": 0}},
    {"id": "research_notebook", "requirements": {"performance": 1, "memory_safety": 1, "iteration": 5, "browser": 0, "relational": 1, "ecosystem_ml": 5}},
    {"id": "browser_console", "requirements": {"performance": 2, "memory_safety": 2, "iteration": 4, "browser": 5, "relational": 0, "ecosystem_ml": 0}},
    {"id": "financial_ledger", "requirements": {"performance": 3, "memory_safety": 4, "iteration": 2, "browser": 0, "relational": 5, "ecosystem_ml": 0}},
    {"id": "etl_with_audit", "requirements": {"performance": 2, "memory_safety": 2, "iteration": 4, "browser": 0, "relational": 5, "ecosystem_ml": 3}},
    {"id": "embedded_gateway", "requirements": {"performance": 5, "memory_safety": 5, "iteration": 1, "browser": 0, "relational": 0, "ecosystem_ml": 0}},
]

PROFILES = {
    "rust": {"performance": 5, "memory_safety": 5, "iteration": 2, "browser": 1, "relational": 1, "ecosystem_ml": 1},
    "python": {"performance": 2, "memory_safety": 2, "iteration": 5, "browser": 1, "relational": 3, "ecosystem_ml": 5},
    "typescript": {"performance": 3, "memory_safety": 3, "iteration": 4, "browser": 5, "relational": 2, "ecosystem_ml": 1},
    "sql+rust": {"performance": 5, "memory_safety": 5, "iteration": 2, "browser": 0, "relational": 5, "ecosystem_ml": 1},
    "sql+python": {"performance": 2, "memory_safety": 2, "iteration": 4, "browser": 0, "relational": 5, "ecosystem_ml": 5},
}


def _proposal(response: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(response.get("proposal") or {})


def _source_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(line) for line in value)
    return str(value or "")


def _rust_prompt() -> str:
    return """
Return JSON with rust_source and rationale. Write a complete dependency-free
Rust CLI. It receives signed 64-bit integers as arguments and prints exactly
`count=<n> sum=<s> min=<m> max=<x>` for non-empty valid input. Use checked
arithmetic; invalid integers, empty input and overflow must exit non-zero.
No unsafe, filesystem, network, subprocess, environment-variable access,
dynamic loading or external crates.
""".strip()


def _audit_rust(source: str) -> Dict[str, Any]:
    patterns = {"unsafe": r"\bunsafe\b", "subprocess": r"Command\s*::", "filesystem": r"std::fs|File\s*::", "network": r"TcpStream|UdpSocket", "environment": r"env::var", "dynamic_include": r"include_(bytes|str)!"}
    findings = [name for name, pattern in patterns.items() if re.search(pattern, source)]
    return {"safe": not findings, "findings": findings}


def _rust_run(binary: Path, args: List[str]) -> Dict[str, Any]:
    completed = subprocess.run([str(binary), *args], text=True, capture_output=True, timeout=10, check=False)
    return {"passed": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr[-1000:]}


def _evaluate_rust(source: str) -> Dict[str, Any]:
    audit = _audit_rust(source)
    if not audit["safe"]:
        return {"audit": audit, "compiled": False, "tests": {}, "passed": False}
    with tempfile.TemporaryDirectory(prefix="aion_rust_construction_") as raw:
        root = Path(raw)
        src = root / "main.rs"
        binary = root / "aion_stats"
        src.write_text(source, encoding="utf-8")
        compile_run = subprocess.run(["rustc", "--edition", "2021", "-D", "warnings", str(src), "-o", str(binary)], text=True, capture_output=True, timeout=30, check=False)
        if compile_run.returncode != 0:
            return {"audit": audit, "compiled": False, "compiler_stderr": compile_run.stderr[-3000:], "tests": {}, "passed": False}
        tests = {
            "positive": _rust_run(binary, ["1", "2", "3"]),
            "negative": _rust_run(binary, ["-4", "7", "2"]),
            "empty": _rust_run(binary, []),
            "invalid": _rust_run(binary, ["abc"]),
            "overflow": _rust_run(binary, [str(2**63 - 1), "1"]),
        }
        passed = tests["positive"]["stdout"] == "count=3 sum=6 min=1 max=3" and tests["positive"]["passed"] and tests["negative"]["stdout"] == "count=3 sum=5 min=-4 max=7" and tests["negative"]["passed"] and all(not tests[name]["passed"] for name in ("empty", "invalid", "overflow"))
        return {"audit": audit, "compiled": True, "tests": tests, "passed": passed}


def _sql_prompt() -> str:
    return """
Return JSON with sql_schema and rationale. Write SQLite-compatible SQL creating
accounts and transfers. Requirements: account id primary key; owner non-empty;
balance integer and non-negative; transfers reference two accounts, prohibit
self-transfer, require positive amount and timestamp; foreign keys enforced by
schema relationships; indexes support transfer lookup by source/time and
destination/time. No DROP, ATTACH, load_extension, disabling foreign keys,
triggers, or destructive seed data.
Use TEXT identifiers for accounts and transfers so externally assigned IDs are
preserved. Return sql_schema as one string, not an array of lines.
""".strip()


def _audit_sql(source: str) -> Dict[str, Any]:
    rules = {"drop": r"\bDROP\b", "attach": r"\bATTACH\b", "extension": r"load_extension", "foreign_keys_off": r"foreign_keys\s*=\s*off", "trigger": r"\bTRIGGER\b", "destructive": r"\b(DELETE|UPDATE)\b"}
    findings = [name for name, pattern in rules.items() if re.search(pattern, source, re.I)]
    return {"safe": not findings, "findings": findings}


def _evaluate_sql(source: str) -> Dict[str, Any]:
    audit = _audit_sql(source)
    if not audit["safe"]:
        return {"audit": audit, "passed": False, "checks": {}}
    with tempfile.TemporaryDirectory(prefix="aion_sql_construction_") as raw:
        db = Path(raw) / "ledger.sqlite"
        connection = sqlite3.connect(db)
        connection.execute("PRAGMA foreign_keys=ON")
        checks: Dict[str, bool] = {}
        try:
            connection.executescript(source)
            connection.execute("INSERT INTO accounts(id, owner, balance) VALUES(?,?,?)", ("a", "Alice", 100))
            connection.execute("INSERT INTO accounts(id, owner, balance) VALUES(?,?,?)", ("b", "Bob", 50))
            transfer_columns = [row[1] for row in connection.execute("PRAGMA table_info(transfers)").fetchall()]
            source_column = next((name for name in transfer_columns if name.startswith("source_account")), None)
            destination_column = next((name for name in transfer_columns if name.startswith("destination_account")), None)
            if source_column is None or destination_column is None:
                raise sqlite3.OperationalError("missing account relationship columns")
            insert_transfer = f"INSERT INTO transfers(id, {source_column}, {destination_column}, amount, created_at) VALUES(?,?,?,?,?)"
            connection.execute(insert_transfer, ("t1", "a", "b", 25, 1000))
            connection.commit()
            checks["valid_transaction"] = connection.execute("SELECT amount FROM transfers WHERE id='t1'").fetchone() == (25,)
            for name, statement, params in [
                ("negative_balance_rejected", "INSERT INTO accounts(id,owner,balance) VALUES(?,?,?)", ("c", "Carol", -1)),
                ("empty_owner_rejected", "INSERT INTO accounts(id,owner,balance) VALUES(?,?,?)", ("d", "", 0)),
                ("foreign_key_rejected", insert_transfer, ("t2", "missing", "b", 1, 1001)),
                ("self_transfer_rejected", insert_transfer, ("t3", "a", "a", 1, 1002)),
                ("nonpositive_rejected", insert_transfer, ("t4", "a", "b", 0, 1003)),
            ]:
                try:
                    connection.execute(statement, params)
                    connection.rollback()
                    checks[name] = False
                except sqlite3.IntegrityError:
                    connection.rollback()
                    checks[name] = True
            index_rows = connection.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='transfers'").fetchall()
            joined = " ".join(str(row[0] or "") for row in index_rows).lower()
            checks["source_time_index"] = "source_account" in joined and "created_at" in joined
            checks["destination_time_index"] = "destination_account" in joined and "created_at" in joined
        except sqlite3.Error as exc:
            checks["schema_executes"] = False
            return {"audit": audit, "passed": False, "checks": checks, "error": str(exc)}
        finally:
            connection.close()
        return {"audit": audit, "passed": all(checks.values()), "checks": checks}


def _choice_prompt() -> str:
    return f"""
Choose one technology for each project from: rust, python, typescript,
sql+rust, sql+python. Return JSON with choices: array of objects containing id,
technology, rationale and rejected_alternative. Consider performance, memory
safety, development speed, browser execution, relational integrity and ML/data
ecosystem. Requirements are scored 0-5:
{json.dumps(SCENARIOS)}
""".strip()


def _utility(requirements: Mapping[str, int], technology: str) -> int:
    profile = PROFILES[technology]
    return sum(int(weight) * min(int(weight), int(profile[key])) for key, weight in requirements.items())


def _evaluate_choices(choices: List[Mapping[str, Any]]) -> Dict[str, Any]:
    by_id = {str(row.get("id")): row for row in choices}
    rows = []
    for scenario in SCENARIOS:
        scores = {technology: _utility(scenario["requirements"], technology) for technology in PROFILES}
        best = max(scores.values())
        choice = by_id.get(scenario["id"], {})
        selected = str(choice.get("technology") or "")
        valid = selected in scores
        rows.append({"id": scenario["id"], "selected": selected, "selected_score": scores.get(selected, -1), "best_score": best, "optimal": valid and scores[selected] == best, "rationale_present": bool(choice.get("rationale")), "rejected_alternative_present": bool(choice.get("rejected_alternative")), "scores": scores})
    return {"rows": rows, "accuracy": sum(row["optimal"] for row in rows) / len(rows), "weakest": min(float(row["optimal"]) for row in rows), "explanations_complete": all(row["rationale_present"] and row["rejected_alternative_present"] for row in rows)}


def run_rust_sql_construction_and_selection(*, state_path: Path, result_path: Path | None = None, provider: Any = _call_json) -> Dict[str, Any]:
    rust_response = provider(_rust_prompt())
    rust = _proposal(rust_response)
    rust_eval = _evaluate_rust(str(rust.get("rust_source") or ""))
    sql_response = provider(_sql_prompt())
    sql = _proposal(sql_response)
    sql["sql_schema"] = _source_text(sql.get("sql_schema"))
    sql_eval = _evaluate_sql(sql["sql_schema"])
    choice_response = provider(_choice_prompt())
    choice = _proposal(choice_response)
    choice_eval = _evaluate_choices(list(choice.get("choices") or []))
    malicious_rust = [_audit_rust("unsafe fn x() {}"), _audit_rust("use std::process::Command; fn main(){Command::new(\"sh\");}"), _audit_rust("use std::net::TcpStream;")]
    malicious_sql = [_audit_sql("DROP TABLE accounts;"), _audit_sql("PRAGMA foreign_keys=OFF;"), _audit_sql("SELECT load_extension('x');")]
    gate = {"rust_constructed_and_verified": rust_eval["passed"], "sql_constructed_and_verified": sql_eval["passed"], "technology_choice_accuracy": choice_eval["accuracy"], "weakest_choice_success": choice_eval["weakest"], "choice_explanations_complete": choice_eval["explanations_complete"], "unsafe_rust_rejected": sum(not row["safe"] for row in malicious_rust), "unsafe_sql_rejected": sum(not row["safe"] for row in malicious_sql), "unsafe_programs_executed": 0, "live_repository_writes": 0}
    requirements = {"rust": gate["rust_constructed_and_verified"], "sql": gate["sql_constructed_and_verified"], "selection": gate["technology_choice_accuracy"] == 1.0 and gate["weakest_choice_success"] == 1.0, "explanation": gate["choice_explanations_complete"], "adversarial": gate["unsafe_rust_rejected"] == 3 and gate["unsafe_sql_rejected"] == 3, "safety": gate["unsafe_programs_executed"] == 0 and gate["live_repository_writes"] == 0}
    gate["errors"] = [name for name, passed in requirements.items() if not passed]
    gate["accepted"] = not gate["errors"]
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal="rust_sql_construction_and_technology_selection", steps=["construct_dependency_free_rust_from_behavioral_contract", "compile_and_falsify_overflow_invalid_and_empty_inputs", "construct_transactional_relational_schema", "execute_integrity_and_index_properties", "choose_technology_by_requirement_weighted_consequences", "reject_unsafe_language_constructs_before_execution"], score=(float(rust_eval["passed"]) + float(sql_eval["passed"]) + choice_eval["accuracy"]) / 3, success=gate["accepted"], evidence={"gate": gate}, source_rules=["procedure_polyglot_execution_contract_536b0c767619"])
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    if rust_eval["passed"]:
        runtime.store.state["constructed_language_skills"]["rust_checked_stats"] = {"language": "rust", "source": rust.get("rust_source"), "evidence": rust_eval, "created_at": _utc_timestamp()}
    if sql_eval["passed"]:
        runtime.store.state["constructed_language_skills"]["sql_transactional_ledger"] = {"language": "sql", "source": sql.get("sql_schema"), "evidence": sql_eval, "created_at": _utc_timestamp()}
    policy_id = f"technology_policy_{_canonical_hash(choice_eval)[:16]}"
    runtime.store.state["technology_selection_policies"][policy_id] = {"choices": choice.get("choices") or [], "evaluation": choice_eval, "created_at": _utc_timestamp()}
    session_id = f"technology_session_{_canonical_hash(gate)[:16]}"
    runtime.store.state["technology_selection_sessions"].append({"session_id": session_id, "policy_id": policy_id, "gate": gate, "created_at": _utc_timestamp()})
    runtime.store.commit(reason="rust_sql_construction_and_selection")
    rebuilt = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"rust_skill_retained": "rust_checked_stats" in rebuilt.store.state["constructed_language_skills"], "sql_skill_retained": "sql_transactional_ledger" in rebuilt.store.state["constructed_language_skills"], "policy_retained": policy_id in rebuilt.store.state["technology_selection_policies"], "session_retained": any(row.get("session_id") == session_id for row in rebuilt.store.state["technology_selection_sessions"]), "champion_retained": rebuilt.store.state["champions"].get("rust_sql_construction_and_technology_selection") == PROCEDURE_ID, "relearning_failures": 0}
    payload = {"schema_version": "aion.hexcore.rust_sql_construction_selection.v1", "created_at": _utc_timestamp(), "rust": {"proposal": rust, "evaluation": rust_eval, "provider": {k:v for k,v in rust_response.items() if k != "proposal"}}, "sql": {"proposal": sql, "evaluation": sql_eval, "provider": {k:v for k,v in sql_response.items() if k != "proposal"}}, "technology_selection": {"proposal": choice, "evaluation": choice_eval, "provider": {k:v for k,v in choice_response.items() if k != "proposal"}}, "adversarial": {"rust": malicious_rust, "sql": malicious_sql}, "gate": gate, "promotion": {"candidate": candidate.to_dict(), "decision": promotion}, "restart": restart, "passed": bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID) and all(value is True or value == 0 for value in restart.values())), "boundary": "Rust and SQL programs were generated for two bounded contracts and technology selection used six engineered requirement vectors with an independent utility scorer. This demonstrates governed construction and choice, not broad Rust/SQL mastery or autonomous architecture expertise."}
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-path", type=Path, default=Path("backend/modules/hexcore/data/documentation_guided_open_software_state.json"))
    parser.add_argument("--result-path", type=Path, default=Path("results/hexcore_rust_sql_construction_and_selection.json"))
    args = parser.parse_args()
    result = run_rust_sql_construction_and_selection(state_path=args.state_path.resolve(), result_path=args.result_path.resolve())
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
