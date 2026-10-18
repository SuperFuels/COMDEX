"""Persistent, model-free conversation runtime for AION.

The runtime composes the existing lexical and discourse engines into a durable
owner-facing conversation path.  It records mention identities, propositions,
topics, corrections and support receipts.  Qwen is intentionally absent from
``respond`` and ``correct``; a teacher may only prepare sealed academy material
outside this module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping, Sequence

from backend.modules.aion_cognition.native_discourse_dialogue import (
    NativeDiscourseDialogueEngine,
    PRONOUNS,
    WORD_RE,
    _normal,
    _sentences,
)
from backend.modules.aion_cognition.native_english_conversation import NativeEnglishConversation
from backend.modules.aion_cognition.sqlite_connection import (
    connect as sqlite_connect,
    connect_read_only as sqlite_read_connect,
)


REFERENCE_WORDS = set(PRONOUNS)
ORDINALS = {"first": 0, "second": 1, "third": 2, "fourth": 3, "last": -1}


def _identifier(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()[:24]


def _sentence(value: str) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return text
    text = text[0].upper() + text[1:]
    return text if text[-1:] in {".", "?", "!"} else text + "."


class NativeConversationRuntime:
    """Interpret, remember, reason and answer through native representations."""

    def __init__(self, *, repo_root: Path | str,
                 discourse: NativeDiscourseDialogueEngine | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.discourse = discourse or NativeDiscourseDialogueEngine(repo_root=self.repo_root)
        self.lexical = self.discourse.lexical
        self.database_path = self.discourse.database_path
        self.lexical_conversation = NativeEnglishConversation(
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
                CREATE TABLE IF NOT EXISTS native_conversation_sessions(
                    session_id TEXT PRIMARY KEY,
                    active_passage TEXT NOT NULL DEFAULT '',
                    active_model_json TEXT NOT NULL DEFAULT '{}',
                    current_topic TEXT NOT NULL DEFAULT '',
                    topic_stack_json TEXT NOT NULL DEFAULT '[]',
                    unresolved_json TEXT NOT NULL DEFAULT '[]',
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_conversation_mentions(
                    mention_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sentence_index INTEGER NOT NULL,
                    token_index INTEGER NOT NULL,
                    surface TEXT NOT NULL,
                    mention_type TEXT NOT NULL,
                    canonical_value TEXT NOT NULL DEFAULT '',
                    candidate_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0,
                    resolution_status TEXT NOT NULL,
                    evidence_text TEXT NOT NULL DEFAULT '',
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_conversation_mention_lookup
                    ON native_conversation_mentions(session_id,surface,sentence_index);
                CREATE TABLE IF NOT EXISTS native_conversation_propositions(
                    proposition_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    time_value TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    negated INTEGER NOT NULL DEFAULT 0,
                    source_id TEXT NOT NULL,
                    evidence_text TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    supersedes_id TEXT NOT NULL DEFAULT '',
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_conversation_proposition_lookup
                    ON native_conversation_propositions(session_id,status,subject,predicate);
                CREATE TABLE IF NOT EXISTS native_conversation_turns(
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    owner_utterance TEXT NOT NULL,
                    request_frame_json TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    proposition_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    support_map_json TEXT NOT NULL,
                    ambiguity_json TEXT NOT NULL,
                    state_change_json TEXT NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_conversation_turn_session
                    ON native_conversation_turns(session_id,turn_index);
                CREATE TABLE IF NOT EXISTS native_conversation_corrections(
                    correction_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    corrected_fact TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    proposition_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    due_epoch REAL NOT NULL,
                    retention_stage INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    cleared_epoch REAL
                );
                CREATE INDEX IF NOT EXISTS native_conversation_correction_due
                    ON native_conversation_corrections(status,due_epoch);
                """
            )

    def _session(self, session_id: str) -> dict[str, Any] | None:
        with self._read_connect() as connection:
            row = connection.execute(
                "SELECT * FROM native_conversation_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _speech_act(text: str) -> str:
        lowered = _normal(text)
        if re.match(r"^(?:actually|no|that is wrong|you are wrong|correction)\b", lowered):
            return "correction"
        if re.match(r"^(?:remember|note|store|keep in mind)\b", lowered):
            return "instruction"
        # Examination prompts may append a sentence anchor after the question
        # (for example, "What happened first? Use sentence 13.").  Looking
        # only at the final character misclassified these as assertions, which
        # caused Aion to store and repeat the question instead of answering it.
        if "?" in text or re.match(
            r"^(?:who|what|when|where|why|how|which|is|are|was|were|do|does|did|can|could|would|will)\b",
            lowered,
        ):
            return "question"
        return "assertion"

    def interpret(self, utterance: str) -> dict[str, Any]:
        text = " ".join(str(utterance or "").split())
        lexical_frame = self.lexical_conversation.parse(text)
        relation = self.discourse._intent(text)
        act = self._speech_act(text)
        lowered = _normal(text)
        if (re.search(r"\bwhat (?:information|evidence) (?:do|would)\b", lowered)
                or re.search(r"\bwhat (?:do|would) you need\b", lowered)
                or re.search(r"\bneed before (?:answering|saying|deciding)\b", lowered)):
            relation = "information_requirement"
        if relation == "unknown":
            if re.search(r"\b(?:evidence|support|source)\b", lowered):
                relation = "evidence"
            elif re.search(r"\b(?:difference|compare|similar)\b", lowered):
                relation = "comparison"
            elif re.search(r"\b(?:mean|define|meaning)\b", lowered):
                relation = "definition"
            elif re.search(r"\b(?:explain|tell me|know about)\b", lowered):
                relation = "summary"
            elif act in {"assertion", "correction", "instruction"}:
                relation = "state_update"
        assumptions = []
        if re.search(r"\b(?:still|again|as before|the other)\b", _normal(text)):
            assumptions.append("prior_discourse_referent_exists")
        missing = []
        if act == "question" and relation == "unknown":
            missing.append("requested_relation")
        return {
            "speech_act": act,
            "requested_relation": relation,
            "lexical_intent": lexical_frame.get("intent"),
            "arguments": lexical_frame.get("slots") or {},
            "entities": list((lexical_frame.get("frame") or {}).get("entities") or []),
            "time_scope": (lexical_frame.get("frame") or {}).get("time"),
            "negated": bool(lexical_frame.get("negated")),
            "presuppositions": assumptions,
            "missing_requirements": missing,
            "confidence": 0.35 if missing else 0.78,
            "model_used": False,
        }

    @staticmethod
    def _topic_from_text(text: str) -> str:
        match = re.search(
            r"\b(?:about|regarding|return(?:ing)? to|going back to)\s+(?:the\s+)?([A-Za-z][A-Za-z' -]{1,80})",
            text, re.I,
        )
        if not match:
            return ""
        return " ".join(match.group(1).strip(" .?!").split())

    def _persist_model(self, *, session_id: str, passage: str, model: Mapping[str, Any],
                       source_id: str, topic: str = "") -> dict[str, Any]:
        now = time.time()
        session = self._session(session_id)
        old_topic = str((session or {}).get("current_topic") or "")
        topic_stack = list(json.loads(str((session or {}).get("topic_stack_json") or "[]")))
        if topic and old_topic and _normal(topic) != _normal(old_topic):
            topic_stack.append(old_topic)
            topic_stack = topic_stack[-12:]
        active_topic = topic or old_topic
        serialisable = {
            **dict(model),
            "events": [
                {key: value for key, value in dict(row).items() if key != "parse"}
                for row in model.get("events") or []
            ],
        }
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_conversation_sessions(
                   session_id,active_passage,active_model_json,current_topic,topic_stack_json,
                   unresolved_json,turn_count,created_epoch,updated_epoch)
                   VALUES(?,?,?,?,?,'[]',0,?,?)
                   ON CONFLICT(session_id) DO UPDATE SET
                   active_passage=excluded.active_passage,
                   active_model_json=excluded.active_model_json,
                   current_topic=CASE WHEN excluded.current_topic!='' THEN excluded.current_topic ELSE current_topic END,
                   topic_stack_json=excluded.topic_stack_json,
                   updated_epoch=excluded.updated_epoch""",
                (session_id, passage, json.dumps(serialisable, sort_keys=True), active_topic,
                 json.dumps(topic_stack), now, now),
            )
            for event in model.get("events") or []:
                if event.get("subordinate"):
                    continue
                proposition_id = _identifier(
                    "native_conversation_proposition_",
                    [session_id, event.get("sentence_index"), event.get("subject"),
                     event.get("action"), event.get("object"), event.get("evidence_text")],
                )
                connection.execute(
                    """INSERT OR IGNORE INTO native_conversation_propositions VALUES(
                       ?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (proposition_id, session_id, str(event.get("subject") or ""),
                     str(event.get("action") or ""), str(event.get("object") or ""),
                     str(event.get("time") or ""), str(event.get("location") or ""),
                     int(bool(event.get("negated"))), source_id,
                     str(event.get("evidence_text") or ""),
                     float(event.get("confidence") or 0), "active", "", now),
                )
        self._persist_mentions(session_id=session_id, passage=passage, model=model)
        return serialisable

    def _persist_mentions(self, *, session_id: str, passage: str,
                          model: Mapping[str, Any]) -> None:
        relations = [dict(row) for row in model.get("relations") or []
                     if row.get("type") == "coreference"]
        entities = [dict(row) for row in model.get("entities") or []]
        sentences = _sentences(passage)
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM native_conversation_mentions WHERE session_id=?", (session_id,),
            )
            for sentence_index, text in enumerate(sentences):
                words = list(WORD_RE.finditer(text))
                for token_index, match in enumerate(words):
                    surface = match.group(0)
                    if surface.lower() not in REFERENCE_WORDS:
                        continue
                    matching = [row for row in relations
                                if int(row.get("sentence_index") or -1) == sentence_index
                                and str(row.get("surface") or "").lower() == surface.lower()]
                    candidates = []
                    for distance, entity in enumerate(reversed(entities)):
                        candidates.append({
                            "canonical_value": entity.get("canonical_name"),
                            "score": round(max(0.05, .82 - distance * .09), 3),
                            "entity_type": entity.get("entity_type"),
                        })
                    target = str(matching[-1].get("target") or "") if matching else ""
                    status = "resolved" if target else "unresolved"
                    confidence = .90 if target else 0.0
                    mention_id = _identifier(
                        "native_conversation_mention_",
                        [session_id, sentence_index, token_index, surface, text],
                    )
                    connection.execute(
                        "INSERT INTO native_conversation_mentions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (mention_id, session_id, sentence_index, token_index, surface,
                         "pronoun", target, json.dumps(candidates), confidence,
                         status, text, now),
                    )

    def ingest_context(self, *, session_id: str, text: str,
                       source_id: str = "owner-conversation",
                       source_family: str = "owner", append: bool = False) -> dict[str, Any]:
        clean = " ".join(str(text or "").split())
        session = self._session(session_id)
        if append and session and str(session.get("active_passage") or "").strip():
            clean = f"{session['active_passage']} {clean}".strip()
        model = self.discourse.build_situation_model(
            clean, session_id=f"native-conversation:{session_id}", source_id=source_id,
            source_family=source_family, persist=False,
        )
        topic = self._topic_from_text(text)
        persisted = self._persist_model(
            session_id=session_id, passage=clean, model=model, source_id=source_id, topic=topic,
        )
        return {"session_id": session_id, "model_id": persisted.get("model_id"),
                "entities": len(persisted.get("entities") or []),
                "events": len(persisted.get("events") or []),
                "mentions": self._mention_count(session_id), "model_used": False}

    def _mention_count(self, session_id: str) -> int:
        with self._read_connect() as connection:
            return int(connection.execute(
                "SELECT COUNT(*) FROM native_conversation_mentions WHERE session_id=?",
                (session_id,),
            ).fetchone()[0])

    def _reference_answer(self, session_id: str, question: str) -> dict[str, Any]:
        lowered = _normal(question)
        surface_match = re.search(r"['\"](he|she|it|they|them|him|her|this|that)['\"]", question, re.I)
        if not surface_match:
            surface_match = re.search(r"\b(he|she|it|they|them|him|her|this|that)\b", lowered)
        surface = surface_match.group(1).lower() if surface_match else ""
        sentence_match = re.search(r"\bsentence\s+(\d+)\b", lowered)
        ordinal = next((index for word, index in ORDINALS.items()
                        if re.search(rf"\b{word}\b", lowered)), None)
        with self._read_connect() as connection:
            rows = connection.execute(
                """SELECT * FROM native_conversation_mentions
                   WHERE session_id=? AND (?='' OR lower(surface)=?)
                   ORDER BY sentence_index,token_index""",
                (session_id, surface, surface),
            ).fetchall()
        mentions = [dict(row) for row in rows]
        if sentence_match:
            requested = int(sentence_match.group(1)) - 1
            mentions = [row for row in mentions if int(row["sentence_index"]) == requested]
        if ordinal is not None and mentions:
            try:
                mentions = [mentions[ordinal]]
            except IndexError:
                mentions = []
        resolved = [row for row in mentions if row["resolution_status"] == "resolved"
                    and str(row["canonical_value"])]
        distinct = list(dict.fromkeys(str(row["canonical_value"]) for row in resolved))
        if len(distinct) == 1:
            row = resolved[0]
            return {"answer": distinct[0], "status": "answered",
                    "confidence": float(row["confidence"]),
                    "evidence": [{"kind": "mention", "id": row["mention_id"],
                                  "text": row["evidence_text"],
                                  "sentence_index": row["sentence_index"]}],
                    "ambiguities": [], "propositions": [distinct[0]]}
        if len(distinct) > 1:
            return {"answer": (
                        f"There is more than one occurrence of '{surface or 'that reference'}'. "
                        "Please name the sentence or occurrence you mean"
                    ), "status": "clarification_required", "confidence": 0.0,
                    "evidence": [], "ambiguities": [{"kind": "multiple_references",
                        "surface": surface, "candidate_targets": distinct}], "propositions": []}
        return {"answer": "I cannot resolve that reference from the current conversation. Please clarify it",
                "status": "clarification_required", "confidence": 0.0,
                "evidence": [], "ambiguities": [{"kind": "unresolved_reference",
                    "surface": surface}], "propositions": []}

    def _model_for_session(self, session_id: str) -> dict[str, Any] | None:
        session = self._session(session_id)
        if not session:
            return None
        try:
            model = json.loads(str(session.get("active_model_json") or "{}"))
        except json.JSONDecodeError:
            return None
        return model if model.get("events") is not None else None

    @staticmethod
    def _information_requirement_answer(question: str) -> dict[str, Any]:
        embedded = re.search(
            r"\bbefore\s+(?:answering|saying|deciding|concluding)\s+(.+?)(?:\?|$)",
            question, re.I,
        )
        requested = "that claim"
        if embedded:
            requested = " ".join(embedded.group(1).strip(" .?").split())
        return {
            "answer": (
                f"I would need supported evidence that answers {requested}. "
                "The current conversation does not provide it"
            ),
            "status": "clarification_required", "confidence": .92,
            "evidence": [], "propositions": [],
            "ambiguities": [{"kind": "missing_evidence", "requested": requested}],
        }

    @staticmethod
    def _realise(plan: Mapping[str, Any], request: Mapping[str, Any], turn_index: int) -> str:
        answer = str(plan.get("answer") or "").strip()
        if not answer:
            return "I do not have enough supported information to answer that."
        evidence = list(plan.get("evidence") or [])
        asks_for_support = str(request.get("requested_relation")) in {"cause", "evidence"}
        if str(request.get("requested_relation")) == "cause" and evidence:
            source = " ".join(str(evidence[0].get("text") or "").split())
            cause = re.search(r"\bbecause\s+(.+?)(?:[.!?]|$)", source, re.I)
            if cause:
                return _sentence(f"Because {cause.group(1).strip()}")
        if evidence and (asks_for_support or turn_index % 3 == 2):
            source = " ".join(str(evidence[0].get("text") or "").split())
            return _sentence(f"{answer.rstrip('.')} The supporting evidence is: {source}")
        if turn_index % 3 == 1 and plan.get("status") == "answered":
            return _sentence(f"From the represented evidence, {answer.rstrip('.')}")
        return _sentence(answer)

    def respond(self, utterance: str, *, session_id: str = "owner",
                context: str = "", source_id: str = "owner-conversation",
                source_family: str = "owner") -> dict[str, Any]:
        text = " ".join(str(utterance or "").split())
        if context.strip():
            self.ingest_context(session_id=session_id, text=context, source_id=source_id,
                                source_family=source_family, append=False)
        request = self.interpret(text)
        session = self._session(session_id)
        turn_index = int((session or {}).get("turn_count") or 0)
        state_change: dict[str, Any] = {}
        if request["speech_act"] in {"assertion", "instruction"}:
            fact = re.sub(r"^(?:remember|note|store|keep in mind)\s+(?:that\s+)?", "", text,
                          flags=re.I).strip()
            if fact:
                self.ingest_context(session_id=session_id, text=fact, source_id=source_id,
                                    source_family=source_family, append=True)
                plan = {"answer": "I have added that information to the current conversation",
                        "status": "answered", "confidence": .90, "evidence": [],
                        "ambiguities": [], "propositions": [fact]}
                state_change = {"added_fact": fact}
            else:
                plan = {"answer": "Please tell me what information I should remember",
                        "status": "clarification_required", "confidence": 0.0,
                        "evidence": [], "ambiguities": [{"kind": "missing_fact"}],
                        "propositions": []}
        else:
            model = self._model_for_session(session_id)
            if request["requested_relation"] == "coreference":
                plan = self._reference_answer(session_id, text)
            elif request["requested_relation"] == "information_requirement":
                plan = self._information_requirement_answer(text)
            elif model:
                discourse_plan = self.discourse._plan(model, text)
                plan = {**discourse_plan, "ambiguities": []}
                if request["missing_requirements"] and plan.get("status") != "answered":
                    plan["ambiguities"] = [{"kind": "unknown_request_intent"}]
            else:
                plan = {"answer": (
                            "I do not yet have enough conversation or source evidence. "
                            "Please give me the relevant facts or passage"
                        ), "status": "clarification_required", "confidence": 0.0,
                        "evidence": [], "ambiguities": [{"kind": "missing_context"}],
                        "propositions": []}
        evidence = list(plan.get("evidence") or [])
        response = self._realise(plan, request, turn_index)
        support_map = [
            {"claim": proposition, "evidence_ids": [str(row.get("id") or "") for row in evidence]}
            for proposition in plan.get("propositions") or []
        ]
        unsupported = bool(plan.get("propositions")) and not bool(evidence) and not state_change
        status = str(plan.get("status") or "clarification_required")
        if unsupported:
            status = "clarification_required"
            response = "I formed a possible answer but cannot support it from the current evidence. Please clarify or provide a source."
        now = time.time()
        turn_id = _identifier("native_conversation_turn_", [session_id, turn_index, text, now])
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_conversation_turns VALUES(
                   ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (turn_id, session_id, turn_index, text, json.dumps(request, sort_keys=True),
                 response, status, float(plan.get("confidence") or 0),
                 json.dumps(plan.get("propositions") or []), json.dumps(evidence),
                 json.dumps(support_map), json.dumps(plan.get("ambiguities") or []),
                 json.dumps(state_change), 0, now),
            )
            connection.execute(
                """INSERT INTO native_conversation_sessions(
                   session_id,active_passage,active_model_json,current_topic,topic_stack_json,
                   unresolved_json,turn_count,created_epoch,updated_epoch)
                   VALUES(?,'','{}','','[]',?,1,?,?)
                   ON CONFLICT(session_id) DO UPDATE SET turn_count=turn_count+1,
                   unresolved_json=excluded.unresolved_json,updated_epoch=excluded.updated_epoch""",
                (session_id, json.dumps(plan.get("ambiguities") or []), now, now),
            )
        return {
            "schema_version": "aion.native_conversation_runtime.v1",
            "turn_id": turn_id, "session_id": session_id, "turn_index": turn_index,
            "request_frame": request, "response": response, "status": status,
            "confidence": float(plan.get("confidence") or 0),
            "propositions": list(plan.get("propositions") or []), "evidence": evidence,
            "support_map": support_map, "ambiguities": list(plan.get("ambiguities") or []),
            "state_change": state_change,
            "checks": {"evidence_supported": bool(evidence) or bool(state_change),
                       "unsupported_claims": unsupported,
                       "ambiguity_detected": bool(plan.get("ambiguities")),
                       "model_or_cloud_route_present": False},
            "generation": {"method": "native_proposition_clause_realizer",
                           "qwen_used": False, "model_used": False,
                           "cloud_used": False, "next_token_prediction": False},
        }

    def correct(self, *, turn_id: str, corrected_fact: str, explanation: str,
                source_ref: str = "owner-verified") -> dict[str, Any]:
        now = time.time()
        with self._connect() as connection:
            turn = connection.execute(
                "SELECT session_id FROM native_conversation_turns WHERE turn_id=?", (turn_id,),
            ).fetchone()
            if not turn:
                raise ValueError("unknown native conversation turn")
            session_id = str(turn["session_id"])
        ingestion = self.ingest_context(session_id=session_id, text=corrected_fact,
                                        source_id=source_ref, source_family="owner_correction",
                                        append=True)
        with self._connect() as connection:
            proposition = connection.execute(
                """SELECT proposition_id FROM native_conversation_propositions
                   WHERE session_id=? ORDER BY created_epoch DESC LIMIT 1""",
                (session_id,),
            ).fetchone()
            proposition_id = str(proposition[0]) if proposition else ""
            correction_id = _identifier(
                "native_conversation_correction_", [turn_id, corrected_fact, now],
            )
            connection.execute(
                "INSERT INTO native_conversation_corrections VALUES(?,?,?,?,?,?,?,'due',?,0,0,?,NULL)",
                (correction_id, session_id, turn_id, corrected_fact, explanation,
                 source_ref, proposition_id, now + 86400.0, now),
            )
        return {"stored": True, "correction_id": correction_id,
                "session_id": session_id, "proposition_id": proposition_id,
                "due_epoch": now + 86400.0, "ingestion": ingestion,
                "model_used": False}

    def session_state(self, session_id: str) -> dict[str, Any]:
        session = self._session(session_id)
        if not session:
            return {"session_id": session_id, "exists": False, "model_used": False}
        with self._read_connect() as connection:
            mentions = connection.execute(
                "SELECT resolution_status,COUNT(*) count FROM native_conversation_mentions WHERE session_id=? GROUP BY resolution_status",
                (session_id,),
            ).fetchall()
            propositions = connection.execute(
                "SELECT COUNT(*) FROM native_conversation_propositions WHERE session_id=? AND status='active'",
                (session_id,),
            ).fetchone()[0]
        return {"session_id": session_id, "exists": True,
                "turn_count": int(session["turn_count"]),
                "current_topic": session["current_topic"],
                "topic_stack": json.loads(session["topic_stack_json"] or "[]"),
                "unresolved": json.loads(session["unresolved_json"] or "[]"),
                "active_propositions": int(propositions),
                "mentions": {str(row["resolution_status"]): int(row["count"]) for row in mentions},
                "model_used": False}

    def metrics(self) -> dict[str, Any]:
        now = time.time()
        with self._read_connect() as connection:
            total = connection.execute(
                """SELECT COUNT(*) turns,
                          SUM(status='answered') answered,
                          SUM(json_extract(ambiguity_json,'$[0].kind') IS NOT NULL) ambiguous,
                          SUM(evidence_json!='[]' OR state_change_json!='{}') evidence_supported,
                          SUM(status!='answered' AND proposition_json!='[]') unsupported,
                          SUM(model_used) model_used,
                          COUNT(DISTINCT session_id) sessions
                   FROM native_conversation_turns"""
            ).fetchone()
            recent = connection.execute(
                """SELECT COUNT(*) turns,SUM(status='answered') answered
                   FROM native_conversation_turns WHERE created_epoch>?""",
                (now - 3600.0,),
            ).fetchone()
            mentions = connection.execute(
                """SELECT COUNT(*) total,SUM(resolution_status='resolved') resolved,
                          SUM(resolution_status='unresolved') unresolved
                   FROM native_conversation_mentions"""
            ).fetchone()
            corrections = connection.execute(
                "SELECT COUNT(*) total,SUM(status='due' AND due_epoch<=?) due FROM native_conversation_corrections",
                (now,),
            ).fetchone()
        mention_total = int(mentions["total"] or 0)
        return {"sessions": int(total["sessions"] or 0), "turns": int(total["turns"] or 0),
                "answered": int(total["answered"] or 0),
                "evidence_supported_turns": int(total["evidence_supported"] or 0),
                "unsupported_claims": int(total["unsupported"] or 0),
                "clarifications": int(total["turns"] or 0) - int(total["answered"] or 0),
                "turns_last_hour": int(recent["turns"] or 0),
                "answered_last_hour": int(recent["answered"] or 0),
                "mentions": mention_total, "mentions_resolved": int(mentions["resolved"] or 0),
                "mentions_unresolved": int(mentions["unresolved"] or 0),
                "reference_resolution_rate": round(int(mentions["resolved"] or 0) / mention_total, 4)
                if mention_total else None,
                "corrections": int(corrections["total"] or 0),
                "verified_corrections": int(corrections["total"] or 0),
                "corrections_due": int(corrections["due"] or 0),
                "student_model_used": bool(total["model_used"]),
                "generation": "native_proposition_clause_realizer",
                "claim_boundary": (
                    "Owner-facing native turns are evidence mapped and model-free; broad conversational "
                    "ability requires independent twenty-turn examinations."
                )}


__all__ = ["NativeConversationRuntime"]
