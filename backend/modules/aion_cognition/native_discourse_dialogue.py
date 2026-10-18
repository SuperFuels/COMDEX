"""Persistent model-free discourse, reasoning, and dialogue for Aion.

This module deliberately keeps the student path deterministic.  A teacher may
author sealed examination material outside this class, but parsing, situation
construction, evidence selection, response planning, realisation, correction,
and delayed retesting never call a model or cloud service.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable, Mapping, Sequence

from backend.modules.aion_cognition.sqlite_connection import (
    connect as sqlite_connect,
    connect_read_only as sqlite_read_connect,
)
from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer, _normal
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
PRONOUNS = {
    "he": "person", "him": "person", "his": "person", "she": "person",
    "her": "person", "hers": "person", "they": "plural", "them": "plural",
    "their": "plural", "theirs": "plural", "it": "thing", "its": "thing",
    "this": "thing", "that": "thing", "these": "plural", "those": "plural",
}
CAUSE_MARKERS = ("because", "since", "as a result", "therefore", "so")
SEQUENCE_MARKERS = {
    "before": "before", "after": "after", "then": "after", "later": "after",
    "earlier": "before", "first": "before", "finally": "after",
}
SEQUENCE_SUBJECT_STOPWORDS = {
    "a", "an", "the", "and", "but", "for", "nor", "or", "so", "yet",
    "after", "although", "because", "before", "concerning", "during",
    "finally", "first", "if", "later", "next", "regarding", "since",
    "then", "there", "therefore", "though", "to", "until", "when",
    "where", "whether", "while", "with", "without",
}
SEQUENCE_ACTION_STOPWORDS = {
    "act", "am", "are", "be", "been", "being", "did", "do", "does",
    "had", "has", "have", "is", "need", "needed", "sense", "was", "were",
}
RETENTION_DELAYS = {"retention_1d": 86400.0, "retention_7d": 604800.0,
                    "retention_30d": 2592000.0}
TIME_EXPRESSION_RE = re.compile(
    r"\b(?:(?:next|last|this)\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"week|month|year)|(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)|"
    r"yesterday|today|tomorrow|tonight|this\s+(?:morning|afternoon|evening)|"
    r"(?:before|after|during|by)\s+(?:the\s+)?(?:dawn|sunrise|morning|noon|afternoon|"
    r"evening|sunset|dusk|night|midnight|breakfast|lunch|dinner|weekend|"
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|today|tomorrow|yesterday)|"
    r"at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)\b",
    re.I,
)


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _sentence(text: str) -> str:
    value = " ".join(str(text or "").strip().split())
    if not value:
        return value
    value = value[0].upper() + value[1:]
    return value if value[-1] in ".?!" else value + "."


def _sentences(text: str) -> list[str]:
    clean = " ".join(str(text or "").strip().split())
    return [part.strip() for part in SENTENCE_RE.split(clean) if part.strip()]


def _proper_names(text: str) -> list[str]:
    words = WORD_RE.findall(text)
    return [word for index, word in enumerate(words)
            if word[:1].isupper() and (index > 0 or word.lower() not in {
                "after", "before", "because", "although", "when", "while", "the",
            }) and word.lower() not in PRONOUNS]


def _explicit_time(text: str) -> str:
    match = TIME_EXPRESSION_RE.search(str(text or ""))
    return " ".join(match.group(0).split()) if match else ""


class NativeDiscourseDialogueEngine:
    """Build situation models and answer from explicit, cited propositions."""

    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.transfer = NativeEnglishTransfer(repo_root=self.repo_root, lexical=self.lexical)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _read_connect(self) -> sqlite3.Connection:
        connection = sqlite_read_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_discourse_models(
                    model_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                    source_id TEXT NOT NULL, source_family TEXT NOT NULL,
                    content_signature TEXT NOT NULL, passage TEXT NOT NULL,
                    model_json TEXT NOT NULL, created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_discourse_session
                    ON native_discourse_models(session_id,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_discourse_entities(
                    entity_id TEXT PRIMARY KEY, model_id TEXT NOT NULL,
                    canonical_name TEXT NOT NULL, entity_type TEXT NOT NULL,
                    mentions_json TEXT NOT NULL, properties_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_discourse_events(
                    event_id TEXT PRIMARY KEY, model_id TEXT NOT NULL,
                    sentence_index INTEGER NOT NULL, subject TEXT NOT NULL,
                    action TEXT NOT NULL, object_value TEXT NOT NULL,
                    time_value TEXT NOT NULL, location TEXT NOT NULL,
                    negated INTEGER NOT NULL, cause_event_id TEXT NOT NULL,
                    evidence_text TEXT NOT NULL, parse_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_dialogue_sessions(
                    session_id TEXT PRIMARY KEY, active_model_id TEXT NOT NULL DEFAULT '',
                    focus_entity TEXT NOT NULL DEFAULT '', focus_event_id TEXT NOT NULL DEFAULT '',
                    turn_count INTEGER NOT NULL DEFAULT 0, state_json TEXT NOT NULL DEFAULT '{}',
                    updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_dialogue_turns(
                    turn_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                    model_id TEXT NOT NULL, question TEXT NOT NULL,
                    intent TEXT NOT NULL, answer TEXT NOT NULL, status TEXT NOT NULL,
                    confidence REAL NOT NULL, response_plan_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL, checks_json TEXT NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0, created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_dialogue_turn_session
                    ON native_dialogue_turns(session_id,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_dialogue_corrections(
                    correction_id TEXT PRIMARY KEY, turn_id TEXT NOT NULL,
                    verified_answer TEXT NOT NULL, explanation TEXT NOT NULL,
                    source_ref TEXT NOT NULL, status TEXT NOT NULL,
                    due_epoch REAL NOT NULL, retention_stage TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL, cleared_epoch REAL
                );
                CREATE TABLE IF NOT EXISTS native_discourse_exams(
                    exam_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
                    source_family TEXT NOT NULL, passage_signature TEXT NOT NULL,
                    family TEXT NOT NULL, question TEXT NOT NULL,
                    expected_answer TEXT NOT NULL, answer TEXT NOT NULL,
                    correct INTEGER NOT NULL, confidence REAL NOT NULL,
                    evidence_json TEXT NOT NULL, answer_sealed INTEGER NOT NULL,
                    source_disjoint INTEGER NOT NULL, retention_stage TEXT NOT NULL,
                    due_epoch REAL, model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS native_discourse_exam_unique
                    ON native_discourse_exams(passage_signature,family,retention_stage);
                CREATE TABLE IF NOT EXISTS native_discourse_exam_remediation(
                    obligation_id TEXT PRIMARY KEY, exam_id TEXT NOT NULL,
                    status TEXT NOT NULL, due_epoch REAL NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL, cleared_epoch REAL
                );
                """
            )
            exam_columns = {str(row[1]) for row in connection.execute(
                "PRAGMA table_info(native_discourse_exams)"
            ).fetchall()}
            for name, definition in (
                ("passage", "TEXT NOT NULL DEFAULT ''"),
                ("answer_reason", "TEXT NOT NULL DEFAULT ''"),
                ("teacher_model", "TEXT NOT NULL DEFAULT ''"),
                ("validity_status", "TEXT NOT NULL DEFAULT 'valid'"),
            ):
                if name not in exam_columns:
                    connection.execute(
                        f"ALTER TABLE native_discourse_exams ADD COLUMN {name} {definition}"
                    )
            # Preserve malformed legacy receipts for audit, but do not punish
            # Aion for an index fragment or a particle mislabelled as an object.
            historical = connection.execute(
                """SELECT exam_id,passage,family,expected_answer,validity_status
                   FROM native_discourse_exams"""
            ).fetchall()
            for row in historical:
                is_valid = self._exam_contract_valid(
                    str(row["passage"] or ""), str(row["family"] or ""),
                    str(row["expected_answer"] or ""),
                )
                if not is_valid and row["validity_status"] == "valid":
                    connection.execute(
                        "UPDATE native_discourse_exams SET validity_status='invalidated_contract',due_epoch=NULL WHERE exam_id=?",
                        (row["exam_id"],),
                    )
                    connection.execute(
                        "UPDATE native_discourse_exam_remediation SET status='invalidated_contract' WHERE exam_id=?",
                        (row["exam_id"],),
                    )
                elif is_valid and row["validity_status"] == "invalidated_contract":
                    connection.execute(
                        "UPDATE native_discourse_exams SET validity_status='valid' WHERE exam_id=?",
                        (row["exam_id"],),
                    )
            # A failed valid sealed exam must never become a dead audit row. Backfill
            # obligations created by earlier engine versions exactly once.
            failed = connection.execute(
                """SELECT exam_id,expected_answer,answer_reason,created_epoch
                   FROM native_discourse_exams e
                   WHERE correct=0 AND validity_status='valid' AND NOT EXISTS(
                     SELECT 1 FROM native_discourse_exam_remediation r WHERE r.exam_id=e.exam_id
                   )"""
            ).fetchall()
            for row in failed:
                obligation_id = _identifier(
                    "native_discourse_remediation_",
                    [row["exam_id"], row["expected_answer"], row["answer_reason"]],
                )
                connection.execute(
                    "INSERT INTO native_discourse_exam_remediation VALUES(?,?,'due',?,0,?,NULL)",
                    (obligation_id, row["exam_id"], time.time() + 900.0,
                     float(row["created_epoch"] or time.time())),
                )

    @staticmethod
    def _passage_is_prose(passage: str) -> bool:
        """Reject contents/index fragments before they become language exams."""
        text = " ".join(str(passage or "").split())
        words = WORD_RE.findall(text)
        if len(words) < 12:
            return False
        if len(words) > 450:
            return False
        # Tables of contents, indexes and scraped navigation can contain many
        # dictionary words while still not being connected English.  They tend
        # to be lists of short, title-cased fragments rather than sentences.
        sentence_parts = [part for part in re.split(r"(?<=[.!?])\s+", text) if part]
        if len(sentence_parts) < 2 and text.count(";") + text.count(",") < 2:
            return False
        title_case = sum(word[:1].isupper() for word in words)
        if len(words) >= 24 and title_case / len(words) > .42:
            return False
        semicolon_parts = text.split(";")
        if len(semicolon_parts) >= 4:
            short_tail = sum(
                len(WORD_RE.findall(part)) <= 4 for part in semicolon_parts[1:]
            )
            if short_tail / max(1, len(semicolon_parts) - 1) >= .75:
                return False
        if len(re.findall(r"\b(?:Of|In|With)\s+[A-Z][A-Za-z'-]+", text)) >= 3:
            return False
        if re.search(r"\b(?:contents|index|chapter\s+[ivxlcdm]+)\b", text, re.I):
            return False
        if re.search(r"(?:^|[.;]\s+)(?:MISCELLANEOUS|APPENDIX|BIBLIOGRAPHY|GLOSSARY)(?:\b|$)", text):
            return False
        if len(re.findall(r"\b(?:vol\.?|pp?\.?|fig\.?|table|section)\s*[ivxlcdm\d]+\b", text, re.I)) >= 3:
            return False
        return True

    def _exam_contract_valid(self, passage: str, family: str, expected: str) -> bool:
        if not self._passage_is_prose(passage):
            return False
        value = " ".join(str(expected or "").split())
        terms = WORD_RE.findall(value)
        if not value or len(terms) > 18:
            return False
        if family == "object" and _normal(value).split(" ")[0] in {
            "up", "down", "out", "off", "away", "over", "through",
        }:
            return False
        if family == "object" and not self._object_answer_safe(value):
            return False
        if family == "location" and not self._location_answer_safe(value):
            return False
        if family == "entity" and not self._grounded_named_entity(value):
            return False
        if family == "action":
            action_terms = [term.lower() for term in terms]
            if (not action_terms or len(action_terms) > 3
                    or action_terms[0] in {
                        "and", "or", "but", "still", "then", "there", "here",
                        "be", "am", "is", "are", "was", "were", "been",
                        "do", "does", "did", "have", "has", "had", "say", "get",
                    }):
                return False
        if family == "coreference":
            terms = WORD_RE.findall(value)
            if (not terms or terms[0].lower() in set(PRONOUNS) | {
                "a", "an", "the", "this", "that", "these", "those", "my",
                "our", "your", "his", "her", "their", "with", "from", "to",
                "in", "on", "at", "by", "for", "of",
            } or not (self._grounded_named_entity(value)
                      or self._object_answer_safe(value))):
                return False
        if family in {"sequence_first", "sequence_next"}:
            if not self._sequence_answer_safe(value):
                return False
        return True

    def _sequence_answer_safe(self, value: str) -> bool:
        """Reject headings and connective fragments masquerading as events."""
        terms = WORD_RE.findall(str(value or ""))
        if len(terms) < 2 or len(terms) > 18:
            return False
        if terms[0].lower() in SEQUENCE_SUBJECT_STOPWORDS:
            return False
        subject_terms: list[str] = []
        action_index = 0
        for index, term in enumerate(terms):
            if term[:1].isupper() and index < 3:
                subject_terms.append(term)
                action_index = index + 1
                continue
            break
        if not subject_terms or action_index >= len(terms):
            return False
        if not self._grounded_named_entity(" ".join(subject_terms)):
            return False
        return terms[action_index].lower() not in SEQUENCE_ACTION_STOPWORDS

    def _sequence_event_safe(self, event: Mapping[str, Any]) -> bool:
        if event.get("subordinate"):
            return False
        subject = str(event.get("subject") or "").strip()
        action = str(event.get("action") or "").strip().lower()
        surface = str(event.get("action_surface") or action).strip()
        if not subject or not surface or not self._grounded_named_entity(subject):
            return False
        first = (WORD_RE.findall(subject) or [""])[0].lower()
        if first in SEQUENCE_SUBJECT_STOPWORDS:
            return False
        if action in SEQUENCE_ACTION_STOPWORDS or surface.lower() in SEQUENCE_ACTION_STOPWORDS:
            return False
        expected = " ".join(str(event.get(key) or "") for key in
                            ("subject", "action_surface", "object")).strip()
        return self._sequence_answer_safe(expected)

    def _grounded_named_entity(self, value: str) -> bool:
        terms = WORD_RE.findall(str(value or ""))
        return bool(
            terms
            and len(terms) <= 3
            and all(term[:1].isupper() for term in terms)
            and terms[0].lower() not in {
                "a", "an", "the", "this", "that", "these", "those",
                "my", "our", "your", "his", "her", "their", "every",
                "each", "some", "any", "one", "of", "in", "on", "at",
                "o", "tis", "twas", "ay", "nay", "alas",
            }
            and not any(self.lexical.lookup_senses(term.lower()) for term in terms)
        )

    def _location_answer_safe(self, value: str) -> bool:
        """Require lexical evidence that a parsed prepositional phrase is a place."""
        terms = [term.lower() for term in WORD_RE.findall(str(value or ""))]
        if not terms or len(terms) > 8 or terms[0] not in {
            "at", "in", "inside", "into", "near", "on", "outside", "under",
            "within", "beside", "behind", "between", "above", "below",
        }:
            return False
        place_cues = {
            "area", "building", "city", "country", "district", "location",
            "place", "region", "room", "site", "space", "structure", "town",
            "village", "workplace",
        }
        for term in reversed(terms[1:]):
            for sense in self.lexical.lookup_senses(term, "n"):
                if set(WORD_RE.findall(str(sense.get("definition") or "").lower())) & place_cues:
                    return True
        return False

    def _object_answer_safe(self, value: str) -> bool:
        terms = [term.lower() for term in WORD_RE.findall(str(value or ""))]
        if not terms or len(terms) > 8:
            return False
        blocked_edges = set(PRONOUNS) | {
            "and", "or", "but", "because", "if", "when", "while", "that",
            "which", "who", "whom", "whose", "to", "from", "for", "of",
            "in", "on", "at", "by", "with", "without", "up", "down", "out",
            "off", "away", "over", "through", "only", "very", "not", "there",
        }
        # Determiners may open a complete noun phrase, but a pronoun, connective
        # or particle cannot be the object Aion is expected to retrieve.
        if terms[0] in blocked_edges or terms[-1] in blocked_edges:
            return False
        head = terms[-1]
        noun_senses = self.lexical.lookup_senses(head, "n")
        if not noun_senses:
            return False
        # Reject parser spill-over such as "air comes": the final token is a
        # verb surface, not the head of a complete noun phrase.
        if self.lexical.lookup_senses(head, "v") and not noun_senses:
            return False
        return True

    def _resolve_pronoun(self, word: str, entities: Sequence[dict[str, Any]],
                         events: Sequence[Mapping[str, Any]] = ()) -> str:
        target = PRONOUNS.get(word.lower())
        if not target:
            return word
        if target == "person":
            for event in reversed(events):
                subject = str(event.get("subject") or "").strip()
                if (subject and _normal(subject) not in PRONOUNS
                        and self._grounded_named_entity(subject)):
                    return subject
        candidates = [row for row in reversed(entities)
                      if target == "plural" or row["entity_type"] == target]
        return str(candidates[0]["canonical_name"]) if candidates else ""

    def build_situation_model(
        self, passage: str, *, session_id: str, source_id: str = "owner_dialogue",
        source_family: str = "owner", persist: bool = True,
    ) -> dict[str, Any]:
        parts = _sentences(passage)
        model_id = _identifier("native_discourse_model_", [session_id, source_id, passage, time.time_ns()])
        entities: list[dict[str, Any]] = []
        entity_by_name: dict[str, dict[str, Any]] = {}
        events: list[dict[str, Any]] = []
        relations: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        last_event_id = ""

        def remember_entity(name: str, kind: str, mention: str, index: int) -> str:
            canonical = " ".join(str(name or "").strip().split())
            if not canonical:
                return ""
            key = canonical.lower()
            row = entity_by_name.get(key)
            if row is None:
                row = {"entity_id": _identifier("native_discourse_entity_", [model_id, key]),
                       "canonical_name": canonical, "entity_type": kind,
                       "mentions": [], "properties": []}
                entities.append(row)
                entity_by_name[key] = row
            row["mentions"].append({"surface": mention, "sentence_index": index})
            return canonical

        for index, text in enumerate(parts):
            # Parse the independent clause first. Feeding an entire literary
            # sentence to a single-clause parser made a trailing relative
            # clause overwrite the real event (for example, "his hand was
            # raised" replacing "he carried a hat").
            fronted_cause = re.match(r"^because\s+(.+?),\s*(.+)$", text, re.I)
            main_clause = (fronted_cause.group(2).strip() if fronted_cause else re.split(
                r",\s*(?:while|although|whereas|which|who|for|as)\b|;", text,
                maxsplit=1, flags=re.I,
            )[0].strip())
            parsed = self.transfer.parse(main_clause or text)
            frame = dict(parsed.get("frame") or {})
            names = _proper_names(text)
            for name in names:
                remember_entity(name, "person", name, index)
            subject = str(frame.get("subject") or "").strip()
            object_value = str(frame.get("object") or "").strip()
            for role, value in (("subject", subject), ("object", object_value)):
                first = (WORD_RE.findall(value) or [""])[0]
                if first.lower() in PRONOUNS:
                    resolved = self._resolve_pronoun(first, entities, events)
                    if resolved:
                        replacement = value.replace(first, resolved, 1)
                        if role == "subject":
                            subject = replacement
                        else:
                            object_value = replacement
                        relations.append({"type": "coreference", "surface": first,
                                          "target": resolved, "sentence_index": index})
                    else:
                        unresolved.append({"type": "coreference", "surface": first,
                                           "sentence_index": index})
            if not subject and names:
                subject = names[0]
            subject = remember_entity(subject, "person" if subject in names else "thing",
                                      str(frame.get("subject") or subject), index) or subject
            if object_value:
                remember_entity(object_value, "thing", object_value, index)
            action = str(frame.get("action") or "").strip()
            # The lower-level parser may label any ``by + noun phrase`` as
            # temporal (for example an author's byline). Keep only phrases
            # that independently match the bounded temporal vocabulary.
            time_value = _explicit_time(str(frame.get("time") or "")) or _explicit_time(text)
            event_id = _identifier("native_discourse_event_", [model_id, index, text])
            event = {
                "event_id": event_id, "sentence_index": index, "subject": subject,
                "action": action, "action_surface": str(frame.get("action_surface") or action),
                "object": object_value, "time": time_value,
                "location": str(frame.get("location") or ""),
                "tense": str(frame.get("tense") or "present"),
                "negated": bool(frame.get("negated")), "cause_event_id": "",
                "evidence_text": text, "confidence": float(parsed.get("confidence") or 0),
                "parse": parsed,
            }
            lowered = text.lower()
            marker = next((item for item in CAUSE_MARKERS
                           if re.search(rf"\b{re.escape(item)}\b", lowered)), "")
            if marker == "because":
                cause_text = (fronted_cause.group(1).strip(" .") if fronted_cause else
                              re.split(r"\bbecause\b", text, maxsplit=1,
                                       flags=re.I)[-1].strip(" ."))
                cause_parse = self.transfer.parse(cause_text)
                cause_frame = dict(cause_parse.get("frame") or {})
                cause_subject = str(cause_frame.get("subject") or "").strip()
                if not cause_subject:
                    cause_words = WORD_RE.findall(cause_text)
                    stop = next((i for i, word in enumerate(cause_words)
                                 if word.lower() in {"had", "has", "have", "was", "were", "is", "are"}), 0)
                    if stop:
                        cause_subject = " ".join(word for word in cause_words[:stop]
                                                 if word.lower() not in {"a", "an", "the"})
                cause_first = (WORD_RE.findall(cause_subject) or [""])[0]
                if cause_first.lower() in PRONOUNS:
                    cause_subject = self._resolve_pronoun(cause_first, entities, events) or cause_subject
                cause_id = _identifier("native_discourse_event_", [model_id, index, "cause", cause_text])
                cause_event = {
                    "event_id": cause_id, "sentence_index": index,
                    "subject": cause_subject,
                    "action": str(cause_frame.get("action") or ""),
                    "action_surface": str(cause_frame.get("action_surface") or cause_frame.get("action") or ""),
                    "object": str(cause_frame.get("object") or ""),
                    "time": str(cause_frame.get("time") or ""),
                    "location": str(cause_frame.get("location") or ""),
                    "tense": str(cause_frame.get("tense") or "past"),
                    "negated": bool(cause_frame.get("negated")), "cause_event_id": "",
                    "evidence_text": text, "confidence": float(cause_parse.get("confidence") or 0),
                    "parse": cause_parse, "subordinate": True,
                }
                events.append(cause_event)
                event["cause_event_id"] = cause_id
                relations.append({"type": "cause", "from_event": cause_id,
                                  "to_event": event_id, "marker": marker})
            elif marker and last_event_id:
                event["cause_event_id"] = last_event_id
                relations.append({"type": "cause", "from_event": last_event_id,
                                  "to_event": event_id, "marker": marker})
            sequence = next((value for key, value in SEQUENCE_MARKERS.items()
                             if re.search(rf"\b{re.escape(key)}\b", lowered)), "")
            if sequence and last_event_id:
                relations.append({"type": sequence, "from_event": last_event_id,
                                  "to_event": event_id})
            events.append(event)
            last_event_id = event_id

        model = {"model_id": model_id, "session_id": session_id, "source_id": source_id,
                 "source_family": source_family, "passage": passage, "entities": entities,
                 "events": events, "relations": relations, "unresolved": unresolved,
                 "content_signature": hashlib.sha256(_normal(passage).encode()).hexdigest(),
                 "model_used": False, "cloud_used": False}
        if persist:
            now = time.time()
            serialisable = {**model, "events": [
                {key: value for key, value in row.items() if key != "parse"} for row in events
            ]}
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO native_discourse_models VALUES(?,?,?,?,?,?,?,?)",
                    (model_id, session_id, source_id, source_family, model["content_signature"],
                     passage, json.dumps(serialisable, sort_keys=True), now),
                )
                for row in entities:
                    connection.execute(
                        "INSERT INTO native_discourse_entities VALUES(?,?,?,?,?,?,?)",
                        (row["entity_id"], model_id, row["canonical_name"], row["entity_type"],
                         json.dumps(row["mentions"]), json.dumps(row["properties"]), now),
                    )
                for row in events:
                    connection.execute(
                        "INSERT INTO native_discourse_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (row["event_id"], model_id, row["sentence_index"], row["subject"],
                         row["action"], row["object"], row["time"], row["location"],
                         int(row["negated"]), row["cause_event_id"], row["evidence_text"],
                         json.dumps(row["parse"], sort_keys=True), now),
                    )
                connection.execute(
                    """INSERT INTO native_dialogue_sessions(
                       session_id,active_model_id,focus_entity,focus_event_id,turn_count,state_json,updated_epoch)
                       VALUES(?,?,?,?,0,?,?) ON CONFLICT(session_id) DO UPDATE SET
                       active_model_id=excluded.active_model_id,state_json=excluded.state_json,
                       updated_epoch=excluded.updated_epoch""",
                    (session_id, model_id, "", last_event_id,
                     json.dumps({"source_id": source_id, "source_family": source_family}), now),
                )
        return model

    def _active_model(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT m.model_json FROM native_dialogue_sessions s
                   JOIN native_discourse_models m ON m.model_id=s.active_model_id
                   WHERE s.session_id=?""", (session_id,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _intent(question: str) -> str:
        lowered = _normal(question)
        if "refer to" in lowered or "reference" in lowered: return "coreference"
        if re.search(r"\b(?:who|whom)\b", lowered): return "entity"
        if lowered.startswith("why") or "what caused" in lowered: return "cause"
        # A temporal question can itself contain words such as "next" or
        # "after".  Recognise its requested answer type before interpreting
        # those words as a request for the next event in the passage.
        if lowered.startswith("when") or re.search(r"\b(?:what|which)\s+(?:day|time|date|year|month)\b", lowered): return "time"
        if "first" in lowered or "before" in lowered: return "sequence_first"
        if "next" in lowered or "after" in lowered: return "sequence_next"
        if lowered.startswith("where"): return "location"
        if "negat" in lowered or "deny" in lowered: return "negation"
        if "object" in lowered or "affected" in lowered or "receive" in lowered: return "object"
        if "contradict" in lowered or "inconsistent" in lowered: return "contradiction"
        if "summar" in lowered or "what happened" in lowered: return "summary"
        if lowered.startswith("what did") or lowered.startswith("what action"): return "action"
        return "unknown"

    @staticmethod
    def _event_match(events: Sequence[Mapping[str, Any]], question: str) -> dict[str, Any] | None:
        terms = set(WORD_RE.findall(question.lower())) - {
            "who", "what", "where", "when", "why", "did", "does", "was", "were",
            "happen", "happened", "the", "a", "an", "first", "next", "after", "before",
        }
        scored = []
        for row in events:
            surface = " ".join(str(row.get(key) or "") for key in
                               ("subject", "action", "action_surface", "object", "location", "time"))
            score = len(terms & set(WORD_RE.findall(surface.lower())))
            scored.append((score, not bool(row.get("subordinate")),
                           int(row.get("sentence_index") or 0), dict(row)))
        return max(scored, key=lambda item: (item[0], item[1], -item[2]))[3] if scored else None

    def _plan(self, model: Mapping[str, Any], question: str,
              preferred_event_id: str = "", forced_intent: str = "") -> dict[str, Any]:
        intent = forced_intent or self._intent(question)
        all_events = [dict(row) for row in model.get("events") or []]
        events = list(all_events)
        relations = [dict(row) for row in model.get("relations") or []]
        sentence_match = re.search(r"\bsentence\s+(\d+)\b", question, re.I)
        requested_sentence = int(sentence_match.group(1)) - 1 if sentence_match else None
        if requested_sentence is not None:
            sentence_events = [row for row in events
                               if int(row.get("sentence_index")
                                      if row.get("sentence_index") is not None else -1)
                               == requested_sentence]
            if sentence_events:
                events = sentence_events
        selected = self._event_match(events, question)
        if intent == "time" and (not selected or not selected.get("time")):
            # A question such as "On what day will he arrive?" may share more
            # surface words with reported speech than with the event carrying
            # the explicit date.  Time answers must come from an explicit time
            # proposition, never from a generic tense label.
            timed = [row for row in events if str(row.get("time") or "").strip()]
            if timed:
                selected = self._event_match(timed, question) or timed[0]
        content_terms = set(WORD_RE.findall(question.lower())) - set(PRONOUNS) - {
            "who", "what", "where", "when", "why", "did", "does", "do", "was",
            "were", "is", "are", "happen", "happened", "refer", "to", "that",
        }
        if preferred_event_id and not content_terms:
            selected = next((row for row in events
                             if row.get("event_id") == preferred_event_id), selected)
        propositions: list[str] = []
        evidence: list[dict[str, Any]] = []
        answer = ""
        focus_entity = ""
        focus_event = ""
        if intent == "entity" and selected and selected.get("subject"):
            answer, focus_entity = str(selected["subject"]), str(selected["subject"])
        elif intent == "action" and selected and selected.get("action"):
            answer = str(selected.get("action_surface") or selected["action"])
        elif intent == "location" and selected and selected.get("location"):
            answer = str(selected["location"])
        elif intent == "time" and selected and selected.get("time"):
            answer = str(selected["time"])
        elif intent == "object" and selected and selected.get("object"):
            answer = str(selected["object"])
        elif intent == "negation" and selected:
            answer = "yes" if selected.get("negated") else "no"
        elif intent in {"sequence_first", "sequence_next"} and events:
            # Use the same grounded, main-clause events that the sealed contract
            # compiler uses.  Previously the answer planner also counted
            # subordinate/cause fragments, so "next" could refer to a different
            # event from the independently compiled answer key.
            ordered = sorted(
                [row for row in events if self._sequence_event_safe(row)],
                key=lambda row: int(row.get("sentence_index") or 0),
            )
            # A sequence requires separate passage events. Multiple parser
            # frames extracted from one sentence do not establish "next".
            ordered = list({int(row.get("sentence_index") or 0): row
                            for row in reversed(ordered)}.values())
            ordered.sort(key=lambda row: int(row.get("sentence_index") or 0))
            needed = 1 if requested_sentence is not None else (1 if intent == "sequence_first" else 2)
            if len(ordered) >= needed:
                selected = ordered[0 if requested_sentence is not None or intent == "sequence_first" else 1]
                answer = " ".join(str(selected.get(key) or "") for key in
                                  ("subject", "action_surface", "object")).strip()
        elif intent == "cause" and selected:
            cause_id = str(selected.get("cause_event_id") or "")
            cause = next((row for row in all_events if row.get("event_id") == cause_id), None)
            if not cause:
                relation = next((row for row in relations
                                 if row.get("type") == "cause" and row.get("to_event") == selected.get("event_id")), None)
                cause = next((row for row in all_events if relation and
                              row.get("event_id") == relation.get("from_event")), None)
            if cause:
                answer = f"Because {cause.get('subject') or 'the subject'} {cause.get('action_surface') or cause.get('action') or 'acted'} {cause.get('object') or ''}".strip()
                selected = cause
        elif intent == "coreference":
            qtokens = set(WORD_RE.findall(question.lower()))
            relation = next((row for row in reversed(relations)
                             if row.get("type") == "coreference" and
                             (requested_sentence is None or
                              int(row.get("sentence_index")
                                  if row.get("sentence_index") is not None else -1)
                              == requested_sentence) and
                             (not (qtokens & set(PRONOUNS)) or
                              str(row.get("surface") or "").lower() in qtokens)), None)
            if relation:
                answer, focus_entity = str(relation["target"]), str(relation["target"])
        elif intent == "contradiction":
            conflict = None
            for left in events:
                for right in events:
                    if left["event_id"] == right["event_id"]: continue
                    same = (_normal(str(left.get("subject"))) == _normal(str(right.get("subject")))
                            and _normal(str(left.get("action"))) == _normal(str(right.get("action")))
                            and _normal(str(left.get("object"))) == _normal(str(right.get("object"))))
                    if same and bool(left.get("negated")) != bool(right.get("negated")):
                        conflict = (left, right); break
                if conflict: break
            answer = ("Yes. One statement affirms the event while another denies it"
                      if conflict else "I found no direct contradiction in the represented events")
            selected = conflict[0] if conflict else selected
        elif intent == "summary" and events:
            clauses = [f"{row.get('subject') or 'Someone'} {'did not ' if row.get('negated') else ''}{row.get('action_surface') or row.get('action') or 'act'} {row.get('object') or ''}".strip()
                       for row in events if not row.get("subordinate")][:3]
            answer = "; then ".join(clauses)
            selected = events[-1]
        if answer and selected:
            focus_event = str(selected.get("event_id") or "")
            propositions.append(answer)
            evidence.append({"kind": "discourse_event", "id": focus_event,
                             "source_id": model.get("source_id"),
                             "sentence_index": selected.get("sentence_index"),
                             "text": selected.get("evidence_text")})
        status = "answered" if answer else "clarification_required"
        if not answer:
            answer = "I cannot support an answer from the current situation model. Please clarify the event or entity you mean"
        confidence = min(.96, .55 + .10 * len(evidence) + .05 * len(propositions)) if evidence else 0.0
        return {"intent": intent, "answer": _sentence(answer), "status": status,
                "confidence": confidence, "propositions": propositions,
                "evidence": evidence, "focus_entity": focus_entity,
                "focus_event_id": focus_event,
                "reasoning_steps": ["identify_intent", "select_situation_evidence",
                                    "derive_supported_proposition", "realise_grammar",
                                    "verify_support"]}

    def ask(self, question: str, *, session_id: str = "default", passage: str = "",
            source_id: str = "owner_dialogue", source_family: str = "owner") -> dict[str, Any]:
        model = (self.build_situation_model(passage, session_id=session_id,
                                            source_id=source_id, source_family=source_family)
                 if passage.strip() else self._active_model(session_id))
        with self._connect() as connection:
            session = connection.execute(
                "SELECT focus_event_id FROM native_dialogue_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
        preferred_event_id = str(session[0]) if session else ""
        if not model:
            plan = {"intent": self._intent(question),
                    "answer": "I do not yet have a passage or situation to reason about. Please provide the relevant information",
                    "status": "clarification_required", "confidence": 0.0,
                    "propositions": [], "evidence": [], "focus_entity": "",
                    "focus_event_id": "", "reasoning_steps": ["request_missing_context"]}
            model_id = ""
        else:
            plan = self._plan(model, question, preferred_event_id=preferred_event_id)
            model_id = str(model["model_id"])
        checks = {"evidence_supported": bool(plan["evidence"]),
                  "contradiction_checked": True,
                  "ambiguity_detected": plan["status"] != "answered",
                  "unsupported_claims": not bool(plan["evidence"]),
                  "model_or_cloud_route_present": False}
        now = time.time()
        turn_id = _identifier("native_dialogue_turn_", [session_id, question, now])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_dialogue_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (turn_id, session_id, model_id, question, plan["intent"], plan["answer"],
                 plan["status"], plan["confidence"], json.dumps(plan, sort_keys=True),
                 json.dumps(plan["evidence"], sort_keys=True), json.dumps(checks, sort_keys=True),
                 0, now),
            )
            connection.execute(
                """INSERT INTO native_dialogue_sessions(
                   session_id,active_model_id,focus_entity,focus_event_id,turn_count,state_json,updated_epoch)
                   VALUES(?,?,?,?,1,'{}',?) ON CONFLICT(session_id) DO UPDATE SET
                   focus_entity=CASE WHEN excluded.focus_entity!='' THEN excluded.focus_entity ELSE focus_entity END,
                   focus_event_id=CASE WHEN excluded.focus_event_id!='' THEN excluded.focus_event_id ELSE focus_event_id END,
                   turn_count=turn_count+1,updated_epoch=excluded.updated_epoch""",
                (session_id, model_id, plan["focus_entity"], plan["focus_event_id"], now),
            )
        return {"schema_version": "aion.native_discourse_dialogue.v1",
                "turn_id": turn_id, "session_id": session_id, "model_id": model_id,
                "question": question, **plan, "checks": checks,
                "generation": {"method": "situation_model_response_plan_rule_grammar",
                               "qwen_used": False, "model_used": False,
                               "cloud_used": False, "next_token_prediction": False}}

    def correct(self, *, turn_id: str, verified_answer: str, explanation: str,
                source_ref: str = "owner_verified") -> dict[str, Any]:
        with self._connect() as connection:
            turn = connection.execute(
                "SELECT * FROM native_dialogue_turns WHERE turn_id=?", (turn_id,),
            ).fetchone()
        if not turn:
            return {"stored": False, "reason": "turn_not_found"}
        if not verified_answer.strip() or not explanation.strip():
            return {"stored": False, "reason": "verified_answer_and_explanation_required"}
        now = time.time()
        correction_id = _identifier("native_dialogue_correction_", [turn_id, verified_answer, now])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_dialogue_corrections VALUES(?,?,?,?,?,'due',?,'correction',0,?,NULL)",
                (correction_id, turn_id, verified_answer.strip(), explanation.strip(),
                 source_ref.strip(), now + 900.0, now),
            )
        return {"stored": True, "correction_id": correction_id,
                "verified_answer": verified_answer.strip(), "due_epoch": now + 900.0,
                "model_used": False}

    def _exam_candidates(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT s.source_id,s.title,s.subject,r.sentence_index,r.text,r.parse_json
                   FROM native_reading_sentences r JOIN native_reading_sources s USING(source_id)
                   WHERE r.status IN ('completed','exposure_only') AND r.text!=''
                     AND NOT EXISTS(
                       SELECT 1 FROM native_discourse_exams e
                       WHERE e.source_id=r.source_id AND e.passage_signature=
                             lower(hex(sha3(r.text,256)))
                     )
                   ORDER BY r.processed_epoch DESC LIMIT ?""",
                (max(8, int(limit) * 4),),
            ).fetchall()
        return [dict(row) for row in rows]

    def _reading_passages(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """WITH ranked AS (
                     SELECT s.source_id,s.title,s.subject,r.sentence_index,r.text,
                            ROW_NUMBER() OVER(
                              PARTITION BY s.source_id ORDER BY r.processed_epoch DESC
                            ) source_rank
                     FROM native_reading_sentences r
                     JOIN native_reading_sources s USING(source_id)
                     WHERE r.text!='' AND r.status IN ('completed','exposure_only')
                       AND lower(s.title) NOT LIKE '%dictionary%'
                       AND lower(s.title) NOT LIKE '%thesaurus%'
                       AND lower(s.title) NOT LIKE '%lexicon%'
                       AND lower(s.title) NOT LIKE '%glossary%'
                   )
                   SELECT source_id,title,subject,sentence_index,text
                   FROM ranked WHERE source_rank<=600
                   ORDER BY source_id,sentence_index""",
            ).fetchall()
        by_source: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_source.setdefault(str(row["source_id"]), []).append(dict(row))
        by_source_passages: dict[str, list[dict[str, Any]]] = {}
        for source_rows in by_source.values():
            source_rows.sort(key=lambda row: int(row["sentence_index"]))
            for offset in range(0, max(0, len(source_rows) - 2), 3):
                group = source_rows[offset:offset + 3]
                if len(group) < 3 or any(
                    int(group[i + 1]["sentence_index"]) != int(group[i]["sentence_index"]) + 1
                    for i in range(2)
                ):
                    continue
                passage = " ".join(str(row["text"]) for row in group)
                if len(passage) < 120 or not self._passage_is_prose(passage):
                    continue
                bucket = by_source_passages.setdefault(str(group[0]["source_id"]), [])
                if len(bucket) < 8:
                    bucket.append({"source_id": group[0]["source_id"],
                                   "title": group[0]["title"],
                                   "source_family": group[0]["subject"],
                                   "passage": passage})
        passages: list[dict[str, Any]] = []
        while by_source_passages and len(passages) < limit:
            for source_id in list(by_source_passages):
                row = by_source_passages[source_id].pop(0)
                row["source_key"] = f"source-{len(passages) + 1}"
                passages.append(row)
                if not by_source_passages[source_id]:
                    del by_source_passages[source_id]
        return passages

    def _contract_candidates(
        self, passages: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """Compile answer-role contracts before Qwen supplies surface wording."""
        contracts: list[dict[str, Any]] = []
        for source in passages:
            if not self._passage_is_prose(str(source.get("passage") or "")):
                continue
            model = self.build_situation_model(
                str(source["passage"]), session_id="discourse-contract-builder",
                source_id=str(source["source_id"]),
                source_family=str(source["source_family"]), persist=False,
            )
            events = [dict(row) for row in model.get("events") or []
                      if not row.get("subordinate")]
            relations = [dict(row) for row in model.get("relations") or []]
            variants: list[tuple[str, str, str, str]] = []
            safe_sequence_events: list[dict[str, Any]] = []
            for event in events:
                subject = str(event.get("subject") or "").strip()
                action = str(event.get("action_surface") or event.get("action") or "").strip()
                object_value = str(event.get("object") or "").strip()
                safe_object = object_value if self._object_answer_safe(object_value) else ""
                anchor = safe_object or (
                    f"{subject} {action}" if subject and action else action
                ) or "the described event"
                subject_is_grounded_entity = self._grounded_named_entity(subject)
                if self._sequence_event_safe(event):
                    safe_sequence_events.append(event)
                # A capitalised fragment is not enough to establish an agent.
                # Literary dialogue often begins with interjections such as
                # "O" or "'Tis"; require an independently parsed action.
                if subject_is_grounded_entity and action:
                    variants.append((
                        "entity", f"Who performed the event involving {anchor}?", subject,
                        "The passage names the agent of the selected event.",
                    ))
                matching_event_count = sum(
                    _normal(str(row.get("subject") or "")) == _normal(subject)
                    and _normal(str(row.get("action") or row.get("action_surface") or ""))
                    == _normal(str(event.get("action") or event.get("action_surface") or ""))
                    for row in events
                )
                if (object_value and subject_is_grounded_entity and action
                        and matching_event_count == 1
                        and self._object_answer_safe(object_value)):
                    if self._exam_contract_valid(
                        str(source["passage"]), "object", object_value,
                    ):
                        variants.append((
                            "object", f"What complete object did {subject} {event.get('action') or action}?",
                            object_value, "The passage identifies the complete affected object.",
                        ))
                if action and subject_is_grounded_entity:
                    variants.append((
                        "action", f"What action did {subject or 'the agent'} perform?",
                        action, "The passage explicitly states the event action.",
                    ))
                if event.get("location") and self._location_answer_safe(str(event["location"])):
                    variants.append((
                        "location", f"Where did the event involving {anchor} occur?",
                        str(event["location"]), "The event carries an explicit location.",
                    ))
                if event.get("time"):
                    variants.append((
                        "time", f"When did the event involving {anchor} occur?",
                        str(event["time"]), "The event carries an explicit time expression.",
                    ))
                cause_id = str(event.get("cause_event_id") or "")
                cause = next((row for row in model.get("events") or []
                              if row.get("event_id") == cause_id), None)
                if (cause and str(cause.get("action") or "").strip()
                        and (self._grounded_named_entity(str(cause.get("subject") or ""))
                             or self._object_answer_safe(str(cause.get("subject") or "")))):
                    expected = " ".join(str(cause.get(key) or "") for key in
                                        ("subject", "action_surface", "object")).strip()
                    if expected:
                        variants.append((
                            "cause", f"Why did the event involving {anchor} happen?", expected,
                            "The linked subordinate event supplies the stated cause.",
                        ))
            for relation in relations:
                if relation.get("type") == "coreference" and relation.get("target"):
                    surface = str(relation.get("surface") or "the pronoun")
                    target = str(relation["target"])
                    sentence_number = int(relation.get("sentence_index") or 0) + 1
                    if self._exam_contract_valid(
                        str(source["passage"]), "coreference", target,
                    ):
                        variants.append((
                            "coreference",
                            f"In sentence {sentence_number}, who or what does '{surface}' refer to?",
                            target, "The reference resolves to an earlier entity.",
                        ))
            ordered_events = sorted(
                safe_sequence_events,
                key=lambda row: int(row.get("sentence_index") or 0),
            )
            ordered_events = list({int(row.get("sentence_index") or 0): row
                                   for row in reversed(ordered_events)}.values())
            ordered_events.sort(key=lambda row: int(row.get("sentence_index") or 0))
            if len(ordered_events) >= 2:
                for family, question, event in (
                    ("sequence_first", "According to passage order, what happened first?",
                     ordered_events[0]),
                    ("sequence_next",
                     "According to passage order, what happened immediately after the first event?",
                     ordered_events[1]),
                ):
                    expected = " ".join(str(event.get(key) or "") for key in
                                        ("subject", "action_surface", "object")).strip()
                    if expected:
                        variants.append((
                            family, question, expected,
                            "The passage order identifies this event's place in the sequence.",
                        ))
            seen: set[tuple[str, str]] = set()
            for family, question, expected, reason in variants:
                if not self._exam_contract_valid(
                    str(source["passage"]), family, expected,
                ):
                    continue
                key = (family, _normal(expected))
                # A book/source contains many independent passages. Exhaustion
                # must therefore be tracked by passage/question (enforced by
                # native_discourse_exam_unique), not by source/family. The old
                # source-wide gate allowed only one entity, time, or sequence
                # exam per entire book and reduced a live service to zero work.
                if key in seen:
                    continue
                seen.add(key)
                contract_key = _identifier(
                    "contract-", [source["source_key"], family, question, expected],
                )
                contracts.append({
                    "contract_key": contract_key, "source_key": source["source_key"],
                    "family": family, "question": question,
                    "expected_answer": expected, "answer_reason": reason,
                })
        return contracts

    @staticmethod
    def _teacher_prompt(passages: Sequence[Mapping[str, Any]],
                        contracts: Sequence[Mapping[str, Any]], requested: int) -> str:
        material = [{"source_key": row["source_key"], "passage": row["passage"]}
                    for row in passages]
        return f"""You are preparing {requested} SEALED English discourse examinations.
The parser has already compiled safe answer-role contracts. Select varied contracts
and optionally rephrase only their question. Return strict JSON:
{{"challenges":[{{"contract_key":"...","question":"...","answer_reason":"..."}}]}}.
Do not change the answer role, invent facts, include the answer in the question, or
reuse a source within this batch. Prefer coreference, cause, time and connected
meaning. No markdown.
Sources:\n{json.dumps(material, ensure_ascii=False)}
Contracts:\n{json.dumps(list(contracts), ensure_ascii=False)}"""

    @staticmethod
    def _meaning_match(answer: str, expected: str) -> bool:
        actual = _normal(answer.rstrip("."))
        target = _normal(expected.rstrip("."))
        if actual == target:
            return True
        ignored = {"a", "an", "the"}
        actual_terms = set(WORD_RE.findall(actual)) - ignored
        target_terms = set(WORD_RE.findall(target)) - ignored
        if not target_terms:
            return False
        return len(actual_terms & target_terms) / len(target_terms) >= .80

    def _run_due_retests(self, limit: int) -> list[dict[str, Any]]:
        now = time.time()
        with self._connect() as connection:
            correction_rows = connection.execute(
                """SELECT c.*,t.question,t.session_id,t.model_id,m.model_json
                   FROM native_dialogue_corrections c
                   JOIN native_dialogue_turns t ON t.turn_id=c.turn_id
                   LEFT JOIN native_discourse_models m ON m.model_id=t.model_id
                   WHERE c.status='due' AND c.due_epoch<=?
                   ORDER BY c.due_epoch LIMIT ?""", (now, limit),
            ).fetchall()
            exam_rows = connection.execute(
                """SELECT * FROM native_discourse_exams
                   WHERE correct=1 AND validity_status='valid'
                     AND due_epoch IS NOT NULL AND due_epoch<=?
                   ORDER BY due_epoch LIMIT ?""", (now, limit),
            ).fetchall()
            remedial_rows = connection.execute(
                """SELECT r.*,e.* FROM native_discourse_exam_remediation r
                   JOIN native_discourse_exams e ON e.exam_id=r.exam_id
                   WHERE r.status='due' AND e.validity_status='valid' AND r.due_epoch<=?
                   ORDER BY r.due_epoch LIMIT ?""", (now, limit),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for raw in correction_rows:
            row = dict(raw)
            model = json.loads(str(row.get("model_json") or "{}"))
            answer = self._plan(model, str(row["question"])) if model else {
                "answer": "", "confidence": 0, "evidence": []}
            correct = self._meaning_match(str(answer["answer"]), str(row["verified_answer"]))
            with self._connect() as connection:
                if correct:
                    connection.execute(
                        "UPDATE native_dialogue_corrections SET status='cleared',cleared_epoch=? WHERE correction_id=?",
                        (now, row["correction_id"]),
                    )
                else:
                    retry = int(row.get("retry_count") or 0) + 1
                    connection.execute(
                        "UPDATE native_dialogue_corrections SET retry_count=?,due_epoch=? WHERE correction_id=?",
                        (retry, now + min(86400.0, 900.0 * (2 ** min(6, retry))),
                         row["correction_id"]),
                    )
            results.append({"kind": "verified_correction", "correct": correct,
                            "stage": "closed_book_retry"})
        for raw in exam_rows:
            row = dict(raw)
            current = str(row["retention_stage"])
            next_stage = {"immediate": "retention_1d", "retention_1d": "retention_7d",
                          "retention_7d": "retention_30d"}.get(current)
            if not next_stage or not str(row.get("passage") or ""):
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE native_discourse_exams SET due_epoch=NULL WHERE exam_id=?",
                        (row["exam_id"],),
                    )
                continue
            model = self.build_situation_model(
                str(row["passage"]), session_id="discourse-retention",
                source_id=str(row["source_id"]), source_family=str(row["source_family"]),
                persist=False,
            )
            answer = self._plan(model, str(row["question"]))
            correct = self._meaning_match(str(answer["answer"]), str(row["expected_answer"]))
            due = (now + RETENTION_DELAYS.get(
                {"retention_1d": "retention_7d", "retention_7d": "retention_30d"}.get(next_stage, ""),
                0.0,
            )) if correct and next_stage != "retention_30d" else None
            retest_id = _identifier("native_discourse_exam_", [row["exam_id"], next_stage, time.time_ns()])
            with self._connect() as connection:
                connection.execute("UPDATE native_discourse_exams SET due_epoch=NULL WHERE exam_id=?",
                                   (row["exam_id"],))
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO native_discourse_exams(
                       exam_id,source_id,source_family,passage_signature,family,question,
                       expected_answer,answer,correct,confidence,evidence_json,answer_sealed,
                       source_disjoint,retention_stage,due_epoch,model_used,created_epoch,
                       passage,answer_reason,teacher_model)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (retest_id, row["source_id"], row["source_family"], row["passage_signature"],
                     row["family"], row["question"], row["expected_answer"], answer["answer"],
                     int(correct), answer["confidence"], json.dumps(answer["evidence"]), 1,
                     row["source_disjoint"], next_stage, due, 0, now, row["passage"],
                     row["answer_reason"], row["teacher_model"]),
                )
            if cursor.rowcount:
                results.append({"kind": "delayed_retention", "correct": correct,
                                "stage": next_stage})
        for raw in remedial_rows:
            row = dict(raw)
            model = self.build_situation_model(
                str(row["passage"]), session_id="discourse-remediation",
                source_id=str(row["source_id"]), source_family=str(row["source_family"]),
                persist=False,
            )
            answer = self._plan(model, str(row["question"]))
            correct = self._meaning_match(str(answer["answer"]), str(row["expected_answer"]))
            with self._connect() as connection:
                if correct:
                    connection.execute(
                        "UPDATE native_discourse_exam_remediation SET status='cleared',cleared_epoch=? WHERE obligation_id=?",
                        (now, row["obligation_id"]),
                    )
                else:
                    retry = int(row.get("retry_count") or 0) + 1
                    connection.execute(
                        "UPDATE native_discourse_exam_remediation SET retry_count=?,due_epoch=? WHERE obligation_id=?",
                        (retry, now + min(86400.0, 900.0 * (2 ** min(6, retry))),
                         row["obligation_id"]),
                    )
            results.append({"kind": "exam_remediation", "correct": correct,
                            "stage": "closed_book_retry"})
        return results

    def run_cycle(self, *, teacher_client: Callable[[str], Mapping[str, Any]] | None = None,
                  limit: int = 4) -> dict[str, Any]:
        """Run Qwen-authored, sealed exams; Qwen is absent from the answer path."""
        requested = max(1, min(12, int(limit)))
        retests = self._run_due_retests(requested)
        passages = self._reading_passages(requested * 4)
        if not passages:
            return {"status": "awaiting_sealed_teacher_contracts", "attempted": 0,
                    "available_passages": len(passages), "retests": retests,
                    "model_used": False,
                    "qwen_used_for_student_answers": False}
        contracts = self._contract_candidates(passages)
        if not contracts:
            return {"status": "awaiting_new_source_role_contracts", "attempted": 0,
                    "available_passages": len(passages), "retests": retests,
                    "model_used": False, "qwen_used_for_student_answers": False}
        teacher_model, drafts = "compiled-native-contracts", []
        if teacher_client is not None:
            try:
                response = dict(teacher_client(self._teacher_prompt(
                    passages[:requested * 2], contracts, requested,
                )))
                teacher_model = str(response.get("model") or "local-qwen")
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "",
                              str(response.get("content") or "").strip(), flags=re.I | re.S)
                drafts = list(json.loads(text).get("challenges") or [])
            except Exception:
                drafts = []
        sources = {str(row["source_key"]): row for row in passages}
        contracts_by_key = {str(row["contract_key"]): dict(row) for row in contracts}
        allowed = {"entity", "action", "object", "location", "time", "cause",
                   "coreference", "sequence_first", "sequence_next", "contradiction"}
        selected_contracts: list[dict[str, Any]] = []
        used_sources: set[str] = set()
        for draft in drafts:
            if not isinstance(draft, Mapping):
                continue
            contract = contracts_by_key.get(str(draft.get("contract_key") or ""))
            # Backwards-compatible validation for older teacher clients: their
            # proposed answer must match one of the compiled contracts exactly.
            if contract is None:
                contract = next((dict(row) for row in contracts
                                 if str(row["source_key"]) == str(draft.get("source_key") or "")
                                 and str(row["family"]) == str(draft.get("family") or "")
                                 and self._meaning_match(
                                     str(draft.get("expected_answer") or ""),
                                     str(row["expected_answer"]),
                                 )), None)
            if contract is None or str(contract["source_key"]) in used_sources:
                continue
            question = " ".join(str(draft.get("question") or contract["question"]).split())
            if not question or _normal(str(contract["expected_answer"])) in _normal(question):
                question = str(contract["question"])
            contract["question"] = question
            contract["answer_reason"] = " ".join(str(
                draft.get("answer_reason") or contract["answer_reason"]
            ).split())
            contract["teacher_selected"] = True
            selected_contracts.append(contract)
            used_sources.add(str(contract["source_key"]))
            if len(selected_contracts) >= requested:
                break
        # Invalid Qwen drafts no longer starve Aion. The precompiled contracts
        # are already sealed, source-backed and role-safe, so unused slots are
        # filled from them while Qwen remains absent from the student path.
        with self._connect() as connection:
            historical_family_counts = {
                str(row["family"]): int(row["count"])
                for row in connection.execute(
                    """SELECT family,COUNT(*) count FROM native_discourse_exams
                       WHERE validity_status='valid' GROUP BY family"""
                ).fetchall()
            }
        family_priority = {
            "sequence_first": 0, "sequence_next": 1, "time": 2,
            "coreference": 3, "cause": 4, "contradiction": 5,
            "location": 6, "object": 7, "action": 8, "entity": 9,
        }
        by_family: dict[str, list[dict[str, Any]]] = {}
        for contract in contracts:
            by_family.setdefault(str(contract["family"]), []).append(contract)
        family_order = sorted(
            by_family,
            key=lambda family: (
                historical_family_counts.get(family, 0),
                family_priority.get(family, 99),
            ),
        )
        # Interleave families before repeating one. This keeps every batch
        # focused on connected meaning (sequence, time, cause, reference) and
        # prevents four easy entity questions from masquerading as breadth.
        ordered_contracts: list[dict[str, Any]] = []
        while any(by_family.values()):
            for family in family_order:
                if by_family[family]:
                    ordered_contracts.append(by_family[family].pop(0))
        for contract in ordered_contracts:
            if str(contract["source_key"]) in used_sources:
                continue
            selected_contracts.append({**dict(contract), "teacher_selected": False})
            used_sources.add(str(contract["source_key"]))
        results: list[dict[str, Any]] = []
        teacher_selected = sum(bool(row.get("teacher_selected")) for row in selected_contracts)
        rejected = max(0, len(drafts) - teacher_selected)
        compiled_attempted = 0
        for draft in selected_contracts:
            if len(results) >= requested:
                break
            source = sources.get(str(draft.get("source_key") or ""))
            family = str(draft.get("family") or "")
            question = " ".join(str(draft.get("question") or "").split())
            expected = " ".join(str(draft.get("expected_answer") or "").split())
            reason = " ".join(str(draft.get("answer_reason") or "").split())
            if (not source or family not in allowed or not question or not expected or not reason
                    or len(expected) < 2 or _normal(expected) in _normal(question)):
                rejected += 1
                continue
            signature = hashlib.sha256(
                f"{_normal(source['passage'])}|{_normal(question)}".encode()
            ).hexdigest()
            with self._connect() as connection:
                if connection.execute(
                    "SELECT 1 FROM native_discourse_exams WHERE passage_signature=? AND family=? AND validity_status='valid'",
                    (signature, family),
                ).fetchone():
                    rejected += 1
                    continue
                prior_sources = {str(row[0]) for row in connection.execute(
                    "SELECT DISTINCT source_id FROM native_discourse_exams WHERE family=? AND validity_status='valid'",
                    (family,),
                ).fetchall()}
            model = self.build_situation_model(
                str(source["passage"]), session_id="discourse-exam",
                source_id=str(source["source_id"]), source_family=str(source["source_family"]),
                persist=False,
            )
            if not bool(draft.get("teacher_selected")):
                compiled_attempted += 1
            # Student inference completes before the sealed key is compared.
            answer = self._plan(model, question, forced_intent=family)
            correct = self._meaning_match(str(answer["answer"]), expected)
            source_disjoint = bool(prior_sources and source["source_id"] not in prior_sources)
            exam_id = _identifier("native_discourse_exam_", [signature, family, time.time_ns()])
            now = time.time()
            with self._connect() as connection:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO native_discourse_exams(
                       exam_id,source_id,source_family,passage_signature,family,question,
                       expected_answer,answer,correct,confidence,evidence_json,answer_sealed,
                       source_disjoint,retention_stage,due_epoch,model_used,created_epoch,
                       passage,answer_reason,teacher_model)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (exam_id, source["source_id"], source["source_family"], signature, family,
                     question, expected, answer["answer"], int(correct), answer["confidence"],
                     json.dumps(answer["evidence"]), 1, int(source_disjoint), "immediate",
                     now + RETENTION_DELAYS["retention_1d"] if correct else None, 0, now,
                     source["passage"], reason, teacher_model),
                )
                if cursor.rowcount and not correct:
                    obligation_id = _identifier(
                        "native_discourse_remediation_", [exam_id, expected, reason]
                    )
                    connection.execute(
                        "INSERT INTO native_discourse_exam_remediation VALUES(?,?,'due',?,0,?,NULL)",
                        (obligation_id, exam_id, now + 900.0, now),
                    )
            # Another worker may have committed this exact sealed examination
            # after our read-only novelty check.  That is normal concurrency,
            # not a failed learning cycle.
            if not cursor.rowcount:
                rejected += 1
                continue
            results.append({"family": family, "source": source["title"],
                            "correct": correct, "answer": answer["answer"],
                            "expected_withheld": True, "source_disjoint": source_disjoint,
                            "independent_answer_key": False,
                            "role_safe_compiled_key": True, "model_used": False})
        return {"status": "completed" if results else "teacher_contracts_rejected",
                "attempted": len(results), "correct": sum(row["correct"] for row in results),
                "rejected": rejected,
                "compiled_fallbacks": compiled_attempted,
                "results": results, "teacher_model": teacher_model,
                "retests": retests,
                "answer_keys_withheld": True, "qwen_used_for_student_answers": False,
                "model_used": False}

    def metrics(self) -> dict[str, Any]:
        with self._read_connect() as connection:
            totals = connection.execute(
                "SELECT COUNT(*),COALESCE(SUM(correct),0),COUNT(DISTINCT source_id),COALESCE(SUM(source_disjoint),0) FROM native_discourse_exams WHERE validity_status='valid'"
            ).fetchone()
            recent = connection.execute(
                "SELECT COUNT(*),COALESCE(SUM(correct),0) FROM native_discourse_exams WHERE validity_status='valid' AND created_epoch>?",
                (time.time() - 3600,),
            ).fetchone()
            families = connection.execute(
                "SELECT family,COUNT(*) attempts,SUM(correct) correct FROM native_discourse_exams WHERE validity_status='valid' GROUP BY family"
            ).fetchall()
            sessions = connection.execute("SELECT COUNT(*) FROM native_dialogue_sessions").fetchone()[0]
            turns = connection.execute("SELECT COUNT(*) FROM native_dialogue_turns").fetchone()[0]
            clarification = connection.execute(
                "SELECT COUNT(*) FROM native_dialogue_turns WHERE status='clarification_required'"
            ).fetchone()[0]
            corrections = connection.execute(
                "SELECT status,COUNT(*) count FROM native_dialogue_corrections GROUP BY status"
            ).fetchall()
            exam_remediation = connection.execute(
                "SELECT status,COUNT(*) count FROM native_discourse_exam_remediation GROUP BY status"
            ).fetchall()
            retention = connection.execute(
                "SELECT retention_stage,COUNT(*) attempts,SUM(correct) correct FROM native_discourse_exams WHERE validity_status='valid' GROUP BY retention_stage"
            ).fetchall()
            due_retests = int(connection.execute(
                "SELECT COUNT(*) FROM native_discourse_exams WHERE validity_status='valid' AND due_epoch IS NOT NULL AND due_epoch<=?",
                (time.time(),),
            ).fetchone()[0])
            models = connection.execute("SELECT COUNT(*) FROM native_discourse_models").fetchone()[0]
        attempts, correct = int(totals[0]), int(totals[1])
        return {"situation_models": int(models), "dialogue_sessions": int(sessions),
                "dialogue_turns": int(turns), "clarifications": int(clarification),
                "exams": attempts, "correct": correct,
                "accuracy": round(correct / attempts, 4) if attempts else None,
                "attempts_last_hour": int(recent[0]), "correct_last_hour": int(recent[1]),
                "recent_accuracy": round(int(recent[1]) / int(recent[0]), 4) if recent[0] else None,
                "source_families": int(totals[2]), "source_disjoint_attempts": int(totals[3]),
                "families": {str(row["family"]): {"attempts": int(row["attempts"]),
                    "correct": int(row["correct"] or 0),
                    "accuracy": round(int(row["correct"] or 0) / int(row["attempts"]), 4)}
                    for row in families},
                "retention": {str(row["retention_stage"]): {
                    "attempts": int(row["attempts"]), "correct": int(row["correct"] or 0)}
                    for row in retention}, "retention_due": due_retests,
                "corrections": {str(row["status"]): int(row["count"]) for row in corrections},
                "exam_remediation": {str(row["status"]): int(row["count"])
                                     for row in exam_remediation},
                "student_model_used": False, "counts_as_mastery": False,
                "claim_boundary": "Only source-labelled, sealed, model-free discourse exams are reported here; definition drills are excluded."}


__all__ = ["NativeDiscourseDialogueEngine"]
