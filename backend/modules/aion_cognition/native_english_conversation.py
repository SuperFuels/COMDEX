"""AION-native English conversation without generative language models.

Questions are parsed into symbolic intents and slots.  Answers are planned from
verified lexical/factual evidence and realised with explicit grammar rules.  No
prompt, completion, token sampler, embedding API, cloud API or teacher model is
present on the answer path.  Native self-improvement replays failures and
paraphrases against verified memory; it cannot promote an unsupported claim.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping

from backend.modules.aion_cognition.sqlite_connection import connect as sqlite_connect
from backend.modules.aion_cognition.native_lexical_intelligence import (
    NativeLexicalIntelligence,
    _normalise_lemma,
    _tokens,
)
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
COMMON_ACTIONS = {
    "accept", "bring", "build", "carry", "change", "collect", "compare", "complete",
    "create", "decide", "deliver", "describe", "explain", "finish", "give", "inspect",
    "learn", "make", "move", "open", "paint", "read", "repair", "say", "store", "teach",
    "understand", "use", "verify", "write",
}
REFERENCE_WORDS = {"it", "this", "that", "they", "them", "he", "she", "him", "her"}


def _identifier(prefix: str, value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return prefix + hashlib.sha256(encoded).hexdigest()[:20]


def _sentence(value: str) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return text
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".?!" else text + "."


class NativeEnglishConversation:
    """Symbolic question understanding, retrieval, reasoning and realisation."""

    def __init__(
        self, *, repo_root: Path | str, lexical: NativeLexicalIntelligence | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.wordwall = NativeWordwallLearning(repo_root=self.repo_root, lexical=self.lexical)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite_connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_english_facts (
                    fact_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    qualifiers_json TEXT NOT NULL DEFAULT '{}',
                    source TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    verified INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_english_fact_lookup
                    ON native_english_facts(subject,predicate,object_value,verified);
                CREATE TABLE IF NOT EXISTS native_english_turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    parse_json TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS native_english_turn_session
                    ON native_english_turns(session_id,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_english_failures (
                    failure_id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    parse_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_english_improvement_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    examined INTEGER NOT NULL,
                    resolved INTEGER NOT NULL,
                    consistency_checks INTEGER NOT NULL,
                    consistency_passed INTEGER NOT NULL,
                    authority_allowed INTEGER NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_english_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    turn_id TEXT NOT NULL,
                    proposed_answer TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    verification_status TEXT NOT NULL,
                    verification_reason TEXT NOT NULL,
                    remedial_action TEXT NOT NULL,
                    created_epoch REAL NOT NULL,
                    FOREIGN KEY(turn_id) REFERENCES native_english_turns(turn_id)
                );
                """
            )
            # Early builds treated the honest "reference only" boundary as a
            # conversation failure. Preserve the audit rows but remove them
            # from the open-failure workload.
            connection.execute(
                "UPDATE native_english_failures SET status='discarded_reference_catalogue_probe',"
                "updated_epoch=? WHERE reason='reference_only' AND status='open'",
                (time.time(),),
            )

    def parse(self, question: str) -> dict[str, Any]:
        text = " ".join(str(question or "").strip().split())
        lowered = text.lower().rstrip("?.!")
        result: dict[str, Any] = {
            "text": text, "intent": "unknown", "slots": {}, "negated": False,
            "tense": "past" if re.search(r"\b(?:did|was|were|had)\b", lowered)
            else "future" if re.search(r"\b(?:will|shall)\b", lowered) else "present",
            "tokens": [word.lower() for word in WORD_RE.findall(text)],
        }
        patterns = (
            ("define", r"^(?:define|meaning of)\s+['\"]?(.+?)['\"]?$", ("term",)),
            ("define", r"^(?:what does|what is)\s+['\"]?(.+?)['\"]?\s+mean$", ("term",)),
            ("synonym", r"^(?:synonyms? (?:for|of)|what is similar to)\s+['\"]?(.+?)['\"]?$", ("term",)),
            ("antonym", r"^(?:antonyms? (?:for|of)|what is the opposite of)\s+['\"]?(.+?)['\"]?$", ("term",)),
            ("compare", r"^(?:compare|what is the difference between|how are)\s+(.+?)\s+(?:and|to)\s+(.+?)(?:\s+related)?$", ("first", "second")),
            ("known_about", r"^(?:what do you know about|tell me about)\s+(.+)$", ("subject",)),
            ("who", r"^who\s+(.+?)\s+(?:the\s+)?(.+)$", ("predicate", "object")),
            ("where", r"^where\s+(?:did|does|is|was)\s+(.+?)\s+(.+)$", ("subject", "predicate")),
            ("when", r"^when\s+(?:did|does|is|was)\s+(.+?)\s+(.+)$", ("subject", "predicate")),
            ("why", r"^why\s+(?:did|does|is|was)\s+(.+?)\s+(.+)$", ("subject", "predicate")),
            ("what_object", r"^what\s+(?:did|does)\s+(.+?)\s+(.+)$", ("subject", "predicate")),
            ("yes_no", r"^(?:is|are|was|were|does|did|has|have)\s+(.+)$", ("proposition",)),
        )
        for intent, pattern, names in patterns:
            match = re.match(pattern, lowered, re.I)
            if match:
                result["intent"] = intent
                result["slots"] = {
                    name: _normalise_lemma(value) for name, value in zip(names, match.groups())
                }
                break
        result["negated"] = bool(re.search(r"\b(?:not|never|no)\b", lowered))
        content = list(result["tokens"])
        action_index = next((
            index for index, word in enumerate(content)
            if word in COMMON_ACTIONS or word.rstrip("s") in COMMON_ACTIONS
            or word.removesuffix("ed") in COMMON_ACTIONS
        ), None)
        result["frame"] = {
            "entities": [word for word in content if self.lexical.lookup(word)],
            "action": content[action_index] if action_index is not None else None,
            "subject_terms": content[2:action_index] if action_index is not None and result["intent"] in {
                "where", "when", "why", "what_object",
            } else [],
            "object_terms": content[action_index + 1:] if action_index is not None else [],
            "properties": [],
            "time": result["tense"], "negated": result["negated"],
        }
        result["ambiguous"] = result["intent"] == "unknown" or any(
            not value for value in result["slots"].values()
        )
        return result

    def _resolve_context(self, parsed: dict[str, Any], session_id: str) -> dict[str, Any]:
        slots = dict(parsed.get("slots") or {})
        references = [key for key, value in slots.items() if str(value).lower() in REFERENCE_WORDS]
        if not references:
            parsed["context"] = {"used": False}
            return parsed
        with self._connect() as connection:
            prior = connection.execute(
                """SELECT turn_id,parse_json FROM native_english_turns
                   WHERE session_id=? AND status='answered'
                   ORDER BY created_epoch DESC LIMIT 1""",
                (session_id,),
            ).fetchone()
        if not prior:
            parsed["context"] = {"used": False, "unresolved_references": references}
            parsed["ambiguous"] = True
            return parsed
        prior_slots = dict(json.loads(prior["parse_json"] or "{}").get("slots") or {})
        candidate = next((
            str(prior_slots.get(key) or "") for key in (
                "term", "subject", "object", "first", "second",
            ) if prior_slots.get(key)
        ), "")
        if not candidate:
            parsed["context"] = {"used": False, "unresolved_references": references}
            parsed["ambiguous"] = True
            return parsed
        for key in references:
            slots[key] = candidate
        parsed["slots"] = slots
        parsed["context"] = {"used": True, "source_turn_id": prior["turn_id"],
                             "resolved_to": candidate, "references": references}
        parsed["ambiguous"] = False
        return parsed

    def remember_fact(
        self, *, subject: str, predicate: str, object_value: str,
        qualifiers: Mapping[str, Any] | None = None, source: str,
        source_ref: str = "", verified: bool = True,
    ) -> dict[str, Any]:
        authority = dict(self.lexical.authority_provider())
        clean = {
            "subject": _normalise_lemma(subject),
            "predicate": _normalise_lemma(predicate),
            "object_value": " ".join(str(object_value or "").strip().split()),
            "qualifiers": dict(qualifiers or {}),
            "source": str(source or "").strip(),
            "source_ref": str(source_ref or "").strip(),
        }
        if not all((clean["subject"], clean["predicate"], clean["object_value"], clean["source"])):
            return {"stored": False, "reason": "incomplete_fact", "authority": authority}
        if not authority.get("allow_learn"):
            return {"stored": False, "reason": "learning_authority_denied", "authority": authority}
        fact_id = _identifier("native_english_fact_", clean)
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO native_english_facts(
                   fact_id,subject,predicate,object_value,qualifiers_json,source,source_ref,
                   verified,created_epoch) VALUES(?,?,?,?,?,?,?,?,?)""",
                (fact_id, clean["subject"], clean["predicate"], clean["object_value"],
                 json.dumps(clean["qualifiers"], sort_keys=True), clean["source"],
                 clean["source_ref"], int(verified), time.time()),
            )
        return {"stored": True, "fact_id": fact_id, "fact": clean, "authority": authority}

    def _facts(self, parsed: Mapping[str, Any], limit: int = 12) -> list[dict[str, Any]]:
        intent = str(parsed.get("intent") or "")
        slots = dict(parsed.get("slots") or {})
        clauses = ["verified=1"]
        params: list[Any] = []
        subject = str(slots.get("subject") or "")
        predicate = str(slots.get("predicate") or "")
        object_value = str(slots.get("object") or "")
        if subject:
            clauses.append("subject=?")
            params.append(subject)
        if predicate:
            clauses.append("predicate LIKE ?")
            params.append(predicate.split()[0] + "%")
        if object_value:
            clauses.append("object_value LIKE ?")
            params.append("%" + object_value + "%")
        if intent == "known_about" and subject:
            clauses = ["verified=1", "(subject=? OR object_value LIKE ?)"]
            params = [subject, "%" + subject + "%"]
        params.append(max(1, int(limit)))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM native_english_facts WHERE {' AND '.join(clauses)} "
                "ORDER BY created_epoch DESC LIMIT ?", tuple(params),
            ).fetchall()
        return [{**dict(row), "qualifiers": json.loads(row["qualifiers_json"] or "{}")} for row in rows]

    def _lexical_plan(self, parsed: Mapping[str, Any]) -> dict[str, Any] | None:
        intent = str(parsed.get("intent") or "")
        slots = dict(parsed.get("slots") or {})
        terms = (
            [str(slots.get("first") or ""), str(slots.get("second") or "")]
            if intent == "compare" else
            [str(slots.get("term") or slots.get("subject") or "")]
        )
        acquired = {term: self.wordwall.acquired(term, active_only=True) for term in terms if term}

        def reference_only(term: str) -> dict[str, Any] | None:
            entry = self.lexical.lookup(term)
            if not entry:
                return None
            in_progress = self.wordwall.acquired(term)
            stage = str(in_progress[0]["stage"]) if in_progress else "not_started"
            return {
                "answer": (
                    f"I have a reference entry for '{entry['lemma']}', but I have not yet "
                    f"completed learning and retention testing for it. Its current acquisition "
                    f"stage is {stage.replace('_', ' ')}"
                ),
                "confidence": .99,
                "status": "reference_only",
                "knowledge_status": "reference_only",
                "acquisition_stage": stage,
                "evidence": [{
                    "kind": "reference_lexeme_not_learned", "id": entry["lemma"],
                    "source": entry["source"],
                }],
            }

        if intent == "define":
            term = str(slots.get("term") or "")
            concepts = acquired.get(term) or []
            if not concepts:
                return reference_only(term)
            concept = concepts[0]
            return {
                "answer": f"I understand '{concept['lemma']}' as: {concept['native_gloss']}",
                "confidence": .91, "status": "answered", "knowledge_status": "acquired",
                "acquisition_stage": concept["stage"],
                "evidence": [{"kind": "acquired_concept", "id": concept["concept_id"],
                              "stage": concept["stage"], "sense": concept["sense_hash"]}],
            }
        if intent in {"synonym", "antonym"}:
            term = str(slots.get("term") or "")
            relation = "synonym" if intent == "synonym" else "antonym"
            concepts = acquired.get(term) or []
            if not concepts:
                return reference_only(term)
            concept = concepts[0]
            words = list((concept.get("relations") or {}).get(relation) or [])[:6]
            if not words:
                return {"answer": f"I have learned '{term}', but I have not acquired a tested {relation} for it",
                        "confidence": .82, "status": "unknown", "knowledge_status": "acquired_incomplete",
                        "acquisition_stage": concept["stage"], "evidence": [{
                            "kind": "acquired_concept", "id": concept["concept_id"],
                            "stage": concept["stage"],
                        }]}
            label = "synonyms" if relation == "synonym" else "antonyms"
            answer = f"The {label} I have acquired for '{term}' include {', '.join(words)}"
            return {"answer": answer, "confidence": .90, "status": "answered",
                    "knowledge_status": "acquired", "acquisition_stage": concept["stage"],
                    "evidence": [{"kind": "acquired_concept_relation",
                                  "id": f"{concept['concept_id']}:{relation}:{word}",
                                  "stage": concept["stage"]} for word in words]}
        if intent == "compare":
            first, second = str(slots.get("first") or ""), str(slots.get("second") or "")
            left_rows, right_rows = acquired.get(first) or [], acquired.get(second) or []
            if not left_rows:
                return reference_only(first)
            if not right_rows:
                return reference_only(second)
            left, right = left_rows[0], right_rows[0]
            relation = next((name for name, values in (left.get("relations") or {}).items()
                             if right["lemma"] in values), None)
            relation_text = (f" I have acquired a {relation} relationship between them."
                             if relation else " I have not acquired a direct relationship between them.")
            return {
                "answer": f"{left['native_gloss']}. {right['native_gloss']}.{relation_text}",
                "confidence": .88 if relation else .72,
                "status": "answered", "knowledge_status": "acquired",
                "acquisition_stage": min(left["stage"], right["stage"]),
                "evidence": [
                    {"kind": "acquired_concept", "id": left["concept_id"], "stage": left["stage"]},
                    {"kind": "acquired_concept", "id": right["concept_id"], "stage": right["stage"]},
                ],
            }
        if intent == "known_about":
            term = str(slots.get("subject") or "")
            concepts = acquired.get(term) or []
            if not concepts:
                return reference_only(term)
            concept = concepts[0]
            relations = [
                f"{relation} of {word}"
                for relation, words in (concept.get("relations") or {}).items()
                for word in words[:2]
            ]
            related = f" Acquired relationships include {', '.join(relations[:4])}." if relations else ""
            return {
                "answer": f"{concept['native_gloss']}.{related}", "confidence": .88,
                "status": "answered", "knowledge_status": "acquired",
                "acquisition_stage": concept["stage"],
                "evidence": [{"kind": "acquired_concept", "id": concept["concept_id"],
                              "stage": concept["stage"]}],
            }
        return None

    def _fact_plan(self, parsed: Mapping[str, Any]) -> dict[str, Any] | None:
        rows = self._facts(parsed)
        if not rows:
            return None
        intent = str(parsed.get("intent") or "")
        row = rows[0]
        qualifiers = row["qualifiers"]
        if intent == "who":
            answer = f"{row['subject']} {row['predicate']} {row['object_value']}"
        elif intent == "what_object":
            answer = f"{row['subject']} {row['predicate']} {row['object_value']}"
        elif intent == "where" and qualifiers.get("place"):
            answer = f"{row['subject']} {row['predicate']} {row['object_value']} in {qualifiers['place']}"
        elif intent == "when" and qualifiers.get("time"):
            answer = f"{row['subject']} {row['predicate']} {row['object_value']} {qualifiers['time']}"
        elif intent == "why" and qualifiers.get("cause"):
            answer = f"{row['subject']} {row['predicate']} {row['object_value']} because {qualifiers['cause']}"
        elif intent == "known_about":
            clauses = [f"{item['subject']} {item['predicate']} {item['object_value']}" for item in rows[:3]]
            answer = ". ".join(clauses)
        else:
            return None
        return {
            "answer": answer, "confidence": .92,
            "evidence": [{"kind": "verified_fact", "id": row["fact_id"],
                          "source": row["source"], "source_ref": row["source_ref"]}],
        }

    def _checks(self, answer: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "has_evidence": bool(evidence),
            "grammatical_surface": bool(answer and answer[0].isupper() and answer[-1] in ".?!"),
            "balanced_quotes": answer.count("'") % 2 == 0 and answer.count('"') % 2 == 0,
            "unsupported_claims_detected": not bool(evidence),
            "model_or_cloud_route_present": False,
        }

    def ask(self, question: str, *, session_id: str = "default") -> dict[str, Any]:
        parsed = self._resolve_context(self.parse(question), session_id)
        plan = self._lexical_plan(parsed) or self._fact_plan(parsed)
        if plan:
            answer = _sentence(str(plan["answer"]))
            confidence = float(plan["confidence"])
            evidence = list(plan["evidence"])
            status = str(plan.get("status") or "answered")
        elif parsed["ambiguous"]:
            answer = "I cannot determine the question's intended meaning. Please state the subject and what you want to know."
            confidence, evidence, status = .0, [], "clarification_required"
        else:
            answer = "I do not have enough verified knowledge to answer that question"
            confidence, evidence, status = .0, [], "unknown"
        answer = _sentence(answer)
        checks = self._checks(answer, evidence)
        now = time.time()
        turn_id = _identifier("native_english_turn_", [session_id, question, answer, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_english_turns(
                   turn_id,session_id,question,parse_json,answer,status,confidence,
                   evidence_json,checks_json,created_epoch) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (turn_id, session_id, question, json.dumps(parsed, sort_keys=True), answer,
                 status, confidence, json.dumps(evidence, sort_keys=True),
                 json.dumps(checks, sort_keys=True), now),
            )
            if status not in {"answered", "reference_only"} or not all((
                    checks["grammatical_surface"], checks["balanced_quotes"],
            )):
                failure_id = _identifier("native_english_failure_", [question, status])
                connection.execute(
                    """INSERT INTO native_english_failures(
                       failure_id,question,reason,parse_json,status,attempts,created_epoch,updated_epoch
                       ) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(failure_id) DO UPDATE SET
                       attempts=native_english_failures.attempts+1,updated_epoch=excluded.updated_epoch""",
                    (failure_id, question, status, json.dumps(parsed, sort_keys=True),
                     "open", 1, now, now),
                )
        return {
            "schema_version": "aion.native_english_conversation.v1",
            "turn_id": turn_id, "question": question, "parse": parsed,
            "answer": answer, "status": status, "confidence": confidence,
            "knowledge_status": str((plan or {}).get("knowledge_status") or status),
            "acquisition_stage": (plan or {}).get("acquisition_stage"),
            "evidence": evidence, "checks": checks,
            "generation": {
                "method": "symbolic_meaning_plan_and_rule_grammar",
                "aion_generated": True, "next_token_prediction": False,
                "qwen_used": False, "model_used": False, "cloud_used": False,
                "external_polisher_used": False,
            },
        }

    def self_improvement_cycle(self, *, limit: int = 24) -> dict[str, Any]:
        """Retry failures and test paraphrase consistency using verified truth only."""
        authority = dict(self.lexical.authority_provider())
        if not authority.get("allow_learn"):
            return {"status": "blocked", "authority": authority, "model_used": False}
        with self._connect() as connection:
            failures = connection.execute(
                "SELECT * FROM native_english_failures WHERE status='open' ORDER BY updated_epoch LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
            # Paraphrase consistency is meaningful only for knowledge Aion has
            # acquired. Running this over the imported dictionary would turn a
            # reference catalogue into a false intelligence claim.
            lexemes = connection.execute(
                """SELECT DISTINCT lemma FROM acquired_concepts
                   WHERE stage IN ('retention_1d','retention_7d','retention_30d',
                                   'retention_90d','mastered')
                   ORDER BY active_epoch,lemma LIMIT ?""",
                (max(2, int(limit)),),
            ).fetchall()
        resolved = 0
        for failure in failures:
            failure_question = str(failure["question"])
            if failure_question.count("'") % 2:
                with self._connect() as connection:
                    connection.execute(
                        """UPDATE native_english_failures
                           SET status='discarded_invalid_probe',updated_epoch=?
                           WHERE failure_id=?""",
                        (time.time(), failure["failure_id"]),
                    )
                continue
            replay = self.ask(failure_question, session_id="native-self-improvement")
            if replay["status"] == "answered" and replay["checks"]["has_evidence"]:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE native_english_failures SET status='resolved',updated_epoch=? WHERE failure_id=?",
                        (time.time(), failure["failure_id"]),
                    )
                resolved += 1
        checked = passed = 0
        for row in lexemes:
            lemma = str(row["lemma"])
            first = self.ask(f"Define {lemma}", session_id="native-self-improvement")
            second = self.ask(f"What does {lemma} mean?", session_id="native-self-improvement")
            checked += 1
            first_evidence = {item.get("id") for item in first["evidence"]}
            second_evidence = {item.get("id") for item in second["evidence"]}
            if first["status"] == second["status"] == "answered" and first_evidence == second_evidence:
                passed += 1
        detail = {
            "examined_failures": len(failures), "resolved_failures": resolved,
            "consistency_checks": checked, "consistency_passed": passed,
            "learning_rule": "verified_evidence_and_cross_paraphrase_consistency_only",
        }
        cycle_id = _identifier("native_english_improvement_", [detail, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_english_improvement_cycles(
                   cycle_id,examined,resolved,consistency_checks,consistency_passed,
                   authority_allowed,detail_json,created_epoch) VALUES(?,?,?,?,?,?,?,?)""",
                (cycle_id, len(failures), resolved, checked, passed, 1,
                 json.dumps(detail, sort_keys=True), time.time()),
            )
        return {
            "status": "completed", "cycle_id": cycle_id, **detail,
            "authority": authority, "model_used": False, "cloud_used": False,
            "next_token_prediction": False,
        }

    def correct(
        self, *, turn_id: str, proposed_answer: str, reason: str = "", source_ref: str = "",
    ) -> dict[str, Any]:
        """Record feedback, independently verify it where possible, and remediate safely."""
        with self._connect() as connection:
            turn = connection.execute(
                "SELECT * FROM native_english_turns WHERE turn_id=?", (turn_id,),
            ).fetchone()
        if not turn:
            return {"status": "not_found", "turn_id": turn_id}
        parsed = json.loads(turn["parse_json"] or "{}")
        intent, slots = str(parsed.get("intent") or ""), dict(parsed.get("slots") or {})
        clean_answer = " ".join(str(proposed_answer or "").strip().split())
        verification_status = "pending_evidence"
        verification_reason = "Open conversation corrections require independent evidence."
        remedial_action = "held_for_review_not_learned"
        verified = False

        if intent == "define":
            term = str(slots.get("term") or "")
            entry = self.lexical.lookup(term)
            if entry:
                proposed_tokens = _tokens(clean_answer)
                definitions = list(entry.get("definitions") or [entry["definition"]])
                scored = [(
                    len(_tokens(str(definition)) & proposed_tokens) /
                    max(1, len(_tokens(str(definition)))), str(definition)
                ) for definition in definitions]
                coverage, matched_definition = max(scored, key=lambda row: row[0])
                verified = coverage >= .60
                verification_status = "verified_reference_alignment" if verified else "rejected_mismatch"
                verification_reason = (
                    f"The correction covered {coverage:.0%} of the independently stored semantic features."
                )
                if verified:
                    self.wordwall.encounter(
                        term, teacher_lesson_id="owner_verified_feedback",
                        sense_definition=matched_definition,
                    )
                    remedial_action = "concept_grounded_or_requeued_for_closed_book_practice"
                else:
                    remedial_action = "not_learned_reference_disagrees"
        elif intent in {"synonym", "antonym"}:
            term = str(slots.get("term") or "")
            relation = "synonym" if intent == "synonym" else "antonym"
            valid = {str(row["target_lemma"]) for row in self.lexical.related(term, relation, limit=32)}
            supplied = {_normalise_lemma(word) for word in re.split(r"[,;/]|\band\b", clean_answer) if word.strip()}
            verified = bool(valid & supplied)
            verification_status = "verified_relation" if verified else "rejected_mismatch"
            verification_reason = "The proposed relation matched independent lexical evidence." if verified else "The proposed relation did not match independent lexical evidence."
            if verified:
                self.wordwall.encounter(term, teacher_lesson_id="owner_verified_feedback")
                remedial_action = "relation_requeued_for_closed_book_practice"
            else:
                remedial_action = "not_learned_reference_disagrees"

        feedback = {
            "turn_id": turn_id, "proposed_answer": clean_answer, "reason": reason.strip(),
            "source_ref": source_ref.strip(), "verification_status": verification_status,
            "verification_reason": verification_reason, "remedial_action": remedial_action,
        }
        feedback_id = _identifier("native_english_feedback_", [feedback, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_feedback VALUES(?,?,?,?,?,?,?,?,?)",
                (feedback_id, turn_id, clean_answer, reason.strip(), source_ref.strip(),
                 verification_status, verification_reason, remedial_action, time.time()),
            )
        return {"status": "accepted" if verified else verification_status,
                "feedback_id": feedback_id, "verified": verified,
                "verification_reason": verification_reason,
                "remedial_action": remedial_action,
                "immediate_answer_overwrite": False,
                "counts_as_mastery": False}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            turns = int(connection.execute("SELECT COUNT(*) FROM native_english_turns").fetchone()[0])
            answered = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_turns WHERE status='answered'"
            ).fetchone()[0])
            open_failures = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_failures WHERE status='open'"
            ).fetchone()[0])
            facts = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_facts WHERE verified=1"
            ).fetchone()[0])
            cycles = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_improvement_cycles"
            ).fetchone()[0])
            verified_feedback = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_feedback WHERE verification_status LIKE 'verified_%'"
            ).fetchone()[0])
            pending_feedback = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_feedback WHERE verification_status='pending_evidence'"
            ).fetchone()[0])
        return {
            "turns": turns, "answered": answered,
            "answer_rate": round(answered / turns, 4) if turns else None,
            "verified_facts": facts, "open_failures": open_failures,
            "self_improvement_cycles": cycles,
            "verified_feedback": verified_feedback, "pending_feedback": pending_feedback,
        }


__all__ = ["NativeEnglishConversation"]
