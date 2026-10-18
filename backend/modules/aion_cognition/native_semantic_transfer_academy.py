"""Local-Qwen teacher academy for model-free Aion semantic transfer.

The teacher creates sealed, grounded challenges from concepts the semantic
spider has already acquired.  Aion answers only after the teacher call has
returned, using :mod:`native_english_transfer` with no model access.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable, Mapping

from backend.modules.aion_cognition.sqlite_connection import (
    connect as sqlite_connect,
    connect_read_only as sqlite_read_connect,
)
from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer, _normal
from backend.modules.aion_cognition.native_english_practice_gym import HIGH_UTILITY_LEMMAS
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


FAMILIES = (
    "contextual_meaning", "semantic_patient", "semantic_entity", "property_inference",
    "paraphrase", "negation_scope", "comparison", "cause_inference",
)
STAGE_ORDER = {
    "mastered": 9, "retention_90d": 8, "retention_30d": 7,
    "retention_7d": 6, "retention_1d": 5, "productive": 4,
    "contextual": 3, "recalled": 2, "grounded": 1,
}
CAPABILITY_ORDER = {"grounded": 0, "recalled": 1, "contextual": 2, "productive": 3}
FAILURE_COOLDOWN_BASE_SECONDS = 120.0
FAILURE_COOLDOWN_MAX_SECONDS = 3600.0
# Reading now supplies real concept-in-context guided evidence.  Keep enough
# concepts in independent transfer for that evidence to turn into productive
# use instead of queueing behind a tiny fixed cohort.
FOCUSED_COHORT_SIZE = 96
ADVANCED_TRANSFER_SHARE = 0.75

POS_TRANSFER_FAMILIES = {
    "v": ("semantic_patient", "cause_inference", "contextual_meaning", "paraphrase", "negation_scope"),
    # The original comparison compiler supplied only one entity/person and then
    # asked Aion to compare it with unspecified alternatives.  That is not a
    # valid closed-book examination.  Keep four genuinely distinct families
    # until a comparison contract can supply two explicit alternatives.
    "n": ("semantic_entity", "contextual_meaning", "paraphrase", "negation_scope"),
    "a": ("property_inference", "contextual_meaning", "paraphrase", "negation_scope"),
    "s": ("property_inference", "contextual_meaning", "paraphrase", "negation_scope"),
}

METALINGUISTIC_QUESTION_PATTERNS = (
    "which word", "what word", "which term", "what term",
    "which verb", "what verb", "which adjective", "what adjective",
    "semantic feature", "semantic relation", "target concept",
    "in the material", "in the text", "in the sentence",
    "using the synonym", "using the relation", "based on the semantic",
)

TRANSFER_NAMES = (
    "Mireya", "Tavian", "Leona", "Kellan", "Amara", "Neryn", "Cassia",
    "Darian", "Elara", "Ivo", "Soren", "Zeta", "Owen", "Rhea", "Varen",
)
TRANSFER_PATIENTS = (
    "report", "sensor", "message", "sample", "record", "signal", "proposal",
    "package", "device", "document", "result", "request",
)
TRANSFER_CONTEXTS = (
    "During the audit", "Before sunrise", "After the meeting",
    "Inside the laboratory", "During the inspection", "Before the review",
    "At the workshop", "During the field test",
)


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _json_object(value: str) -> dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(value or "").strip(),
                  flags=re.I | re.S)
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("teacher_response_not_json")
        candidate = match.group(0)
        # Local compact models occasionally omit a comma between JSON lines
        # or leave a comma before a closing bracket. Repair only these narrow
        # syntax faults; semantic validation still runs afterwards.
        candidate = re.sub(r'([}\]"0-9])\s*\n(\s*")', r'\1,\n\2', candidate)
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            decoded = json.loads(candidate)
        except json.JSONDecodeError:
            # With one challenge per cycle, recover an otherwise valid inner
            # object even if the outer wrapper was truncated.
            marker = re.search(r'"challenges"\s*:\s*\[', candidate)
            if not marker:
                raise ValueError("teacher_response_not_json")
            start = candidate.find("{", marker.end())
            depth, quoted, escaped, end = 0, False, False, -1
            for index in range(start, len(candidate)):
                char = candidate[index]
                if escaped:
                    escaped = False
                    continue
                if char == "\\" and quoted:
                    escaped = True
                    continue
                if char == '"':
                    quoted = not quoted
                elif not quoted and char == "{":
                    depth += 1
                elif not quoted and char == "}":
                    depth -= 1
                    if depth == 0:
                        end = index + 1
                        break
            if start < 0 or end < 0:
                raise ValueError("teacher_response_truncated")
            inner = candidate[start:end]
            inner = re.sub(r'([}\]"0-9])\s*\n(\s*")', r'\1,\n\2', inner)
            inner = re.sub(r",\s*([}\]])", r"\1", inner)
            decoded = {"challenges": [json.loads(inner)]}
    if not isinstance(decoded, dict):
        raise ValueError("teacher_response_not_object")
    return decoded


class NativeSemanticTransferAcademy:
    """Generate, verify, seal and run transfer challenges continuously."""

    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None,
                 transfer: NativeEnglishTransfer | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.transfer = transfer or NativeEnglishTransfer(
            repo_root=self.repo_root, lexical=self.lexical,
        )
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
                CREATE TABLE IF NOT EXISTS native_semantic_transfer_academy_challenges (
                    academy_challenge_id TEXT PRIMARY KEY,
                    transfer_challenge_id TEXT NOT NULL DEFAULT '',
                    concept_id TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    sense_hash TEXT NOT NULL,
                    learning_stage TEXT NOT NULL,
                    family TEXT NOT NULL,
                    material TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL,
                    answer_reason TEXT NOT NULL,
                    teacher_model TEXT NOT NULL,
                    verifier_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correct INTEGER,
                    created_epoch REAL NOT NULL,
                    attempted_epoch REAL
                );
                CREATE INDEX IF NOT EXISTS semantic_academy_concept
                    ON native_semantic_transfer_academy_challenges(concept_id,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_semantic_transfer_academy_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    teacher_model TEXT NOT NULL,
                    generated INTEGER NOT NULL,
                    verified INTEGER NOT NULL,
                    rejected INTEGER NOT NULL,
                    attempted INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    reinforced INTEGER NOT NULL,
                    remediation_due INTEGER NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_semantic_transfer_concept_progress (
                    concept_id TEXT PRIMARY KEY,
                    guided_successes INTEGER NOT NULL DEFAULT 0,
                    remedial_successes INTEGER NOT NULL DEFAULT 0,
                    free_successes INTEGER NOT NULL DEFAULT 0,
                    free_families_json TEXT NOT NULL DEFAULT '[]',
                    failure_streak INTEGER NOT NULL DEFAULT 0,
                    cooldown_until REAL NOT NULL DEFAULT 0,
                    capability_stage TEXT NOT NULL DEFAULT 'grounded',
                    last_failure_epoch REAL,
                    last_attempt_epoch REAL,
                    updated_epoch REAL NOT NULL,
                    FOREIGN KEY(concept_id) REFERENCES acquired_concepts(concept_id)
                );
                CREATE INDEX IF NOT EXISTS semantic_transfer_progress_phase
                    ON native_semantic_transfer_concept_progress(
                        capability_stage,cooldown_until,last_attempt_epoch
                    );
                CREATE TABLE IF NOT EXISTS native_semantic_transfer_cohort (
                    concept_id TEXT PRIMARY KEY,
                    cohort_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    added_epoch REAL NOT NULL,
                    completed_epoch REAL,
                    FOREIGN KEY(concept_id) REFERENCES acquired_concepts(concept_id)
                );
                CREATE INDEX IF NOT EXISTS semantic_transfer_cohort_status
                    ON native_semantic_transfer_cohort(status,added_epoch);
                CREATE TABLE IF NOT EXISTS native_english_practice_progress (
                    concept_id TEXT NOT NULL,
                    family TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    correct INTEGER NOT NULL DEFAULT 0,
                    rewards INTEGER NOT NULL DEFAULT 0,
                    corrections INTEGER NOT NULL DEFAULT 0,
                    retests_passed INTEGER NOT NULL DEFAULT 0,
                    consecutive_passes INTEGER NOT NULL DEFAULT 0,
                    last_attempt_epoch REAL,
                    next_due_epoch REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY(concept_id,family)
                );
                """
            )
            self._invalidate_legacy_comparison_contracts(connection)
            self._backfill_progress(connection)
            self._refresh_focused_cohort(connection)
            # Migrate early academy receipts created before challenges carried
            # an explicit sealed target. Remove collateral concept updates and
            # retain only one active remediation obligation per target.
            connection.execute(
                """UPDATE native_english_transfer_challenges
                   SET learning_target_concept_id=(
                     SELECT a.concept_id FROM native_semantic_transfer_academy_challenges a
                     WHERE a.transfer_challenge_id=native_english_transfer_challenges.challenge_id
                   )
                   WHERE source='local_qwen_teacher_sealed'
                     AND learning_target_concept_id=''"""
            )
            misplaced = connection.execute(
                """SELECT e.event_id,e.concept_id,e.event_type
                   FROM native_english_transfer_learning_events e
                   JOIN native_english_transfer_challenges c ON c.challenge_id=e.challenge_id
                   WHERE c.source='local_qwen_teacher_sealed'
                     AND c.learning_target_concept_id<>''
                     AND e.concept_id<>c.learning_target_concept_id"""
            ).fetchall()
            for event in misplaced:
                correct_delta = 1 if event["event_type"] == "semantic_transfer_reinforcement" else 0
                failed_delta = 1 if event["event_type"] == "remedial_correction" else 0
                connection.execute(
                    """UPDATE acquired_concepts SET attempts=MAX(0,attempts-1),
                       correct_attempts=MAX(0,correct_attempts-?),
                       failed_attempts=MAX(0,failed_attempts-?),updated_epoch=?
                       WHERE concept_id=?""",
                    (correct_delta, failed_delta, time.time(), event["concept_id"]),
                )
                connection.execute(
                    "DELETE FROM native_english_transfer_learning_events WHERE event_id=?",
                    (event["event_id"],),
                )
            active_due: set[str] = set()
            duplicate_due = connection.execute(
                """SELECT e.event_id,e.concept_id FROM native_english_transfer_learning_events e
                   JOIN native_english_transfer_challenges c ON c.challenge_id=e.challenge_id
                   WHERE c.source='local_qwen_teacher_sealed' AND e.status='due'
                   ORDER BY e.created_epoch"""
            ).fetchall()
            for event in duplicate_due:
                if event["concept_id"] in active_due:
                    connection.execute(
                        "UPDATE native_english_transfer_learning_events SET status='recorded_failure' WHERE event_id=?",
                        (event["event_id"],),
                    )
                active_due.add(str(event["concept_id"]))

    def _invalidate_legacy_comparison_contracts(
        self, connection: sqlite3.Connection,
    ) -> None:
        """Remove impossible one-entity comparison tests from learning evidence.

        These receipts were generated by an earlier constrained compiler.  It
        produced prompts such as "Compared with the other entities" while the
        material contained no other entity.  They must remain auditable, but
        must not count as Aion failures, cooldowns, remedies or transfer scores.
        """
        rows = connection.execute(
            """SELECT academy_challenge_id,transfer_challenge_id,concept_id
               FROM native_semantic_transfer_academy_challenges
               WHERE status='attempted' AND family='comparison'
                 AND verifier_json LIKE '%\"transfer_contract_compiled\": true%'"""
        ).fetchall()
        if not rows:
            return
        academy_ids = [str(row["academy_challenge_id"]) for row in rows]
        transfer_ids = [str(row["transfer_challenge_id"]) for row in rows
                        if row["transfer_challenge_id"]]
        concept_ids = sorted({str(row["concept_id"]) for row in rows})
        connection.executemany(
            """UPDATE native_semantic_transfer_academy_challenges
               SET status='invalidated_contract',correct=NULL
               WHERE academy_challenge_id=?""",
            [(value,) for value in academy_ids],
        )
        if transfer_ids:
            connection.executemany(
                """UPDATE native_english_transfer_learning_events
                   SET status='invalidated_contract'
                   WHERE challenge_id=? AND event_type='remedial_correction'""",
                [(value,) for value in transfer_ids],
            )
        for concept_id in concept_ids:
            self._rebuild_progress_from_valid_evidence(connection, concept_id)

    def _rebuild_progress_from_valid_evidence(
        self, connection: sqlite3.Connection, concept_id: str,
    ) -> None:
        """Recalculate one progress row solely from still-valid sealed receipts."""
        now = time.time()
        rows = connection.execute(
            """SELECT family,correct,verifier_json,attempted_epoch,created_epoch
               FROM native_semantic_transfer_academy_challenges
               WHERE concept_id=? AND status='attempted'
               ORDER BY COALESCE(attempted_epoch,created_epoch)""",
            (concept_id,),
        ).fetchall()
        guided = remedial = free = failure_streak = 0
        families: set[str] = set()
        last_failure = last_attempt = None
        for row in rows:
            try:
                verifier = json.loads(row["verifier_json"] or "{}")
            except json.JSONDecodeError:
                verifier = {}
            tier = str(verifier.get("evidence_tier") or "legacy")
            correct = bool(row["correct"])
            last_attempt = float(row["attempted_epoch"] or row["created_epoch"] or now)
            if correct:
                failure_streak = 0
                if tier == "free_transfer":
                    free += 1
                    families.add(str(row["family"]))
                elif tier == "remedial_retry":
                    remedial += 1
                else:
                    guided += 1
            else:
                failure_streak += 1
                last_failure = last_attempt
        cooldown = 0.0
        if failure_streak and last_failure:
            cooldown = last_failure + min(
                FAILURE_COOLDOWN_MAX_SECONDS,
                FAILURE_COOLDOWN_BASE_SECONDS * (2 ** (failure_streak - 1)),
            )
        capability = self._capability_stage(guided, free, families)
        connection.execute(
            """INSERT INTO native_semantic_transfer_concept_progress(
                 concept_id,guided_successes,remedial_successes,free_successes,
                 free_families_json,failure_streak,cooldown_until,capability_stage,
                 last_failure_epoch,last_attempt_epoch,updated_epoch
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(concept_id) DO UPDATE SET
                 guided_successes=excluded.guided_successes,
                 remedial_successes=excluded.remedial_successes,
                 free_successes=excluded.free_successes,
                 free_families_json=excluded.free_families_json,
                 failure_streak=excluded.failure_streak,
                 cooldown_until=excluded.cooldown_until,
                 capability_stage=excluded.capability_stage,
                 last_failure_epoch=excluded.last_failure_epoch,
                 last_attempt_epoch=excluded.last_attempt_epoch,
                 updated_epoch=excluded.updated_epoch""",
            (concept_id, guided, remedial, free, json.dumps(sorted(families)),
             failure_streak, cooldown, capability, last_failure, last_attempt, now),
        )

    def _refresh_focused_cohort(self, connection: sqlite3.Connection) -> None:
        """Keep a bounded set of concepts in transfer until they graduate.

        The previous breadth-first scheduler continually selected concepts with
        the fewest academy uses.  That produced many recalled concepts but gave
        too few of them the four varied free-transfer successes required for
        productive use.
        """
        now = time.time()
        connection.execute(
            """UPDATE native_semantic_transfer_cohort
               SET status='deferred_unsupported',completed_epoch=?
               WHERE status='active' AND concept_id IN (
                 SELECT concept_id FROM acquired_concepts
                 WHERE part_of_speech NOT IN ('n','v','a','s')
               )""",
            (now,),
        )
        connection.execute(
            """UPDATE native_semantic_transfer_cohort
               SET status='graduated',completed_epoch=?
               WHERE status='active' AND concept_id IN (
                 SELECT concept_id FROM native_semantic_transfer_concept_progress
                 WHERE capability_stage='productive'
               )""",
            (now,),
        )
        active = int(connection.execute(
            "SELECT COUNT(*) FROM native_semantic_transfer_cohort WHERE status='active'"
        ).fetchone()[0])
        vacancies = max(0, FOCUSED_COHORT_SIZE - active)
        if not vacancies:
            return
        cohort_id = "semantic_transfer_focus_" + time.strftime("%Y%m%d", time.gmtime(now))
        candidates = connection.execute(
            """SELECT p.concept_id
               FROM native_semantic_transfer_concept_progress p
               JOIN acquired_concepts a ON a.concept_id=p.concept_id
               LEFT JOIN native_semantic_transfer_cohort c ON c.concept_id=p.concept_id
               WHERE c.concept_id IS NULL
                 AND p.guided_successes>=2
                 AND p.capability_stage IN ('recalled','contextual')
                 AND a.part_of_speech IN ('n','v','a','s')
                 AND INSTR(a.lemma,' ')=0
               ORDER BY CASE p.capability_stage WHEN 'contextual' THEN 0 ELSE 1 END,
                        p.free_successes DESC,p.last_attempt_epoch ASC,p.updated_epoch ASC
               LIMIT ?""",
            (vacancies,),
        ).fetchall()
        connection.executemany(
            """INSERT OR IGNORE INTO native_semantic_transfer_cohort
               (concept_id,cohort_id,status,added_epoch,completed_epoch)
               VALUES(?,?,'active',?,NULL)""",
            [(str(row["concept_id"]), cohort_id, now) for row in candidates],
        )

    @staticmethod
    def _next_transfer_family(candidate: Mapping[str, Any], cycle_number: int) -> str:
        allowed = POS_TRANSFER_FAMILIES.get(
            str(candidate.get("part_of_speech") or ""),
            ("contextual_meaning", "paraphrase", "comparison"),
        )
        used = set(candidate.get("free_families") or [])
        unseen = [family for family in allowed if family not in used]
        choices = unseen or list(allowed)
        return choices[cycle_number % len(choices)]

    @staticmethod
    def _safe_slot(value: Any, allowed: tuple[str, ...], fallback_index: int) -> str:
        normalized = _normal(str(value or ""))
        for option in allowed:
            if _normal(option) == normalized:
                return option
        return allowed[fallback_index % len(allowed)]

    def _compile_transfer_contract(
        self, candidate: Mapping[str, Any], slots: Mapping[str, Any], cycle_number: int,
    ) -> dict[str, str]:
        """Compile Qwen's bounded scenario slots into a provable unseen test.

        Qwen varies the scenario, but cannot select the grammatical role,
        target sense, answer span, or evidence family.  This preserves teacher
        variation without allowing an impossible or mislabeled examination.
        """
        lemma = str(candidate["lemma"])
        pos = str(candidate.get("part_of_speech") or "")
        family = str(candidate.get("required_transfer_family") or
                     self._next_transfer_family(candidate, cycle_number))
        seed = int(hashlib.sha256(
            f"{candidate['concept_id']}:{cycle_number}".encode()
        ).hexdigest()[:8], 16)
        requested_name = slots.get("name") or slots.get("subject")
        requested_patient = slots.get("patient") or slots.get("object")
        requested_context = slots.get("context") or slots.get("setting")
        bridge = self._semantic_bridge(candidate)
        recent = {_normal(value) for value in candidate.get("recent_materials") or []}

        for offset in range(len(TRANSFER_NAMES) * 2):
            name = self._safe_slot(requested_name, TRANSFER_NAMES, seed + offset)
            patient = self._safe_slot(
                requested_patient, TRANSFER_PATIENTS, seed // 7 + offset,
            )
            context = self._safe_slot(
                requested_context, TRANSFER_CONTEXTS, seed // 13 + offset,
            )
            if offset:
                name = TRANSFER_NAMES[(seed + offset) % len(TRANSFER_NAMES)]
                patient = TRANSFER_PATIENTS[(seed // 7 + offset) % len(TRANSFER_PATIENTS)]
                context = TRANSFER_CONTEXTS[(seed // 13 + offset) % len(TRANSFER_CONTEXTS)]

            if pos == "v":
                negator = " not" if family == "negation_scope" else ""
                material = f"{context}, {name} will{negator} {lemma} the {patient}."
                expected = patient
                question = (
                    f"Which item is affected by an action associated with {bridge}?"
                    if family != "cause_inference" else
                    f"Which item is affected because {name} performs an action associated with {bridge}?"
                )
                reason = (
                    f"The acquired action {lemma} is associated with {bridge}; "
                    f"{patient} is its complete direct object."
                )
            elif pos == "n":
                material = f"{context}, {name} examined the {lemma}."
                expected = lemma
                question = (
                    f"Which entity is associated with {bridge}?"
                    if family != "comparison" else
                    f"Compared with the other entities, which entity is associated with {bridge}?"
                )
                reason = (
                    f"The acquired entity {lemma} is associated with {bridge} and is "
                    "the complete direct object."
                )
            elif pos in {"a", "s"}:
                material = f"{context}, {name} remained {lemma}."
                expected = name
                question = (
                    f"Which person has the property associated with {bridge}?"
                    if family != "comparison" else
                    f"Compared with the other people, which person has the property associated with {bridge}?"
                )
                reason = (
                    f"The acquired property {lemma} is associated with {bridge} and "
                    f"applies to {name}."
                )
            else:
                return {}
            parsed = self.transfer.parse(material)
            self.transfer._bind_sealed_target(parsed, str(candidate["concept_id"]))
            role_matches = False
            for raw_clause in parsed.get("clauses") or []:
                clause = dict(raw_clause)
                if pos == "v" and str(
                    (clause.get("action_evidence") or {}).get("concept_id") or ""
                ) == str(candidate["concept_id"]):
                    role_matches = _normal(str(clause.get("object") or "")) == _normal(expected)
                elif pos == "n" and str(
                    (clause.get("object_evidence") or {}).get("concept_id") or ""
                ) == str(candidate["concept_id"]):
                    role_matches = _normal(str(clause.get("object") or "")) == _normal(expected)
                elif pos in {"a", "s"} and str(
                    (clause.get("complement_evidence") or {}).get("concept_id") or ""
                ) == str(candidate["concept_id"]):
                    role_matches = _normal(str(clause.get("subject") or "")) == _normal(expected)
                if role_matches:
                    break
            if role_matches and _normal(material) not in recent:
                return {
                    "concept_id": str(candidate["concept_id"]), "lemma": lemma,
                    "family": family, "material": material, "question": question,
                    "expected_answer": expected, "answer_reason": reason,
                }
        return {}

    @staticmethod
    def _capability_stage(guided: int, free: int, families: set[str]) -> str:
        """Return the highest evidence-backed semantic-use capability."""
        if free >= 4 and len(families) >= 3:
            return "productive"
        if free >= 2 and len(families) >= 2:
            return "contextual"
        if guided >= 2:
            return "recalled"
        return "grounded"

    def _backfill_progress(self, connection: sqlite3.Connection) -> None:
        """Seed the new state machine from existing sealed attempt receipts."""
        concept_ids = connection.execute(
            "SELECT DISTINCT concept_id FROM native_semantic_transfer_academy_challenges "
            "WHERE status='attempted'"
        ).fetchall()
        now = time.time()
        for concept_row in concept_ids:
            concept_id = str(concept_row[0])
            exists = connection.execute(
                "SELECT 1 FROM native_semantic_transfer_concept_progress WHERE concept_id=?",
                (concept_id,),
            ).fetchone()
            if exists:
                continue
            rows = connection.execute(
                """SELECT family,correct,verifier_json,attempted_epoch,created_epoch
                   FROM native_semantic_transfer_academy_challenges
                   WHERE concept_id=? AND status='attempted'
                   ORDER BY COALESCE(attempted_epoch,created_epoch)""",
                (concept_id,),
            ).fetchall()
            guided = remedial = free = failure_streak = 0
            families: set[str] = set()
            last_failure = None
            last_attempt = None
            for row in rows:
                try:
                    verifier = json.loads(row["verifier_json"] or "{}")
                except json.JSONDecodeError:
                    verifier = {}
                tier = str(verifier.get("evidence_tier") or "legacy")
                correct = bool(row["correct"])
                last_attempt = float(row["attempted_epoch"] or row["created_epoch"] or now)
                if correct:
                    failure_streak = 0
                    if tier == "free_transfer":
                        free += 1
                        families.add(str(row["family"]))
                    elif tier == "remedial_retry":
                        remedial += 1
                    else:
                        guided += 1
                else:
                    failure_streak += 1
                    last_failure = last_attempt
            cooldown = 0.0
            if failure_streak and last_failure:
                cooldown = last_failure + min(
                    FAILURE_COOLDOWN_MAX_SECONDS,
                    FAILURE_COOLDOWN_BASE_SECONDS * (2 ** (failure_streak - 1)),
                )
            capability = self._capability_stage(guided, free, families)
            connection.execute(
                """INSERT INTO native_semantic_transfer_concept_progress VALUES
                   (?,?,?,?,?,?,?,?,?,?,?)""",
                (concept_id, guided, remedial, free, json.dumps(sorted(families)),
                 failure_streak, cooldown, capability, last_failure, last_attempt, now),
            )

    def _record_progress(self, *, concept_id: str, evidence_tier: str,
                         family: str, correct: bool, now: float) -> dict[str, Any]:
        """Advance one concept only from independently demonstrated evidence."""
        with self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO native_semantic_transfer_concept_progress
                   (concept_id,updated_epoch) VALUES(?,?)""",
                (concept_id, now),
            )
            row = connection.execute(
                "SELECT * FROM native_semantic_transfer_concept_progress WHERE concept_id=?",
                (concept_id,),
            ).fetchone()
            guided = int(row["guided_successes"] or 0)
            remedial = int(row["remedial_successes"] or 0)
            free = int(row["free_successes"] or 0)
            families = set(json.loads(row["free_families_json"] or "[]"))
            failure_streak = int(row["failure_streak"] or 0)
            last_failure = row["last_failure_epoch"]
            cooldown = 0.0
            if correct:
                failure_streak = 0
                if evidence_tier == "free_transfer":
                    free += 1
                    families.add(family)
                elif evidence_tier == "remedial_retry":
                    remedial += 1
                else:
                    guided += 1
            else:
                failure_streak += 1
                last_failure = now
                cooldown = now + min(
                    FAILURE_COOLDOWN_MAX_SECONDS,
                    FAILURE_COOLDOWN_BASE_SECONDS * (2 ** (failure_streak - 1)),
                )
            capability = self._capability_stage(guided, free, families)
            connection.execute(
                """UPDATE native_semantic_transfer_concept_progress SET
                   guided_successes=?,remedial_successes=?,free_successes=?,
                   free_families_json=?,failure_streak=?,cooldown_until=?,
                   capability_stage=?,last_failure_epoch=?,last_attempt_epoch=?,updated_epoch=?
                   WHERE concept_id=?""",
                (guided, remedial, free, json.dumps(sorted(families)), failure_streak,
                 cooldown, capability, last_failure, now, now, concept_id),
            )
            acquired = connection.execute(
                "SELECT stage FROM acquired_concepts WHERE concept_id=?", (concept_id,),
            ).fetchone()
            stage_before = str(acquired["stage"] if acquired else "")
            stage_after = stage_before
            # Never demote retention/mastery. Early stages advance only when the
            # academy has direct evidence for that exact capability.
            if stage_before in CAPABILITY_ORDER and (
                CAPABILITY_ORDER[capability] > CAPABILITY_ORDER[stage_before]
            ):
                stage_after = capability
                connection.execute(
                    "UPDATE acquired_concepts SET stage=?,consecutive_passes=0,updated_epoch=? "
                    "WHERE concept_id=?",
                    (stage_after, now, concept_id),
                )
        return {
            "capability_stage": capability, "stage_before": stage_before,
            "stage_after": stage_after, "promoted": stage_after != stage_before,
            "guided_successes": guided, "remedial_successes": remedial,
            "free_successes": free, "distinct_free_families": len(families),
            "failure_streak": failure_streak, "cooldown_until": cooldown,
        }

    def _candidates(self, limit: int, *, prefer_advanced: bool = False) -> list[dict[str, Any]]:
        progression_order = (
            "CASE WHEN COALESCE(p.guided_successes,0)>=2 THEN 0 ELSE 1 END"
            if prefer_advanced else
            "CASE WHEN COALESCE(p.guided_successes,0)=1 THEN 0 "
            "WHEN COALESCE(p.guided_successes,0)=0 THEN 1 ELSE 2 END"
        )
        cohort_order = (
            "CASE WHEN cohort.status='active' THEN 0 ELSE 1 END"
            if prefer_advanced else
            "CASE WHEN cohort.status='active' THEN 1 ELSE 0 END"
        )
        now = time.time()
        utility_terms = ",".join(
            "'" + term.replace("'", "''") + "'" for term in sorted(HIGH_UTILITY_LEMMAS)
        )
        with self._connect() as connection:
            self._refresh_focused_cohort(connection)
            rows = connection.execute(
                f"""SELECT a.concept_id,a.lemma,a.sense_hash,a.stage,a.native_gloss,
                          a.features_json,a.relations_json,a.examples_json,
                          a.part_of_speech,a.attempts,a.correct_attempts,
                          COUNT(DISTINCT CASE WHEN e.event_type='remedial_correction' AND e.status='due'
                              THEN e.event_id END) AS remediation_due,
                          COUNT(DISTINCT c.academy_challenge_id) AS academy_uses
                          ,COUNT(DISTINCT CASE WHEN c.correct=1 THEN c.academy_challenge_id END)
                           AS academy_correct
                          ,COALESCE(p.guided_successes,0) AS guided_successes
                          ,COALESCE(p.remedial_successes,0) AS remedial_successes
                          ,COALESCE(p.free_successes,0) AS free_successes
                          ,COALESCE(p.free_families_json,'[]') AS free_families_json
                          ,COALESCE(p.failure_streak,0) AS failure_streak
                          ,COALESCE(p.cooldown_until,0) AS cooldown_until
                          ,COALESCE(p.capability_stage,'grounded') AS capability_stage
                          ,CASE WHEN cohort.status='active' THEN 1 ELSE 0 END AS focused_cohort
                          ,(
                            CASE WHEN COALESCE((SELECT gp.correct FROM native_english_practice_progress gp
                              WHERE gp.concept_id=a.concept_id AND gp.family='meaning_discrimination'),0)>=2 THEN 1 ELSE 0 END +
                            CASE WHEN COALESCE((SELECT gp.correct FROM native_english_practice_progress gp
                              WHERE gp.concept_id=a.concept_id AND gp.family='context_completion'),0)>=2 THEN 1 ELSE 0 END +
                            CASE WHEN COALESCE((SELECT gp.correct FROM native_english_practice_progress gp
                              WHERE gp.concept_id=a.concept_id AND gp.family='sentence_construction'),0)>=2 THEN 1 ELSE 0 END +
                            CASE WHEN COALESCE((SELECT gp.correct FROM native_english_practice_progress gp
                              WHERE gp.concept_id=a.concept_id AND gp.family='sentence_transformation'),0)>=1 THEN 1 ELSE 0 END +
                            CASE WHEN COALESCE((SELECT gp.correct FROM native_english_practice_progress gp
                              WHERE gp.concept_id=a.concept_id AND gp.family='reading_comprehension'),0)>=1 THEN 1 ELSE 0 END
                           ) AS practice_readiness_components
                          ,COALESCE((SELECT e2.expected_answer
                            FROM native_english_transfer_learning_events e2
                            WHERE e2.concept_id=a.concept_id
                              AND e2.event_type='remedial_correction' AND e2.status='due'
                            ORDER BY e2.created_epoch DESC LIMIT 1),'') AS correction_answer
                          ,COALESCE((SELECT e2.answer_reason
                            FROM native_english_transfer_learning_events e2
                            WHERE e2.concept_id=a.concept_id
                              AND e2.event_type='remedial_correction' AND e2.status='due'
                            ORDER BY e2.created_epoch DESC LIMIT 1),'') AS correction_reason
                   FROM acquired_concepts a
                   LEFT JOIN native_semantic_transfer_concept_progress p
                     ON p.concept_id=a.concept_id
                   LEFT JOIN native_english_transfer_learning_events e
                     ON e.concept_id=a.concept_id
                   LEFT JOIN native_semantic_transfer_academy_challenges c
                     ON c.concept_id=a.concept_id
                   LEFT JOIN native_semantic_transfer_cohort cohort
                     ON cohort.concept_id=a.concept_id
                   WHERE a.stage IN ('grounded','productive','retention_1d','retention_7d',
                                     'retention_30d','retention_90d','mastered',
                                     'contextual','recalled')
                     AND COALESCE(p.cooldown_until,0)<=?
                     AND INSTR(a.lemma,' ')=0
                     AND a.concept_id=(
                       SELECT a2.concept_id FROM acquired_concepts a2
                       WHERE a2.lemma=a.lemma ORDER BY
                       CASE a2.stage WHEN 'mastered' THEN 9 WHEN 'retention_90d' THEN 8
                       WHEN 'retention_30d' THEN 7 WHEN 'retention_7d' THEN 6
                       WHEN 'retention_1d' THEN 5 WHEN 'productive' THEN 4
                       WHEN 'contextual' THEN 3 WHEN 'recalled' THEN 2 ELSE 1 END DESC,
                       a2.updated_epoch DESC,a2.concept_id ASC LIMIT 1
                     )
                     AND NOT EXISTS (
                       SELECT 1 FROM native_semantic_transfer_academy_challenges recent
                       WHERE recent.concept_id=a.concept_id AND recent.status='rejected'
                         AND recent.created_epoch>?
                     )
                   GROUP BY a.concept_id
                   ORDER BY remediation_due DESC,
                     {cohort_order},
                     practice_readiness_components DESC,
                     {progression_order},
                     COALESCE(p.free_successes,0) DESC,
                     CASE WHEN a.lemma IN ({utility_terms}) THEN 0 ELSE 1 END,
                     CASE WHEN a.examples_json NOT IN ('','[]') THEN 0 ELSE 1 END,
                     CASE a.stage WHEN 'productive' THEN 0 WHEN 'retention_1d' THEN 1
                     WHEN 'retention_7d' THEN 2 WHEN 'retention_30d' THEN 3
                     WHEN 'retention_90d' THEN 4 WHEN 'mastered' THEN 5
                     WHEN 'contextual' THEN 6 ELSE 7 END,
                     academy_uses ASC,a.updated_epoch ASC LIMIT ?""",
                (now, now - 1800, max(1, int(limit))),
            ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in rows:
            value = dict(row)
            for source, target in (("features_json", "features"),
                                   ("relations_json", "relations"),
                                   ("examples_json", "examples")):
                try:
                    value[target] = json.loads(value.pop(source) or "[]")
                except json.JSONDecodeError:
                    value[target] = []
            with self._connect() as connection:
                recent = connection.execute(
                    """SELECT material FROM native_semantic_transfer_academy_challenges
                       WHERE concept_id=? AND status='attempted'
                       ORDER BY created_epoch DESC LIMIT 4""",
                    (value["concept_id"],),
                ).fetchall()
            value["recent_materials"] = [str(item["material"]) for item in recent]
            value["free_families"] = json.loads(value.pop("free_families_json") or "[]")
            value["needs_scaffold"] = (
                int(value.get("guided_successes") or 0) < 2
                or int(value.get("remediation_due") or 0) > 0
            )
            value["remedial_retry"] = int(value.get("remediation_due") or 0) > 0
            value["practice_transfer_ready"] = int(
                value.get("practice_readiness_components") or 0
            ) >= 5
            candidates.append(value)
        return candidates

    @staticmethod
    def _foundation_family(candidate: Mapping[str, Any]) -> str:
        pos = str(candidate.get("part_of_speech") or "")
        return "semantic_patient" if pos == "v" else (
            "property_inference" if pos in {"a", "s"} else "semantic_entity"
        )

    @staticmethod
    def _semantic_bridge(candidate: Mapping[str, Any]) -> str:
        stop = {
            "associated", "concept", "characterized", "relating", "having", "being",
            "any", "some", "something", "someone", "thing", "person", "property",
            "act", "action", "state", "used", "made", "form", "kind", "type",
        }
        values: list[str] = []
        relations = candidate.get("relations") or {}
        for kind in ("synonym", "hypernym", "antonym", "hyponym"):
            values.extend(str(value).lower() for value in relations.get(kind) or [])
        values.extend(str(value).lower() for value in candidate.get("features") or [])
        for value in values:
            words = [word for word in re.findall(r"[a-z][a-z'-]+", value)
                     if word not in stop and word != str(candidate.get("lemma") or "").lower()]
            if words:
                return words[0]
        return str(candidate.get("lemma") or "meaning")

    def _compile_foundation(self, candidate: Mapping[str, Any], cycle_number: int) -> dict[str, str]:
        """Build transparent guided practice; this never counts as mastery."""
        names = ("Mireya", "Tavian", "Leona", "Kellan", "Amara", "Neryn", "Zeta",
                 "Owen", "Cassia", "Darian", "Elara", "Ivo", "Soren")
        recent = {_normal(value) for value in candidate.get("recent_materials") or []}
        lemma = str(candidate["lemma"])
        bridge = self._semantic_bridge(candidate)
        family = self._foundation_family(candidate)
        prior_successes = int(candidate.get("academy_correct") or 0)
        if family == "semantic_patient":
            options = [
                (names[(cycle_number + offset) % len(names)], auxiliary, obj)
                for offset, (auxiliary, obj) in enumerate((
                    ("will", "report"), ("did", "message"), ("will", "sensor"),
                    ("did", "sample"), ("will", "record"), ("did", "signal"),
                ))
            ]
            name, auxiliary, obj = next(
                (option for option in options
                 if _normal(f"{option[0]} {option[1]} {lemma} the {option[2]}.") not in recent),
                options[prior_successes % len(options)],
            )
            return {
                "concept_id": str(candidate["concept_id"]), "lemma": lemma,
                "family": family, "material": f"{name} {auxiliary} {lemma} the {obj}.",
                "question": f"Which object was affected by an action associated with {bridge}?",
                "expected_answer": obj,
                "answer_reason": f"The acquired action {lemma} is associated with {bridge}; {obj} is its object.",
            }
        if family == "property_inference":
            options = [
                (names[(cycle_number + offset) % len(names)], copula)
                for offset, copula in enumerate(("is", "was", "seems", "remained"))
            ]
            name, copula = next(
                (option for option in options
                 if _normal(f"{option[0]} {option[1]} {lemma}.") not in recent),
                options[prior_successes % len(options)],
            )
            return {
                "concept_id": str(candidate["concept_id"]), "lemma": lemma,
                "family": family, "material": f"{name} {copula} {lemma}.",
                "question": f"Which entity has the property associated with {bridge}?",
                "expected_answer": name,
                "answer_reason": f"The acquired property {lemma} is associated with {bridge} and applies to {name}.",
            }
        options = [
            (names[(cycle_number + offset) % len(names)], action, action_base)
            for offset, (action, action_base) in enumerate((
                ("observed", "observe"), ("inspected", "inspect"),
                ("measured", "measure"), ("recorded", "record"),
                ("examined", "examine"), ("catalogued", "catalogue"),
            ))
        ]
        name, action, action_base = next(
            (option for option in options
             if _normal(f"{option[0]} {option[1]} the {lemma}.") not in recent),
            options[prior_successes % len(options)],
        )
        return {
            "concept_id": str(candidate["concept_id"]), "lemma": lemma,
            "family": family, "material": f"{name} {action} the {lemma}.",
            "question": f"What did {name} {action_base} that is associated with {bridge}?",
            "expected_answer": lemma,
            "answer_reason": f"The acquired entity {lemma} is associated with {bridge} and is the direct object.",
        }

    @staticmethod
    def _prompt(candidates: list[dict[str, Any]], cycle_number: int) -> str:
        compact = [{
            "concept_id": row["concept_id"], "lemma": row["lemma"],
            "stage": row["stage"], "part_of_speech": row["part_of_speech"],
            "native_gloss": row["native_gloss"], "features": row["features"],
            "relations": row["relations"], "examples": row["examples"],
            "remediation_due": row["remediation_due"],
            "forbidden_recent_materials": row["recent_materials"],
            "guided_successes": row["guided_successes"],
            "free_transfer_successes": row["free_successes"],
            "free_transfer_families": row["free_families"],
            "remedial_retry": row["remedial_retry"],
            "verified_correction": {
                "answer": row.get("correction_answer") or "",
                "reason": row.get("correction_reason") or "",
            } if row["remedial_retry"] else None,
        } for row in candidates]
        candidate = candidates[0]
        foundational = bool(candidate.get("needs_scaffold"))
        if foundational:
            family = NativeSemanticTransferAcademy._foundation_family(candidate)
        else:
            family = str(candidate.get("required_transfer_family") or
                         NativeSemanticTransferAcademy._next_transfer_family(
                             candidate, cycle_number,
                         ))
        return f"""Select unfamiliar scenario slots for one sealed English transfer challenge.
You are the teacher, not the student or grader. The system has already fixed the target sense,
grammatical role, answer span and evidence family. You must not write the final question or answer.
Aion will answer later with Qwen disconnected.

REQUIRED FAMILY: {family}
ACQUIRED CONCEPT
{json.dumps(compact, ensure_ascii=False, separators=(',', ':'))}

Choose exactly one value from each list. Prefer a combination unlike the forbidden recent materials.
name: {json.dumps(TRANSFER_NAMES)}
patient: {json.dumps(TRANSFER_PATIENTS)}
context: {json.dumps(TRANSFER_CONTEXTS)}

Return only JSON:
{{"challenges":[{{"concept_id":"{candidate['concept_id']}","lemma":"{candidate['lemma']}",
"family":"{family}","name":"one allowed name","patient":"one allowed patient",
"context":"one allowed context"}}]}}"""

    def _verify(self, item: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[bool, list[str]]:
        problems: list[str] = []
        material = str(item.get("material") or "").strip()
        question = str(item.get("question") or "").strip()
        expected = str(item.get("expected_answer") or "").strip()
        reason = str(item.get("answer_reason") or "").strip()
        lemma = str(candidate["lemma"])
        if str(item.get("concept_id") or "") != candidate["concept_id"]:
            problems.append("concept_id_mismatch")
        if _normal(str(item.get("lemma") or "")) != _normal(lemma):
            problems.append("lemma_mismatch")
        if not material or not question or not expected or not reason:
            problems.append("missing_required_field")
        material_normal = _normal(material)
        expected_normal = _normal(expected)
        material_words = set(material_normal.split())
        expected_words = set(expected_normal.split())
        if (not expected_words or not expected_words.issubset(material_words)
                or expected_normal not in material_normal):
            problems.append("answer_not_grounded_in_material")
        lemma_root = _normal(lemma)
        if not any(word == lemma_root or word.startswith(lemma_root[:max(3, len(lemma_root)-2)])
                   for word in material_words):
            problems.append("target_not_in_material")
        question_words = set(_normal(question).split())
        if expected_words and expected_words.issubset(question_words):
            problems.append("answer_leaked_in_question")
        lowered_question = _normal(question)
        target_surface_intent = any(phrase in lowered_question for phrase in (
            "which word", "what word", "which term", "what term",
            "which action", "what action", "which verb", "what verb",
            "which property", "what property", "which state", "what state",
            "what is the status", "what is the characteristic",
            "action is associated", "word is associated",
        ))
        target_stem = lemma_root[:max(3, len(lemma_root) - 2)]
        if target_surface_intent and not any(
            word == lemma_root or word.startswith(target_stem) for word in expected_words
        ):
            problems.append("target_surface_answer_mismatch")
        if str(item.get("family") or "") not in FAMILIES:
            problems.append("unsupported_family")
        if _normal(material) in {_normal(value) for value in candidate.get("recent_materials") or []}:
            problems.append("repeated_material")
        signature = set(_normal(str(candidate.get("native_gloss") or "")).split())
        signature.update(_normal(" ".join(str(x) for x in candidate.get("features") or [])).split())
        if not (signature & set(_normal(reason + " " + question).split())):
            problems.append("meaning_not_grounded")
        family = str(item.get("family") or "")
        if bool(candidate.get("needs_scaffold")):
            required = self._foundation_family(candidate)
            if family != required:
                problems.append("foundation_family_mismatch")
            parsed = self.transfer.parse(material) if material else {"frame": {}}
            self.transfer._bind_sealed_target(parsed, str(candidate["concept_id"]))
            frame = dict(parsed.get("frame") or {})
            expected_normal = _normal(expected)
            grounded_role = (frame.get("subject") if required == "property_inference"
                             else frame.get("object"))
            if _normal(str(grounded_role or "")) != expected_normal:
                problems.append("foundation_answer_role_mismatch")
            target_seen = any(
                str(token.get("concept_id") or "") == str(candidate["concept_id"])
                for token in parsed.get("tokens") or []
            )
            if not target_seen:
                problems.append("foundation_target_not_parsed")
            question_signature = signature & set(_normal(question).split())
            if not question_signature:
                problems.append("foundation_question_missing_semantic_bridge")
        else:
            required_family = str(candidate.get("required_transfer_family") or "")
            if required_family and family != required_family:
                problems.append("advanced_family_mismatch")
            allowed = POS_TRANSFER_FAMILIES.get(
                str(candidate.get("part_of_speech") or ""),
                ("contextual_meaning", "paraphrase", "comparison"),
            )
            if family not in allowed:
                problems.append("part_of_speech_family_mismatch")
            if any(pattern in lowered_question
                   for pattern in METALINGUISTIC_QUESTION_PATTERNS):
                problems.append("metalinguistic_question")
            # A plausible explanation cannot rescue a question that contains
            # no meaning clue and can only be answered by surface matching.
            semantic_terms = signature - {lemma_root}
            if not (semantic_terms & question_words):
                problems.append("advanced_question_missing_semantic_bridge")
            parsed = self.transfer.parse(material) if material else {"tokens": []}
            self.transfer._bind_sealed_target(parsed, str(candidate["concept_id"]))
            target_tokens = [
                token for token in parsed.get("tokens") or []
                if str(token.get("concept_id") or "") == str(candidate["concept_id"])
            ]
            expected_pos = str(candidate.get("part_of_speech") or "")
            compatible_pos = ({"a", "s"} if expected_pos in {"a", "s"}
                              else {expected_pos})
            if (not target_tokens or not any(
                    str(token.get("pos") or "") in compatible_pos
                    for token in target_tokens)):
                problems.append("target_part_of_speech_mismatch")
            matching_clause: dict[str, Any] | None = None
            expected_role = ""
            for raw_clause in parsed.get("clauses") or []:
                clause = dict(raw_clause)
                if expected_pos == "v" and str(
                    (clause.get("action_evidence") or {}).get("concept_id") or ""
                ) == str(candidate["concept_id"]):
                    matching_clause, expected_role = clause, str(clause.get("object") or "")
                    break
                if expected_pos == "n" and str(
                    (clause.get("object_evidence") or {}).get("concept_id") or ""
                ) == str(candidate["concept_id"]):
                    matching_clause, expected_role = clause, str(clause.get("object") or "")
                    break
                if expected_pos in {"a", "s"} and str(
                    (clause.get("complement_evidence") or {}).get("concept_id") or ""
                ) == str(candidate["concept_id"]):
                    matching_clause, expected_role = clause, str(clause.get("subject") or "")
                    break
            if (matching_clause is None
                    or _normal(expected_role) != expected_normal):
                problems.append("advanced_answer_role_mismatch")
        return not problems, problems

    @staticmethod
    def _repair_prompt(candidate: Mapping[str, Any], item: Mapping[str, Any],
                       problems: list[str]) -> str:
        required = NativeSemanticTransferAcademy._foundation_family(candidate)
        if not candidate.get("needs_scaffold"):
            requested_family = str(candidate.get("required_transfer_family") or "")
            if not requested_family:
                requested_family = NativeSemanticTransferAcademy._next_transfer_family(
                    candidate, 0,
                )
            return f"""Your scenario-slot suggestion failed deterministic checks: {json.dumps(problems)}.
Choose replacement slots for a genuinely new advanced transfer challenge. The trusted system will
compile the final sentence, question, answer span and explanation. Do not write any of those fields.
Target concept ID: {candidate['concept_id']}
Target lemma: {candidate['lemma']}
Required transfer family: {requested_family}
Choose exactly one value from each allowed list:
name: {json.dumps(TRANSFER_NAMES)}
patient: {json.dumps(TRANSFER_PATIENTS)}
context: {json.dumps(TRANSFER_CONTEXTS)}
Return only JSON:
{{"challenges":[{{"concept_id":"{candidate['concept_id']}","lemma":"{candidate['lemma']}",
"family":"{requested_family}","name":"one allowed name","patient":"one allowed patient",
"context":"one allowed context"}}]}}"""
        return f"""Your proposed lesson failed deterministic checks: {json.dumps(problems)}.
Rewrite it once. Return only JSON with one item in challenges.
Target concept: {json.dumps({
    'concept_id': candidate['concept_id'], 'lemma': candidate['lemma'],
    'part_of_speech': candidate['part_of_speech'],
    'native_gloss': candidate['native_gloss'], 'features': candidate['features'],
    'relations': candidate['relations'], 'forbidden_recent_materials': candidate['recent_materials'],
}, ensure_ascii=False)}
Required family: {required}.
For semantic_patient: one-word proper-name subject + target verb + direct object; expected answer is the exact direct object.
For semantic_entity: one-word proper-name subject + simple transitive verb + target as direct object; expected answer is the target object.
For property_inference: one-word proper-name subject + copula + target adjective; expected answer is the named subject.
The question must paraphrase meaning using an exact supplied feature/relation term. No negation, clauses,
coordination, definitions, quotation, comparison, metalinguistic wording, or repeated material.
Fields: concept_id, lemma, family, material, question, expected_answer, answer_reason."""

    def run_cycle(self, *, teacher_client: Callable[[str], Mapping[str, Any]],
                  limit: int = 4) -> dict[str, Any]:
        with self._connect() as connection:
            cycle_number = int(connection.execute(
                "SELECT COUNT(*) FROM native_semantic_transfer_academy_cycles"
            ).fetchone()[0])
        requested = max(1, min(int(limit), 12))
        if requested == 1:
            candidates = self._candidates(
                1, prefer_advanced=(cycle_number % 4 != 0),
            )
        else:
            # Concentrate most work on a bounded transfer cohort. Foundations
            # continue at a lower rate so acquisition does not stop entirely.
            advanced_pool = [
                row for row in self._candidates(requested * 3, prefer_advanced=True)
                if not row.get("needs_scaffold")
            ]
            scaffold_pool = [
                row for row in self._candidates(requested * 3, prefer_advanced=False)
                if row.get("needs_scaffold")
            ]
            advanced_slots = max(1, min(
                requested - 1,
                int(round(requested * ADVANCED_TRANSFER_SHARE)),
            ))
            candidates = advanced_pool[:advanced_slots]
            seen = {str(row["concept_id"]) for row in candidates}
            candidates.extend(
                row for row in scaffold_pool
                if str(row["concept_id"]) not in seen
            )
            candidates = candidates[:requested]
            if len(candidates) < requested:
                for row in (*advanced_pool, *self._candidates(requested * 3)):
                    if str(row["concept_id"]) in {str(x["concept_id"]) for x in candidates}:
                        continue
                    candidates.append(row)
                    if len(candidates) >= requested:
                        break
        if not candidates:
            return {"status": "awaiting_acquired_concepts", "generated": 0,
                    "verified": 0, "attempted": 0, "correct": 0,
                    "model_used_for_student_answers": False}
        teacher_model = "local-qwen"
        results: list[dict[str, Any]] = []
        rejected = 0
        generated = 0
        now = time.time()
        # Foundation drills are deterministic and compiled locally. Qwen is
        # reserved for one advanced concept at a time so it cannot omit items
        # from a batch or leak one concept's answer into another challenge.
        for candidate_index, candidate in enumerate(candidates):
            is_foundation = bool(candidate.get("needs_scaffold"))
            if not is_foundation:
                candidate["required_transfer_family"] = self._next_transfer_family(
                    candidate, cycle_number + candidate_index,
                )
            foundation_compiled = False
            transfer_contract_compiled = False
            teacher_slot_fallback = False
            if is_foundation:
                item = self._compile_foundation(candidate, cycle_number + candidate_index)
                foundation_compiled = True
                verified, problems = self._verify(item, candidate)
            else:
                raw_item: dict[str, Any] = {}
                try:
                    response = dict(teacher_client(
                        self._prompt([candidate], cycle_number + candidate_index)
                    ))
                    teacher_model = str(response.get("model") or teacher_model)
                    payload = _json_object(str(response.get("content") or ""))
                    items = payload.get("challenges")
                    if not isinstance(items, list):
                        raise ValueError("teacher_response_missing_challenges")
                    generated += len(items)
                    raw_item = next(
                        (dict(raw) for raw in items if isinstance(raw, Mapping)
                         and str(raw.get("concept_id") or "") == str(candidate["concept_id"])),
                        {},
                    )
                    teacher_slot_fallback = not bool(raw_item)
                except Exception:
                    # Teacher variation is optional. A malformed or missing
                    # slot response must not stop the sealed native exam.
                    teacher_slot_fallback = True
                    raw_item = {}
                item = self._compile_transfer_contract(
                    candidate, raw_item, cycle_number + candidate_index,
                )
                transfer_contract_compiled = bool(item)
                verified, problems = (
                    self._verify(item, candidate) if item
                    else (False, ["unsupported_transfer_contract"])
                )
            evidence_tier = (
                "remedial_retry" if candidate.get("remedial_retry") else
                "guided_foundation" if is_foundation else "free_transfer"
            )
            repair_attempted = False
            if not verified and not is_foundation:
                repair_attempted = True
                try:
                    repair_response = dict(teacher_client(
                        self._repair_prompt(candidate, item, problems)
                    ))
                    repaired_payload = _json_object(str(repair_response.get("content") or ""))
                    repaired_items = repaired_payload.get("challenges") or []
                    if repaired_items and isinstance(repaired_items[0], Mapping):
                        item = self._compile_transfer_contract(
                            candidate, dict(repaired_items[0]),
                            cycle_number + candidate_index + 1,
                        )
                        transfer_contract_compiled = bool(item)
                        verified, problems = self._verify(item, candidate)
                except Exception as exc:
                    problems = [*problems, f"teacher_repair_failed:{type(exc).__name__}"]
            if not verified and is_foundation:
                compiled = self._compile_foundation(candidate, cycle_number)
                compiled_verified, compiled_problems = self._verify(compiled, candidate)
                if compiled_verified:
                    item, verified, problems = compiled, True, []
                    foundation_compiled = True
                else:
                    problems = [*problems, *[f"compiler:{p}" for p in compiled_problems]]
            if not verified:
                rejected += 1
            academy_id = _identifier("semantic_academy_", [candidate["concept_id"], item, now])
            row = {
                "academy_challenge_id": academy_id,
                "concept_id": candidate["concept_id"], "lemma": candidate["lemma"],
                "verified": verified, "problems": problems,
                "teacher_repair_attempted": repair_attempted,
                "foundation_compiled": foundation_compiled,
                "transfer_contract_compiled": transfer_contract_compiled,
                "teacher_slot_fallback": teacher_slot_fallback,
                "evidence_tier": evidence_tier,
            }
            if not verified:
                with self._connect() as connection:
                    connection.execute(
                        """INSERT INTO native_semantic_transfer_academy_challenges VALUES
                           (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (academy_id, "", candidate["concept_id"], candidate["lemma"],
                         candidate["sense_hash"], candidate["stage"],
                         str(item.get("family") or "invalid"), str(item.get("material") or ""),
                         str(item.get("question") or ""), str(item.get("expected_answer") or ""),
                         str(item.get("answer_reason") or ""), teacher_model,
                        json.dumps({"verified": False, "problems": problems,
                                     "teacher_repair_attempted": repair_attempted,
                                     "foundation_compiled": foundation_compiled,
                                     "transfer_contract_compiled": transfer_contract_compiled,
                                     "teacher_slot_fallback": teacher_slot_fallback}),
                         "rejected", None, now, None),
                    )
                results.append(row)
                continue
            challenge = self.transfer.create_challenge(
                kind="sentence_qa", material=str(item["material"]),
                question=str(item["question"]), expected_answer=str(item["expected_answer"]),
                answer_reason=str(item["answer_reason"]), source="local_qwen_teacher_sealed",
                learning_target_concept_id=str(candidate["concept_id"]),
            )
            attempt = self.transfer.attempt(challenge["challenge_id"])
            progress = self._record_progress(
                concept_id=str(candidate["concept_id"]), evidence_tier=evidence_tier,
                family=str(item["family"]), correct=attempt.get("correct") is True,
                now=time.time(),
            )
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO native_semantic_transfer_academy_challenges VALUES
                       (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (academy_id, challenge["challenge_id"], candidate["concept_id"],
                     candidate["lemma"], candidate["sense_hash"], candidate["stage"],
                     str(item["family"]), str(item["material"]), str(item["question"]),
                     str(item["expected_answer"]), str(item["answer_reason"]), teacher_model,
                     json.dumps({"verified": True, "checks": ["concept_id", "answer_span",
                                "target_surface", "no_answer_leak", "meaning_overlap"],
                                "teacher_repair_attempted": repair_attempted,
                                "foundation_compiled": foundation_compiled,
                                "transfer_contract_compiled": transfer_contract_compiled,
                                "teacher_slot_fallback": teacher_slot_fallback,
                                "evidence_tier": evidence_tier,
                                "progress": progress}),
                     "attempted", int(bool(attempt.get("correct"))), now, time.time()),
                )
            row["attempt"] = attempt
            row["progress"] = progress
            results.append(row)
        attempted = [row for row in results if "attempt" in row]
        correct = sum(row["attempt"].get("correct") is True for row in attempted)
        reinforced = sum(int((row["attempt"].get("learning_update") or {}).get("reinforced") or 0)
                         for row in attempted)
        remediation = sum(int((row["attempt"].get("learning_update") or {}).get("remediation_due") or 0)
                          for row in attempted)
        compiled_foundations = sum(bool(row.get("foundation_compiled")) for row in attempted)
        compiled_transfers = sum(bool(row.get("transfer_contract_compiled")) for row in attempted)
        teacher_slot_fallbacks = sum(bool(row.get("teacher_slot_fallback")) for row in attempted)
        guided_foundations = sum(
            row.get("evidence_tier") == "guided_foundation" for row in attempted
        )
        remedial_retries = sum(
            row.get("evidence_tier") == "remedial_retry" for row in attempted
        )
        cycle = {
            "status": "completed", "teacher_model": teacher_model,
            "generated": generated, "verified": len(attempted), "rejected": rejected,
            "attempted": len(attempted), "correct": correct,
            "reinforced": reinforced, "remediation_due": remediation,
            "compiled_foundations": compiled_foundations,
            "compiled_transfer_contracts": compiled_transfers,
            "teacher_slot_fallbacks": teacher_slot_fallbacks,
            "guided_foundations": guided_foundations,
            "remedial_retries": remedial_retries,
            "free_transfer_attempts": len(attempted) - guided_foundations - remedial_retries,
            "concepts": [{"lemma": row["lemma"], "concept_id": row["concept_id"],
                          "verified": row["verified"],
                          "foundation_compiled": row.get("foundation_compiled", False),
                          "transfer_contract_compiled": row.get(
                              "transfer_contract_compiled", False,
                          ),
                          "correct": (row.get("attempt") or {}).get("correct"),
                          "progress": row.get("progress")}
                         for row in results],
            "model_used_for_student_answers": False,
            "teacher_saw_student_answer": False,
            "answer_key_withheld_until_after_student_answer": True,
        }
        cycle_id = _identifier("semantic_academy_cycle_", [cycle_number, now, cycle])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_semantic_transfer_academy_cycles VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (cycle_id, teacher_model, generated, len(attempted), rejected, len(attempted),
                 correct, reinforced, remediation, json.dumps(cycle), time.time()),
            )
        cycle["cycle_id"] = cycle_id
        return cycle

    def metrics(self) -> dict[str, Any]:
        with self._read_connect() as connection:
            row = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(generated),0),COALESCE(SUM(verified),0),
                          COALESCE(SUM(rejected),0),COALESCE(SUM(attempted),0),
                          COALESCE(SUM(correct),0),COALESCE(SUM(reinforced),0),
                          COALESCE(SUM(remediation_due),0),MAX(created_epoch)
                   FROM native_semantic_transfer_academy_cycles"""
            ).fetchone()
            latest = connection.execute(
                "SELECT teacher_model,detail_json FROM native_semantic_transfer_academy_cycles ORDER BY created_epoch DESC LIMIT 1"
            ).fetchone()
            valid_totals = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(correct),0)
                   FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted'"""
            ).fetchone()
            eligible = int(connection.execute(
                "SELECT COUNT(*) FROM acquired_concepts WHERE stage!='encountered'"
            ).fetchone()[0])
            compiled = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted' AND verifier_json LIKE '%\"foundation_compiled\": true%'"""
            ).fetchone()[0])
            compiled_transfers = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted'
                     AND verifier_json LIKE '%\"transfer_contract_compiled\": true%'"""
            ).fetchone()[0])
            slot_fallbacks = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted'
                     AND verifier_json LIKE '%\"teacher_slot_fallback\": true%'"""
            ).fetchone()[0])
            guided = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted' AND verifier_json LIKE '%\"evidence_tier\": \"guided_foundation\"%'"""
            ).fetchone()[0])
            free_transfer = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted' AND verifier_json LIKE '%\"evidence_tier\": \"free_transfer\"%'"""
            ).fetchone()[0])
            free_correct = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted' AND correct=1
                     AND verifier_json LIKE '%\"evidence_tier\": \"free_transfer\"%'"""
            ).fetchone()[0])
            recent_free_rows = connection.execute(
                """SELECT correct FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted'
                     AND verifier_json LIKE '%\"evidence_tier\": \"free_transfer\"%'
                   ORDER BY created_epoch DESC LIMIT 25"""
            ).fetchall()
            remedial_retries = int(connection.execute(
                """SELECT COUNT(*) FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted'
                     AND verifier_json LIKE '%\"evidence_tier\": \"remedial_retry\"%'"""
            ).fetchone()[0])
            progress_rows = connection.execute(
                """SELECT capability_stage,COUNT(*) AS count
                   FROM native_semantic_transfer_concept_progress
                   GROUP BY capability_stage"""
            ).fetchall()
            capability_counts = {str(item["capability_stage"]): int(item["count"])
                                 for item in progress_rows}
            cohort_rows = connection.execute(
                """SELECT status,COUNT(*) AS count
                   FROM native_semantic_transfer_cohort GROUP BY status"""
            ).fetchall()
            cohort_counts = {str(item["status"]): int(item["count"])
                             for item in cohort_rows}
            cohort_pipeline = connection.execute(
                """SELECT
                     SUM(CASE WHEN p.free_successes=0 THEN 1 ELSE 0 END),
                     SUM(CASE WHEN p.free_successes=1 THEN 1 ELSE 0 END),
                     SUM(CASE WHEN p.free_successes=2 THEN 1 ELSE 0 END),
                     SUM(CASE WHEN p.free_successes=3 THEN 1 ELSE 0 END),
                     SUM(CASE WHEN p.free_successes>=4
                               AND p.capability_stage<>'productive' THEN 1 ELSE 0 END)
                   FROM native_semantic_transfer_cohort c
                   JOIN native_semantic_transfer_concept_progress p
                     ON p.concept_id=c.concept_id
                   WHERE c.status='active'"""
            ).fetchone()
            cooling_down = int(connection.execute(
                "SELECT COUNT(*) FROM native_semantic_transfer_concept_progress WHERE cooldown_until>?",
                (time.time(),),
            ).fetchone()[0])
            recent = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END),0)
                   FROM native_semantic_transfer_academy_challenges
                   WHERE status='attempted' AND created_epoch>?""",
                (time.time() - 3600,),
            ).fetchone()
            remediation = connection.execute(
                """SELECT
                   SUM(CASE WHEN status='due' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status='verified' THEN 1 ELSE 0 END)
                   FROM native_english_transfer_learning_events
                   WHERE event_type='remedial_correction'"""
            ).fetchone()
        attempts = int(valid_totals[0] or 0)
        correct = int(valid_totals[1] or 0)
        return {
            "cycles": int(row[0] or 0), "generated": int(row[1] or 0),
            "verified": int(row[2] or 0), "rejected": int(row[3] or 0),
            "attempted": attempts, "correct": correct,
            "accuracy": round(correct / attempts, 4) if attempts else None,
            "reinforced": int(row[6] or 0),
            "remedial_links_created": int(row[7] or 0),
            "remediation_due": int(remediation[0] or 0),
            "remediation_verified": int(remediation[1] or 0),
            "compiled_foundations": compiled,
            "compiled_transfer_contracts": compiled_transfers,
            "teacher_slot_fallbacks": slot_fallbacks,
            "guided_foundations": guided,
            "remedial_retries": remedial_retries,
            "free_transfer_attempts": free_transfer,
            "free_transfer_correct": free_correct,
            "free_transfer_accuracy": (
                round(free_correct / free_transfer, 4) if free_transfer else None
            ),
            "recent_free_transfer_attempts": len(recent_free_rows),
            "recent_free_transfer_correct": sum(
                int(item["correct"] or 0) for item in recent_free_rows
            ),
            "recent_free_transfer_accuracy": (
                round(sum(int(item["correct"] or 0) for item in recent_free_rows)
                      / len(recent_free_rows), 4) if recent_free_rows else None
            ),
            "legacy_unclassified_attempts": max(
                0, attempts - guided - remedial_retries - free_transfer
            ),
            "capability_counts": capability_counts,
            "recalled_use_concepts": capability_counts.get("recalled", 0),
            # "Reached contextual" is cumulative: productive concepts have
            # necessarily passed through contextual use.  Retain the exact
            # current-stage count separately for diagnostics.
            "contextual_use_concepts": (
                capability_counts.get("contextual", 0)
                + capability_counts.get("productive", 0)
            ),
            "currently_contextual_use_concepts": capability_counts.get("contextual", 0),
            "productive_use_concepts": capability_counts.get("productive", 0),
            "focused_cohort_size": FOCUSED_COHORT_SIZE,
            "focused_cohort_active": cohort_counts.get("active", 0),
            "focused_cohort_graduated": cohort_counts.get("graduated", 0),
            "focused_cohort_pipeline": {
                "zero_free_successes": int(cohort_pipeline[0] or 0),
                "one_free_success": int(cohort_pipeline[1] or 0),
                "two_free_successes": int(cohort_pipeline[2] or 0),
                "three_free_successes": int(cohort_pipeline[3] or 0),
                "four_plus_needing_family_variety": int(cohort_pipeline[4] or 0),
            },
            "advanced_transfer_share": ADVANCED_TRANSFER_SHARE,
            "concepts_cooling_down": cooling_down,
            "attempts_last_hour": int(recent[0] or 0),
            "correct_last_hour": int(recent[1] or 0),
            "last_cycle_epoch": row[8], "eligible_acquired_concepts": eligible,
            "teacher_model": str(latest["teacher_model"] if latest else ""),
            "last_cycle": json.loads(latest["detail_json"]) if latest else None,
            "model_used_for_student_answers": False,
        }


__all__ = ["FAMILIES", "NativeSemanticTransferAcademy"]
