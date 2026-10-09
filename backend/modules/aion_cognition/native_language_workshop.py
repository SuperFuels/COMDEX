"""Governed connected-English practice for Aion's native language system.

Qwen may author sealed exercises, but it returns before the student acts.  The
student path uses only lexical capsules, semantic parsing, explicit sentence
planning and native conversation.  Workshop success is practice evidence; the
Semantic Transfer Academy remains the promotion authority.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable, Mapping

from backend.modules.aion_cognition.native_english_conversation import NativeEnglishConversation
from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer, _normal
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence, _tokens


FAMILY_SEQUENCE = (
    *("clause_inference",) * 6,
    *("native_generation",) * 5,
    *("paraphrase_transformation",) * 4,
    *("multi_turn_dialogue",) * 3,
    *("delayed_vocabulary",) * 2,
)
FAMILIES = tuple(dict.fromkeys(FAMILY_SEQUENCE))
NAMES = ("Mireya", "Tavian", "Leona", "Kellan", "Amara", "Neryn", "Cassia", "Soren")
OBJECTS = ("report", "sensor", "proposal", "evidence", "machine", "record", "sample")
WORKSHOP_FUNCTION_WORDS = frozenset({
    "a", "all", "an", "and", "any", "as", "at", "but", "by", "every", "for",
    "from", "if", "in", "less", "more", "most", "no", "non", "not", "of", "on",
    "or", "some", "than", "the", "then", "to", "with",
})


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _past(word: str) -> str:
    irregular = {"be": "was", "have": "had", "do": "did", "write": "wrote",
                 "make": "made", "give": "gave", "read": "read"}
    if word in irregular:
        return irregular[word]
    if word.endswith("e"):
        return word + "d"
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        return word[:-1] + "ied"
    return word + "ed"


def _present(word: str, subject: str) -> str:
    if subject.lower() in {"i", "you", "we", "they"}:
        return word
    if word.endswith(("s", "sh", "ch", "x", "z")):
        return word + "es"
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


class NativeLanguageWorkshop:
    """Train connected language without allowing the teacher onto the answer path."""

    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None,
                 retry_delay_seconds: float = 900.0) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.transfer = NativeEnglishTransfer(repo_root=self.repo_root, lexical=self.lexical)
        self.conversation = NativeEnglishConversation(repo_root=self.repo_root, lexical=self.lexical)
        self.retry_delay_seconds = max(.01, float(retry_delay_seconds))
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_language_workshop_exercises(
                    exercise_id TEXT PRIMARY KEY, family TEXT NOT NULL,
                    concept_id TEXT NOT NULL, lemma TEXT NOT NULL,
                    material TEXT NOT NULL, prompt TEXT NOT NULL,
                    expected_answer TEXT NOT NULL, answer_reason TEXT NOT NULL,
                    frame_json TEXT NOT NULL, teacher_model TEXT NOT NULL,
                    teacher_generated INTEGER NOT NULL, answer_sealed INTEGER NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_language_workshop_attempts(
                    attempt_id TEXT PRIMARY KEY, exercise_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL, family TEXT NOT NULL,
                    answer TEXT NOT NULL, score REAL NOT NULL, correct INTEGER NOT NULL,
                    feedback TEXT NOT NULL, model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_language_workshop_remediation(
                    obligation_id TEXT PRIMARY KEY, concept_id TEXT NOT NULL,
                    family TEXT NOT NULL, expected_answer TEXT NOT NULL,
                    answer_reason TEXT NOT NULL, status TEXT NOT NULL,
                    due_epoch REAL NOT NULL, created_epoch REAL NOT NULL,
                    cleared_epoch REAL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS workshop_one_due
                    ON native_language_workshop_remediation(concept_id,family)
                    WHERE status='due';
                CREATE TABLE IF NOT EXISTS native_language_workshop_cycles(
                    cycle_id TEXT PRIMARY KEY, attempted INTEGER NOT NULL,
                    correct INTEGER NOT NULL, rejected INTEGER NOT NULL,
                    teacher_model TEXT NOT NULL, detail_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                """
            )
            columns = {str(row[1]) for row in connection.execute(
                "PRAGMA table_info(native_language_workshop_remediation)"
            ).fetchall()}
            if "retry_count" not in columns:
                connection.execute(
                    "ALTER TABLE native_language_workshop_remediation "
                    "ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
                )

    def _candidates(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT a.concept_id,a.lemma,a.part_of_speech,a.stage,a.native_gloss,
                          a.features_json,a.relations_json,
                          COUNT(w.exercise_id) workshop_uses
                   FROM acquired_concepts a
                   JOIN native_english_practice_progress m ON m.concept_id=a.concept_id
                     AND m.family='meaning_discrimination' AND m.correct>=2
                   JOIN native_english_practice_progress x ON x.concept_id=a.concept_id
                     AND x.family='context_completion' AND x.correct>=2
                   JOIN native_english_practice_progress s ON s.concept_id=a.concept_id
                     AND s.family='sentence_construction' AND s.correct>=2
                   JOIN native_english_practice_progress t ON t.concept_id=a.concept_id
                     AND t.family='sentence_transformation' AND t.correct>=1
                   JOIN native_english_practice_progress r ON r.concept_id=a.concept_id
                     AND r.family='reading_comprehension' AND r.correct>=1
                   LEFT JOIN native_language_workshop_exercises w
                     ON w.concept_id=a.concept_id
                   WHERE a.stage!='encountered' AND INSTR(a.lemma,' ')=0
                   GROUP BY a.concept_id
                   ORDER BY workshop_uses,a.updated_epoch,a.concept_id LIMIT ?""",
                (max(1, int(limit)),),
            ).fetchall()
        result = []
        for row in rows:
            value = dict(row)
            if str(value.get("lemma") or "").lower() in WORKSHOP_FUNCTION_WORDS:
                continue
            value["features"] = json.loads(value.pop("features_json") or "[]")
            value["relations"] = json.loads(value.pop("relations_json") or "{}")
            result.append(value)
        return result

    def _due_candidates(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT o.obligation_id,o.family AS remedial_family,
                          o.expected_answer AS correction_answer,
                          o.answer_reason AS correction_reason,
                          COALESCE(o.retry_count,0) AS retry_count,
                          a.concept_id,a.lemma,a.part_of_speech,a.stage,a.native_gloss,
                          a.features_json,a.relations_json
                   FROM native_language_workshop_remediation o
                   JOIN acquired_concepts a ON a.concept_id=o.concept_id
                   WHERE o.status='due' AND o.due_epoch<=?
                   ORDER BY o.due_epoch LIMIT ?""",
                (time.time(), max(0, int(limit))),
            ).fetchall()
        result = []
        for row in rows:
            value = dict(row)
            if str(value.get("lemma") or "").lower() in WORKSHOP_FUNCTION_WORDS:
                continue
            value["features"] = json.loads(value.pop("features_json") or "[]")
            value["relations"] = json.loads(value.pop("relations_json") or "{}")
            result.append(value)
        return result

    @staticmethod
    def _prompt(candidates: list[Mapping[str, Any]], families: list[str]) -> str:
        targets = [{
            "concept_id": row["concept_id"], "lemma": row["lemma"],
            "part_of_speech": row["part_of_speech"], "native_gloss": row["native_gloss"],
            "features": row["features"], "relations": row["relations"],
            "family": family,
            "remedial_retry": bool(row.get("obligation_id")),
            "verified_correction": str(row.get("correction_answer") or ""),
            "correction_reason": str(row.get("correction_reason") or ""),
        } for row, family in zip(candidates, families)]
        return f"""Create one sealed connected-English exercise for every supplied target.
Qwen is the teacher only. Aion answers later with the model disconnected.
Use novel names, situations and syntax. Never reveal expected_answer in prompt.

Families:
- clause_inference: 2-3 clauses; ask cause, contrast, condition, time, negation scope or reference.
- native_generation: give an intended semantic frame and ask for one original grammatical sentence.
- paraphrase_transformation: provide a sentence and require a meaning-preserving structural rewrite.
- multi_turn_dialogue: ask a contextual question answerable from the acquired meaning.
- delayed_vocabulary: place the target in unfamiliar material and ask which word expresses its meaning.

For generation/transformation include frame with subject, action, object, tense, negated,
target_role and required_connector. expected_answer is a valid reference, not a template the
student must copy. For comprehension, expected_answer must be an exact material span.
Use the target meaning, not unrelated world knowledge.
For remedial_retry targets, change the name, wording and situation, simplify the
syntax, and test the same meaning without copying the verified correction into the prompt.
TARGETS={json.dumps(targets, ensure_ascii=False, separators=(',', ':'))}
Return only JSON: {{"exercises":[{{"concept_id":"...","family":"...",
"material":"...","prompt":"...","expected_answer":"...","answer_reason":"...",
"frame":{{"subject":"","action":"","object":"","tense":"present|past|future",
"negated":false,"target_role":"action|object|property","required_connector":""}}}}]}}"""

    def _compile(self, concept: Mapping[str, Any], family: str, variant: int) -> dict[str, Any]:
        lemma, pos = str(concept["lemma"]), str(concept.get("part_of_speech") or "")
        name, obj = NAMES[variant % len(NAMES)], OBJECTS[(variant * 3) % len(OBJECTS)]
        cue = ", ".join(str(x) for x in concept.get("features") or []) or str(
            concept.get("native_gloss") or lemma
        )
        if pos == "v":
            action, object_value, target_role = lemma, obj, "action"
        elif pos in {"a", "s"}:
            action, object_value, target_role = "be", "", "property"
        elif pos == "r":
            action, object_value, target_role = "work", "", "manner"
        else:
            action, object_value, target_role = "inspect", lemma, "object"
        frame = {"subject": name, "action": action, "object": object_value,
                 "property": lemma if target_role == "property" else "",
                 "manner": lemma if target_role == "manner" else "",
                 "tense": "past", "negated": False, "target_role": target_role,
                 "required_connector": ""}
        sentence = self._realize(frame)
        if family == "clause_inference":
            material = f"Although the alarm sounded, {sentence} Because the evidence was verified, the review continued."
            if target_role == "property":
                prompt = f"Which property described {name} although the alarm sounded?"
                expected = lemma
            elif target_role == "manner":
                prompt = f"Which word described how {name} worked although the alarm sounded?"
                expected = lemma
            elif target_role == "object":
                prompt = f"What did {name} inspect although the alarm sounded?"
                expected = lemma
            else:
                prompt = f"What action did {name} perform although the alarm sounded?"
                expected = str(frame["action"])
        elif family == "native_generation":
            material = ""
            prompt, expected = f"Express this semantic frame in one grammatical sentence: {json.dumps(frame)}", sentence
        elif family == "paraphrase_transformation":
            material = sentence
            frame["tense"] = "future"
            expected = self._realize(frame)
            prompt = "Rewrite the sentence in the future while preserving its participants and meaning."
        elif family == "multi_turn_dialogue":
            material = f"The target concept is '{lemma}', associated with {cue}."
            prompt, expected = f"What does '{lemma}' mean?", str(concept.get("native_gloss") or cue)
        else:
            material = sentence
            prompt, expected = f"Which word in the material is associated with {cue}?", lemma
        return {"concept_id": concept["concept_id"], "lemma": lemma, "family": family,
                "material": material, "prompt": prompt, "expected_answer": expected,
                "answer_reason": f"The acquired concept '{lemma}' is associated with {cue}.",
                "frame": frame, "teacher_generated": False}

    @staticmethod
    def _realize(frame: Mapping[str, Any]) -> str:
        subject = str(frame.get("subject") or "Aion")
        action = str(frame.get("action") or "inspect")
        obj = str(frame.get("object") or "evidence")
        tense = str(frame.get("tense") or "present")
        negated = bool(frame.get("negated"))
        property_value = str(frame.get("property") or "")
        manner = str(frame.get("manner") or "")
        if property_value:
            copula = "will not be" if tense == "future" and negated else (
                "will be" if tense == "future" else
                "was not" if tense == "past" and negated else
                "was" if tense == "past" else
                "is not" if negated else "is"
            )
            sentence = f"{subject} {copula} {property_value}."
            connector = str(frame.get("required_connector") or "").strip()
            return sentence + (f" {connector.capitalize()} the evidence supported this property."
                               if connector else "")
        if tense == "future":
            verb = f"will {'not ' if negated else ''}{action}"
        elif tense == "past":
            verb = f"did not {action}" if negated else _past(action)
        else:
            verb = f"does not {action}" if negated else _present(action, subject)
        sentence = f"{subject} {verb}{(' ' + manner) if manner else ''}{(' the ' + obj) if obj else ''}."
        connector = str(frame.get("required_connector") or "").strip()
        if connector:
            sentence += f" {connector.capitalize()} the evidence supported this action."
        return sentence

    def _verify(self, item: Mapping[str, Any], concept: Mapping[str, Any],
                family: str) -> tuple[bool, list[str]]:
        problems = []
        if str(item.get("concept_id") or "") != str(concept["concept_id"]):
            problems.append("concept_id_mismatch")
        if str(item.get("family") or "") != family:
            problems.append("family_mismatch")
        for key in ("prompt", "expected_answer", "answer_reason"):
            if not str(item.get(key) or "").strip():
                problems.append(f"missing_{key}")
        lemma = _normal(str(concept.get("lemma") or ""))
        stem = lemma[:max(3, len(lemma) - 2)]
        grounding_text = _normal(" ".join((
            str(item.get("material") or ""), str(item.get("expected_answer") or ""),
            json.dumps(item.get("frame") or {}),
        )))
        if not any(word == lemma or word.startswith(stem) for word in grounding_text.split()):
            problems.append("target_not_grounded")
        if family in {"clause_inference", "delayed_vocabulary"}:
            expected = _normal(str(item.get("expected_answer") or ""))
            if expected and expected not in _normal(str(item.get("material") or "")):
                problems.append("answer_not_in_material")
        if family in {"native_generation", "paraphrase_transformation"}:
            frame = item.get("frame")
            if not isinstance(frame, Mapping) or not frame.get("action"):
                problems.append("missing_semantic_frame")
        return not problems, problems

    def _answer(self, exercise: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        family = str(exercise["family"])
        if family in {"clause_inference", "delayed_vocabulary"}:
            # Resolve explicit copular properties and adverbial manner as
            # grammatical roles before the general semantic parser.  This is
            # especially important for participial adjectives ("adapted",
            # "crooked"), whose surface can also resemble a verb.
            if family == "clause_inference":
                prompt = str(exercise.get("prompt") or "").lower()
                material = str(exercise.get("material") or "")
                if prompt.startswith("which property"):
                    match = re.search(
                        r"\b(?:is|are|was|were)\s+(?:not\s+)?([A-Za-z][A-Za-z'-]*)",
                        material,
                    )
                    if match:
                        return match.group(1), {
                            "native_role": "copular_property", "model_used": False,
                        }
                if prompt.startswith("which word described how"):
                    match = re.search(
                        r"\bworked\s+([A-Za-z][A-Za-z'-]*)", material,
                    )
                    if match:
                        return match.group(1), {
                            "native_role": "adverbial_manner", "model_used": False,
                        }
            result = self.transfer.answer(
                str(exercise["material"]), str(exercise["prompt"]),
                str(exercise["concept_id"]),
            )
            return str(result["answer"]), {"native_result": result}
        if family == "native_generation":
            return self._realize(exercise.get("frame") or {}), {
                "semantic_plan": dict(exercise.get("frame") or {}),
            }
        if family == "paraphrase_transformation":
            parsed = self.transfer.parse(str(exercise.get("material") or ""))
            source = dict(parsed.get("frame") or {})
            requested = dict(exercise.get("frame") or {})
            plan = {
                "subject": source.get("subject") or requested.get("subject"),
                "action": source.get("action") or requested.get("action"),
                "object": source.get("object") or requested.get("object"),
                "property": requested.get("property") or "",
                "manner": requested.get("manner") or "",
                "tense": requested.get("tense") or source.get("tense") or "present",
                "negated": bool(requested.get("negated")),
                "required_connector": requested.get("required_connector") or "",
            }
            return self._realize(plan), {"source_parse": parsed, "semantic_plan": plan}
        # Dialogue uses the exact acquired capsule selected before the lesson,
        # not the reference dictionary and not the teacher's answer. Grounded
        # concepts are deliberately allowed here because the workshop is what
        # advances them toward active, conversational use.
        with self._connect() as connection:
            concept = connection.execute(
                """SELECT concept_id,lemma,native_gloss,features_json,relations_json,stage
                   FROM acquired_concepts WHERE concept_id=?""",
                (str(exercise.get("concept_id") or ""),),
            ).fetchone()
        if concept:
            acquired = dict(concept)
            gloss = str(acquired.get("native_gloss") or "").strip()
            if not gloss:
                features = json.loads(acquired.get("features_json") or "[]")
                gloss = ", ".join(str(value) for value in features)
            first_answer = gloss or "I do not yet have a usable acquired meaning."
            follow_up_answer = f"It means {first_answer[0].lower() + first_answer[1:]}"
            return first_answer, {
                "dialogue_turns": [
                    {"question": str(exercise["prompt"]), "answer": first_answer,
                     "concept_id": acquired["concept_id"], "stage": acquired["stage"]},
                    {"question": "What does it mean?", "answer": follow_up_answer,
                     "resolved_reference": acquired["lemma"],
                     "concept_id": acquired["concept_id"]},
                ],
                "answer_source": "acquired_concept_memory",
                "model_used": False,
            }
        session_id = f"workshop:{exercise['exercise_id']}"
        first = self.conversation.ask(str(exercise["prompt"]), session_id=session_id)
        follow_up = self.conversation.ask("What does it mean?", session_id=session_id)
        return str(follow_up["answer"]), {"dialogue_turns": [first, follow_up]}

    def _grade(self, exercise: Mapping[str, Any], answer: str,
               evidence: Mapping[str, Any]) -> tuple[float, bool]:
        family = str(exercise["family"])
        if family in {"native_generation", "paraphrase_transformation"}:
            frame = dict(exercise.get("frame") or {})
            tokens = _tokens(answer)
            required_keys = ["subject", "object"]
            if frame.get("property"):
                required_keys.append("property")
            else:
                required_keys.append("action")
            if frame.get("manner"):
                required_keys.append("manner")
            required = {str(frame.get(key) or "").lower() for key in required_keys}
            required.discard("")
            hits = sum(
                term in tokens or _past(term) in tokens
                or any(token.startswith(term[:max(3, len(term) - 2)]) for token in tokens)
                for term in required
            )
            role_score = hits / max(1, len(required))
            parsed = self.transfer.parse(answer)
            parsed_frame = dict(parsed.get("frame") or {})
            tense_score = float(
                str(parsed_frame.get("tense") or "") == str(frame.get("tense") or "present")
            )
            sentence_score = 1.0 if re.search(r"[.!?]$", answer.strip()) else .5
            negation_score = 1.0 if bool(frame.get("negated")) == bool(
                re.search(r"\b(?:not|never|no)\b", answer.lower())
            ) else 0.0
            connector = _normal(str(frame.get("required_connector") or ""))
            connector_score = float(not connector or connector in _tokens(answer))
            score = round(
                role_score * .50 + tense_score * .15 + negation_score * .15
                + connector_score * .10 + sentence_score * .10, 4,
            )
            correct = (
                score >= .85 and role_score >= .8 and tense_score == 1.0
                and negation_score == 1.0 and connector_score == 1.0
            )
            return score, correct
        expected = _normal(str(exercise.get("expected_answer") or ""))
        actual = _normal(answer)
        if family == "multi_turn_dialogue":
            expected_terms = _tokens(expected)
            score = len(expected_terms & _tokens(actual)) / max(1, len(expected_terms))
            return round(score, 4), score >= .45
        correct = actual == expected
        if not correct and family == "delayed_vocabulary" and " " not in expected:
            # The transfer parser rightly returns the surface word found in
            # the passage ("learned", "allowed", "included").  Delayed recall
            # targets the acquired lemma, so a verified inflection is the same
            # lexical answer—not a failure requiring remediation.
            resolved = self.lexical.resolve_form(actual, "v") if actual else []
            resolved_lemmas = {_normal(str(row.get("lemma") or "")) for row in resolved}
            native_lemma = _normal(self.transfer._verb_lemma(actual)) if actual else ""
            correct = expected in resolved_lemmas or native_lemma == expected
        if not correct and family == "clause_inference" and " " not in expected:
            stem = expected[:max(3, len(expected) - 2)]
            correct = bool(stem and actual.startswith(stem))
        return (1.0 if correct else 0.0), correct

    def run_cycle(self, *, teacher_client: Callable[[str], Mapping[str, Any]] | None = None,
                  limit: int = 5) -> dict[str, Any]:
        with self._connect() as connection:
            cycle_number = int(connection.execute(
                "SELECT COUNT(*) FROM native_language_workshop_cycles"
            ).fetchone()[0])
        requested = max(1, min(20, int(limit)))
        with self._connect() as connection:
            due_count = int(connection.execute(
                "SELECT COUNT(*) FROM native_language_workshop_remediation "
                "WHERE status='due' AND due_epoch<=?", (time.time(),),
            ).fetchone()[0])
        # A correction backlog gets most of the batch, while at least one slot
        # remains available for new connected-language transfer.
        retry_slots = min(
            due_count,
            max(1, requested - max(1, requested // 4)) if due_count else 0,
        )
        due = self._due_candidates(retry_slots)
        seen = {str(row["concept_id"]) for row in due}
        candidates = list(due)
        candidates.extend(
            row for row in self._candidates(requested * 2)
            if str(row["concept_id"]) not in seen
        )
        candidates = candidates[:requested]
        if not candidates:
            return {"status": "awaiting_transfer_ready_concepts", "attempted": 0,
                    "model_used_for_student_answers": False}
        families = [
            str(row.get("remedial_family") or
                FAMILY_SEQUENCE[(cycle_number * len(candidates) + i) % len(FAMILY_SEQUENCE)])
            for i, row in enumerate(candidates)
        ]
        teacher_model, teacher_items = "compiled-native-teacher", []
        if teacher_client:
            try:
                response = dict(teacher_client(self._prompt(candidates, families)))
                teacher_model = str(response.get("model") or "local-qwen")
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(response.get("content") or "").strip(), flags=re.I | re.S)
                payload = json.loads(text)
                teacher_items = list(payload.get("exercises") or [])
            except Exception:
                teacher_items = []
        by_id = {str(item.get("concept_id") or ""): item for item in teacher_items
                 if isinstance(item, Mapping)}
        results, rejected = [], 0
        for index, (concept, family) in enumerate(zip(candidates, families)):
            item = dict(by_id.get(str(concept["concept_id"])) or {})
            verified, problems = self._verify(item, concept, family) if item else (False, ["teacher_omitted"])
            if not verified:
                rejected += int(bool(item))
                item = self._compile(concept, family, cycle_number * len(candidates) + index)
            else:
                item.update({"lemma": concept["lemma"], "teacher_generated": True})
            item["obligation_id"] = str(concept.get("obligation_id") or "")
            exercise_id = _identifier("native_workshop_exercise_", [item, time.time_ns()])
            item["exercise_id"] = exercise_id
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO native_language_workshop_exercises VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exercise_id, family, concept["concept_id"], concept["lemma"],
                     str(item.get("material") or ""), str(item["prompt"]),
                     str(item["expected_answer"]), str(item["answer_reason"]),
                     json.dumps(item.get("frame") or {}), teacher_model,
                     int(bool(item.get("teacher_generated"))), 1, time.time()),
                )
            answer, evidence = self._answer(item)
            score, correct = self._grade(item, answer, evidence)
            attempt_id = _identifier("native_workshop_attempt_", [exercise_id, answer, time.time_ns()])
            feedback = ("Correct connected-language use." if correct else
                        f"Verified correction: {item['expected_answer']}. {item['answer_reason']}")
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO native_language_workshop_attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (attempt_id, exercise_id, concept["concept_id"], family, answer,
                     score, int(correct), feedback, 0, time.time()),
                )
                if item["obligation_id"]:
                    if correct:
                        connection.execute(
                            "UPDATE native_language_workshop_remediation SET status='cleared',cleared_epoch=? WHERE obligation_id=?",
                            (time.time(), item["obligation_id"]),
                        )
                    else:
                        connection.execute(
                            """UPDATE native_language_workshop_remediation
                               SET retry_count=retry_count+1,due_epoch=? WHERE obligation_id=?""",
                            (time.time() + min(
                                86400.0,
                                self.retry_delay_seconds * (2 ** min(
                                    6, int(concept.get("retry_count") or 0) + 1,
                                )),
                            ), item["obligation_id"]),
                        )
                if not correct and not item["obligation_id"]:
                    existing = connection.execute(
                        "SELECT 1 FROM native_language_workshop_remediation WHERE concept_id=? AND family=? AND status='due'",
                        (concept["concept_id"], family),
                    ).fetchone()
                    if not existing:
                        obligation = _identifier("native_workshop_remediation_", [attempt_id, family])
                        connection.execute(
                            """INSERT INTO native_language_workshop_remediation(
                               obligation_id,concept_id,family,expected_answer,answer_reason,
                               status,due_epoch,created_epoch,cleared_epoch,retry_count)
                               VALUES(?,?,?,?,?,?,?,?,NULL,0)""",
                            (obligation, concept["concept_id"], family, item["expected_answer"],
                             item["answer_reason"], "due", time.time() + self.retry_delay_seconds,
                             time.time()),
                        )
            results.append({"lemma": concept["lemma"], "family": family,
                            "correct": correct, "score": score, "answer": answer,
                            "teacher_generated": bool(item.get("teacher_generated")),
                            "remedial_retry": bool(item["obligation_id"]),
                            "model_used": False})
        detail = {"status": "completed", "attempted": len(results),
                  "correct": sum(x["correct"] for x in results), "rejected": rejected,
                  "families": dict(Counter(x["family"] for x in results)),
                  "remedial_retries": sum(x["remedial_retry"] for x in results),
                  "remedial_retries_cleared": sum(
                      x["remedial_retry"] and x["correct"] for x in results
                  ),
                  "due_before_cycle": due_count,
                  "retry_slots": retry_slots,
                  "results": results, "teacher_model": teacher_model,
                  "model_used_for_student_answers": False,
                  "answer_key_withheld_until_after_student_answer": True,
                  "counts_as_mastery": False}
        cycle_id = _identifier("native_workshop_cycle_", [cycle_number, detail, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_language_workshop_cycles VALUES(?,?,?,?,?,?,?)",
                (cycle_id, detail["attempted"], detail["correct"], rejected,
                 teacher_model, json.dumps(detail), time.time()),
            )
        return {"cycle_id": cycle_id, **detail}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            totals = connection.execute(
                "SELECT COUNT(*),COALESCE(SUM(correct),0) FROM native_language_workshop_attempts"
            ).fetchone()
            recent = connection.execute(
                "SELECT COUNT(*),COALESCE(SUM(correct),0) FROM native_language_workshop_attempts WHERE created_epoch>?",
                (time.time() - 3600,),
            ).fetchone()
            families = connection.execute(
                "SELECT family,COUNT(*) attempts,SUM(correct) correct,AVG(score) score FROM native_language_workshop_attempts GROUP BY family"
            ).fetchall()
            recent_families = connection.execute(
                """SELECT family,COUNT(*) attempts,SUM(correct) correct,AVG(score) score
                   FROM native_language_workshop_attempts WHERE created_epoch>?
                   GROUP BY family""", (time.time() - 3600,),
            ).fetchall()
            due = int(connection.execute(
                "SELECT COUNT(*) FROM native_language_workshop_remediation WHERE status='due'"
            ).fetchone()[0])
            cleared = int(connection.execute(
                "SELECT COUNT(*) FROM native_language_workshop_remediation WHERE status='cleared'"
            ).fetchone()[0])
            due_families = connection.execute(
                """SELECT family,COUNT(*) count,MAX(COALESCE(retry_count,0)) max_retries
                   FROM native_language_workshop_remediation WHERE status='due'
                   GROUP BY family"""
            ).fetchall()
            cycles = int(connection.execute(
                "SELECT COUNT(*) FROM native_language_workshop_cycles"
            ).fetchone()[0])
        attempts, correct = int(totals[0] or 0), int(totals[1] or 0)
        return {"cycles": cycles, "attempts": attempts, "correct": correct,
                "accuracy": round(correct / attempts, 4) if attempts else None,
                "recent_accuracy": round(int(recent[1] or 0) / int(recent[0]), 4)
                if int(recent[0]) else None,
                "attempts_last_hour": int(recent[0] or 0),
                "correct_last_hour": int(recent[1] or 0), "remediation_due": due,
                "remediation_cleared": cleared,
                "families": {str(row["family"]): {"attempts": int(row["attempts"]),
                    "correct": int(row["correct"] or 0),
                    "accuracy": round(int(row["correct"] or 0) / int(row["attempts"]), 4),
                    "average_score": round(float(row["score"] or 0), 4)} for row in families},
                "recent_families": {str(row["family"]): {
                    "attempts": int(row["attempts"]),
                    "correct": int(row["correct"] or 0),
                    "accuracy": round(int(row["correct"] or 0) / int(row["attempts"]), 4),
                    "average_score": round(float(row["score"] or 0), 4),
                } for row in recent_families},
                "remediation_due_by_family": {str(row["family"]): {
                    "count": int(row["count"]), "max_retries": int(row["max_retries"] or 0),
                } for row in due_families},
                "allocation": {"clause_inference": .30, "native_generation": .25,
                    "paraphrase_transformation": .20, "multi_turn_dialogue": .15,
                    "delayed_vocabulary": .10},
                "model_used_for_student_answers": False, "counts_as_mastery": False}


__all__ = ["FAMILIES", "FAMILY_SEQUENCE", "NativeLanguageWorkshop"]
