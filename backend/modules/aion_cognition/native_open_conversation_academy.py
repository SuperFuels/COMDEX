"""Source-disjoint twenty-turn examinations for AION native conversation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable, Mapping, Sequence

from backend.modules.aion_cognition.native_conversation_runtime import NativeConversationRuntime
from backend.modules.aion_cognition.native_discourse_dialogue import (
    NativeDiscourseDialogueEngine,
    WORD_RE,
    _normal,
    _sentences,
)
from backend.modules.aion_cognition.sqlite_connection import (
    connect as sqlite_connect,
    connect_read_only as sqlite_read_connect,
)


TARGET_TURNS = 20
RETENTION_DELAYS = (86400.0, 604800.0, 2592000.0)
_SOURCE_ANALYSIS_CACHE: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


class NativeOpenConversationAcademy:
    """Examine persistent native dialogue while the teacher is disconnected."""

    def __init__(self, *, repo_root: Path | str,
                 runtime: NativeConversationRuntime | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runtime = runtime or NativeConversationRuntime(repo_root=self.repo_root)
        self.discourse: NativeDiscourseDialogueEngine = self.runtime.discourse
        self.database_path = self.runtime.database_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _read_connect(self) -> sqlite3.Connection:
        connection = sqlite_read_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_open_conversation_exams(
                    exam_id TEXT PRIMARY KEY,
                    runtime_session_id TEXT NOT NULL,
                    passage_signature TEXT NOT NULL,
                    source_ids_json TEXT NOT NULL,
                    source_families_json TEXT NOT NULL,
                    target_turns INTEGER NOT NULL,
                    completed_turns INTEGER NOT NULL,
                    correct_turns INTEGER NOT NULL,
                    evidence_turns INTEGER NOT NULL,
                    clarification_correct INTEGER NOT NULL,
                    unsupported_claims INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    teacher_model TEXT NOT NULL,
                    student_model_used INTEGER NOT NULL DEFAULT 0,
                    validity_status TEXT NOT NULL DEFAULT 'valid',
                    created_epoch REAL NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS native_open_conversation_unique
                    ON native_open_conversation_exams(passage_signature,validity_status);
                CREATE TABLE IF NOT EXISTS native_open_conversation_turns(
                    academy_turn_id TEXT PRIMARY KEY,
                    exam_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    contract_key TEXT NOT NULL,
                    family TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL,
                    native_answer TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    evidence_supported INTEGER NOT NULL,
                    unsupported_claims INTEGER NOT NULL,
                    ambiguity_json TEXT NOT NULL,
                    runtime_turn_id TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_open_conversation_turn_exam
                    ON native_open_conversation_turns(exam_id,turn_index);
                CREATE TABLE IF NOT EXISTS native_open_conversation_retests(
                    retest_id TEXT PRIMARY KEY,
                    academy_turn_id TEXT NOT NULL,
                    context TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL,
                    family TEXT NOT NULL,
                    retention_stage INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    due_epoch REAL NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    cleared_epoch REAL
                );
                CREATE INDEX IF NOT EXISTS native_open_conversation_retest_due
                    ON native_open_conversation_retests(status,due_epoch);
                """
            )
            # Every valid twenty-turn exam receives delayed closed-book checks,
            # including initially correct turns. Earlier versions scheduled
            # only failures, which could prove correction but not retention.
            rows = connection.execute(
                """SELECT t.academy_turn_id,t.question,t.expected_answer,t.family,
                          t.created_epoch,s.active_passage
                   FROM native_open_conversation_turns t
                   JOIN native_open_conversation_exams e USING(exam_id)
                   JOIN native_conversation_sessions s
                     ON s.session_id=e.runtime_session_id
                   WHERE e.validity_status='valid' AND NOT EXISTS(
                     SELECT 1 FROM native_open_conversation_retests r
                     WHERE r.academy_turn_id=t.academy_turn_id
                   )"""
            ).fetchall()
            for row in rows:
                retest_id = _identifier(
                    "native_open_conversation_retest_", [row["academy_turn_id"]],
                )
                connection.execute(
                    "INSERT OR IGNORE INTO native_open_conversation_retests VALUES(?,?,?,?,?,?,0,'due',?,0,?,NULL)",
                    (retest_id, row["academy_turn_id"], row["active_passage"],
                     row["question"], row["expected_answer"], row["family"],
                     float(row["created_epoch"]) + RETENTION_DELAYS[0],
                     float(row["created_epoch"])),
                )
            # A previous runtime classified anchored sequence questions as
            # assertions when the final sentence ended in a full stop. Keep
            # those receipts for audit, but do not report the resulting echoed
            # questions as failures of Aion's sequence reasoning or retest
            # them as if they were valid student answers.
            contaminated = connection.execute(
                """SELECT DISTINCT t.exam_id
                   FROM native_open_conversation_turns t
                   JOIN native_open_conversation_exams e USING(exam_id)
                   WHERE e.validity_status='valid'
                     AND t.family IN ('sequence_first','sequence_next')
                     AND instr(t.question,'?')>0
                     AND lower(trim(t.native_answer))=lower(trim(t.question))"""
            ).fetchall()
            contaminated_ids = [str(row[0]) for row in contaminated]
            if contaminated_ids:
                marks = ",".join("?" for _ in contaminated_ids)
                connection.execute(
                    f"""UPDATE native_open_conversation_exams
                        SET validity_status='invalidated_runtime_question_classification'
                        WHERE exam_id IN ({marks})""",
                    tuple(contaminated_ids),
                )
                connection.execute(
                    f"""UPDATE native_open_conversation_retests
                        SET status='invalidated_runtime_question_classification'
                        WHERE academy_turn_id IN (
                          SELECT academy_turn_id FROM native_open_conversation_turns
                          WHERE exam_id IN ({marks})
                        )""",
                    tuple(contaminated_ids),
                )

    @staticmethod
    def _teacher_prompt(contracts: Sequence[Mapping[str, Any]]) -> str:
        safe = [{"contract_key": row["contract_key"], "family": row["family"],
                 "question": row["question"]} for row in contracts]
        return (
            "You are preparing a sealed twenty-turn conversation examination. "
            "Select exactly 20 different contract_key values and optionally rephrase each "
            "question without changing its requested role or adding its answer. Include varied "
            "wording and preserve sentence-number anchors. Return strict JSON as "
            "{\"turns\":[{\"contract_key\":\"...\",\"question\":\"...\"}]}. "
            f"Contracts: {json.dumps(safe, ensure_ascii=False)}"
        )

    def _source_package(self) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
        passages: list[dict[str, Any]] = []
        # The online reader may deliberately clear sentence bodies after they
        # have been converted into durable evidence.  The small, authored,
        # versioned cross-subject curriculum remains locally available and is
        # therefore a reliable source-disjoint examination pool rather than a
        # dependency on retained book files.
        curriculum_path = Path(__file__).with_name("reading_library") / "cross_subject_curriculum.json"
        try:
            curriculum = json.loads(curriculum_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            curriculum = []
        for row in curriculum if isinstance(curriculum, list) else []:
            text = " ".join(str(row.get("text") or "").split())
            if not text or not self.discourse._passage_is_prose(text):
                continue
            source_id = _identifier("native_open_source_", [row.get("title"), text])
            passages.append({"source_id": source_id, "title": row.get("title") or "Curriculum",
                             "source_family": row.get("subject") or "general",
                             "passage": text, "source_key": source_id})
        with self._read_connect() as connection:
            attempts = int(connection.execute(
                "SELECT COUNT(*) FROM native_open_conversation_exams WHERE validity_status='valid'"
            ).fetchone()[0])
            used_signatures = {
                str(row[0]) for row in connection.execute(
                    "SELECT passage_signature FROM native_open_conversation_exams "
                    "WHERE validity_status='valid'"
                ).fetchall()
            }
        authored = sorted(passages, key=lambda item: (str(item["source_family"]),
                                                       str(item["title"])))
        # The fixed curriculum bootstraps the first exams, but cannot sustain a
        # continuing twenty-turn programme.  Mix it with source-disjoint
        # windows that the reader has already converted into local evidence.
        # No original book file or online dependency is required here.
        reading: list[dict[str, Any]] = []
        try:
            reading_passages = self.discourse._reading_passages(96)
        except sqlite3.OperationalError:
            # Fresh test/development databases may not have initialised the
            # reader tables yet; authored material still bootstraps the lane.
            reading_passages = []
        for row in reading_passages:
            item = dict(row)
            item["source_key"] = _identifier(
                "native_open_reading_",
                [item.get("source_id"), item.get("passage")],
            )
            reading.append(item)
        if len({str(row["source_family"]) for row in authored + reading}) < 3:
            return [], "", []

        def ranked(rows: Sequence[Mapping[str, Any]], seed: str) -> list[dict[str, Any]]:
            return sorted(
                (dict(row) for row in rows),
                key=lambda row: hashlib.sha256(
                    f"{seed}:{row.get('source_key')}:{row.get('source_id')}".encode()
                ).hexdigest(),
            )

        # Four stable authored passages keep every examination rich enough to
        # yield twenty safe contracts. Four changing reading windows prevent
        # the package pool from exhausting. Hash ranking creates a very large
        # deterministic combination space without storing book bodies twice.
        selected: list[dict[str, Any]] = []
        signature = ""
        for salt in range(256):
            seed = f"{attempts}:{salt}"
            authored_quota = min(4, len(authored))
            reading_quota = min(4, len(reading))
            candidate = ranked(authored, seed + ":authored")[:authored_quota]
            candidate.extend(ranked(reading, seed + ":reading")[:reading_quota])
            if len(candidate) < min(8, len(authored) + len(reading)):
                chosen = {str(row.get("source_key")) for row in candidate}
                remainder = [row for row in authored + reading
                             if str(row.get("source_key")) not in chosen]
                candidate.extend(ranked(remainder, seed + ":remainder")[:8 - len(candidate)])
            if len({str(row.get("source_family") or "general") for row in candidate}) < 3:
                continue
            # Novelty is based on the material set, not its display order. A
            # reordered copy of the same eight passages must not masquerade as
            # a new source-disjoint examination.
            material_keys = sorted(
                hashlib.sha256(_normal(str(row["passage"])).encode()).hexdigest()
                for row in candidate
            )
            candidate_signature = hashlib.sha256(
                json.dumps(material_keys, separators=(",", ":")).encode()
            ).hexdigest()
            if candidate_signature in used_signatures:
                continue
            selected = candidate
            signature = candidate_signature
            break
        if not selected:
            return [], "", []
        contracts: list[dict[str, Any]] = []
        sentence_offset = 0
        for row in selected:
            analysis_key = hashlib.sha256(_normal(str(row["passage"])).encode()).hexdigest()
            cached = _SOURCE_ANALYSIS_CACHE.get(analysis_key)
            if cached:
                source_contracts = [dict(item) for item in cached[0]]
                model = dict(cached[1])
            else:
                source_contracts = self.discourse._contract_candidates([row])
                model = self.discourse.build_situation_model(
                    str(row["passage"]), session_id="open-contract-anchor",
                    source_id=str(row["source_id"]), source_family=str(row["source_family"]),
                    persist=False,
                )
                _SOURCE_ANALYSIS_CACHE[analysis_key] = (
                    [dict(item) for item in source_contracts], dict(model),
                )
            events = [dict(event) for event in model.get("events") or []]
            relations = [dict(relation) for relation in model.get("relations") or []]
            for contract in source_contracts:
                question = str(contract["question"])
                match = re.search(r"\bIn sentence (\d+)\b", question, re.I)
                if match:
                    adjusted = int(match.group(1)) + sentence_offset
                    question = re.sub(r"\bIn sentence \d+\b", f"In sentence {adjusted}",
                                      question, flags=re.I)
                else:
                    expected = _normal(str(contract["expected_answer"]))
                    family = str(contract["family"])
                    anchored = None
                    if family == "cause":
                        events_by_id = {str(event.get("event_id")): event for event in events}
                        for relation in relations:
                            if relation.get("type") != "cause":
                                continue
                            cause_event = events_by_id.get(str(relation.get("from_event")))
                            target_event = events_by_id.get(str(relation.get("to_event")))
                            cause_text = _normal(" ".join(str((cause_event or {}).get(key) or "")
                                                         for key in ("subject", "action_surface", "object")))
                            if cause_text == expected and target_event:
                                anchored = (int(target_event.get("sentence_index") or 0)
                                            + sentence_offset + 1)
                                break
                    for event in events:
                        if anchored is not None:
                            break
                        values = {
                            "entity": _normal(str(event.get("subject") or "")),
                            "action": _normal(str(event.get("action_surface") or event.get("action") or "")),
                            "object": _normal(str(event.get("object") or "")),
                            "time": _normal(str(event.get("time") or "")),
                            "location": _normal(str(event.get("location") or "")),
                            "sequence_first": _normal(" ".join(str(event.get(key) or "") for key in
                                                               ("subject", "action_surface", "object"))),
                            "sequence_next": _normal(" ".join(str(event.get(key) or "") for key in
                                                              ("subject", "action_surface", "object"))),
                            "cause": _normal(" ".join(str(event.get(key) or "") for key in
                                                      ("subject", "action_surface", "object"))),
                        }
                        if values.get(family) == expected:
                            anchored = int(event.get("sentence_index") or 0) + sentence_offset + 1
                            break
                    if anchored is not None:
                        question = f"{question.rstrip()} Use sentence {anchored}."
                if str(contract["family"]) == "coreference":
                    target = str(contract["expected_answer"])
                    title_terms = set(WORD_RE.findall(_normal(str(row.get("title") or ""))))
                    if (target.lower().endswith("ing")
                            or _normal(target) in {"year", "years", "month", "months", "day", "days"}
                            or _normal(target) in title_terms):
                        continue
                contracts.append({**contract, "question": question,
                                  "source_family": row["source_family"]})
            sentence_offset += len(_sentences(str(row["passage"])))
        return selected, signature, contracts

    @staticmethod
    def _diverse_contracts(contracts: Sequence[Mapping[str, Any]], count: int) -> list[dict[str, Any]]:
        by_family: dict[str, list[dict[str, Any]]] = {}
        for row in contracts:
            by_family.setdefault(str(row["family"]), []).append(dict(row))
        priority = ("coreference", "cause", "sequence_first", "sequence_next", "time",
                    "location", "object", "action", "entity", "contradiction")
        ordered_families = [family for family in priority if family in by_family]
        selected: list[dict[str, Any]] = []
        family_counts: dict[str, int] = {}
        while len(selected) < count and any(by_family.values()):
            progress = False
            for family in ordered_families:
                if not by_family.get(family) or family_counts.get(family, 0) >= 4:
                    continue
                selected.append(by_family[family].pop(0))
                family_counts[family] = family_counts.get(family, 0) + 1
                progress = True
                if len(selected) >= count:
                    break
            if not progress:
                break
        return selected

    def _teacher_selection(self, contracts: Sequence[Mapping[str, Any]],
                           teacher_client: Callable[[str], Mapping[str, Any]] | None,
                           count: int) -> tuple[str, list[dict[str, Any]], int]:
        compiled = self._diverse_contracts(contracts, count)
        if not teacher_client:
            return "compiled-native-open-conversation", compiled, 0
        by_key = {str(row["contract_key"]): dict(row) for row in contracts}
        try:
            payload = dict(teacher_client(self._teacher_prompt(contracts)))
            model = str(payload.get("model") or "local-qwen")
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "",
                         str(payload.get("content") or "").strip(), flags=re.I | re.S)
            proposals = list(json.loads(raw).get("turns") or [])
        except Exception:
            return "compiled-native-open-conversation", compiled, 1
        selected: list[dict[str, Any]] = []
        used: set[str] = set()
        rejected = 0
        for proposal in proposals:
            contract = by_key.get(str(proposal.get("contract_key") or ""))
            if not contract or str(contract["contract_key"]) in used:
                rejected += 1
                continue
            question = " ".join(str(proposal.get("question") or contract["question"]).split())
            if (not question or _normal(str(contract["expected_answer"])) in _normal(question)
                    or ("sentence" in _normal(str(contract["question"]))
                        and "sentence" not in _normal(question))):
                rejected += 1
                question = str(contract["question"])
            selected.append({**contract, "question": question})
            used.add(str(contract["contract_key"]))
            if len(selected) >= count:
                break
        for row in compiled:
            if len(selected) >= count:
                break
            if str(row["contract_key"]) not in used:
                selected.append(row)
                used.add(str(row["contract_key"]))
        return model, selected, rejected

    def _run_due_retests(self, limit: int = 20) -> list[dict[str, Any]]:
        now = time.time()
        with self._read_connect() as connection:
            rows = connection.execute(
                """SELECT * FROM native_open_conversation_retests
                   WHERE status='due' AND due_epoch<=? ORDER BY due_epoch LIMIT ?""",
                (now, max(1, limit)),
            ).fetchall()
        results = []
        for raw in rows:
            row = dict(raw)
            result = self.runtime.respond(
                row["question"], session_id=f"open-retest:{row['retest_id']}",
                context=row["context"], source_id="open-conversation-retest",
                source_family="retention",
            )
            candidate = str((result.get("propositions") or [result.get("response") or ""])[0])
            correct = self.discourse._meaning_match(candidate, str(row["expected_answer"]))
            stage = int(row["retention_stage"])
            with self._connect() as connection:
                if correct and stage + 1 < len(RETENTION_DELAYS):
                    connection.execute(
                        "UPDATE native_open_conversation_retests SET retention_stage=?,due_epoch=?,attempts=attempts+1 WHERE retest_id=?",
                        (stage + 1, now + RETENTION_DELAYS[stage + 1], row["retest_id"]),
                    )
                elif correct:
                    connection.execute(
                        "UPDATE native_open_conversation_retests SET status='cleared',attempts=attempts+1,cleared_epoch=? WHERE retest_id=?",
                        (now, row["retest_id"]),
                    )
                else:
                    connection.execute(
                        "UPDATE native_open_conversation_retests SET attempts=attempts+1,due_epoch=? WHERE retest_id=?",
                        (now + 86400.0, row["retest_id"]),
                    )
            results.append({"retest_id": row["retest_id"], "correct": correct,
                            "retention_stage": stage, "model_used": False})
        return results

    def run_cycle(self, *, teacher_client: Callable[[str], Mapping[str, Any]] | None = None,
                  limit: int = 1) -> dict[str, Any]:
        retests = self._run_due_retests(20)
        results = []
        for _ in range(max(1, min(2, int(limit)))):
            sources, signature, contracts = self._source_package()
            if not sources or len(contracts) < TARGET_TURNS:
                break
            with self._read_connect() as connection:
                prior = connection.execute(
                    "SELECT 1 FROM native_open_conversation_exams WHERE passage_signature=? AND validity_status='valid'",
                    (signature,),
                ).fetchone()
            if prior:
                break
            teacher_model, selected, rejected = self._teacher_selection(
                contracts, teacher_client, TARGET_TURNS,
            )
            if len(selected) < TARGET_TURNS:
                break
            context = " ".join(str(row["passage"]) for row in sources)
            now = time.time()
            exam_id = _identifier("native_open_conversation_exam_", [signature, now])
            runtime_session_id = f"open-academy:{exam_id}"
            turns = []
            for index, contract in enumerate(selected):
                result = self.runtime.respond(
                    str(contract["question"]), session_id=runtime_session_id,
                    context=context if index == 0 else "",
                    source_id="+".join(str(row["source_id"]) for row in sources),
                    source_family="+".join(str(row["source_family"]) for row in sources),
                )
                candidate = str((result.get("propositions") or [result.get("response") or ""])[0])
                correct = self.discourse._meaning_match(candidate, str(contract["expected_answer"]))
                evidence_supported = bool(result.get("evidence"))
                unsupported = bool((result.get("checks") or {}).get("unsupported_claims"))
                turn_id = _identifier("native_open_conversation_turn_", [exam_id, index])
                with self._connect() as connection:
                    connection.execute(
                        "INSERT INTO native_open_conversation_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (turn_id, exam_id, index, contract["contract_key"], contract["family"],
                         contract["question"], contract["expected_answer"], candidate,
                         int(correct), int(evidence_supported), int(unsupported),
                         json.dumps(result.get("ambiguities") or []), result["turn_id"], now + index / 1000),
                    )
                    retest_id = _identifier("native_open_conversation_retest_", [turn_id])
                    connection.execute(
                        "INSERT OR IGNORE INTO native_open_conversation_retests VALUES(?,?,?,?,?,?,0,'due',?,0,?,NULL)",
                        (retest_id, turn_id, context, contract["question"],
                         contract["expected_answer"], contract["family"],
                         now + RETENTION_DELAYS[0], now),
                    )
                turns.append({"family": contract["family"], "correct": correct,
                              "evidence_supported": evidence_supported, "unsupported": unsupported})
            correct_turns = sum(int(row["correct"]) for row in turns)
            evidence_turns = sum(int(row["evidence_supported"]) for row in turns)
            unsupported_claims = sum(int(row["unsupported"]) for row in turns)
            passed = (len(turns) == TARGET_TURNS and correct_turns >= 18
                      and evidence_turns == TARGET_TURNS and unsupported_claims == 0)
            families = sorted({str(row["source_family"]) for row in sources})
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO native_open_conversation_exams VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exam_id, runtime_session_id, signature,
                     json.dumps([row["source_id"] for row in sources]), json.dumps(families),
                     TARGET_TURNS, len(turns), correct_turns, evidence_turns, 0,
                     unsupported_claims, int(passed), teacher_model, 0, "valid", now),
                )
            results.append({"exam_id": exam_id, "turns": len(turns),
                            "correct": correct_turns, "evidence_supported": evidence_turns,
                            "unsupported_claims": unsupported_claims, "passed": passed,
                            "source_families": families, "teacher_model": teacher_model,
                            "teacher_drafts_rejected": rejected, "student_model_used": False})
        return {"status": "completed" if results else "awaiting_eligible_twenty_turn_material",
                "attempted": len(results), "passed": sum(int(row["passed"]) for row in results),
                "results": results, "retests": retests,
                "target_turns": TARGET_TURNS, "qwen_used_for_student_answers": False,
                "model_used": False, "next_token_prediction": False}

    def metrics(self) -> dict[str, Any]:
        now = time.time()
        with self._read_connect() as connection:
            total = connection.execute(
                """SELECT COUNT(*) exams,COALESCE(SUM(passed),0) passed,
                          COALESCE(SUM(completed_turns),0) turns,
                          COALESCE(SUM(correct_turns),0) correct,
                          COALESCE(SUM(evidence_turns),0) evidence,
                          COALESCE(SUM(unsupported_claims),0) unsupported,
                          COUNT(DISTINCT passage_signature) passages
                   FROM native_open_conversation_exams WHERE validity_status='valid'"""
            ).fetchone()
            recent = connection.execute(
                """SELECT COUNT(*) exams,COALESCE(SUM(completed_turns),0) turns,
                          COALESCE(SUM(correct_turns),0) correct
                   FROM native_open_conversation_exams
                   WHERE validity_status='valid' AND created_epoch>?""", (now - 3600.0,),
            ).fetchone()
            due = connection.execute(
                "SELECT COUNT(*) FROM native_open_conversation_retests WHERE status='due' AND due_epoch<=?",
                (now,),
            ).fetchone()[0]
            pending = connection.execute(
                "SELECT COUNT(*) FROM native_open_conversation_retests WHERE status='due'",
            ).fetchone()[0]
            cleared = connection.execute(
                "SELECT COUNT(*) FROM native_open_conversation_retests WHERE status='cleared'",
            ).fetchone()[0]
            family_rows = connection.execute(
                """SELECT t.family,COUNT(*) attempts,COALESCE(SUM(t.correct),0) correct
                   FROM native_open_conversation_turns t
                   JOIN native_open_conversation_exams e USING(exam_id)
                   WHERE e.validity_status='valid' GROUP BY t.family"""
            ).fetchall()
        turns = int(total["turns"] or 0)
        recent_turns = int(recent["turns"] or 0)
        families = {
            str(row["family"]): {
                "attempts": int(row["attempts"] or 0),
                "correct": int(row["correct"] or 0),
                "accuracy": round(int(row["correct"] or 0) / int(row["attempts"] or 1), 4),
            }
            for row in family_rows
        }
        reference_accuracy = (families.get("coreference") or {}).get("accuracy")
        cause_accuracy = (families.get("cause") or {}).get("accuracy")
        unsupported_rate = (int(total["unsupported"] or 0) / turns) if turns else None
        return {"exams": int(total["exams"] or 0), "passed": int(total["passed"] or 0),
                "turns": turns, "correct": int(total["correct"] or 0),
                "accuracy": round(int(total["correct"] or 0) / turns, 4) if turns else None,
                "evidence_supported_rate": round(int(total["evidence"] or 0) / turns, 4)
                if turns else None,
                "unsupported_claims": int(total["unsupported"] or 0),
                "unsupported_claim_rate": round(int(total["unsupported"] or 0) / turns, 4)
                if turns else None,
                "source_disjoint_passages": int(total["passages"] or 0),
                "exams_last_hour": int(recent["exams"] or 0),
                "recent_accuracy": round(int(recent["correct"] or 0) / recent_turns, 4)
                if recent_turns else None,
                "retests_due": int(due), "retests_pending": int(pending),
                "retests_cleared": int(cleared), "target_turns": TARGET_TURNS,
                "family_evidence": families,
                "benchmarks": {
                    "reference_resolution_90": bool(reference_accuracy is not None
                                                     and reference_accuracy >= .90),
                    "causal_reasoning_85": bool(cause_accuracy is not None
                                                and cause_accuracy >= .85),
                    "two_twenty_turn_passes": int(total["passed"] or 0) >= 2,
                    "unsupported_claims_below_2_percent": bool(
                        unsupported_rate is not None and unsupported_rate < .02),
                    "student_model_absent": True,
                    "delayed_retention_complete": int(cleared) >= TARGET_TURNS,
                },
                "student_model_used": False, "qwen_role": "sealed_teacher_only",
                "claim_boundary": (
                    "Passing requires at least 18/20 correct, evidence on all turns, no unsupported "
                    "claims, source-disjoint material and delayed retention."
                )}


__all__ = ["NativeOpenConversationAcademy", "TARGET_TURNS"]
