"""Governed native lexical intelligence for AION.

This is the live successor to the Phase 41/48 lexical prototypes.  It keeps
dictionary knowledge, semantic relations, native question answering and
closed-book practice in one local SQLite store.  No generative model is used
to answer or grade a task.  The expected answer is withheld until after the
student path has produced its answer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sqlite3
import time
from typing import Any, Callable, Iterable, Mapping, Sequence


SCHEMA_VERSION = 4
TOKEN_RE = re.compile(r"[a-z][a-z'-]{1,}", re.I)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "which", "with",
}


def _tokens(value: str) -> set[str]:
    return {
        token.lower() for token in TOKEN_RE.findall(str(value or ""))
        if token.lower() not in STOPWORDS
    }


def _normalise_lemma(value: str) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _past_form(word: str) -> str:
    irregular = {"be": "was", "do": "did", "have": "had", "make": "made",
                 "give": "gave", "take": "took", "write": "wrote", "read": "read"}
    if word in irregular:
        return irregular[word]
    if word.endswith("e"):
        return word + "d"
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        return word[:-1] + "ied"
    return word + "ed"


def _present_form(word: str) -> str:
    if word.endswith(("s", "sh", "ch", "x", "z")):
        return word + "es"
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def default_database_path(repo_root: Path | None = None) -> Path:
    configured = os.getenv("AION_NATIVE_LEXICON_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    root = Path(repo_root or Path.cwd()).resolve()
    external_candidates = [
        volume / "TessarisLearning/AION/native_lexical_intelligence.sqlite3"
        for volume in sorted(Path("/Volumes").glob("*"))
        if volume.is_dir()
    ] if Path("/Volumes").is_dir() else []
    existing_external = next((path for path in external_candidates if path.is_file()), None)
    if existing_external is not None:
        return existing_external.resolve()
    return root / "data" / "aion" / "native_lexical_intelligence.sqlite3"


def _default_authority() -> dict[str, Any]:
    try:
        from backend.modules.aion_cognition.cau_authority import compute_authority
        return dict(compute_authority(goal="native_lexical_learning"))
    except Exception as exc:  # fail closed
        return {"allow_learn": False, "deny_reason": f"CAU_UNAVAILABLE:{type(exc).__name__}"}


@dataclass(frozen=True)
class LexicalTask:
    task_id: str
    family: str
    prompt: str
    choices: tuple[str, ...]
    expected: str
    lemma: str
    source: str
    source_disjoint: bool = False

    def student_view(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "family": self.family,
            "prompt": self.prompt,
            "choices": list(self.choices),
            "lemma": self.lemma if self.family in {"synonym_choice", "antonym_choice"} else None,
            "response_mode": "selected" if self.choices else "free_response",
        }


class NativeLexicalIntelligence:
    """Persistent local word, relation, practice and native-QA runtime."""

    def __init__(
        self,
        database_path: Path | str | None = None,
        *,
        repo_root: Path | None = None,
        authority_provider: Callable[[], Mapping[str, Any]] | None = None,
    ) -> None:
        self.database_path = Path(database_path or default_database_path(repo_root))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.authority_provider = authority_provider or _default_authority
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @property
    def _is_removable_volume(self) -> bool:
        try:
            self.database_path.resolve().relative_to(Path("/Volumes").resolve())
            return True
        except ValueError:
            return False

    def _initialize(self) -> None:
        with self._connect() as connection:
            # WAL requires a reliable shared-memory sidecar and is unsafe on
            # several removable/card filesystems. Rollback journalling permits
            # governed multi-process access without WAL/SHM open failures.
            desired_journal = "delete" if self._is_removable_volume else "wal"
            current_journal = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if current_journal != desired_journal:
                connection.execute(f"PRAGMA journal_mode={desired_journal.upper()}")
            if self._is_removable_volume:
                connection.execute("PRAGMA synchronous=FULL")
            else:
                connection.execute("PRAGMA synchronous=NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS lexemes (
                    lemma TEXT PRIMARY KEY,
                    part_of_speech TEXT NOT NULL DEFAULT '',
                    definition TEXT NOT NULL,
                    definitions_json TEXT NOT NULL DEFAULT '[]',
                    examples_json TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    verified INTEGER NOT NULL DEFAULT 0,
                    reinforcement_count INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS relations (
                    source_lemma TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    target_lemma TEXT NOT NULL,
                    strength REAL NOT NULL,
                    source TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (source_lemma, relation, target_lemma)
                );
                CREATE INDEX IF NOT EXISTS relation_source_idx
                    ON relations(source_lemma, relation, strength DESC);
                CREATE TABLE IF NOT EXISTS lexical_senses (
                    sense_id TEXT PRIMARY KEY,
                    lemma TEXT NOT NULL,
                    part_of_speech TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    examples_json TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    verified INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    UNIQUE(lemma,part_of_speech,definition)
                );
                CREATE INDEX IF NOT EXISTS lexical_sense_lemma_pos
                    ON lexical_senses(lemma,part_of_speech);
                CREATE TABLE IF NOT EXISTS morphology_forms (
                    surface TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    part_of_speech TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    source TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(surface,lemma,part_of_speech,feature)
                );
                CREATE INDEX IF NOT EXISTS morphology_surface_idx
                    ON morphology_forms(surface,part_of_speech);
                CREATE TABLE IF NOT EXISTS practice_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    family TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    student_answer TEXT,
                    expected_answer TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    authority_allowed INTEGER NOT NULL,
                    project_family TEXT,
                    curriculum_family TEXT NOT NULL DEFAULT '',
                    evidence_source TEXT NOT NULL DEFAULT '',
                    source_disjoint INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS practice_family_idx
                    ON practice_attempts(family, created_epoch DESC);
                CREATE TABLE IF NOT EXISTS teacher_lessons (
                    lesson_id TEXT PRIMARY KEY,
                    stage_id TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    referenced_lemmas_json TEXT NOT NULL DEFAULT '[]',
                    teacher_model TEXT NOT NULL,
                    verified_reference_count INTEGER NOT NULL DEFAULT 0,
                    authority_allowed INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(practice_attempts)")
            }
            if "curriculum_family" not in columns:
                connection.execute(
                    "ALTER TABLE practice_attempts ADD COLUMN curriculum_family TEXT NOT NULL DEFAULT ''"
                )
            if "evidence_source" not in columns:
                connection.execute(
                    "ALTER TABLE practice_attempts ADD COLUMN evidence_source TEXT NOT NULL DEFAULT ''"
                )
            if "source_disjoint" not in columns:
                connection.execute(
                    "ALTER TABLE practice_attempts ADD COLUMN source_disjoint INTEGER NOT NULL DEFAULT 0"
                )
            connection.execute(
                "UPDATE practice_attempts SET curriculum_family=family WHERE curriculum_family=''"
            )
            connection.execute(
                """UPDATE practice_attempts SET curriculum_family='mixed'
                   WHERE project_family='native_english_mixed_transfer_v1'
                      OR project_family LIKE 'native_mixed_transfer_%'"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS practice_curriculum_family_idx "
                "ON practice_attempts(curriculum_family, created_epoch DESC)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )

    def ingest_records(
        self,
        records: Iterable[Mapping[str, Any]],
        *,
        source: str,
        source_ref: str = "",
        verified: bool = True,
        require_authority: bool = True,
    ) -> dict[str, Any]:
        authority = dict(self.authority_provider()) if require_authority else {
            "allow_learn": True, "source": "explicit_curated_seed_import"
        }
        if not authority.get("allow_learn"):
            return {
                "status": "blocked_by_learning_authority", "stored": 0,
                "authority": authority,
            }
        stored = relations = skipped = 0
        now = time.time()
        with self._connect() as connection:
            for raw in records:
                lemma = _normalise_lemma(str(raw.get("lemma") or raw.get("word") or ""))
                definitions = [
                    " ".join(str(item).split()) for item in (
                        raw.get("definitions") or [raw.get("definition")]
                    ) if str(item or "").strip()
                ]
                if not lemma or not definitions:
                    skipped += 1
                    continue
                examples = [
                    " ".join(str(item).split()) for item in (raw.get("examples") or [])
                    if str(item or "").strip()
                ]
                pos = str(raw.get("part_of_speech") or raw.get("pos") or "")
                connection.execute(
                    """
                    INSERT INTO lexemes(
                        lemma,part_of_speech,definition,definitions_json,examples_json,
                        source,source_ref,verified,created_epoch,updated_epoch
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(lemma) DO UPDATE SET
                        part_of_speech=excluded.part_of_speech,
                        definition=excluded.definition,
                        definitions_json=excluded.definitions_json,
                        examples_json=excluded.examples_json,
                        source=excluded.source,
                        source_ref=excluded.source_ref,
                        verified=MAX(lexemes.verified,excluded.verified),
                        updated_epoch=excluded.updated_epoch
                    """,
                    (lemma, pos, definitions[0], json.dumps(definitions), json.dumps(examples),
                     source, source_ref, int(verified), now, now),
                )
                for definition in definitions:
                    sense_id = "lexical_sense_" + _canonical_hash(
                        [lemma, pos, definition]
                    )[:24]
                    connection.execute(
                        """INSERT INTO lexical_senses(
                           sense_id,lemma,part_of_speech,definition,examples_json,
                           source,source_ref,verified,created_epoch
                           ) VALUES(?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(lemma,part_of_speech,definition) DO UPDATE SET
                           examples_json=excluded.examples_json,
                           verified=MAX(lexical_senses.verified,excluded.verified)""",
                        (sense_id, lemma, pos, definition, json.dumps(examples),
                         source, source_ref, int(verified), now),
                    )
                for form in raw.get("morphology") or []:
                    surface = _normalise_lemma(str(form.get("surface") or ""))
                    feature = str(form.get("feature") or "")
                    form_pos = str(form.get("part_of_speech") or pos)
                    if surface and feature:
                        connection.execute(
                            """INSERT OR REPLACE INTO morphology_forms(
                               surface,lemma,part_of_speech,feature,source,verified
                               ) VALUES(?,?,?,?,?,?)""",
                            (surface, lemma, form_pos, feature, source, int(verified)),
                        )
                stored += 1
                relation_groups = {
                    "synonym": raw.get("synonyms") or [],
                    "antonym": raw.get("antonyms") or [],
                    "hypernym": raw.get("hypernyms") or [],
                    "hyponym": raw.get("hyponyms") or [],
                    "derivation": raw.get("derivations") or [],
                }
                for relation, targets in relation_groups.items():
                    strength = {"synonym": .95, "antonym": -.95}.get(relation, .70)
                    for target_raw in targets:
                        target = _normalise_lemma(str(target_raw))
                        if not target or target == lemma:
                            continue
                        connection.execute(
                            """
                            INSERT INTO relations(source_lemma,relation,target_lemma,strength,source,verified)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(source_lemma,relation,target_lemma) DO UPDATE SET
                                strength=excluded.strength, source=excluded.source,
                                verified=MAX(relations.verified,excluded.verified)
                            """,
                            (lemma, relation, target, strength, source, int(verified)),
                        )
                        relations += 1
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES('last_ingest_epoch',?)",
                (str(now),),
            )
        return {
            "status": "ingested", "stored": stored, "relations": relations,
            "skipped": skipped, "authority": authority,
        }

    def stats(self) -> dict[str, Any]:
        with self._connect() as connection:
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
            words = int(connection.execute("SELECT COUNT(*) FROM lexemes").fetchone()[0])
            verified = int(connection.execute(
                "SELECT COUNT(*) FROM lexemes WHERE verified=1"
            ).fetchone()[0])
            relations = int(connection.execute("SELECT COUNT(*) FROM relations").fetchone()[0])
            attempts = int(connection.execute("SELECT COUNT(*) FROM practice_attempts").fetchone()[0])
            correct = int(connection.execute(
                "SELECT COUNT(*) FROM practice_attempts WHERE correct=1"
            ).fetchone()[0])
            lessons = int(connection.execute("SELECT COUNT(*) FROM teacher_lessons").fetchone()[0])
            last_ingest = connection.execute(
                "SELECT value FROM metadata WHERE key='last_ingest_epoch'"
            ).fetchone()
        return {
            "schema_version": SCHEMA_VERSION, "lexemes": words,
            "verified_lexemes": verified, "relations": relations,
            "practice_attempts": attempts, "verified_correct_attempts": correct,
            "teacher_lessons": lessons,
            "practice_accuracy": round(correct / attempts, 4) if attempts else None,
            "last_ingest_epoch": float(last_ingest[0]) if last_ingest else None,
            "database_path": str(self.database_path),
            "journal_mode": journal_mode,
            "removable_volume": self._is_removable_volume,
        }

    def practice_summary(self, *, family: str | None = None, limit: int = 200) -> dict[str, Any]:
        """Return closed-book results only; teacher content is never counted as evidence."""
        where = "WHERE curriculum_family=?" if family else ""
        params: tuple[Any, ...] = (family, max(1, int(limit))) if family else (max(1, int(limit)),)
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT curriculum_family,correct,authority_allowed,created_epoch,
                    source_disjoint,task_id,evidence_source FROM practice_attempts """
                f"{where} ORDER BY created_epoch DESC LIMIT ?", params,
            ).fetchall()
        total = len(rows)
        correct = sum(int(row["correct"]) for row in rows)
        governed = sum(int(row["authority_allowed"]) for row in rows)
        return {
            "family": family or "all", "attempts": total, "correct": correct,
            "accuracy": round(correct / total, 4) if total else None,
            "authority_allowed_attempts": governed,
            "unique_tasks": len({str(row["task_id"]) for row in rows}),
            "source_disjoint_attempts": sum(int(row["source_disjoint"]) for row in rows),
            "evidence_sources": sorted({str(row["evidence_source"]) for row in rows if row["evidence_source"]}),
            "first_attempt_epoch": min((float(row["created_epoch"]) for row in rows), default=None),
            "last_attempt_epoch": max((float(row["created_epoch"]) for row in rows), default=None),
            "retention_span_seconds": round(
                max((float(row["created_epoch"]) for row in rows), default=0.0)
                - min((float(row["created_epoch"]) for row in rows), default=0.0), 3,
            ) if rows else 0.0,
            "model_used_for_answers": False,
        }

    def record_teacher_lesson(
        self, *, stage_id: str, content: Mapping[str, Any], teacher_model: str,
        referenced_lemmas: Sequence[str],
    ) -> dict[str, Any]:
        """Store study material separately from verified lexical facts and exam evidence."""
        authority = dict(self.authority_provider())
        clean_lemmas = sorted({_normalise_lemma(item) for item in referenced_lemmas if item})
        verified = [lemma for lemma in clean_lemmas if (self.lookup(lemma) or {}).get("verified")]
        lesson_id = "native_english_lesson_" + _canonical_hash(
            [stage_id, content, teacher_model, time.time_ns()]
        )[:20]
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO teacher_lessons(
                   lesson_id,stage_id,content_json,referenced_lemmas_json,teacher_model,
                   verified_reference_count,authority_allowed,created_epoch
                   ) VALUES(?,?,?,?,?,?,?,?)""",
                (lesson_id, stage_id, json.dumps(dict(content), ensure_ascii=False),
                 json.dumps(clean_lemmas), teacher_model, len(verified),
                 int(bool(authority.get("allow_learn"))), time.time()),
            )
        return {
            "lesson_id": lesson_id, "stage_id": stage_id,
            "referenced_lemmas": clean_lemmas, "verified_references": verified,
            "authority": authority, "counts_as_exam_evidence": False,
        }

    def lookup(self, lemma: str) -> dict[str, Any] | None:
        clean = _normalise_lemma(lemma)
        if not clean:
            return None
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM lexemes WHERE lemma=?", (clean,)).fetchone()
            if row is None and clean.endswith("s"):
                row = connection.execute("SELECT * FROM lexemes WHERE lemma=?", (clean[:-1],)).fetchone()
            if row is None:
                return None
            relations = connection.execute(
                """SELECT relation,target_lemma,strength FROM relations
                   WHERE source_lemma=? ORDER BY ABS(strength) DESC, target_lemma LIMIT 24""",
                (row["lemma"],),
            ).fetchall()
        return {
            "lemma": row["lemma"], "part_of_speech": row["part_of_speech"],
            "definition": row["definition"],
            "definitions": json.loads(row["definitions_json"] or "[]"),
            "examples": json.loads(row["examples_json"] or "[]"),
            "source": row["source"], "source_ref": row["source_ref"],
            "verified": bool(row["verified"]),
            "relations": [dict(item) for item in relations],
        }

    def lookup_senses(self, lemma: str, part_of_speech: str | None = None) -> list[dict[str, Any]]:
        clean = _normalise_lemma(lemma)
        clause = "lemma=?" + (" AND part_of_speech=?" if part_of_speech else "")
        params: tuple[Any, ...] = (clean, part_of_speech) if part_of_speech else (clean,)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM lexical_senses WHERE {clause} "
                "ORDER BY verified DESC,part_of_speech,created_epoch", params,
            ).fetchall()
        return [{**dict(row), "examples": json.loads(row["examples_json"] or "[]")}
                for row in rows]

    def resolve_form(self, surface: str, part_of_speech: str = "v") -> list[dict[str, Any]]:
        clean = _normalise_lemma(surface)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT surface,lemma,part_of_speech,feature,source,verified
                   FROM morphology_forms WHERE surface=? AND part_of_speech=?
                   ORDER BY verified DESC,lemma""", (clean, part_of_speech),
            ).fetchall()
        return [dict(row) for row in rows]

    def related(self, lemma: str, relation: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        clean = _normalise_lemma(lemma)
        query = (
            "SELECT relation,target_lemma,strength FROM relations WHERE source_lemma=? "
            + ("AND relation=? " if relation else "")
            + "ORDER BY ABS(strength) DESC,target_lemma LIMIT ?"
        )
        params: tuple[Any, ...] = (clean, relation, limit) if relation else (clean, limit)
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def compare(self, first: str, second: str) -> dict[str, Any]:
        left, right = self.lookup(first), self.lookup(second)
        if not left or not right:
            return {"known": False, "first": left, "second": right}
        direct = next(
            (row for row in left["relations"] if row["target_lemma"] == right["lemma"]), None
        )
        overlap = _tokens(" ".join(left["definitions"])) & _tokens(" ".join(right["definitions"]))
        return {
            "known": True, "first": left, "second": right, "direct_relation": direct,
            "definition_overlap": sorted(overlap),
            "similarity": round(
                min(1.0, (abs(float(direct["strength"])) if direct else 0.0) + min(.6, len(overlap) * .1)), 3
            ),
        }

    def context(self, lemma: str, sentence: str) -> dict[str, Any]:
        entry = self.lookup(lemma)
        if not entry:
            return {"known": False, "lemma": _normalise_lemma(lemma), "sentence": sentence}
        context_tokens = _tokens(sentence) - _tokens(lemma)
        senses = entry["definitions"] or [entry["definition"]]
        ranked = sorted(
            ((len(_tokens(sense) & context_tokens), sense) for sense in senses), reverse=True
        )
        best_score, best_sense = ranked[0] if ranked else (0, entry["definition"])
        return {
            "known": True, "lemma": entry["lemma"], "sentence": sentence,
            "sense": best_sense, "context_overlap": best_score,
            "confidence": round(min(.95, .45 + best_score * .1), 3),
            "source": entry["source"],
        }

    def answer(self, question: str) -> dict[str, Any]:
        text = " ".join(str(question or "").strip().split())
        lowered = text.lower().rstrip("?.!")
        patterns = (
            ("define", r"^(?:define|meaning of)\s+['\"]?(.+?)['\"]?$"),
            ("define", r"^(?:what does|what is)\s+['\"]?(.+?)['\"]?\s+mean$"),
            ("define", r"^what is\s+(?:an?\s+|the\s+)?['\"]?(.+?)['\"]?$"),
            ("synonym", r"^(?:synonyms? (?:for|of)|what is similar to)\s+['\"]?(.+?)['\"]?$"),
            ("antonym", r"^(?:antonyms? (?:for|of)|what is the opposite of)\s+['\"]?(.+?)['\"]?$"),
        )
        for mode, pattern in patterns:
            match = re.match(pattern, lowered, re.I)
            if not match:
                continue
            lemma = _normalise_lemma(match.group(1))
            entry = self.lookup(lemma)
            if not entry:
                return {
                    "answered": False, "mode": mode, "confidence": 0.0,
                    "answer": f"I do not yet have a verified lexical entry for '{lemma}'.",
                    "missing_lemma": lemma,
                }
            if mode == "define":
                example = f" Example: {entry['examples'][0]}" if entry["examples"] else ""
                return {
                    "answered": True, "mode": mode, "confidence": .96,
                    "answer": f"{entry['lemma']}: {entry['definition']}{example}",
                    "evidence": entry,
                }
            relation_rows = self.related(entry["lemma"], mode, limit=8)
            words = [row["target_lemma"] for row in relation_rows]
            label = "Synonyms" if mode == "synonym" else "Antonyms"
            return {
                "answered": bool(words), "mode": mode, "confidence": .93 if words else .2,
                "answer": f"{label} for {entry['lemma']}: {', '.join(words)}." if words
                else f"I know the definition of '{entry['lemma']}', but have no verified {mode} relation yet.",
                "evidence": {"entry": entry, "relations": relation_rows},
            }
        comparison = re.match(
            r"^(?:compare|difference between|how are)\s+(.+?)\s+(?:and|to)\s+(.+?)(?:\s+related)?$",
            lowered,
        )
        if comparison:
            result = self.compare(comparison.group(1), comparison.group(2))
            if not result["known"]:
                return {"answered": False, "mode": "compare", "confidence": 0.0,
                        "answer": "I do not yet know both requested terms.", "evidence": result}
            direct = result["direct_relation"]
            relation_text = (
                f" They have a verified {direct['relation']} relationship."
                if direct else " No direct lexical relationship is currently stored."
            )
            overlap = ", ".join(result["definition_overlap"][:6]) or "none"
            return {
                "answered": True, "mode": "compare", "confidence": .88,
                "answer": (
                    f"{result['first']['lemma']}: {result['first']['definition']} "
                    f"{result['second']['lemma']}: {result['second']['definition']}"
                    f"{relation_text} Shared definition concepts: {overlap}."
                ),
                "evidence": result,
            }
        contextual = re.match(r"^context\s+(.+?)\s+in\s+(.+)$", lowered)
        if contextual:
            result = self.context(contextual.group(1), contextual.group(2))
            return {
                "answered": bool(result["known"]), "mode": "context",
                "confidence": float(result.get("confidence") or 0.0),
                "answer": (
                    f"In that context, '{result['lemma']}' most closely means: {result['sense']}"
                    if result["known"] else f"I do not yet know '{result['lemma']}'."
                ), "evidence": result,
            }
        return {"answered": False, "mode": "unhandled", "confidence": 0.0, "answer": ""}

    def _candidate_words(self, *, offset: int, limit: int = 80) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT lemma FROM lexemes WHERE verified=1 AND LENGTH(definition)>12
                   ORDER BY lemma LIMIT ? OFFSET ?""", (limit, max(0, offset)),
            ).fetchall()
            if len(rows) < 8:
                rows = connection.execute(
                    "SELECT lemma FROM lexemes WHERE verified=1 ORDER BY lemma LIMIT ?", (limit,)
                ).fetchall()
        return [str(row[0]) for row in rows]

    @staticmethod
    def _realise_productive_sentence(*, lemma: str, pos: str, subject: str, obj: str,
                                     tense: str, negated: bool, connector: str) -> str:
        """Realise a semantic plan without an LLM or next-token generator."""
        if pos == "v":
            if tense == "future":
                predicate = f"will {'not ' if negated else ''}{lemma} the {obj}"
            elif tense == "past":
                predicate = (f"did not {lemma} the {obj}" if negated
                             else f"{_past_form(lemma)} the {obj}")
            else:
                predicate = (f"does not {lemma} the {obj}" if negated
                             else f"{_present_form(lemma)} the {obj}")
            sentence = f"{subject} {predicate}."
        elif pos in {"a", "s"}:
            copula = ("will not be" if tense == "future" and negated else
                      "will be" if tense == "future" else
                      "was not" if tense == "past" and negated else
                      "was" if tense == "past" else
                      "is not" if negated else "is")
            sentence = f"{subject} said the {obj} {copula} {lemma}."
        elif pos == "r":
            action = ("will not work" if tense == "future" and negated else
                      "will work" if tense == "future" else
                      "did not work" if tense == "past" and negated else
                      "worked" if tense == "past" else
                      "does not work" if negated else "works")
            sentence = f"{subject} {action} {lemma} on the {obj}."
        else:
            action = ("will not inspect" if tense == "future" and negated else
                      "will inspect" if tense == "future" else
                      "did not inspect" if tense == "past" and negated else
                      "inspected" if tense == "past" else
                      "does not inspect" if negated else "inspects")
            sentence = f"{subject} {action} the {lemma} beside the {obj}."
        if connector == "because":
            sentence = sentence.rstrip(".") + " because the evidence required it."
        return sentence

    def generate_tasks(
        self, *, family: str, limit: int = 12, seed: int = 0, offset: int = 0,
    ) -> list[LexicalTask]:
        if family in {"productive_semantic_transfer", "productive_sentence_transfer"}:
            with self._connect() as connection:
                count = int(connection.execute(
                    """SELECT COUNT(*) FROM acquired_concepts
                       WHERE stage!='encountered' AND INSTR(lemma,' ')=0
                         AND LENGTH(lemma) BETWEEN 3 AND 24"""
                ).fetchone()[0])
                if not count:
                    return []
                start = (max(0, int(offset)) + max(0, int(seed)) * 97) % count
                rows = connection.execute(
                    """SELECT concept_id,lemma,part_of_speech,native_gloss,
                              reference_definition,features_json,relations_json
                       FROM acquired_concepts
                       WHERE stage!='encountered' AND INSTR(lemma,' ')=0
                         AND LENGTH(lemma) BETWEEN 3 AND 24
                       ORDER BY concept_id LIMIT ? OFFSET ?""",
                    (max(1, int(limit)), start),
                ).fetchall()
                if len(rows) < max(1, int(limit)):
                    rows = list(rows) + list(connection.execute(
                        """SELECT concept_id,lemma,part_of_speech,native_gloss,
                                  reference_definition,features_json,relations_json
                           FROM acquired_concepts
                           WHERE stage!='encountered' AND INSTR(lemma,' ')=0
                             AND LENGTH(lemma) BETWEEN 3 AND 24
                           ORDER BY concept_id LIMIT ?""",
                        (max(1, int(limit)) - len(rows),),
                    ).fetchall())
            names = ("Mireya", "Tavian", "Leona", "Kellan", "Amara", "Neryn")
            objects = ("report", "sensor", "record", "sample", "proposal", "result")
            tasks: list[LexicalTask] = []
            for index, row in enumerate(rows):
                value = dict(row)
                lemma = str(value["lemma"])
                pos = str(value.get("part_of_speech") or "")
                features = json.loads(value.get("features_json") or "[]")
                definition = str(
                    value.get("native_gloss") or value.get("reference_definition") or ""
                ).strip()
                feature_cue = ", ".join(str(item) for item in features[:7])
                cue = "; related features: ".join(
                    item for item in (definition, feature_cue) if item
                )
                if not cue:
                    continue
                name = names[(start + index) % len(names)]
                obj = objects[(start * 3 + index) % len(objects)]
                if family == "productive_sentence_transfer":
                    tense = ("past", "present", "future")[(start + index) % 3]
                    negated = bool((start + index) % 4 == 0)
                    connector = "because" if (start + index) % 5 == 0 else "none"
                    sentence = self._realise_productive_sentence(
                        lemma=lemma, pos=pos, subject=name, obj=obj, tense=tense,
                        negated=negated, connector=connector,
                    )
                    prompt = (
                        f"Fresh native-production challenge {start + index + 1}. "
                        f"Meaning cue: {cue}. Retrieve the acquired word that matches this meaning "
                        "and use it in one new grammatical sentence. "
                        f"Required subject: {name}. Required topic: {obj}. Tense: {tense}. "
                        f"Polarity: {'negative' if negated else 'positive'}. "
                        f"Required connector: {connector}. Required word class: {pos or 'n'}."
                    )
                    source = "aion_acquired_concepts_v5"
                else:
                    if pos == "v":
                        sentence = f"{name} chose to {lemma} the {obj}."
                    elif pos in {"a", "s"}:
                        sentence = f"The {obj} seemed {lemma}."
                    elif pos == "r":
                        sentence = f"{name} worked {lemma}."
                    else:
                        sentence = f"{name} inspected the {lemma}."
                    prompt = (
                        f"Fresh acquired-concept challenge {start + index + 1}. Passage: {sentence} "
                        f"Meaning cue: {cue}. Question: Which acquired word in the passage expresses "
                        "that meaning? Return the word only."
                    )
                    source = "aion_acquired_concepts_v4"
                task_id = "native_productive_semantic_" + _canonical_hash(
                    [value["concept_id"], prompt]
                )[:20]
                tasks.append(LexicalTask(
                    task_id, family, prompt, (), sentence,
                    lemma, source, True,
                ))
            return tasks
        if family in {
            "sentence_semantics", "discourse_reasoning", "compositional_syntax",
            "paragraph_comprehension", "unseen_document_qa", "dialogue_tracking",
            "ambiguity_pragmatics", "explanation_generation", "error_correction",
            "cross_domain_transfer", "scope_counterfactual_reasoning",
            "multi_source_evidence_synthesis", "paraphrase_revision",
            "conversation_belief_revision", "adversarial_uncertainty",
            "delayed_open_generalisation",
        }:
            from backend.modules.aion_cognition.native_english_reasoning import (
                generate_reasoning_tasks,
            )
            return [LexicalTask(
                row["task_id"], row["family"], row["prompt"], tuple(row["choices"]),
                row["expected"], row["lemma"], row["source"], bool(row["source_disjoint"]),
            ) for row in generate_reasoning_tasks(
                family=family, limit=limit, seed=seed, offset=offset,
            )]
        rng = random.Random(seed)
        words = self._candidate_words(offset=offset, limit=max(80, limit * 8))
        if len(words) < 4:
            return []
        rng.shuffle(words)
        tasks: list[LexicalTask] = []
        for lemma in words:
            if len(tasks) >= limit:
                break
            entry = self.lookup(lemma)
            if not entry:
                continue
            selected_family = family
            if family == "mixed":
                selected_family = ("definition_match", "synonym_choice", "antonym_choice", "context_completion")[len(tasks) % 4]
            choices = [lemma] + [word for word in words if word != lemma][:7]
            rng.shuffle(choices)
            prompt = entry["definition"]
            expected = lemma
            if selected_family == "synonym_choice":
                related = self.related(lemma, "synonym", limit=4)
                if not related:
                    continue
                expected = related[0]["target_lemma"]
                choices = [expected] + [word for word in words if word not in {lemma, expected}][:7]
                rng.shuffle(choices)
                prompt = f"Select the closest verified synonym for {lemma}."
            elif selected_family == "antonym_choice":
                related = self.related(lemma, "antonym", limit=4)
                if not related:
                    continue
                expected = related[0]["target_lemma"]
                choices = [expected] + [word for word in words if word not in {lemma, expected}][:7]
                rng.shuffle(choices)
                prompt = f"Select the verified opposite of {lemma}."
            elif selected_family == "context_completion":
                if not entry["examples"]:
                    continue
                example = next((item for item in entry["examples"] if re.search(
                    rf"\b{re.escape(lemma)}\b", item, re.I)), "")
                if not example:
                    continue
                prompt = re.sub(rf"\b{re.escape(lemma)}\b", "_____", example, count=1, flags=re.I)
            task_id = "native_lexical_task_" + _canonical_hash(
                [selected_family, prompt, choices, expected]
            )[:20]
            tasks.append(LexicalTask(
                task_id, selected_family, prompt, tuple(choices), expected, lemma, entry["source"]
            ))
        return tasks

    def answer_task(self, task: Mapping[str, Any]) -> str | None:
        """Student path. The mapping deliberately contains no expected answer."""
        family = str(task.get("family") or "")
        if family in {"productive_semantic_transfer", "productive_sentence_transfer"}:
            prompt = str(task.get("prompt") or "")
            cue_match = re.search(
                r"Meaning cue:\s*(.+?)\.\s+(?:Question:|Retrieve)", prompt, re.S,
            )
            if not cue_match:
                return None
            cue_tokens = _tokens(cue_match.group(1))
            if not cue_tokens:
                return None
            with self._connect() as connection:
                if family == "productive_semantic_transfer":
                    passage_match = re.search(r"Passage:\s*(.+?)\s+Meaning cue:", prompt, re.S)
                    if not passage_match:
                        return None
                    passage_words = sorted(_tokens(passage_match.group(1)))
                    if not passage_words:
                        return None
                    marks = ",".join("?" for _ in passage_words)
                    rows = connection.execute(
                        f"""SELECT lemma,part_of_speech,reference_definition,native_gloss,
                                   features_json,relations_json
                            FROM acquired_concepts WHERE lemma IN ({marks})""",
                        tuple(passage_words),
                    ).fetchall()
                else:
                    required_pos = re.search(
                        r"Required word class:\s*([A-Za-z]+)", prompt,
                    )
                    rows = connection.execute(
                        """SELECT lemma,part_of_speech,reference_definition,native_gloss,
                                  features_json,relations_json
                           FROM acquired_concepts WHERE stage!='encountered'
                             AND (?='' OR part_of_speech=?)""",
                        ((required_pos.group(1) if required_pos else ""),) * 2,
                    ).fetchall()
            scored: list[tuple[float, str]] = []
            pos_by_lemma: dict[str, str] = {}
            for row in rows:
                material = " ".join((
                    str(row["reference_definition"] or ""),
                    str(row["native_gloss"] or ""),
                    " ".join(json.loads(row["features_json"] or "[]")),
                    " ".join(
                        str(item)
                        for values in json.loads(row["relations_json"] or "{}").values()
                        for item in values
                    ),
                ))
                score = len(cue_tokens & _tokens(material)) / max(1, len(cue_tokens))
                scored.append((score, str(row["lemma"])))
                pos_by_lemma[str(row["lemma"])] = str(row["part_of_speech"] or "")
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            if not scored or scored[0][0] <= 0:
                return None
            lemma = scored[0][1]
            if family == "productive_semantic_transfer":
                return lemma
            subject = re.search(r"Required subject:\s*([A-Za-z'-]+)", prompt)
            topic = re.search(r"Required topic:\s*([A-Za-z'-]+)", prompt)
            tense = re.search(r"Tense:\s*(past|present|future)", prompt)
            polarity = re.search(r"Polarity:\s*(positive|negative)", prompt)
            connector = re.search(r"Required connector:\s*(because|none)", prompt)
            if not all((subject, topic, tense, polarity, connector)):
                return None
            return self._realise_productive_sentence(
                lemma=lemma, pos=pos_by_lemma.get(lemma, ""),
                subject=subject.group(1), obj=topic.group(1), tense=tense.group(1),
                negated=polarity.group(1) == "negative", connector=connector.group(1),
            )
        if family in {
            "sentence_semantics", "discourse_reasoning", "compositional_syntax",
            "paragraph_comprehension", "unseen_document_qa", "dialogue_tracking",
            "ambiguity_pragmatics", "explanation_generation", "error_correction",
            "cross_domain_transfer", "scope_counterfactual_reasoning",
            "multi_source_evidence_synthesis", "paraphrase_revision",
            "conversation_belief_revision", "adversarial_uncertainty",
            "delayed_open_generalisation",
        }:
            from backend.modules.aion_cognition.native_english_reasoning import answer_reasoning_task
            return answer_reasoning_task(task)
        choices = [str(item) for item in task.get("choices") or []]
        prompt = str(task.get("prompt") or "")
        lemma = _normalise_lemma(str(task.get("lemma") or ""))
        if not choices:
            return None
        if family in {"synonym_choice", "antonym_choice"}:
            relation = "synonym" if family == "synonym_choice" else "antonym"
            strengths = {row["target_lemma"]: abs(float(row["strength"]))
                         for row in self.related(lemma, relation, limit=64)}
            ranked = sorted(choices, key=lambda word: (strengths.get(_normalise_lemma(word), 0.0), word), reverse=True)
            return ranked[0] if strengths.get(_normalise_lemma(ranked[0]), 0.0) > 0 else None
        prompt_tokens = _tokens(prompt)
        scored: list[tuple[float, str]] = []
        for choice in choices:
            entry = self.lookup(choice)
            if not entry:
                scored.append((0.0, choice)); continue
            material = " ".join(entry["definitions"] + entry["examples"])
            overlap = len(prompt_tokens & _tokens(material))
            direct_name = 1.0 if _normalise_lemma(choice) in prompt.lower() else 0.0
            scored.append((overlap + direct_name, choice))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return scored[0][1] if scored and scored[0][0] > 0 else None

    def _grade_student_answer(self, task: LexicalTask, answer: str | None) -> bool:
        """Grade productive language by semantic constraints, not exact wording."""
        if task.family != "productive_sentence_transfer":
            return _normalise_lemma(answer or "") == _normalise_lemma(task.expected)
        prompt = task.prompt
        normal = _normalise_lemma(answer or "")
        tokens = _tokens(answer or "")
        target = _normalise_lemma(task.lemma)
        cue = re.search(r"Meaning cue:\s*(.+?)\.\s+Retrieve", prompt, re.S)
        required_pos = re.search(r"Required word class:\s*([A-Za-z]+)", prompt)
        candidate_lemmas = set(tokens)
        past_surface = False
        if required_pos and required_pos.group(1) == "v":
            for token in list(tokens):
                resolved = self.resolve_form(token, "v")
                candidate_lemmas.update(str(row.get("lemma") or "") for row in resolved)
                past_surface = past_surface or any(
                    "past" in str(row.get("feature") or "") for row in resolved
                )
        semantic_use = False
        if cue and required_pos and candidate_lemmas:
            cue_tokens = _tokens(cue.group(1))
            marks = ",".join("?" for _ in candidate_lemmas)
            with self._connect() as connection:
                concepts = connection.execute(
                    f"""SELECT lemma,reference_definition,native_gloss,
                               features_json,relations_json
                        FROM acquired_concepts
                        WHERE lemma IN ({marks}) AND part_of_speech=?""",
                    (*sorted(candidate_lemmas), required_pos.group(1)),
                ).fetchall()
            for concept in concepts:
                material = " ".join((
                    str(concept["reference_definition"] or ""),
                    str(concept["native_gloss"] or ""),
                    " ".join(json.loads(concept["features_json"] or "[]")),
                    " ".join(
                        str(item)
                        for values in json.loads(concept["relations_json"] or "{}").values()
                        for item in values
                    ),
                ))
                overlap = len(cue_tokens & _tokens(material)) / max(1, len(cue_tokens))
                if overlap >= .45:
                    semantic_use = True
                    break
        subject = re.search(r"Required subject:\s*([A-Za-z'-]+)", prompt)
        topic = re.search(r"Required topic:\s*([A-Za-z'-]+)", prompt)
        tense = re.search(r"Tense:\s*(past|present|future)", prompt)
        polarity = re.search(r"Polarity:\s*(positive|negative)", prompt)
        connector = re.search(r"Required connector:\s*(because|none)", prompt)
        participant_ok = bool(
            subject and topic and subject.group(1).lower() in tokens
            and topic.group(1).lower() in tokens
        )
        negative = bool(re.search(r"\b(?:not|never|no)\b", normal))
        polarity_ok = bool(polarity and negative == (polarity.group(1) == "negative"))
        tense_value = tense.group(1) if tense else ""
        tense_ok = (
            (tense_value == "future" and "will" in tokens)
            or (tense_value == "past" and (
                "did" in tokens or "was" in tokens or "worked" in tokens
                or "inspected" in tokens or _past_form(target) in normal or past_surface
            ))
            or (tense_value == "present" and "will" not in tokens and "did" not in tokens
                and "was" not in tokens)
        )
        connector_ok = bool(
            connector and (connector.group(1) == "none" or "because" in tokens)
        )
        sentence_ok = bool(re.search(r"[.!?]$", str(answer or "").strip()))
        return all((semantic_use, participant_ok, polarity_ok, tense_ok,
                    connector_ok, sentence_ok))

    def run_practice_cycle(
        self, *, family: str = "mixed", limit: int = 12, seed: int = 0,
        offset: int = 0, project_family: str | None = None,
    ) -> dict[str, Any]:
        tasks = self.generate_tasks(family=family, limit=limit, seed=seed, offset=offset)
        authority = dict(self.authority_provider())
        rows: list[dict[str, Any]] = []
        for task in tasks:
            student_view = task.student_view()
            student_answer = self.answer_task(student_view)
            correct = self._grade_student_answer(task, student_answer)
            attempt = {
                "task_id": task.task_id, "family": task.family, "lemma": task.lemma,
                "prompt": task.prompt, "student_answer": student_answer,
                "expected_answer": task.expected, "correct": correct,
                "expected_withheld_from_student": "expected" not in student_view,
                "source": task.source, "source_disjoint": task.source_disjoint,
            }
            attempt_id = "native_lexical_attempt_" + _canonical_hash(
                [attempt, project_family, time.time_ns()]
            )[:20]
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO practice_attempts(
                       attempt_id,task_id,family,lemma,prompt,student_answer,expected_answer,
                       correct,authority_allowed,project_family,curriculum_family,evidence_source,
                       source_disjoint,created_epoch
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (attempt_id, task.task_id, task.family, task.lemma, task.prompt,
                     student_answer, task.expected, int(correct), int(bool(authority.get("allow_learn"))),
                     project_family, family, task.source, int(task.source_disjoint), time.time()),
                )
                if correct and authority.get("allow_learn"):
                    connection.execute(
                        "UPDATE lexemes SET reinforcement_count=reinforcement_count+1,updated_epoch=? WHERE lemma=?",
                        (time.time(), task.lemma),
                    )
            rows.append(attempt)
        correct_count = sum(int(row["correct"]) for row in rows)
        score = correct_count / len(rows) if rows else 0.0
        return {
            "passed": bool(rows and score >= .70 and authority.get("allow_learn")),
            "score": round(score, 4), "correct": correct_count, "total": len(rows),
            "family": family, "project_family": project_family,
            "authority": authority, "model_used": False, "cloud_used": False,
            "source_disjoint": bool(rows and all(row["source_disjoint"] for row in rows)),
            "free_response": bool(rows and all(not task.choices for task in tasks)),
            "response_modes": sorted({
                "free_response" if not task.choices else "selected" for task in tasks
            }),
            "evidence_sources": sorted({str(row["source"]) for row in rows}),
            "expected_withheld": all(row["expected_withheld_from_student"] for row in rows),
            "attempts": rows,
        }

    def teach_term(self, term: str, *, level: int = 1) -> dict[str, Any]:
        entry = self.lookup(term)
        if not entry:
            return {"status": "unknown_term", "term": _normalise_lemma(term), "learned": False}
        families = ["definition_match", "synonym_choice", "antonym_choice", "context_completion"]
        outcomes = [
            self.run_practice_cycle(
                family=family, limit=max(2, min(8, level * 2)), seed=level + index,
                offset=index * 31, project_family=f"interactive_{family}",
            ) for index, family in enumerate(families)
        ]
        attempted = sum(row["total"] for row in outcomes)
        correct = sum(row["correct"] for row in outcomes)
        return {
            "status": "practised", "term": entry["lemma"], "entry": entry,
            "attempted": attempted, "correct": correct,
            "score": round(correct / attempted, 4) if attempted else 0.0,
            "learned": bool(attempted), "outcomes": outcomes,
        }


def wordnet_records(wordnet: Any) -> Iterable[dict[str, Any]]:
    """Aggregate an installed NLTK WordNet corpus into durable local records."""
    aggregate: dict[tuple[str, str], dict[str, Any]] = {}
    for synset in wordnet.all_synsets():
        definition = " ".join(str(synset.definition()).split())
        examples = [" ".join(str(item).split()) for item in synset.examples()]
        lemmas = [_normalise_lemma(item.name()) for item in synset.lemmas()]
        hypernyms = [_normalise_lemma(item.name()) for parent in synset.hypernyms() for item in parent.lemmas()]
        hyponyms = [_normalise_lemma(item.name()) for child in synset.hyponyms() for item in child.lemmas()]
        for lemma_obj, lemma in zip(synset.lemmas(), lemmas):
            if not lemma or len(lemma) > 100:
                continue
            row = aggregate.setdefault((lemma, synset.pos()), {
                "lemma": lemma, "part_of_speech": synset.pos(), "definitions": [],
                "examples": [], "synonyms": [], "antonyms": [], "hypernyms": [],
                "hyponyms": [], "derivations": [],
            })
            if definition and definition not in row["definitions"]:
                row["definitions"].append(definition)
            for value in examples:
                if value not in row["examples"]: row["examples"].append(value)
            row["synonyms"].extend(item for item in lemmas if item != lemma)
            row["antonyms"].extend(
                _normalise_lemma(item.name()) for item in lemma_obj.antonyms()
            )
            row["derivations"].extend(
                _normalise_lemma(item.name()) for item in lemma_obj.derivationally_related_forms()
            )
            row["hypernyms"].extend(hypernyms)
            row["hyponyms"].extend(hyponyms)
    for row in aggregate.values():
        for key in ("synonyms", "antonyms", "hypernyms", "hyponyms", "derivations"):
            row[key] = sorted(set(item for item in row[key] if item and item != row["lemma"]))
        yield row


__all__ = [
    "NativeLexicalIntelligence", "LexicalTask", "default_database_path", "wordnet_records",
]
