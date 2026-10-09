"""Persistent, model-free reading practice over real local documents.

The reading academy does not train a next-token model.  It converts a source
into ordered sentences, parses each sentence with Aion's native English stack,
records provenance and concept encounters, then runs sealed comprehension
questions.  Reading evidence is practice evidence only; it cannot grant
mastery without the independent transfer and retention authorities.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import math
from typing import Any, Mapping

from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer, _normal
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning
from backend.modules.aion_cognition.native_document_ingestion import (
    DocumentExtractionError,
    NativeDocumentExtractor,
    SUPPORTED_DOCUMENT_EXTENSIONS,
)
from backend.modules.aion_cognition.native_online_reading_harvester import (
    NativeOnlineReadingHarvester,
)


SUPPORTED_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS
READING_FAMILIES = (
    "subject_retrieval", "action_retrieval", "object_retrieval",
    "time_retrieval", "location_retrieval", "negation_scope",
    "sequence_retrieval", "contextual_vocabulary",
)
FUNCTION_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but",
    "by", "did", "do", "does", "for", "from", "had", "has", "have", "he",
    "her", "hers", "him", "his", "i", "if", "in", "is", "it", "its", "me",
    "my", "no", "not", "of", "on", "or", "our", "ours", "she", "so", "than",
    "that", "the", "their", "theirs", "them", "they", "this", "those", "to",
    "was", "we", "were", "will", "with", "you", "your", "yours",
})
WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]*")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])(?:[\"'’”)]*)\s+(?=[A-Z0-9\"'“‘(])")


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _sentences(text: str) -> list[str]:
    clean = re.sub(r"[ \t]+", " ", str(text or "")).strip()
    return [piece.strip() for piece in SENTENCE_PATTERN.split(clean)
            if len(WORD_PATTERN.findall(piece)) >= 3]


class NativeReadingAcademy:
    """Read ordered local text and turn it into retained language experience."""

    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None,
                 retry_delay_seconds: float = 1800.0,
                 retention_delay_seconds: float = 86400.0,
                 online_enabled: bool | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.transfer = NativeEnglishTransfer(repo_root=self.repo_root, lexical=self.lexical)
        self.wordwall = NativeWordwallLearning(repo_root=self.repo_root, lexical=self.lexical)
        self.extractor = NativeDocumentExtractor(repo_root=self.repo_root)
        self.retry_delay_seconds = max(1.0, float(retry_delay_seconds))
        self.retention_delay_seconds = max(1.0, float(retention_delay_seconds))
        self.deep_test_ratio = max(
            0.02, min(0.50, float(os.getenv("AION_READING_DEEP_TEST_RATIO", "0.12")))
        )
        self.short_source_full_test = max(
            1, min(100, int(os.getenv("AION_READING_FULL_TEST_MAX_SENTENCES", "24")))
        )
        self.max_imports_per_cycle = max(
            1, min(100, int(os.getenv("AION_READING_IMPORT_BATCH", "25")))
        )
        self.library_directories = (
            self.repo_root / "data/aion/reading_library",
            self.database_path.parent / "reading_library",
        )
        for directory in self.library_directories:
            directory.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self.online_enabled = (
            os.getenv("AION_ONLINE_READING", "0") not in {"0", "false", "False"}
            if online_enabled is None else bool(online_enabled)
        )
        self.online = NativeOnlineReadingHarvester(
            database_path=self.database_path, extractor=self.extractor,
            ingest=self.ingest_text,
            max_download_bytes=int(os.getenv("AION_ONLINE_READING_MAX_BYTES", "20000000")),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_reading_sources(
                    source_id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
                    subject TEXT NOT NULL, license TEXT NOT NULL, source_ref TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
                    paragraph_count INTEGER NOT NULL, sentence_count INTEGER NOT NULL,
                    next_sentence_index INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL, updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_reading_sentences(
                    sentence_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
                    sentence_index INTEGER NOT NULL, paragraph_index INTEGER NOT NULL,
                    text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                    parse_json TEXT NOT NULL DEFAULT '{}',
                    acquired_concepts_json TEXT NOT NULL DEFAULT '[]',
                    reference_words_json TEXT NOT NULL DEFAULT '[]',
                    unknown_words_json TEXT NOT NULL DEFAULT '[]',
                    summary_text TEXT NOT NULL DEFAULT '', processed_epoch REAL,
                    created_epoch REAL NOT NULL,
                    UNIQUE(source_id,sentence_index),
                    FOREIGN KEY(source_id) REFERENCES native_reading_sources(source_id)
                );
                CREATE INDEX IF NOT EXISTS native_reading_sentence_queue
                    ON native_reading_sentences(status,source_id,sentence_index);
                CREATE TABLE IF NOT EXISTS native_reading_exercises(
                    exercise_id TEXT PRIMARY KEY, sentence_id TEXT NOT NULL,
                    source_id TEXT NOT NULL, family TEXT NOT NULL,
                    question TEXT NOT NULL, expected_answer TEXT NOT NULL,
                    answer_reason TEXT NOT NULL, answer TEXT NOT NULL,
                    correct INTEGER NOT NULL, confidence REAL NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL, due_epoch REAL,
                    created_epoch REAL NOT NULL, attempted_epoch REAL NOT NULL,
                    FOREIGN KEY(sentence_id) REFERENCES native_reading_sentences(sentence_id)
                );
                CREATE INDEX IF NOT EXISTS native_reading_exercise_due
                    ON native_reading_exercises(status,due_epoch);
                CREATE TABLE IF NOT EXISTS native_reading_claims(
                    claim_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
                    sentence_id TEXT NOT NULL, subject TEXT NOT NULL,
                    action TEXT NOT NULL, object TEXT NOT NULL,
                    tense TEXT NOT NULL, negated INTEGER NOT NULL,
                    provenance_json TEXT NOT NULL, confidence REAL NOT NULL,
                    corroboration_count INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'single_source_claim',
                    created_epoch REAL NOT NULL,
                    FOREIGN KEY(sentence_id) REFERENCES native_reading_sentences(sentence_id)
                );
                CREATE TABLE IF NOT EXISTS native_reading_word_experience(
                    lemma TEXT NOT NULL, concept_id TEXT NOT NULL DEFAULT '',
                    source_id TEXT NOT NULL, encounters INTEGER NOT NULL DEFAULT 0,
                    parsed_uses INTEGER NOT NULL DEFAULT 0,
                    successful_exercises INTEGER NOT NULL DEFAULT 0,
                    first_sentence_id TEXT NOT NULL, last_sentence_id TEXT NOT NULL,
                    first_seen_epoch REAL NOT NULL, last_seen_epoch REAL NOT NULL,
                    PRIMARY KEY(lemma,source_id)
                );
                CREATE TABLE IF NOT EXISTS native_reading_cycles(
                    cycle_id TEXT PRIMARY KEY, sentences_read INTEGER NOT NULL,
                    exercises_attempted INTEGER NOT NULL, exercises_correct INTEGER NOT NULL,
                    new_concepts_encountered INTEGER NOT NULL, claims_recorded INTEGER NOT NULL,
                    detail_json TEXT NOT NULL, created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_reading_runtime(
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    busy INTEGER NOT NULL DEFAULT 0,
                    lease_epoch REAL,
                    updated_epoch REAL NOT NULL
                );
                INSERT OR IGNORE INTO native_reading_runtime(singleton,busy,updated_epoch)
                    VALUES(1,0,0);
                CREATE TABLE IF NOT EXISTS native_reading_imports(
                    import_id TEXT PRIMARY KEY,path TEXT NOT NULL,format TEXT NOT NULL,
                    method TEXT NOT NULL,status TEXT NOT NULL,quality REAL NOT NULL,
                    page_count INTEGER NOT NULL DEFAULT 0,character_count INTEGER NOT NULL DEFAULT 0,
                    warning TEXT NOT NULL DEFAULT '',metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_reading_storage_metrics(
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    sentence_characters_compacted INTEGER NOT NULL DEFAULT 0,
                    updated_epoch REAL NOT NULL DEFAULT 0
                );
                INSERT OR IGNORE INTO native_reading_storage_metrics(singleton)
                    VALUES(1);
                """
            )
            source_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(native_reading_sources)")
            }
            for name, definition in (
                ("format", "TEXT NOT NULL DEFAULT 'text'"),
                ("extraction_method", "TEXT NOT NULL DEFAULT 'native_text'"),
                ("extraction_quality", "REAL NOT NULL DEFAULT 1.0"),
                ("metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
            ):
                if name not in source_columns:
                    connection.execute(
                        f"ALTER TABLE native_reading_sources ADD COLUMN {name} {definition}"
                    )
            sentence_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(native_reading_sentences)")
            }
            for name, definition in (
                ("section_index", "INTEGER NOT NULL DEFAULT 0"),
                ("section_title", "TEXT NOT NULL DEFAULT ''"),
            ):
                if name not in sentence_columns:
                    connection.execute(
                        f"ALTER TABLE native_reading_sentences ADD COLUMN {name} {definition}"
                    )

    def _acquire_cycle_lease(self) -> bool:
        now = time.time()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            state = connection.execute(
                "SELECT busy,lease_epoch FROM native_reading_runtime WHERE singleton=1"
            ).fetchone()
            if bool(state["busy"]) and float(state["lease_epoch"] or 0) > now - 1800:
                return False
            connection.execute(
                """UPDATE native_reading_runtime
                   SET busy=1,lease_epoch=?,updated_epoch=? WHERE singleton=1""",
                (now, now),
            )
        return True

    def _release_cycle_lease(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE native_reading_runtime
                   SET busy=0,lease_epoch=NULL,updated_epoch=? WHERE singleton=1""",
                (time.time(),),
            )

    @staticmethod
    def _paragraphs(text: str) -> list[str]:
        normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        blocks = [re.sub(r"\s+", " ", block).strip()
                  for block in re.split(r"\n\s*\n+", normalized)]
        return [
            block for block in blocks
            if len(WORD_PATTERN.findall(block)) >= 3
            or bool(re.match(r"^(?:chapter|section|part|book)\b", block, re.I))
        ]

    @classmethod
    def _structured_sentences(
        cls, text: str,
    ) -> tuple[list[str], list[tuple[int, int, int, str, str]]]:
        paragraphs = cls._paragraphs(text)
        sentence_rows: list[tuple[int, int, int, str, str]] = []
        section_index = 0
        section_title = "Opening"
        sequence = 0
        for paragraph_index, paragraph in enumerate(paragraphs):
            words = WORD_PATTERN.findall(paragraph)
            heading = (
                len(words) <= 14
                and not re.search(r"[.!?][\"'’”)]?$", paragraph)
                and (paragraph.isupper() or paragraph.istitle()
                     or bool(re.match(r"^(?:chapter|section|part|book)\b", paragraph, re.I)))
            )
            if heading:
                section_index += 1
                section_title = paragraph[:300]
                continue
            for sentence in _sentences(paragraph):
                sentence_rows.append(
                    (sequence, paragraph_index, section_index, section_title, sentence)
                )
                sequence += 1
        return paragraphs, sentence_rows

    def ingest_text(self, *, title: str, text: str, author: str = "Unknown",
                    subject: str = "general", license_name: str = "owner-provided",
                    source_ref: str = "local-text",
                    extraction: Mapping[str, Any] | None = None) -> dict[str, Any]:
        clean_title = str(title or "Untitled").strip()[:300]
        content = str(text or "").strip()
        if len(content) < 20:
            raise ValueError("reading_source_too_short")
        if len(content) > 5_000_000:
            raise ValueError("reading_source_too_large")
        digest = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM native_reading_sources WHERE content_hash=?", (digest,),
            ).fetchone()
        if existing:
            return {**dict(existing), "status": "already_ingested"}
        paragraphs, sentence_rows = self._structured_sentences(content)
        if not sentence_rows:
            raise ValueError("reading_source_has_no_sentences")
        source_id = _identifier("reading_source_", [clean_title, digest])
        now = time.time()
        extraction = dict(extraction or {})
        quality = dict(extraction.get("quality") or {})
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_reading_sources(
                   source_id,title,author,subject,license,source_ref,content_hash,status,
                   paragraph_count,sentence_count,next_sentence_index,created_epoch,updated_epoch,
                   format,extraction_method,extraction_quality,metadata_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (source_id, clean_title, str(author or "Unknown")[:300],
                 str(subject or "general")[:120], str(license_name or "unspecified")[:120],
                 str(source_ref or "local-text")[:1200], digest, "queued",
                 len(paragraphs), len(sentence_rows), 0, now, now,
                 str(extraction.get("format") or "text")[:30],
                 str(extraction.get("method") or "native_text")[:80],
                 float(quality.get("score") if quality else 1.0),
                 json.dumps({key: value for key, value in extraction.items() if key != "text"})),
            )
            connection.executemany(
                """INSERT INTO native_reading_sentences(
                   sentence_id,source_id,sentence_index,paragraph_index,text,created_epoch,
                   section_index,section_title)
                   VALUES(?,?,?,?,?,?,?,?)""",
                [(_identifier("reading_sentence_", [source_id, index]), source_id,
                  index, paragraph_index, sentence, now, section_index, section_title)
                 for index, paragraph_index, section_index, section_title, sentence
                 in sentence_rows],
            )
        return {"status": "queued", "source_id": source_id, "title": clean_title,
                "paragraphs": len(paragraphs), "sentences": len(sentence_rows),
                "format": str(extraction.get("format") or "text"),
                "extraction_quality": float(quality.get("score") if quality else 1.0)}

    def _record_import(self, *, import_id: str, path: Path, extraction: Mapping[str, Any],
                       status: str, warning: str = "") -> None:
        quality = dict(extraction.get("quality") or {})
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO native_reading_imports
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (import_id, str(path), path.suffix.lower().lstrip("."),
                 str(extraction.get("method") or "unavailable"), status,
                 float(quality.get("score") or 0), int(extraction.get("page_count") or 0),
                 int(quality.get("character_count") or 0), str(warning)[:2000],
                 json.dumps({key: value for key, value in extraction.items() if key != "text"}),
                 time.time()),
            )

    def ingest_path(self, path: Path | str, *, subject: str = "general",
                    license_name: str = "owner-provided") -> dict[str, Any]:
        candidate = Path(path).expanduser().resolve()
        if not candidate.is_file() or candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("unsupported_or_missing_reading_source")
        stat = candidate.stat()
        import_id = _identifier("reading_import_", [str(candidate), stat.st_size, stat.st_mtime_ns])
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM native_reading_imports WHERE import_id=?", (import_id,),
            ).fetchone()
        if existing:
            return {**dict(existing), "status": "already_imported"}
        try:
            extraction = self.extractor.extract(candidate)
            outcome = self.ingest_text(
                title=str(extraction.get("document_title") or candidate.stem.replace("_", " ")),
                author=str(extraction.get("document_author") or "Unknown"),
                text=extraction["text"], subject=subject,
                license_name=license_name, source_ref=str(candidate), extraction=extraction,
            )
        except DocumentExtractionError as exc:
            self._record_import(
                import_id=import_id, path=candidate, extraction=exc.detail,
                status="quarantined", warning=exc.code,
            )
            raise ValueError(exc.code) from None
        self._record_import(
            import_id=import_id, path=candidate, extraction=extraction,
            status="queued", warning=";".join(extraction.get("warnings") or []),
        )
        return outcome

    def scan_library(self, *, max_new_sources: int = 3) -> list[dict[str, Any]]:
        configured = [Path(value).expanduser() for value in
                      os.getenv("AION_READING_LIBRARY_DIRS", "").split(os.pathsep) if value]
        configured.append(self.repo_root / "data/aion/reading_library")
        if self.database_path.parent.exists():
            configured.append(self.database_path.parent / "reading_library")
        ingested: list[dict[str, Any]] = []
        seen_paths: set[Path] = set()
        for directory in configured:
            directory = directory.resolve()
            if directory in seen_paths or not directory.is_dir():
                continue
            seen_paths.add(directory)
            for path in sorted(directory.iterdir()):
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS or not path.is_file():
                    continue
                try:
                    outcome = self.ingest_path(path)
                except (OSError, ValueError):
                    continue
                if outcome.get("status") == "queued":
                    ingested.append(outcome)
                if len(ingested) >= max(0, int(max_new_sources)):
                    return ingested
        return ingested

    def seed_public_domain_starter(self) -> list[dict[str, Any]]:
        starter = Path(__file__).with_name("reading_library") / "public_domain_starter.json"
        if not starter.is_file():
            return []
        try:
            sources = json.loads(starter.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        outcomes = []
        for source in sources:
            try:
                outcomes.append(self.ingest_text(
                    title=source["title"], author=source.get("author", "Unknown"),
                    subject=source.get("subject", "literature"),
                    license_name=source.get("license", "public-domain"),
                    source_ref=source.get("source_ref", "bundled-public-domain-starter"),
                    text=source["text"],
                ))
            except (KeyError, ValueError):
                continue
        return outcomes

    def _analyse_words(self, parsed: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[str], list[str]]:
        acquired: dict[str, dict[str, str]] = {}
        reference: set[str] = set()
        unknown: set[str] = set()
        for token in parsed.get("tokens") or []:
            lemma = _normal(str(token.get("lemma") or token.get("token") or ""))
            if not lemma or lemma in FUNCTION_WORDS or not WORD_PATTERN.fullmatch(lemma):
                continue
            source = str(token.get("source") or "")
            concept_id = str(token.get("concept_id") or "")
            if source == "acquired_concept" and concept_id:
                acquired[concept_id] = {"concept_id": concept_id, "lemma": lemma,
                                        "stage": str(token.get("stage") or "")}
            elif source in {"reference_dictionary", "reference"}:
                reference.add(lemma)
            elif source == "unknown":
                unknown.add(lemma)
        return list(acquired.values()), sorted(reference), sorted(unknown)

    @staticmethod
    def _summary(frame: Mapping[str, Any]) -> str:
        subject = str(frame.get("subject") or "").strip()
        action = str(frame.get("action_surface") or frame.get("action") or "").strip()
        obj = str(frame.get("object") or "").strip()
        complement = str(frame.get("complement") or "").strip()
        if not subject or not action:
            return ""
        parts = [subject, action]
        if frame.get("negated") and "not" not in action.split():
            parts.insert(1, "not")
        if obj:
            parts.append(obj)
        elif complement:
            parts.append(complement)
        return " ".join(parts).strip().rstrip(".") + "."

    @staticmethod
    def _compact_parse(parsed: Mapping[str, Any]) -> dict[str, Any]:
        """Keep semantic evidence without retaining token-level source copies."""
        return {
            "frame": dict(parsed.get("frame") or {}),
            "clauses": list(parsed.get("clauses") or []),
            "ambiguities": list(parsed.get("ambiguities") or []),
            "confidence": float(parsed.get("confidence") or 0),
            "compacted": True,
        }

    @staticmethod
    def _exercise(parsed: Mapping[str, Any], cycle_number: int) -> dict[str, str] | None:
        frame = dict(parsed.get("frame") or {})
        options: list[tuple[str, str, str, str]] = []
        if frame.get("subject"):
            options.append(("subject_retrieval", "Who performed the action?",
                            str(frame["subject"]), "The answer is the parsed subject."))
        if frame.get("action"):
            options.append(("action_retrieval", "What action happened?",
                            str(frame["action"]), "The answer is the parsed action lemma."))
        if frame.get("object"):
            options.append(("object_retrieval", "What object was affected?",
                            str(frame["object"]), "The answer is the complete parsed object."))
        if frame.get("time"):
            options.append(("time_retrieval", "When did the action happen?",
                            str(frame["time"]), "The answer is the parsed time expression."))
        if frame.get("location"):
            options.append(("location_retrieval", "Where did the action happen?",
                            str(frame["location"]), "The answer is the parsed location expression."))
        if frame.get("action"):
            options.append(("negation_scope", "Is the main action negated?",
                            "yes" if frame.get("negated") else "no",
                            "The answer follows the clause-specific negation flag."))
        if not options:
            return None
        family, question, expected, reason = options[cycle_number % len(options)]
        return {"family": family, "question": question,
                "expected_answer": expected, "answer_reason": reason}

    def _record_word_experience(self, *, source_id: str, sentence_id: str,
                                parsed: Mapping[str, Any], correct: bool) -> None:
        now = time.time()
        rows: dict[str, tuple[str, int]] = {}
        for token in parsed.get("tokens") or []:
            lemma = _normal(str(token.get("lemma") or token.get("token") or ""))
            if not lemma or lemma in FUNCTION_WORDS or not WORD_PATTERN.fullmatch(lemma):
                continue
            concept_id = str(token.get("concept_id") or "")
            parsed_use = int(str(token.get("source") or "") == "acquired_concept")
            rows[lemma] = (concept_id, parsed_use)
        with self._connect() as connection:
            for lemma, (concept_id, parsed_use) in rows.items():
                connection.execute(
                    """INSERT INTO native_reading_word_experience VALUES(?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(lemma,source_id) DO UPDATE SET
                       concept_id=CASE WHEN excluded.concept_id!='' THEN excluded.concept_id
                                      ELSE native_reading_word_experience.concept_id END,
                       encounters=encounters+1,parsed_uses=parsed_uses+excluded.parsed_uses,
                       successful_exercises=successful_exercises+excluded.successful_exercises,
                       last_sentence_id=excluded.last_sentence_id,last_seen_epoch=excluded.last_seen_epoch""",
                    (lemma, concept_id, source_id, 1, parsed_use, int(correct),
                     sentence_id, sentence_id, now, now),
                )

    def _record_claim(self, *, source: Mapping[str, Any], sentence_id: str,
                      frame: Mapping[str, Any], confidence: float) -> bool:
        subject, action = str(frame.get("subject") or ""), str(frame.get("action") or "")
        if not subject or not action:
            return False
        obj = str(frame.get("object") or frame.get("complement") or "")
        signature = [_normal(subject), _normal(action), _normal(obj), bool(frame.get("negated"))]
        claim_id = _identifier("reading_claim_", [source["source_id"], sentence_id, signature])
        provenance = {"source_id": source["source_id"], "title": source["title"],
                      "author": source["author"], "source_ref": source["source_ref"],
                      "sentence_id": sentence_id}
        with self._connect() as connection:
            corroborating = connection.execute(
                """SELECT claim_id FROM native_reading_claims
                   WHERE lower(subject)=? AND lower(action)=? AND lower(object)=?
                     AND negated=? AND source_id!=?""",
                (signature[0], signature[1], signature[2], int(signature[3]),
                 source["source_id"]),
            ).fetchall()
            corroboration_count = 1 + len({row[0] for row in corroborating})
            claim_status = ("corroborated" if corroboration_count > 1
                            else "single_source_claim")
            connection.execute(
                """INSERT OR IGNORE INTO native_reading_claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (claim_id, source["source_id"], sentence_id, subject, action, obj,
                 str(frame.get("tense") or "unknown"), int(bool(frame.get("negated"))),
                 json.dumps(provenance), float(confidence), corroboration_count,
                 claim_status, time.time()),
            )
            if corroborating:
                connection.executemany(
                    """UPDATE native_reading_claims SET corroboration_count=?,status='corroborated'
                       WHERE claim_id=?""",
                    [(corroboration_count, row[0]) for row in corroborating],
                )
        return True

    def _pending(self, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT s.*,r.title,r.author,r.subject,r.license,r.source_ref,
                          r.sentence_count AS source_sentence_count
                   FROM native_reading_sentences s
                   JOIN native_reading_sources r ON r.source_id=s.source_id
                   WHERE s.status='pending'
                   ORDER BY r.created_epoch,s.sentence_index LIMIT ?""",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def _should_deep_test(self, *, row: Mapping[str, Any], parsed: Mapping[str, Any],
                          discovered: list[str], slots_remaining: int,
                          candidates_remaining: int) -> bool:
        """Select evidence-rich sentences without examining routine prose one by one."""
        if slots_remaining <= 0:
            return False
        if int(row.get("source_sentence_count") or 0) <= self.short_source_full_test:
            return True
        if candidates_remaining <= slots_remaining:
            return True
        if discovered:
            return True
        confidence = float(parsed.get("confidence") or 0)
        if (parsed.get("ambiguities") or []) and confidence < 0.80:
            return True
        # Always sample the opening and regular checkpoints so long, familiar
        # stretches cannot disappear from comprehension coverage.
        checkpoint = max(4, round(1.0 / self.deep_test_ratio))
        if int(row.get("sentence_index") or 0) % checkpoint == 0:
            return True
        # Stable sampling makes restarts reproducible and prevents easy early
        # sentences from consuming every examination slot.
        digest = hashlib.sha256(str(row.get("sentence_id") or "").encode()).digest()
        return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF < self.deep_test_ratio

    def _due_retests(self, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT e.*,s.text,s.sentence_index,s.paragraph_index,
                          r.title,r.author,r.subject,r.license,r.source_ref
                   FROM native_reading_exercises e
                   JOIN native_reading_sentences s ON s.sentence_id=e.sentence_id
                   JOIN native_reading_sources r ON r.source_id=e.source_id
                   WHERE e.status IN ('correction_due','retention_scheduled')
                     AND COALESCE(e.due_epoch,0)<=?
                   ORDER BY e.due_epoch,e.created_epoch LIMIT ?""",
                (time.time(), int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _retest_question(family: str, original: str) -> str:
        variants = {
            "subject_retrieval": "Who carried out the action?",
            "action_retrieval": "What action did the sentence express?",
            "object_retrieval": "What complete object was affected by the action?",
            "time_retrieval": "When did the action occur?",
            "location_retrieval": "Where did the action occur?",
            "negation_scope": "Does the sentence deny its main action?",
        }
        return variants.get(str(family), original)

    def run_cycle(self, *, limit: int = 200,
                  discover_words: int | None = None) -> dict[str, Any]:
        if not self._acquire_cycle_lease():
            return {"status": "busy", "sentences_read": 0, "model_used": False}
        try:
            return self._run_cycle_locked(limit=limit, discover_words=discover_words)
        finally:
            self._release_cycle_lease()

    def _run_cycle_locked(self, *, limit: int,
                          discover_words: int | None) -> dict[str, Any]:
        cycle_started = time.time()
        self.seed_public_domain_starter()
        imported = self.scan_library(max_new_sources=self.max_imports_per_cycle)
        with self._connect() as connection:
            cycle_number = int(connection.execute(
                "SELECT COUNT(*) FROM native_reading_cycles"
            ).fetchone()[0])
        requested = max(1, min(500, int(limit)))
        with self._connect() as connection:
            pending_before = int(connection.execute(
                "SELECT COUNT(*) FROM native_reading_sentences WHERE status='pending'"
            ).fetchone()[0])
        online_outcome: dict[str, Any] = {"status": "disabled", "imported": 0}
        if self.online_enabled and pending_before < requested:
            online_outcome = self.online.harvest_once()
        if discover_words is None:
            discover_words = max(12, min(100, requested // 4))
        due = self._due_retests(max(1, min(40, requested // 5)))
        candidates = self._pending(max(0, requested - len(due)))
        if not candidates and not due:
            return {"status": "library_complete", "sentences_read": 0,
                    "sources_imported": len(imported) + int(online_outcome.get("imported") or 0),
                    "online_reader": online_outcome, "model_used": False}
        results: list[dict[str, Any]] = []
        new_concepts = 0
        claims = 0
        discovery_budget = max(0, int(discover_words))
        candidate_counts: dict[str, int] = {}
        candidate_source_sizes: dict[str, int] = {}
        for row in candidates:
            source_id = str(row.get("source_id") or "")
            candidate_counts[source_id] = candidate_counts.get(source_id, 0) + 1
            candidate_source_sizes[source_id] = int(row.get("source_sentence_count") or 0)
        deep_test_budget_by_source = {
            source_id: (
                count if candidate_source_sizes.get(source_id, 0) <= self.short_source_full_test
                else max(1, int(math.ceil(count * self.deep_test_ratio)))
            )
            for source_id, count in candidate_counts.items()
        }
        deep_tests_used = 0
        deep_tests_by_source: dict[str, int] = {}
        candidates_seen_by_source: dict[str, int] = {}
        for retry in due:
            parsed = self.transfer.parse(str(retry["text"]))
            question = self._retest_question(str(retry["family"]), str(retry["question"]))
            native = self.transfer.answer(str(retry["text"]), question)
            answer = str(native.get("answer") or "")
            correct = _normal(answer) == _normal(str(retry["expected_answer"] or ""))
            now = time.time()
            retry_id = _identifier("reading_exercise_", [retry["exercise_id"], question,
                                                           time.time_ns()])
            with self._connect() as connection:
                retention_exam = retry["status"] == "retention_scheduled"
                connection.execute(
                    "UPDATE native_reading_exercises SET status=? WHERE exercise_id=?",
                    ("retention_passed" if retention_exam and correct else "retested",
                     retry["exercise_id"]),
                )
                next_status = (
                    "passed" if retention_exam and correct
                    else "retention_scheduled" if correct
                    else "correction_due"
                )
                next_due = (
                    None if retention_exam and correct
                    else now + self.retention_delay_seconds if correct
                    else now + self.retry_delay_seconds * 2
                )
                connection.execute(
                    """INSERT INTO native_reading_exercises VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (retry_id, retry["sentence_id"], retry["source_id"], retry["family"],
                     question, retry["expected_answer"], retry["answer_reason"], answer,
                     int(correct), float(native.get("confidence") or 0), 0,
                     next_status, next_due, now, now),
                )
                if correct:
                    connection.execute(
                        """UPDATE native_reading_sentences SET status='completed',
                           text=CASE WHEN ? THEN '' ELSE text END,
                           parse_json=CASE WHEN ? THEN ? ELSE parse_json END
                           WHERE sentence_id=?""",
                        (int(retention_exam), int(retention_exam),
                         json.dumps(self._compact_parse(parsed)), retry["sentence_id"]),
                    )
                    if retention_exam:
                        connection.execute(
                            """UPDATE native_reading_storage_metrics
                               SET sentence_characters_compacted=sentence_characters_compacted+?,
                                   updated_epoch=? WHERE singleton=1""",
                            (len(str(retry["text"] or "")), now),
                        )
            self._record_word_experience(
                source_id=retry["source_id"], sentence_id=retry["sentence_id"],
                parsed=parsed, correct=correct,
            )
            results.append({"source": retry["title"], "sentence_id": retry["sentence_id"],
                            "sentence_index": retry["sentence_index"],
                            "family": retry["family"], "answer": answer, "correct": correct,
                            "summary": self._summary(parsed.get("frame") or {}),
                            "acquired_words_used": len(self._analyse_words(parsed)[0]),
                            "reference_words": len(self._analyse_words(parsed)[1]),
                            "unknown_words": self._analyse_words(parsed)[2],
                            "new_concepts_encountered": [], "retest": True,
                            "retention_exam": retention_exam,
                            "model_used": False})
        for offset, row in enumerate(candidates):
            source_id = str(row.get("source_id") or "")
            candidates_seen_by_source[source_id] = candidates_seen_by_source.get(source_id, 0) + 1
            parsed = self.transfer.parse(str(row["text"]))
            acquired, reference, unknown = self._analyse_words(parsed)
            discovered: list[str] = []
            for lemma in [*reference, *unknown]:
                if discovery_budget <= 0:
                    break
                if self.wordwall.acquired(lemma):
                    continue
                created = self.wordwall.encounter(
                    lemma, teacher_lesson_id=f"reading:{row['source_id']}:{row['sentence_id']}",
                )
                if created:
                    discovered.append(lemma)
                    new_concepts += len(created)
                    discovery_budget -= 1
            should_test = self._should_deep_test(
                row=row, parsed=parsed, discovered=discovered,
                slots_remaining=(deep_test_budget_by_source.get(source_id, 0)
                                 - deep_tests_by_source.get(source_id, 0)),
                candidates_remaining=(candidate_counts.get(source_id, 0)
                                      - candidates_seen_by_source[source_id] + 1),
            )
            exercise = self._exercise(parsed, cycle_number + offset) if should_test else None
            if exercise:
                deep_tests_used += 1
                deep_tests_by_source[source_id] = deep_tests_by_source.get(source_id, 0) + 1
            answer, confidence, correct, exercise_id = "", float(parsed.get("confidence") or 0), False, ""
            if exercise:
                # The answer key is sealed in `exercise`; only the material,
                # question and acquired memory reach the student operation.
                native = self.transfer.answer(str(row["text"]), exercise["question"])
                answer = str(native.get("answer") or "")
                confidence = float(native.get("confidence") or confidence)
                correct = _normal(answer) == _normal(exercise["expected_answer"])
                exercise_id = _identifier("reading_exercise_", [row["sentence_id"],
                                                                  exercise, time.time_ns()])
                now = time.time()
                with self._connect() as connection:
                    connection.execute(
                        """INSERT INTO native_reading_exercises VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (exercise_id, row["sentence_id"], row["source_id"], exercise["family"],
                         exercise["question"], exercise["expected_answer"], exercise["answer_reason"],
                         answer, int(correct), confidence, 0,
                         "retention_scheduled" if correct else "correction_due",
                         (now + self.retention_delay_seconds if correct
                          else now + self.retry_delay_seconds), now, now),
                    )
            summary = self._summary(parsed.get("frame") or {})
            sentence_status = (
                "completed" if exercise and correct else
                "needs_review" if exercise else "exposed"
            )
            compacted_characters = 0 if exercise else len(str(row["text"] or ""))
            with self._connect() as connection:
                connection.execute(
                    """UPDATE native_reading_sentences SET status=?,text=?,parse_json=?,
                       acquired_concepts_json=?,reference_words_json=?,unknown_words_json=?,
                       summary_text=?,processed_epoch=? WHERE sentence_id=?""",
                    (sentence_status, str(row["text"] or "") if exercise else "",
                     json.dumps(self._compact_parse(parsed)), json.dumps(acquired), json.dumps(reference),
                     json.dumps(unknown), summary, time.time(), row["sentence_id"]),
                )
                if compacted_characters:
                    connection.execute(
                        """UPDATE native_reading_storage_metrics
                           SET sentence_characters_compacted=sentence_characters_compacted+?,
                               updated_epoch=? WHERE singleton=1""",
                        (compacted_characters, time.time()),
                    )
                remaining = int(connection.execute(
                    "SELECT COUNT(*) FROM native_reading_sentences WHERE source_id=? AND status='pending'",
                    (row["source_id"],),
                ).fetchone()[0])
                connection.execute(
                    """UPDATE native_reading_sources SET status=?,next_sentence_index=?,updated_epoch=?
                       WHERE source_id=?""",
                    ("completed" if remaining == 0 else "reading",
                     max(int(row["sentence_index"]) + 1, int(connection.execute(
                         "SELECT next_sentence_index FROM native_reading_sources WHERE source_id=?",
                         (row["source_id"],),
                     ).fetchone()[0])), time.time(), row["source_id"]),
                )
            self._record_word_experience(
                source_id=row["source_id"], sentence_id=row["sentence_id"],
                parsed=parsed, correct=bool(exercise and correct),
            )
            claims += int(self._record_claim(
                source=row, sentence_id=row["sentence_id"],
                frame=parsed.get("frame") or {}, confidence=confidence,
            ))
            results.append({"source": row["title"], "sentence_id": row["sentence_id"],
                            "sentence_index": row["sentence_index"],
                            "family": exercise.get("family") if exercise else None,
                            "answer": answer, "correct": correct if exercise else None,
                            "summary": summary, "acquired_words_used": len(acquired),
                            "reference_words": len(reference), "unknown_words": unknown,
                            "new_concepts_encountered": discovered, "model_used": False})
        attempted = sum(row["correct"] is not None for row in results)
        correct_count = sum(row["correct"] is True for row in results)
        elapsed = max(0.001, time.time() - cycle_started)
        detail = {"status": "completed", "sentences_read": len(results),
                  "exercises_attempted": attempted, "exercises_correct": correct_count,
                  "exposure_only": len(candidates) - deep_tests_used,
                  "deep_tests_selected": deep_tests_used,
                  "deep_test_ratio": self.deep_test_ratio,
                  "elapsed_seconds": round(elapsed, 4),
                  "sentences_per_second": round(len(results) / elapsed, 4),
                  "new_concepts_encountered": new_concepts, "claims_recorded": claims,
                  "sources_imported": (len(imported)
                                       + int(online_outcome.get("imported") or 0)),
                  "online_reader": online_outcome, "results": results,
                  "retests_attempted": len(due),
                  "retests_cleared": sum(bool(row.get("retest") and row.get("correct"))
                                         for row in results),
                  "model_used_for_reading": False,
                  "next_token_prediction": False,
                  "counts_as_mastery": False}
        cycle_id = _identifier("reading_cycle_", [cycle_number, detail, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_reading_cycles VALUES(?,?,?,?,?,?,?,?)",
                (cycle_id, len(results), attempted, correct_count, new_concepts,
                 claims, json.dumps(detail), time.time()),
            )
        return {"cycle_id": cycle_id, **detail}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            sources = connection.execute(
                """SELECT COUNT(*),SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),
                          COALESCE(SUM(sentence_count),0)
                   FROM native_reading_sources"""
            ).fetchone()
            sentences = connection.execute(
                """SELECT COUNT(*),SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='needs_review' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='exposed' THEN 1 ELSE 0 END)
                   FROM native_reading_sentences"""
            ).fetchone()
            exercises = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(correct),0),
                          SUM(CASE WHEN status='correction_due' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='correction_due' AND due_epoch<=? THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='retention_scheduled' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='retention_scheduled' AND due_epoch<=? THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='retention_passed' THEN 1 ELSE 0 END)
                   FROM native_reading_exercises""", (time.time(), time.time()),
            ).fetchone()
            experience = connection.execute(
                """SELECT COUNT(DISTINCT lemma),COALESCE(SUM(encounters),0),
                          COALESCE(SUM(parsed_uses),0),COALESCE(SUM(successful_exercises),0)
                   FROM native_reading_word_experience"""
            ).fetchone()
            claims = connection.execute("SELECT COUNT(*) FROM native_reading_claims").fetchone()
            imports = connection.execute(
                """SELECT COUNT(*),
                          SUM(CASE WHEN status='queued' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='quarantined' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN format='pdf' AND status='queued' THEN 1 ELSE 0 END)
                   FROM native_reading_imports"""
            ).fetchone()
            storage = connection.execute(
                """SELECT sentence_characters_compacted FROM native_reading_storage_metrics
                   WHERE singleton=1"""
            ).fetchone()
            stored_characters = connection.execute(
                "SELECT COALESCE(SUM(length(text)),0) FROM native_reading_sentences"
            ).fetchone()
            cycles = connection.execute("SELECT COUNT(*),MAX(created_epoch) FROM native_reading_cycles").fetchone()
            latest_cycle = connection.execute(
                "SELECT detail_json FROM native_reading_cycles ORDER BY created_epoch DESC LIMIT 1"
            ).fetchone()
            runtime = connection.execute(
                "SELECT busy,lease_epoch FROM native_reading_runtime WHERE singleton=1"
            ).fetchone()
            recent = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(correct),0) FROM native_reading_exercises
                   WHERE attempted_epoch>?""", (time.time() - 3600,),
            ).fetchone()
            source_rows = connection.execute(
                """SELECT source_id,title,author,subject,license,status,sentence_count,
                          next_sentence_index,source_ref,format,extraction_method,
                          extraction_quality FROM native_reading_sources
                   ORDER BY updated_epoch DESC LIMIT 12"""
            ).fetchall()
        attempts, correct = int(exercises[0] or 0), int(exercises[1] or 0)
        latest_detail = json.loads(latest_cycle[0]) if latest_cycle else {}
        online_metrics = self.online.metrics()
        online_metrics["enabled"] = self.online_enabled
        return {
            "cycles": int(cycles[0] or 0), "last_cycle_epoch": cycles[1],
            "running": bool(runtime[0]) and float(runtime[1] or 0) > time.time() - 1800,
            "sources": int(sources[0] or 0), "sources_completed": int(sources[1] or 0),
            "sentences_available": int(sources[2] or 0),
            "sentences_processed": (int(sentences[1] or 0) + int(sentences[2] or 0)
                                    + int(sentences[4] or 0)),
            "sentences_passed": int(sentences[1] or 0),
            "sentences_needing_review": int(sentences[2] or 0),
            "sentences_pending": int(sentences[3] or 0),
            "sentences_exposure_only": int(sentences[4] or 0),
            "stored_sentence_characters": int(stored_characters[0] or 0),
            "sentence_characters_compacted": int(storage[0] or 0),
            "latest_cycle_sentences_per_second": latest_detail.get("sentences_per_second"),
            "latest_cycle_elapsed_seconds": latest_detail.get("elapsed_seconds"),
            "latest_cycle_deep_tests": int(latest_detail.get("deep_tests_selected") or 0),
            "deep_test_ratio": self.deep_test_ratio,
            "configured_batch_size": max(
                1, min(100, int(os.getenv("AION_READING_ACADEMY_BATCH", "40")))
            ),
            "configured_interval_seconds": max(
                30.0, float(os.getenv("AION_READING_ACADEMY_INTERVAL", "60"))
            ),
            "exercises": attempts, "correct": correct,
            "accuracy": round(correct / attempts, 4) if attempts else None,
            "corrections_due": int(exercises[2] or 0),
            "corrections_due_now": int(exercises[3] or 0),
            "retention_scheduled": int(exercises[4] or 0),
            "retention_due": int(exercises[5] or 0),
            "retention_passed": int(exercises[6] or 0),
            "recent_attempts": int(recent[0] or 0), "recent_correct": int(recent[1] or 0),
            "recent_accuracy": (round(int(recent[1] or 0) / int(recent[0]), 4)
                                if int(recent[0] or 0) else None),
            "distinct_words_experienced": int(experience[0] or 0),
            "word_encounters": int(experience[1] or 0),
            "acquired_word_uses": int(experience[2] or 0),
            "successful_word_contexts": int(experience[3] or 0),
            "provenanced_claims": int(claims[0] or 0),
            "document_imports": int(imports[0] or 0),
            "imports_ready": int(imports[1] or 0),
            "imports_quarantined": int(imports[2] or 0),
            "pdfs_ready": int(imports[3] or 0),
            "online_reader": online_metrics,
            "source_list": [dict(row) for row in source_rows],
            "supported_formats": sorted(SUPPORTED_EXTENSIONS),
            "library_directories": [str(path) for path in self.library_directories],
            "model_used_for_reading": False,
            "counts_as_mastery": False,
            "claim_boundary": (
                "A read sentence is sourced experience, not established truth. "
                "Comprehension practice does not grant mastery without independent transfer and retention."
            ),
        }


__all__ = ["NativeReadingAcademy", "READING_FAMILIES", "SUPPORTED_EXTENSIONS"]
