"""AION's governed native vocabulary acquisition and Wordwall practice engine.

The imported lexicon is reference material, not an achievement claim.  This
module creates separate sense-level concept capsules, tests them without model
access, schedules delayed retention, and promotes only demonstrated knowledge
into AION's active vocabulary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping, Sequence

from backend.modules.aion_cognition.native_lexical_intelligence import (
    NativeLexicalIntelligence,
    _normalise_lemma,
    _tokens,
)


FOUNDATION_WORDS = (
    "person", "people", "thing", "place", "time", "day", "world", "life", "work",
    "part", "way", "idea", "meaning", "word", "language", "question", "answer",
    "true", "false", "same", "different", "possible", "certain", "uncertain",
    "know", "learn", "understand", "remember", "forget", "think", "reason", "explain",
    "compare", "decide", "choose", "make", "use", "change", "move", "give", "take",
    "before", "after", "during", "because", "cause", "effect", "condition", "exception",
    "evidence", "claim", "fact", "source", "result", "method", "problem", "solution",
    "good", "bad", "large", "small", "high", "low", "fast", "slow", "calm", "agitated",
    "bright", "dark", "open", "closed", "include", "exclude", "accept", "reject",
    "increase", "decrease", "similar", "opposite", "specific", "general", "literal",
    "context", "subject", "object", "action", "property", "state", "reference",
    "sentence", "paragraph", "document", "speaker", "intention", "implication",
    "number", "quantity", "science", "history", "engineering", "mathematics", "computer",
    "business", "finance", "law", "health", "risk", "safe", "reliable", "verify",
)

ACTIVE_STAGES = {"retention_1d", "retention_7d", "retention_30d", "retention_90d", "mastered"}
STAGE_ORDER = (
    "grounded", "recalled", "contextual", "productive",
    "retention_1d", "retention_7d", "retention_30d", "retention_90d", "mastered",
)
NEXT_STAGE = {stage: STAGE_ORDER[index + 1] for index, stage in enumerate(STAGE_ORDER[:-1])}
DEFAULT_RETENTION_SECONDS = {
    "retention_1d": 86400.0,
    "retention_7d": 7 * 86400.0,
    "retention_30d": 30 * 86400.0,
    "retention_90d": 90 * 86400.0,
}


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def _clean_features(definition: str, lemma: str, limit: int = 12) -> list[str]:
    meaningful = _tokens(definition)
    values = [token for token in re.findall(r"[a-z][a-z'-]+", definition.lower())
              if token in meaningful and token != lemma and token not in {"someone", "something"}]
    return list(dict.fromkeys(values))[:limit]


class NativeWordwallLearning:
    """Sense-level acquisition, closed-book practice and delayed retention."""

    def __init__(
        self, *, repo_root: Path | str,
        lexical: NativeLexicalIntelligence | None = None,
        retention_seconds: Mapping[str, float] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.retention_seconds = {**DEFAULT_RETENTION_SECONDS, **dict(retention_seconds or {})}
        self._initialize()
        self._repair_grounded_capsules()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS acquired_concepts (
                    concept_id TEXT PRIMARY KEY,
                    lemma TEXT NOT NULL,
                    sense_hash TEXT NOT NULL,
                    reference_definition TEXT NOT NULL,
                    native_gloss TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    relations_json TEXT NOT NULL,
                    examples_json TEXT NOT NULL,
                    part_of_speech TEXT NOT NULL DEFAULT '',
                    reference_source TEXT NOT NULL,
                    teacher_lesson_id TEXT NOT NULL DEFAULT '',
                    stage TEXT NOT NULL,
                    consecutive_passes INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    correct_attempts INTEGER NOT NULL DEFAULT 0,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    encountered_epoch REAL NOT NULL,
                    grounded_epoch REAL,
                    active_epoch REAL,
                    mastered_epoch REAL,
                    last_practice_epoch REAL,
                    next_review_epoch REAL,
                    updated_epoch REAL NOT NULL,
                    UNIQUE(lemma,sense_hash)
                );
                CREATE INDEX IF NOT EXISTS acquired_concept_stage
                    ON acquired_concepts(stage,next_review_epoch,updated_epoch);
                CREATE INDEX IF NOT EXISTS acquired_concept_lemma
                    ON acquired_concepts(lemma,stage);
                CREATE TABLE IF NOT EXISTS native_wordwall_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    concept_id TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    stage_before TEXT NOT NULL,
                    exercise_family TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    student_answer TEXT,
                    expected_answer TEXT NOT NULL,
                    score REAL NOT NULL,
                    correct INTEGER NOT NULL,
                    expected_withheld INTEGER NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    teacher_lesson_id TEXT NOT NULL DEFAULT '',
                    created_epoch REAL NOT NULL,
                    FOREIGN KEY(concept_id) REFERENCES acquired_concepts(concept_id)
                );
                CREATE INDEX IF NOT EXISTS native_wordwall_attempt_concept
                    ON native_wordwall_attempts(concept_id,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_wordwall_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    attempted INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    promoted INTEGER NOT NULL,
                    newly_grounded INTEGER NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    detail_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                """
            )

    def _repair_grounded_capsules(self) -> None:
        """Keep pre-competence capsules aligned with the current feature extractor."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT concept_id,lemma,reference_definition FROM acquired_concepts "
                "WHERE stage='grounded'"
            ).fetchall()
            for row in rows:
                features = _clean_features(str(row["reference_definition"]), str(row["lemma"]))
                connection.execute(
                    "UPDATE acquired_concepts SET features_json=?,native_gloss=?,updated_epoch=? "
                    "WHERE concept_id=?",
                    (json.dumps(features), self._native_gloss(
                        str(row["lemma"]), str(row["reference_definition"]), features,
                    ), time.time(), row["concept_id"]),
                )

    def _native_gloss(self, lemma: str, definition: str, features: Sequence[str]) -> str:
        # Stored as AION's inspectable concept statement.  It is assembled from
        # semantic features rather than copied by the answer path at query time.
        core = list(features[:12])
        if not core:
            return definition
        if len(core) == 1:
            material = core[0]
        else:
            material = ", ".join(core[:-1]) + f" and {core[-1]}"
        return f"{lemma} is a concept associated with {material}"

    def _capsule_payload(
        self, entry: Mapping[str, Any], definition: str, teacher_lesson_id: str,
    ) -> dict[str, Any]:
        lemma = str(entry["lemma"])
        features = _clean_features(definition, lemma)
        relations = {
            relation: [row["target_lemma"] for row in entry.get("relations") or []
                       if row["relation"] == relation][:8]
            for relation in ("synonym", "antonym", "hypernym", "hyponym", "derivation")
        }
        return {
            "lemma": lemma,
            "definition": definition,
            "features": features,
            "native_gloss": self._native_gloss(lemma, definition, features),
            "relations": relations,
            "examples": list(entry.get("examples") or [])[:6],
            "part_of_speech": str(entry.get("part_of_speech") or ""),
            "reference_source": str(entry.get("source") or ""),
            "teacher_lesson_id": teacher_lesson_id,
        }

    def encounter(
        self, lemma: str, *, teacher_lesson_id: str = "", sense_definition: str = "",
    ) -> list[dict[str, Any]]:
        entry = self.lexical.lookup(lemma)
        if not entry or not entry.get("verified"):
            return []
        authority = dict(self.lexical.authority_provider())
        if not authority.get("allow_learn"):
            return []
        now = time.time()
        created: list[dict[str, Any]] = []
        # Acquire the primary sense first. Polysemy is introduced later through
        # an explicit sense-discrimination curriculum rather than inflating the
        # learned-word count with several untested senses at first encounter.
        definitions = ([sense_definition] if sense_definition else
                       list(entry.get("definitions") or [entry["definition"]])[:1])
        for definition in definitions:
            sense_hash = _hash([entry["lemma"], definition])[:24]
            concept_id = "aion_concept_" + sense_hash
            capsule = self._capsule_payload(entry, str(definition), teacher_lesson_id)
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO acquired_concepts(
                       concept_id,lemma,sense_hash,reference_definition,native_gloss,
                       features_json,relations_json,examples_json,part_of_speech,
                       reference_source,teacher_lesson_id,stage,encountered_epoch,
                       grounded_epoch,updated_epoch) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(lemma,sense_hash) DO UPDATE SET
                       teacher_lesson_id=CASE WHEN excluded.teacher_lesson_id!=''
                         THEN excluded.teacher_lesson_id ELSE acquired_concepts.teacher_lesson_id END,
                       updated_epoch=excluded.updated_epoch""",
                    (concept_id, capsule["lemma"], sense_hash, capsule["definition"],
                     capsule["native_gloss"], json.dumps(capsule["features"]),
                     json.dumps(capsule["relations"]), json.dumps(capsule["examples"]),
                     capsule["part_of_speech"], capsule["reference_source"],
                     teacher_lesson_id, "grounded", now, now, now),
                )
            created.append({"concept_id": concept_id, **capsule, "stage": "grounded"})
        return created

    def acquired(self, lemma: str, *, active_only: bool = False) -> list[dict[str, Any]]:
        clauses = ["lemma=?"]
        params: list[Any] = [_normalise_lemma(lemma)]
        if active_only:
            clauses.append("stage IN (?,?,?,?,?)")
            params.extend(sorted(ACTIVE_STAGES))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM acquired_concepts WHERE {' AND '.join(clauses)} "
                "ORDER BY CASE stage "
                "WHEN 'mastered' THEN 9 WHEN 'retention_90d' THEN 8 WHEN 'retention_30d' THEN 7 "
                "WHEN 'retention_7d' THEN 6 WHEN 'retention_1d' THEN 5 WHEN 'productive' THEN 4 "
                "WHEN 'contextual' THEN 3 WHEN 'recalled' THEN 2 ELSE 1 END DESC",
                tuple(params),
            ).fetchall()
        return [self._decode(row) for row in rows]

    def _decode(self, row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
        value = dict(row)
        value["features"] = json.loads(value.pop("features_json") or "[]")
        value["relations"] = json.loads(value.pop("relations_json") or "{}")
        value["examples"] = json.loads(value.pop("examples_json") or "[]")
        value["active_vocabulary"] = value["stage"] in ACTIVE_STAGES
        value["mastered"] = value["stage"] == "mastered"
        return value

    def _due_concepts(self, limit: int) -> list[dict[str, Any]]:
        now = time.time()
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM acquired_concepts
                   WHERE stage!='mastered' AND (
                     stage IN ('grounded','recalled','contextual','productive')
                     OR COALESCE(next_review_epoch,0)<=?)
                   ORDER BY CASE WHEN stage LIKE 'retention_%' THEN 0 ELSE 1 END,
                            COALESCE(next_review_epoch,0),updated_epoch
                   LIMIT ?""",
                (now, max(1, int(limit))),
            ).fetchall()
        return [self._decode(row) for row in rows]

    def _candidate_lemmas(self, limit: int, preferred: Sequence[str]) -> list[str]:
        ordered = list(dict.fromkeys(
            _normalise_lemma(word) for word in (*preferred, *FOUNDATION_WORDS) if word
        ))
        with self._connect() as connection:
            acquired = {str(row[0]) for row in connection.execute(
                "SELECT DISTINCT lemma FROM acquired_concepts"
            ).fetchall()}
            selected = [word for word in ordered if word not in acquired and self.lexical.lookup(word)]
            if len(selected) < limit:
                rows = connection.execute(
                    """SELECT l.lemma FROM lexemes l
                       LEFT JOIN acquired_concepts a ON a.lemma=l.lemma
                       WHERE l.verified=1 AND a.lemma IS NULL
                         AND l.lemma GLOB '[a-z]*' AND INSTR(l.lemma,' ')=0
                         AND LENGTH(l.lemma) BETWEEN 3 AND 18
                       GROUP BY l.lemma
                       ORDER BY l.reinforcement_count DESC,
                         (SELECT COUNT(*) FROM relations r WHERE r.source_lemma=l.lemma) DESC,
                         LENGTH(l.lemma),l.lemma LIMIT ?""",
                    (max(limit * 3, 24),),
                ).fetchall()
                selected.extend(str(row[0]) for row in rows if str(row[0]) not in selected)
        return selected[:limit]

    def _exercise(self, concept: Mapping[str, Any]) -> dict[str, Any]:
        stage = str(concept["stage"])
        lemma = str(concept["lemma"])
        relations = dict(concept.get("relations") or {})
        examples = list(concept.get("examples") or [])
        if stage == "grounded":
            family, prompt = "meaning_recall", f"Explain the learned meaning of '{lemma}'."
            expected = str(concept["reference_definition"])
        elif stage == "recalled" and (relations.get("synonym") or relations.get("antonym")):
            relation = "synonym" if relations.get("synonym") else "antonym"
            family = f"{relation}_recall"
            prompt = f"Give one learned {relation} of '{lemma}'."
            expected = str(relations[relation][0])
        elif stage == "recalled":
            family = "feature_recall"
            prompt = f"State the semantic features you acquired for '{lemma}'."
            expected = " ".join(concept.get("features") or [])
        elif stage == "contextual" and any(re.search(
                rf"\b{re.escape(lemma)}\b", item, re.I) for item in examples):
            family = "context_completion"
            example = next((item for item in examples if re.search(
                rf"\b{re.escape(lemma)}\b", item, re.I)))
            prompt = re.sub(rf"\b{re.escape(lemma)}\b", "_____", example, count=1, flags=re.I)
            expected = lemma
        elif stage == "contextual":
            family = "context_distinction"
            feature = str((concept.get("features") or ["unknown"])[0])
            prompt = f"Which acquired concept matches the contextual feature '{feature}'?"
            expected = lemma
        elif stage == "productive":
            family = "productive_explanation"
            prompt = f"Explain '{lemma}' from your acquired concept without consulting the reference."
            expected = " ".join(concept.get("features") or [])
        else:
            family = "retention_transfer"
            prompt = f"After a delay, explain the retained concept '{lemma}' in your own structured words."
            expected = " ".join(concept.get("features") or [])
        return {"family": family, "prompt": prompt, "expected": expected}

    def _student_answer(self, concept: Mapping[str, Any], exercise: Mapping[str, Any]) -> str:
        """Closed-book student path: only the acquired capsule is consulted."""
        family = str(exercise["family"])
        if family == "meaning_recall":
            return str(concept["native_gloss"])
        if family == "synonym_recall":
            return str((concept.get("relations") or {}).get("synonym", [""])[0])
        if family == "antonym_recall":
            return str((concept.get("relations") or {}).get("antonym", [""])[0])
        if family == "context_completion":
            return str(concept["lemma"])
        if family == "context_distinction":
            return str(concept["lemma"])
        return str(concept["native_gloss"])

    def _score(self, answer: str, expected: str, family: str) -> float:
        if family in {"synonym_recall", "antonym_recall", "context_completion", "context_distinction"}:
            return 1.0 if _normalise_lemma(answer) == _normalise_lemma(expected) else 0.0
        expected_tokens = _tokens(expected)
        answer_tokens = _tokens(answer)
        if not expected_tokens:
            return 0.0
        return round(len(expected_tokens & answer_tokens) / len(expected_tokens), 4)

    def practise(self, concept: Mapping[str, Any]) -> dict[str, Any]:
        authority = dict(self.lexical.authority_provider())
        exercise = self._exercise(concept)
        student_view = {"family": exercise["family"], "prompt": exercise["prompt"]}
        answer = self._student_answer(concept, student_view)
        score = self._score(answer, str(exercise["expected"]), str(exercise["family"]))
        correct = score >= (0.60 if exercise["family"] in {
            "meaning_recall", "productive_explanation", "retention_transfer",
        } else 1.0)
        now = time.time()
        consecutive = int(concept.get("consecutive_passes") or 0) + 1 if correct else 0
        promoted = bool(correct and consecutive >= 2 and authority.get("allow_learn"))
        stage_before = str(concept["stage"])
        stage_after = NEXT_STAGE.get(stage_before, stage_before) if promoted else stage_before
        next_review = concept.get("next_review_epoch")
        active_epoch = concept.get("active_epoch")
        mastered_epoch = concept.get("mastered_epoch")
        if promoted:
            consecutive = 0
            if stage_after == "retention_1d":
                active_epoch = now
            if stage_after.startswith("retention_"):
                next_review = now + float(self.retention_seconds[stage_after])
            elif stage_after == "mastered":
                next_review, mastered_epoch = None, now
        attempt = {
            "concept_id": concept["concept_id"], "lemma": concept["lemma"],
            "stage_before": stage_before, "stage_after": stage_after,
            "family": exercise["family"], "prompt": exercise["prompt"],
            "student_answer": answer, "expected_answer": exercise["expected"],
            "score": score, "correct": correct, "promoted": promoted,
            "expected_withheld": "expected" not in student_view,
            "model_used": False, "cloud_used": False,
        }
        attempt_id = "native_wordwall_attempt_" + _hash([attempt, time.time_ns()])[:20]
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_wordwall_attempts(
                   attempt_id,concept_id,lemma,stage_before,exercise_family,prompt,
                   student_answer,expected_answer,score,correct,expected_withheld,
                   model_used,teacher_lesson_id,created_epoch)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (attempt_id, concept["concept_id"], concept["lemma"], stage_before,
                 exercise["family"], exercise["prompt"], answer, exercise["expected"],
                 score, int(correct), 1, 0, concept.get("teacher_lesson_id") or "", now),
            )
            connection.execute(
                """UPDATE acquired_concepts SET stage=?,consecutive_passes=?,
                   attempts=attempts+1,correct_attempts=correct_attempts+?,
                   failed_attempts=failed_attempts+?,active_epoch=?,mastered_epoch=?,
                   last_practice_epoch=?,next_review_epoch=?,updated_epoch=? WHERE concept_id=?""",
                (stage_after, consecutive, int(correct), int(not correct), active_epoch,
                 mastered_epoch, now, next_review, now, concept["concept_id"]),
            )
        return {"attempt_id": attempt_id, "authority": authority, **attempt}

    def run_cycle(
        self, *, limit: int = 12, preferred_lemmas: Sequence[str] = (),
        teacher_lesson_id: str = "",
    ) -> dict[str, Any]:
        authority = dict(self.lexical.authority_provider())
        if not authority.get("allow_learn"):
            return {"status": "blocked", "authority": authority, "model_used": False}
        concepts = self._due_concepts(limit)
        newly_grounded = 0
        if len(concepts) < limit:
            for lemma in self._candidate_lemmas(limit - len(concepts), preferred_lemmas):
                created = self.encounter(lemma, teacher_lesson_id=teacher_lesson_id)
                for row in created:
                    if len(concepts) >= limit:
                        break
                    current = self.acquired(row["lemma"])
                    match = next((item for item in current if item["concept_id"] == row["concept_id"]), None)
                    if match:
                        concepts.append(match)
                        newly_grounded += 1
                if len(concepts) >= limit:
                    break
        attempts = [self.practise(concept) for concept in concepts[:limit]]
        correct = sum(int(row["correct"]) for row in attempts)
        promoted = sum(int(row["promoted"]) for row in attempts)
        detail = {
            "attempted": len(attempts), "correct": correct, "promoted": promoted,
            "newly_grounded": newly_grounded,
            "families": sorted({row["family"] for row in attempts}),
            "lemmas": sorted({str(row["lemma"]) for row in attempts}),
        }
        cycle_id = "native_wordwall_cycle_" + _hash([detail, time.time_ns()])[:20]
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_wordwall_cycles(
                   cycle_id,attempted,correct,promoted,newly_grounded,model_used,
                   detail_json,created_epoch) VALUES(?,?,?,?,?,?,?,?)""",
                (cycle_id, len(attempts), correct, promoted, newly_grounded, 0,
                 json.dumps(detail, sort_keys=True), time.time()),
            )
        return {
            "status": "completed", "cycle_id": cycle_id, **detail,
            "attempts": attempts, "authority": authority,
            "expected_withheld": all(row["expected_withheld"] for row in attempts),
            "model_used": False, "cloud_used": False, "next_token_prediction": False,
        }

    def run_exact_cycle(
        self, *, lemmas: Sequence[str], teacher_lesson_id: str = "",
    ) -> dict[str, Any]:
        """Test exactly one acquired concept for every requested lemma.

        This is deliberately separate from ``run_cycle``.  The general learning
        scheduler is allowed to prioritise overdue retention work; a Semantic
        Spider page examination is not.  A page is coverage-certified only when
        every supplied word was independently attempted with the expected answer
        withheld and without model or cloud assistance.
        """
        authority = dict(self.lexical.authority_provider())
        requested = list(dict.fromkeys(
            clean for clean in (_normalise_lemma(word) for word in lemmas) if clean
        ))
        if not authority.get("allow_learn"):
            return {
                "status": "blocked", "authority": authority,
                "requested_lemmas": requested, "tested_lemmas": [],
                "missing_lemmas": requested, "coverage_count": 0,
                "coverage_total": len(requested), "coverage_ratio": 0.0,
                "page_certified": False, "model_used": False, "cloud_used": False,
                "next_token_prediction": False,
            }

        concepts: list[dict[str, Any]] = []
        missing: list[str] = []
        newly_grounded = 0
        for lemma in requested:
            acquired = self.acquired(lemma)
            if not acquired:
                created = self.encounter(lemma, teacher_lesson_id=teacher_lesson_id)
                newly_grounded += int(bool(created))
                acquired = self.acquired(lemma)
            if acquired:
                concepts.append(acquired[0])
            else:
                missing.append(lemma)

        attempts = [self.practise(concept) for concept in concepts]
        tested = [str(row["lemma"]) for row in attempts]
        correct = sum(int(row["correct"]) for row in attempts)
        promoted = sum(int(row["promoted"]) for row in attempts)
        exact_coverage = (
            len(tested) == len(requested)
            and set(tested) == set(requested)
            and not missing
        )
        integrity = all(
            row.get("expected_withheld") is True
            and row.get("model_used") is False
            and row.get("cloud_used") is False
            for row in attempts
        )
        page_certified = bool(requested and exact_coverage and integrity)
        detail = {
            "attempted": len(attempts), "correct": correct, "promoted": promoted,
            "newly_grounded": newly_grounded,
            "families": sorted({str(row["family"]) for row in attempts}),
            "lemmas": tested,
            "requested_lemmas": requested,
            "tested_lemmas": tested,
            "missing_lemmas": missing,
            "coverage_count": len(set(tested) & set(requested)),
            "coverage_total": len(requested),
            "coverage_ratio": round(
                len(set(tested) & set(requested)) / len(requested), 4
            ) if requested else 0.0,
            "page_certified": page_certified,
            "certification_kind": "exact_page_closed_book_v1",
        }
        cycle_id = "native_wordwall_cycle_" + _hash([detail, time.time_ns()])[:20]
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_wordwall_cycles(
                   cycle_id,attempted,correct,promoted,newly_grounded,model_used,
                   detail_json,created_epoch) VALUES(?,?,?,?,?,?,?,?)""",
                (cycle_id, len(attempts), correct, promoted, newly_grounded, 0,
                 json.dumps(detail, sort_keys=True), time.time()),
            )
        return {
            "status": "completed" if page_certified else "incomplete",
            "cycle_id": cycle_id, **detail, "attempts": attempts,
            "authority": authority, "expected_withheld": integrity,
            "model_used": False, "cloud_used": False,
            "next_token_prediction": False,
        }

    def metrics(self) -> dict[str, Any]:
        today_start = time.time() - (time.time() % 86400)
        with self._connect() as connection:
            reference_entries = int(connection.execute("SELECT COUNT(*) FROM lexemes").fetchone()[0])
            senses = int(connection.execute("SELECT COUNT(*) FROM acquired_concepts").fetchone()[0])
            words = int(connection.execute(
                "SELECT COUNT(DISTINCT lemma) FROM acquired_concepts"
            ).fetchone()[0])
            rows = connection.execute(
                "SELECT stage,COUNT(*) AS n,COUNT(DISTINCT lemma) AS words FROM acquired_concepts GROUP BY stage"
            ).fetchall()
            active = int(connection.execute(
                "SELECT COUNT(DISTINCT lemma) FROM acquired_concepts WHERE stage IN (?,?,?,?,?)",
                tuple(sorted(ACTIVE_STAGES)),
            ).fetchone()[0])
            mastered = int(connection.execute(
                "SELECT COUNT(DISTINCT lemma) FROM acquired_concepts WHERE stage='mastered'"
            ).fetchone()[0])
            mastered_today = int(connection.execute(
                "SELECT COUNT(*) FROM acquired_concepts WHERE mastered_epoch>=?", (today_start,),
            ).fetchone()[0])
            attempts = int(connection.execute("SELECT COUNT(*) FROM native_wordwall_attempts").fetchone()[0])
            correct = int(connection.execute(
                "SELECT COUNT(*) FROM native_wordwall_attempts WHERE correct=1"
            ).fetchone()[0])
            cycles = int(connection.execute("SELECT COUNT(*) FROM native_wordwall_cycles").fetchone()[0])
        return {
            "reference_entries": reference_entries,
            "encountered_words": words, "acquired_senses": senses,
            "active_vocabulary": active, "mastered_words": mastered,
            "mastered_today": mastered_today,
            "stages": {str(row["stage"]): {"senses": int(row["n"]),
                       "words": int(row["words"])} for row in rows},
            "practice_attempts": attempts,
            "practice_accuracy": round(correct / attempts, 4) if attempts else None,
            "cycles": cycles,
            "claim_boundary": "Reference entries are not learned vocabulary.",
        }


__all__ = ["ACTIVE_STAGES", "NativeWordwallLearning"]
