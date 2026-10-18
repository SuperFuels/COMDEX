"""Progressive, model-free communication training for Aion.

Qwen may select or rephrase sealed questions before an examination begins.  It
is never called while the student reads, maintains dialogue state, reasons,
plans a response, realises English, checks evidence, or completes a delayed
retest.  The academy therefore measures the native discourse engine rather
than the teacher model.
"""
from __future__ import annotations

import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable, Mapping, Sequence

from backend.modules.aion_cognition.native_discourse_dialogue import (
    NativeDiscourseDialogueEngine,
    _normal,
)
from backend.modules.aion_cognition.sqlite_connection import (
    connect as sqlite_connect,
    connect_read_only as sqlite_read_connect,
)


STAGES: tuple[dict[str, Any], ...] = (
    {"id": "one_sentence", "title": "One-sentence answer", "turns": 1},
    {"id": "connected_explanation", "title": "Two connected sentences", "turns": 2},
    {"id": "short_paragraph", "title": "Short evidence paragraph", "turns": 3},
    {"id": "passage_discussion", "title": "Passage discussion", "turns": 4},
    {"id": "five_turn_dialogue", "title": "Five-turn conversation", "turns": 5},
    {"id": "ten_turn_dialogue", "title": "Ten-turn conversation", "turns": 10},
    {"id": "cross_subject_dialogue", "title": "Cross-subject conversation", "turns": 10},
    {"id": "delayed_dialogue_retest", "title": "Delayed conversation retest", "turns": 10},
)
RETENTION_DELAYS = (86400.0, 604800.0, 2592000.0)


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


class NativeCommunicationAcademy:
    """Advance Aion from isolated answers to retained multi-turn dialogue."""

    def __init__(self, *, repo_root: Path | str,
                 discourse: NativeDiscourseDialogueEngine | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.discourse = discourse or NativeDiscourseDialogueEngine(repo_root=self.repo_root)
        self.database_path = self.discourse.database_path
        self._initialize()

    def _connect(self):
        connection = sqlite_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _read_connect(self):
        connection = sqlite_read_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_communication_sessions(
                    academy_session_id TEXT PRIMARY KEY,
                    dialogue_session_id TEXT NOT NULL,
                    stage_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_family TEXT NOT NULL,
                    passage_signature TEXT NOT NULL,
                    passage TEXT NOT NULL,
                    target_turns INTEGER NOT NULL,
                    completed_turns INTEGER NOT NULL,
                    correct_turns INTEGER NOT NULL,
                    evidence_turns INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    teacher_model TEXT NOT NULL,
                    student_model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_communication_stage_result
                    ON native_communication_sessions(stage_id,passed,created_epoch DESC);
                CREATE INDEX IF NOT EXISTS native_communication_source_result
                    ON native_communication_sessions(source_family,source_id,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_communication_turns(
                    academy_turn_id TEXT PRIMARY KEY,
                    academy_session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    family TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL,
                    native_answer TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    proposition_count INTEGER NOT NULL,
                    evidence_json TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_communication_turn_session
                    ON native_communication_turns(academy_session_id,turn_index);
                CREATE TABLE IF NOT EXISTS native_communication_retests(
                    retest_id TEXT PRIMARY KEY,
                    academy_turn_id TEXT NOT NULL,
                    passage TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_family TEXT NOT NULL,
                    family TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL,
                    verified_explanation TEXT NOT NULL,
                    retention_stage INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    due_epoch REAL NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    cleared_epoch REAL,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_communication_retest_due
                    ON native_communication_retests(status,due_epoch);
                CREATE TABLE IF NOT EXISTS native_communication_meta(
                    key TEXT PRIMARY KEY,value TEXT NOT NULL
                );
                """
            )
            session_columns = {str(row[1]) for row in connection.execute(
                "PRAGMA table_info(native_communication_sessions)"
            ).fetchall()}
            if "validity_status" not in session_columns:
                connection.execute(
                    "ALTER TABLE native_communication_sessions ADD COLUMN validity_status TEXT NOT NULL DEFAULT 'valid'"
                )
            # Keep malformed historical teacher material for audit without
            # charging it to the student. These fragments pre-date the stricter
            # named-agent contract and were never valid English examinations.
            malformed = connection.execute(
                """SELECT DISTINCT s.academy_session_id,t.family,t.expected_answer
                   FROM native_communication_sessions s
                   JOIN native_communication_turns t USING(academy_session_id)
                   WHERE s.validity_status='valid'"""
            ).fetchall()
            for row in malformed:
                if (str(row["family"]) == "entity"
                        and not self.discourse._grounded_named_entity(row["expected_answer"])):
                    connection.execute(
                        "UPDATE native_communication_sessions SET validity_status='invalidated_teacher_contract' WHERE academy_session_id=?",
                        (row["academy_session_id"],),
                    )
                    connection.execute(
                        """UPDATE native_communication_retests
                           SET status='invalidated_contract'
                           WHERE academy_turn_id IN(
                             SELECT academy_turn_id FROM native_communication_turns
                             WHERE academy_session_id=?
                           )""",
                        (row["academy_session_id"],),
                    )
            # Earlier builds silently reduced a ten-turn stage to however many
            # contracts a short passage happened to provide.  Preserve those
            # receipts for audit, but do not call a three- or eight-turn
            # exchange a completed ten-turn conversation.
            required_turns = {str(stage["id"]): int(stage["turns"]) for stage in STAGES}
            sessions = connection.execute(
                """SELECT academy_session_id,stage_id,completed_turns
                   FROM native_communication_sessions WHERE validity_status='valid'"""
            ).fetchall()
            for row in sessions:
                required = required_turns.get(str(row["stage_id"]), 1)
                if int(row["completed_turns"] or 0) >= required:
                    continue
                connection.execute(
                    "UPDATE native_communication_sessions SET validity_status='invalidated_incomplete_stage' WHERE academy_session_id=?",
                    (row["academy_session_id"],),
                )
                connection.execute(
                    """UPDATE native_communication_retests
                       SET status='invalidated_incomplete_stage'
                       WHERE academy_turn_id IN(
                         SELECT academy_turn_id FROM native_communication_turns
                         WHERE academy_session_id=?
                       )""",
                    (row["academy_session_id"],),
                )
            # Contract quality audit v2: invalidate only sessions whose sealed
            # answer contract is demonstrably not connected prose or a complete
            # semantic role.  Their receipts remain for audit, but neither the
            # accuracy score nor correction queue may punish Aion for them.
            audit = connection.execute(
                "SELECT value FROM native_communication_meta WHERE key='contract_audit'"
            ).fetchone()
            if not audit or str(audit[0]) != "2":
                rows = connection.execute(
                    """SELECT s.academy_session_id,s.passage,t.family,t.expected_answer
                       FROM native_communication_sessions s
                       JOIN native_communication_turns t USING(academy_session_id)
                       WHERE s.validity_status='valid'"""
                ).fetchall()
                invalid_sessions = {
                    str(row["academy_session_id"])
                    for row in rows
                    if not self.discourse._exam_contract_valid(
                        str(row["passage"] or ""), str(row["family"] or ""),
                        str(row["expected_answer"] or ""),
                    )
                }
                for session_id in invalid_sessions:
                    connection.execute(
                        "UPDATE native_communication_sessions SET validity_status='invalidated_contract_quality' WHERE academy_session_id=?",
                        (session_id,),
                    )
                    connection.execute(
                        """UPDATE native_communication_retests
                           SET status='invalidated_contract_quality'
                           WHERE academy_turn_id IN(
                             SELECT academy_turn_id FROM native_communication_turns
                             WHERE academy_session_id=?
                           )""",
                        (session_id,),
                    )
                connection.execute(
                    "INSERT OR REPLACE INTO native_communication_meta(key,value) VALUES('contract_audit','2')"
                )

    def _stage(self) -> dict[str, Any]:
        """Choose the first level without two independent perfect sessions."""
        with self._read_connect() as connection:
            rows = connection.execute(
                """SELECT stage_id,COUNT(*) passes,COUNT(DISTINCT source_id) sources,
                          COUNT(DISTINCT passage_signature) passages,
                          COUNT(DISTINCT source_family) families
                   FROM native_communication_sessions
                   WHERE passed=1 AND validity_status='valid' GROUP BY stage_id"""
            ).fetchall()
        evidence = {str(row["stage_id"]): dict(row) for row in rows}
        for stage in STAGES:
            row = evidence.get(str(stage["id"]), {})
            passes = int(row.get("passes") or 0)
            sources = int(row.get("sources") or 0)
            passages = int(row.get("passages") or 0)
            families = int(row.get("families") or 0)
            required_families = 2 if stage["id"] in {
                "cross_subject_dialogue", "delayed_dialogue_retest",
            } else 1
            required_sources = 2 if required_families > 1 else 1
            if (passes < 2 or passages < 2 or sources < required_sources
                    or families < required_families):
                return {**stage, "passes": passes, "sources": sources,
                        "passages": passages, "source_families": families}
        last = STAGES[-1]
        return {**last, "passes": int(evidence.get(last["id"], {}).get("passes") or 0),
                "sources": int(evidence.get(last["id"], {}).get("sources") or 0),
                "passages": int(evidence.get(last["id"], {}).get("passages") or 0),
                "source_families": int(evidence.get(last["id"], {}).get("families") or 0)}

    @staticmethod
    def _teacher_prompt(stage: Mapping[str, Any],
                        contracts: Sequence[Mapping[str, Any]]) -> str:
        safe = [{key: row.get(key) for key in (
            "contract_key", "family", "question", "answer_reason",
        )} for row in contracts]
        return (
            "You are the teacher, not the student. Select varied SEALED dialogue "
            f"questions for stage {stage['id']}. You may rephrase a question but must "
            "not change its requested semantic role or include its answer. Return strict "
            "JSON as {\"turns\":[{\"contract_key\":\"...\",\"question\":\"...\"}]}. "
            "Prefer reference, cause, time, sequence and contradiction over simple names. "
            f"Contracts: {json.dumps(safe, ensure_ascii=False)}"
        )

    def _select_contracts(self, contracts: Sequence[Mapping[str, Any]], count: int,
                          teacher_client: Callable[[str], Mapping[str, Any]] | None,
                          stage: Mapping[str, Any]) -> tuple[str, list[dict[str, Any]], int]:
        by_key = {str(row["contract_key"]): dict(row) for row in contracts}
        teacher_model = "compiled-native-dialogue"
        proposals: list[Mapping[str, Any]] = []
        rejected = 0
        if teacher_client and contracts:
            try:
                payload = dict(teacher_client(self._teacher_prompt(stage, contracts)))
                teacher_model = str(payload.get("model") or "local-qwen")
                raw = re.sub(r"^```(?:json)?\s*|\s*```$", "",
                             str(payload.get("content") or "").strip(), flags=re.I | re.S)
                proposals = list(json.loads(raw).get("turns") or [])
            except Exception:
                proposals = []
        selected: list[dict[str, Any]] = []
        used: set[str] = set()
        family_counts: dict[str, int] = {}
        family_cap = 2
        for proposal in proposals:
            contract = by_key.get(str(proposal.get("contract_key") or ""))
            if not contract or contract["contract_key"] in used:
                rejected += 1
                continue
            family = str(contract["family"])
            if family_counts.get(family, 0) >= family_cap:
                rejected += 1
                continue
            question = " ".join(str(proposal.get("question") or contract["question"]).split())
            if not question or _normal(str(contract["expected_answer"])) in _normal(question):
                rejected += 1
                question = str(contract["question"])
            selected.append({**contract, "question": question})
            used.add(str(contract["contract_key"]))
            family_counts[family] = family_counts.get(family, 0) + 1
            if len(selected) >= count:
                break
        priority = {"coreference": 0, "cause": 1, "time": 2, "sequence_first": 3,
                    "sequence_next": 4, "contradiction": 5, "object": 6,
                    "location": 7, "action": 8, "entity": 9}
        for contract in sorted(contracts, key=lambda row: priority.get(str(row["family"]), 99)):
            if str(contract["contract_key"]) in used:
                continue
            family = str(contract["family"])
            if family_counts.get(family, 0) >= family_cap:
                continue
            selected.append(dict(contract))
            used.add(str(contract["contract_key"]))
            family_counts[family] = family_counts.get(family, 0) + 1
            if len(selected) >= count:
                break
        return teacher_model, selected, rejected

    @staticmethod
    def _connected_response(plan: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]],
                            stage_id: str) -> str:
        """Realise a bounded response from propositions and cited evidence."""
        answer = str(plan.get("answer") or "").strip()
        if not answer:
            return answer
        if stage_id == "one_sentence" or not evidence:
            return answer
        citation = " ".join(str(evidence[0].get("text") or "").strip().split())
        support = f"The passage supports this with the statement: {citation}"
        if stage_id == "connected_explanation":
            return f"{answer} {support}."
        return f"{answer} {support}. Therefore, the answer follows from the represented events rather than an unsupported guess."

    def _run_due_retests(self, limit: int) -> list[dict[str, Any]]:
        now = time.time()
        with self._read_connect() as connection:
            rows = connection.execute(
                """SELECT * FROM native_communication_retests
                   WHERE status='due' AND due_epoch<=? ORDER BY due_epoch LIMIT ?""",
                (now, max(1, limit)),
            ).fetchall()
        outcomes: list[dict[str, Any]] = []
        model_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
        for raw in rows:
            row = dict(raw)
            model_key = (str(row["source_id"]), str(row["source_family"]),
                         hashlib.sha256(_normal(str(row["passage"])).encode()).hexdigest())
            model = model_cache.get(model_key)
            if model is None:
                model = self.discourse.build_situation_model(
                    row["passage"], session_id="communication-retention",
                    source_id=row["source_id"], source_family=row["source_family"], persist=False,
                )
                model_cache[model_key] = model
            plan = self.discourse._plan(model, row["question"], forced_intent=row["family"])
            correct = self.discourse._meaning_match(plan["answer"], row["expected_answer"])
            stage = int(row["retention_stage"])
            with self._connect() as connection:
                if correct and stage + 1 < len(RETENTION_DELAYS):
                    connection.execute(
                        "UPDATE native_communication_retests SET retention_stage=?,due_epoch=?,attempts=attempts+1 WHERE retest_id=?",
                        (stage + 1, now + RETENTION_DELAYS[stage + 1], row["retest_id"]),
                    )
                elif correct:
                    connection.execute(
                        "UPDATE native_communication_retests SET status='cleared',attempts=attempts+1,cleared_epoch=? WHERE retest_id=?",
                        (now, row["retest_id"]),
                    )
                else:
                    connection.execute(
                        "UPDATE native_communication_retests SET attempts=attempts+1,due_epoch=? WHERE retest_id=?",
                        (now + 86400.0, row["retest_id"]),
                    )
            outcomes.append({"retest_id": row["retest_id"], "correct": correct,
                             "retention_stage": stage, "model_used": False})
        return outcomes

    def run_cycle(self, *, teacher_client: Callable[[str], Mapping[str, Any]] | None = None,
                  limit: int = 1) -> dict[str, Any]:
        requested = max(1, min(4, int(limit)))
        # Corrections have priority over generating more work.  A larger native
        # batch drains old obligations quickly without involving Qwen.
        retests = self._run_due_retests(max(32, requested * 12))
        stage = self._stage()
        with self._read_connect() as connection:
            due_after_retests = int(connection.execute(
                "SELECT COUNT(*) FROM native_communication_retests WHERE status='due' AND due_epoch<=?",
                (time.time(),),
            ).fetchone()[0])
        if due_after_retests > 100:
            return {"status": "draining_verified_corrections", "attempted": 0,
                    "stage": stage, "retests": retests,
                    "retests_due_remaining": due_after_retests,
                    "qwen_used_for_student_answers": False, "model_used": False}
        passages = self.discourse._reading_passages(requested * 12)
        if not passages:
            return {"status": "awaiting_connected_reading_passages", "attempted": 0,
                    "stage": stage, "retests": retests,
                    "qwen_used_for_student_answers": False, "model_used": False}
        if int(stage["turns"]) > 5:
            # A three-sentence reading window rarely carries ten independent
            # semantic roles. Join two unseen windows before compiling the
            # contracts; the student receives one larger situation model, not
            # repeated questions padded to imitate a ten-turn conversation.
            combined: list[dict[str, Any]] = []
            cross_subject = stage["id"] in {
                "cross_subject_dialogue", "delayed_dialogue_retest",
            }
            group_size = 3 if cross_subject else 2
            for group in combinations(passages, group_size):
                normalized = {_normal(str(row["passage"])) for row in group}
                if len(normalized) != group_size:
                    continue
                families = {str(row["source_family"]) for row in group}
                if cross_subject and len(families) != group_size:
                    continue
                combined.append({
                    "source_key": f"combined-{len(combined) + 1}",
                    "source_id": "+".join(str(row["source_id"]) for row in group),
                    "title": " + ".join(str(row["title"]) for row in group),
                    "source_family": "+".join(str(row["source_family"]) for row in group),
                    "passage": " ".join(str(row["passage"]) for row in group),
                })
                if len(combined) >= requested * 8:
                    break
            passages = combined
            if not passages:
                return {"status": "awaiting_cross_passage_dialogue_material", "attempted": 0,
                        "stage": stage, "retests": retests,
                        "qwen_used_for_student_answers": False, "model_used": False}
        with self._read_connect() as connection:
            prior = connection.execute(
                "SELECT source_id,passage_signature FROM native_communication_sessions WHERE stage_id=? AND validity_status='valid'",
                (stage["id"],),
            ).fetchall()
        prior_sources = {str(row["source_id"]) for row in prior}
        prior_passages = {str(row["passage_signature"]) for row in prior}
        passages.sort(key=lambda row: (
            str(row["source_id"]) in prior_sources,
            hashlib.sha256(_normal(str(row["passage"])).encode()).hexdigest() in prior_passages,
        ))
        # Reusing an identical passage can create impressive-looking volume
        # without transfer.  Wait for fresh reading material instead.
        passages = [
            row for row in passages
            if hashlib.sha256(_normal(str(row["passage"])).encode()).hexdigest()
            not in prior_passages
        ]
        results: list[dict[str, Any]] = []
        for source in passages:
            if len(results) >= requested:
                break
            contracts = self.discourse._contract_candidates([source])
            target_turns = int(stage["turns"])
            if len(contracts) < target_turns:
                continue
            teacher_model, selected, rejected = self._select_contracts(
                contracts, target_turns, teacher_client, stage,
            )
            if len(selected) < target_turns:
                continue
            now = time.time()
            signature = hashlib.sha256(_normal(source["passage"]).encode()).hexdigest()
            academy_session_id = _identifier(
                "native_communication_session_",
                [stage["id"], source["source_key"], now],
            )
            dialogue_session_id = academy_session_id + "_dialogue"
            model = self.discourse.build_situation_model(
                str(source["passage"]), session_id=dialogue_session_id,
                source_id=str(source["source_id"]),
                source_family=str(source["source_family"]), persist=True,
            )
            turns: list[dict[str, Any]] = []
            remedies_created = 0
            remedy_families: set[str] = set()
            for index, contract in enumerate(selected[:target_turns]):
                # The complete answer key remains outside the student call.
                plan = self.discourse._plan(
                    model, str(contract["question"]), forced_intent=str(contract["family"]),
                )
                correct = self.discourse._meaning_match(
                    str(plan["answer"]), str(contract["expected_answer"]),
                )
                evidence = list(plan.get("evidence") or [])
                checks = {
                    "evidence_supported": bool(evidence),
                    "unsupported_claims": not bool(evidence),
                    "answer_key_withheld_until_after_response": True,
                    "model_or_cloud_route_present": False,
                }
                response = self._connected_response(plan, evidence, str(stage["id"]))
                academy_turn_id = _identifier(
                    "native_communication_turn_", [academy_session_id, index],
                )
                with self._connect() as connection:
                    connection.execute(
                        """INSERT INTO native_communication_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (academy_turn_id, academy_session_id, index, contract["family"],
                         contract["question"], contract["expected_answer"], plan["answer"],
                         int(correct), plan["status"], plan["confidence"],
                         len(plan.get("propositions") or []), json.dumps(evidence),
                         json.dumps(checks), response, now + index / 1000.0),
                    )
                    family = str(contract["family"])
                    if (not correct and remedies_created < 4
                            and family not in remedy_families):
                        retest_id = _identifier(
                            "native_communication_retest_", [academy_turn_id, "correction"],
                        )
                        connection.execute(
                            """INSERT OR IGNORE INTO native_communication_retests
                               VALUES(?,?,?,?,?,?,?,?,?,0,'due',?,0,NULL,?)""",
                            (retest_id, academy_turn_id, source["passage"], source["source_id"],
                             source["source_family"], contract["family"], contract["question"],
                             contract["expected_answer"], contract["answer_reason"],
                             now + 900.0, now),
                        )
                        remedies_created += 1
                        remedy_families.add(family)
                turns.append({"family": contract["family"], "correct": correct,
                              "answer": plan["answer"], "response": response,
                              "evidence_supported": bool(evidence), "confidence": plan["confidence"]})
            correct_turns = sum(bool(row["correct"]) for row in turns)
            evidence_turns = sum(bool(row["evidence_supported"]) for row in turns)
            passed = (len(turns) == target_turns and correct_turns == target_turns
                      and evidence_turns == target_turns)
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO native_communication_sessions(
                       academy_session_id,dialogue_session_id,stage_id,source_id,source_family,
                       passage_signature,passage,target_turns,completed_turns,correct_turns,
                       evidence_turns,passed,teacher_model,student_model_used,created_epoch,
                       validity_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'valid')""",
                    (academy_session_id, dialogue_session_id, stage["id"], source["source_id"],
                     source["source_family"], signature, source["passage"], target_turns,
                     len(turns), correct_turns, evidence_turns, int(passed), teacher_model,
                     0, now),
                )
                if passed:
                    for row in connection.execute(
                        "SELECT * FROM native_communication_turns WHERE academy_session_id=?",
                        (academy_session_id,),
                    ).fetchall():
                        retest_id = _identifier(
                            "native_communication_retest_", [row["academy_turn_id"], "retention"],
                        )
                        connection.execute(
                            """INSERT OR IGNORE INTO native_communication_retests
                               VALUES(?,?,?,?,?,?,?,?,?,0,'due',?,0,NULL,?)""",
                            (retest_id, row["academy_turn_id"], source["passage"], source["source_id"],
                             source["source_family"], row["family"], row["question"],
                             row["expected_answer"], "Reproduce the supported meaning after delay.",
                             now + RETENTION_DELAYS[0], now),
                        )
            results.append({"academy_session_id": academy_session_id,
                            "stage_id": stage["id"], "turns": len(turns),
                            "correct": correct_turns, "evidence_supported": evidence_turns,
                            "passed": passed, "source": source.get("title"),
                            "source_family": source["source_family"], "teacher_model": teacher_model,
                            "teacher_drafts_rejected": rejected, "student_model_used": False,
                            "answers_sealed": True})
        return {"status": "completed" if results else "awaiting_eligible_dialogue_passage",
                "attempted": len(results), "passed": sum(bool(row["passed"]) for row in results),
                "stage": stage, "results": results, "retests": retests,
                "qwen_used_for_student_answers": False, "model_used": False,
                "next_token_prediction": False}

    def metrics(self) -> dict[str, Any]:
        now = time.time()
        with self._read_connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) attempts,COALESCE(SUM(passed),0) passed,COALESCE(SUM(completed_turns),0) turns,COALESCE(SUM(correct_turns),0) correct FROM native_communication_sessions WHERE validity_status='valid'"
            ).fetchone()
            recent = connection.execute(
                "SELECT COUNT(*) attempts,COALESCE(SUM(passed),0) passed,COALESCE(SUM(completed_turns),0) turns,COALESCE(SUM(correct_turns),0) correct FROM native_communication_sessions WHERE validity_status='valid' AND created_epoch>?",
                (now - 3600.0,),
            ).fetchone()
            stages = connection.execute(
                "SELECT stage_id,COUNT(*) attempts,SUM(passed) passed,SUM(completed_turns) turns,SUM(correct_turns) correct,COUNT(DISTINCT source_id) sources,COUNT(DISTINCT source_family) families FROM native_communication_sessions WHERE validity_status='valid' GROUP BY stage_id"
            ).fetchall()
            due = connection.execute(
                "SELECT COUNT(*) FROM native_communication_retests WHERE status='due' AND due_epoch<=?",
                (now,),
            ).fetchone()[0]
            pending = connection.execute(
                "SELECT COUNT(*) FROM native_communication_retests WHERE status='due'",
            ).fetchone()[0]
            cleared = connection.execute(
                "SELECT COUNT(*) FROM native_communication_retests WHERE status='cleared'",
            ).fetchone()[0]
            invalidated = connection.execute(
                "SELECT COUNT(*) FROM native_communication_sessions WHERE validity_status!='valid'",
            ).fetchone()[0]
        turns = int(total["turns"] or 0)
        recent_turns = int(recent["turns"] or 0)
        return {
            "current_stage": self._stage(), "sessions": int(total["attempts"] or 0),
            "sessions_passed": int(total["passed"] or 0), "dialogue_turns": turns,
            "turn_accuracy": round(int(total["correct"] or 0) / turns, 4) if turns else None,
            "sessions_last_hour": int(recent["attempts"] or 0),
            "turns_last_hour": recent_turns,
            "recent_turn_accuracy": round(int(recent["correct"] or 0) / recent_turns, 4)
            if recent_turns else None,
            "retests_due": int(due), "retests_pending": int(pending),
            "retests_cleared": int(cleared),
            "invalid_teacher_contracts": int(invalidated),
            "stages": {str(row["stage_id"]): {
                "attempts": int(row["attempts"]), "passed": int(row["passed"] or 0),
                "turns": int(row["turns"] or 0), "correct": int(row["correct"] or 0),
                "sources": int(row["sources"] or 0), "source_families": int(row["families"] or 0),
            } for row in stages},
            "student_model_used": False, "qwen_role": "sealed_teacher_only",
            "claim_boundary": (
                "Graduation requires complete evidence-backed conversations from distinct passages; "
                "advanced stages additionally require different source subjects. Practice or teacher "
                "output alone never counts."
            ),
        }


__all__ = ["NativeCommunicationAcademy", "STAGES"]
