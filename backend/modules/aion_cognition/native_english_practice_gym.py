"""Adaptive, model-free English practice over Aion's acquired concepts.

Activities are learning opportunities, not mastery evidence.  Every prompt has
an answer sealed before Aion sees it.  A wrong answer creates a verified
correction and a delayed, surface-varied retest; a correct retest clears the
obligation.  The separate semantic-transfer academy remains the authority for
contextual/productive promotion.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping

from backend.modules.aion_cognition.native_lexical_intelligence import (
    NativeLexicalIntelligence, _tokens,
)
from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer


FAMILY_SEQUENCE = (
    *("meaning_discrimination",) * 6,
    *("context_completion",) * 5,
    *("sentence_construction",) * 3,
    *("sentence_transformation",) * 2,
    *("reading_comprehension",) * 2,
    "controlled_writing", "native_conversation",
)
FAMILIES = tuple(dict.fromkeys(FAMILY_SEQUENCE))
TRANSFER_READINESS = {
    "meaning_discrimination": 2,
    "context_completion": 2,
    "sentence_construction": 2,
    "sentence_transformation": 1,
    "reading_comprehension": 1,
}
ACTIVITY_MODES = {
    "meaning_discrimination": ("match_up", "quiz", "flash_cards", "group_sort",
                               "find_the_match", "matching_pairs", "anagram"),
    "context_completion": ("complete_the_sentence", "open_the_box"),
    "sentence_construction": ("speaking_cards", "spin_the_wheel"),
    "sentence_transformation": ("unjumble", "quiz"),
    "reading_comprehension": ("quiz", "open_the_box"),
    "controlled_writing": ("speaking_cards",),
    "native_conversation": ("speaking_cards",),
}
NAMES = ("Mireya", "Tavian", "Leona", "Kellan", "Amara", "Neryn", "Zeta", "Owen")
OBJECTS = ("report", "sensor", "message", "sample", "machine", "result", "evidence")
HIGH_UTILITY_LEMMAS = frozenset("""
accept achieve act add agree allow answer appear apply ask become begin believe build
cause change choose compare complete consider contain continue create decide describe
develop differ discover discuss explain fail follow give happen help identify improve
include increase know learn make mean measure move need notice offer plan prevent produce
provide question read reason receive reduce remember require respond result say select show
solve start stop support take teach test think understand use verify want work write
accurate active available basic clear common correct different difficult direct early easy
effective equal false final important likely local main necessary new possible prepared ready
recent reliable safe same simple specific strong true useful wrong
action answer cause condition confidence consequence context contrast evidence example fact
goal idea information language meaning method object person place problem process property
question reason relationship result sentence subject system time value word
""".split())


def _id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _normal(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", str(value or "").lower()).split())


def _past(word: str) -> str:
    if word.endswith("e"):
        return word + "d"
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        return word[:-1] + "ied"
    return word + "ed"


class NativeEnglishPracticeGym:
    """Run adaptive Wordwall-style practice with correction and retesting."""

    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None,
                 retry_delay_seconds: float = 300.0) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.transfer = NativeEnglishTransfer(repo_root=self.repo_root, lexical=self.lexical)
        self.retry_delay_seconds = max(0.01, float(retry_delay_seconds))
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
                CREATE TABLE IF NOT EXISTS native_english_practice_exercises (
                    exercise_id TEXT PRIMARY KEY,
                    concept_id TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    family TEXT NOT NULL,
                    activity_mode TEXT NOT NULL,
                    variant INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    choices_json TEXT NOT NULL,
                    answer_key TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    answer_sealed INTEGER NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS practice_exercise_concept
                    ON native_english_practice_exercises(concept_id,family,created_epoch DESC);
                CREATE TABLE IF NOT EXISTS native_english_practice_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    exercise_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    family TEXT NOT NULL,
                    student_answer TEXT NOT NULL,
                    score REAL NOT NULL,
                    correct INTEGER NOT NULL,
                    reward INTEGER NOT NULL,
                    feedback TEXT NOT NULL,
                    correction_revealed_after_answer INTEGER NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL
                );
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
                CREATE TABLE IF NOT EXISTS native_english_practice_remediation (
                    obligation_id TEXT PRIMARY KEY,
                    concept_id TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    family TEXT NOT NULL,
                    failed_exercise_id TEXT NOT NULL,
                    wrong_answer TEXT NOT NULL,
                    verified_answer TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    due_epoch REAL NOT NULL,
                    created_epoch REAL NOT NULL,
                    cleared_epoch REAL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS practice_one_due_per_target
                    ON native_english_practice_remediation(concept_id,family)
                    WHERE status='due';
                CREATE TABLE IF NOT EXISTS native_english_practice_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    attempted INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    rewards INTEGER NOT NULL,
                    corrections INTEGER NOT NULL,
                    retests INTEGER NOT NULL,
                    retests_passed INTEGER NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _decode(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
        value = dict(row)
        for source, target, fallback in (
            ("features_json", "features", []), ("relations_json", "relations", {}),
            ("examples_json", "examples", []),
        ):
            if source in value:
                try:
                    value[target] = json.loads(value.pop(source) or json.dumps(fallback))
                except json.JSONDecodeError:
                    value[target] = fallback
        return value

    def _concept(self, concept_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM acquired_concepts WHERE concept_id=?", (concept_id,),
            ).fetchone()
        return self._decode(row) if row else None

    def _candidate(self, family: str, *, exclude: set[str]) -> dict[str, Any] | None:
        marks = ",".join("?" for _ in exclude)
        exclusion = f"AND a.concept_id NOT IN ({marks})" if exclude else ""
        params: list[Any] = [family, *sorted(exclude)]
        with self._connect() as connection:
            row = connection.execute(
                f"""SELECT a.*,COALESCE(p.attempts,0) AS gym_attempts,
                           COALESCE(p.correct,0) AS gym_correct
                    FROM acquired_concepts a
                    LEFT JOIN native_english_practice_progress p
                      ON p.concept_id=a.concept_id AND p.family=?
                    WHERE a.stage!='encountered' AND INSTR(a.lemma,' ')=0
                      AND LENGTH(a.lemma) BETWEEN 3 AND 20 {exclusion}
                    ORDER BY COALESCE(p.attempts,0),COALESCE(p.last_attempt_epoch,0),
                             a.updated_epoch,a.concept_id LIMIT 1""",
                tuple(params),
            ).fetchone()
        return self._decode(row) if row else None

    @staticmethod
    def _readiness_summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
        progress = {str(row["family"]): dict(row) for row in rows}
        passed = {
            family: int(progress.get(family, {}).get("correct") or 0) >= required
            for family, required in TRANSFER_READINESS.items()
        }
        return {
            "ready": all(passed.values()),
            "components_passed": sum(passed.values()),
            "components_required": len(TRANSFER_READINESS),
            "passed": passed,
            "progress": progress,
            "attempts": sum(int(row.get("attempts") or 0) for row in progress.values()),
            "last_attempt_epoch": max(
                (float(row.get("last_attempt_epoch") or 0) for row in progress.values()),
                default=0.0,
            ),
        }

    def _readiness(self, concept_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT family,correct,attempts,last_attempt_epoch
                   FROM native_english_practice_progress WHERE concept_id=?""",
                (concept_id,),
            ).fetchall()
        return self._readiness_summary([dict(row) for row in rows])

    def _cohort_candidates(self, limit: int, *, exclude: set[str]) -> list[dict[str, Any]]:
        """Choose a small, nearly-ready cohort instead of touching thousands once."""
        marks = ",".join("?" for _ in exclude)
        exclusion = f"AND a.concept_id NOT IN ({marks})" if exclude else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT a.* FROM acquired_concepts a
                    WHERE a.stage!='encountered' AND INSTR(a.lemma,' ')=0
                      AND LENGTH(a.lemma) BETWEEN 3 AND 20 {exclusion}
                    ORDER BY a.updated_epoch,a.concept_id LIMIT 2000""",
                tuple(sorted(exclude)),
            ).fetchall()
            progress_rows = connection.execute(
                """SELECT concept_id,family,correct,attempts,last_attempt_epoch
                   FROM native_english_practice_progress"""
            ).fetchall()
            # A failed concept waits for its sealed correction and closed-book
            # retry.  Do not quietly present it as fresh practice every cycle
            # while that obligation is cooling down.
            cooling_concepts = {
                str(row["concept_id"]) for row in connection.execute(
                    """SELECT DISTINCT concept_id
                       FROM native_english_practice_remediation
                       WHERE status='due'"""
                ).fetchall()
            }
        progress_by_concept: dict[str, list[dict[str, Any]]] = {}
        for progress_row in progress_rows:
            progress_by_concept.setdefault(str(progress_row["concept_id"]), []).append(
                dict(progress_row)
            )
        ranked: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        for row in rows:
            concept = self._decode(row)
            if str(concept["concept_id"]) in cooling_concepts:
                continue
            readiness = self._readiness_summary(
                progress_by_concept.get(str(concept["concept_id"]), [])
            )
            if readiness["ready"]:
                continue
            concept["practice_readiness"] = readiness
            # Finish partially prepared concepts first. Within the same depth,
            # prefer the least attempted and least recently practised concept.
            lemma = str(concept.get("lemma") or "").lower()
            examples = concept.get("examples") or []
            utility = (
                0 if lemma in HIGH_UTILITY_LEMMAS else 1,
                0 if examples else 1,
                min(len(lemma), 20),
            )
            key = (-readiness["components_passed"], utility, readiness["attempts"],
                   readiness["last_attempt_epoch"], str(concept["concept_id"]))
            ranked.append((key, concept))
        ranked.sort(key=lambda item: item[0])
        return [concept for _, concept in ranked[:max(1, int(limit))]]

    @staticmethod
    def _practice_package(readiness: Mapping[str, Any]) -> list[str]:
        progress = dict(readiness.get("progress") or {})
        package: list[str] = []
        for family, required in TRANSFER_READINESS.items():
            correct = int(progress.get(family, {}).get("correct") or 0)
            package.extend([family] * max(0, required - correct))
        # Once the core frame operations are covered, require productive use
        # and an answer in English before passing the concept to transfer exams.
        package.extend(["controlled_writing", "native_conversation"])
        return package

    def _distractors(self, concept: Mapping[str, Any], limit: int = 3) -> list[str]:
        pos = str(concept.get("part_of_speech") or "")
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT lemma,reference_definition,features_json,relations_json
                   FROM acquired_concepts
                   WHERE concept_id<>? AND lemma<>? AND INSTR(lemma,' ')=0
                     AND (?='' OR part_of_speech=?)
                   ORDER BY ABS(LENGTH(lemma)-?),updated_epoch LIMIT ?""",
                (concept["concept_id"], concept["lemma"], pos, pos,
                 len(str(concept["lemma"])), max(24, limit * 12)),
            ).fetchall()
        cue_tokens = _tokens(self._cue(concept))
        target_relations = {
            _normal(str(value))
            for values in (concept.get("relations") or {}).values()
            for value in values
        }
        ranked: list[tuple[tuple[int, float, int, str], str]] = []
        for row in rows:
            material = str(row["reference_definition"] or "")
            try:
                material += " " + " ".join(json.loads(row["features_json"] or "[]"))
                relations = json.loads(row["relations_json"] or "{}")
                material += " " + " ".join(
                    str(value) for values in relations.values() for value in values
                )
            except (TypeError, json.JSONDecodeError):
                pass
            overlap = len(cue_tokens & _tokens(material)) / max(1, len(cue_tokens))
            lemma = str(row["lemma"])
            # A synonym is not a distractor: it makes the question genuinely
            # multi-answer.  Likewise, reject candidates whose acquired sense
            # matches almost as much of the cue as the intended concept.  Rank
            # moderate semantic neighbours first, then unrelated fallbacks.
            if _normal(lemma) in target_relations or overlap >= .45:
                continue
            band = 0 if .08 <= overlap < .45 else 1
            ranked.append(((band, -overlap,
                            abs(len(lemma) - len(str(concept["lemma"]))), lemma), lemma))
        ranked.sort(key=lambda item: item[0])
        return list(dict.fromkeys(lemma for _, lemma in ranked))[:limit]

    @staticmethod
    def _cue(concept: Mapping[str, Any]) -> str:
        features = [str(x) for x in concept.get("features") or []]
        if features:
            return ", ".join(features[:5])
        definition = str(concept.get("reference_definition") or "")
        return definition or str(concept.get("native_gloss") or "")

    def _build(self, concept: Mapping[str, Any], family: str, variant: int,
               *, obligation_id: str = "") -> dict[str, Any]:
        lemma = str(concept["lemma"])
        pos = str(concept.get("part_of_speech") or "")
        cue = self._cue(concept)
        name = NAMES[variant % len(NAMES)]
        obj = OBJECTS[(variant * 3) % len(OBJECTS)]
        modes = ACTIVITY_MODES[family]
        mode = modes[variant % len(modes)]
        distractors = self._distractors(concept)
        choices: list[str] = []
        metadata: dict[str, Any] = {
            "target_pos": pos, "semantic_cue": cue, "obligation_id": obligation_id,
            "counts_as_mastery": False,
        }
        explanation = f"'{lemma}' is linked in Aion's acquired memory with {cue}."

        if family == "meaning_discrimination":
            if mode == "anagram":
                scrambled = "".join(sorted(lemma, reverse=bool(variant % 2)))
                if scrambled == lemma:
                    scrambled = lemma[::-1]
                prompt = f"Unscramble the acquired word '{scrambled}' using its meaning: {cue}."
                answer = lemma
                choices = [lemma, *distractors]
            elif mode == "group_sort":
                prompt = f"Which grammatical group contains '{lemma}'?"
                answer = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective",
                          "r": "adverb"}.get(pos, "word")
                choices = ["noun", "verb", "adjective", "adverb", "word"]
                explanation = f"The acquired capsule records '{lemma}' as a {answer}."
            else:
                prompt = f"Which acquired word best matches this meaning: {cue}?"
                answer = lemma
                choices = [lemma, *distractors]
        elif family == "context_completion":
            if pos == "v":
                prompt = f"Complete the sentence with the word whose action is associated with {cue}: {name} will _____ the {obj}."
            elif pos in {"a", "s"}:
                prompt = f"Complete the sentence with the property associated with {cue}: The {obj} was _____."
            elif pos == "r":
                prompt = f"Complete the sentence with the manner associated with {cue}: {name} worked _____."
            else:
                prompt = f"Complete the sentence with the thing associated with {cue}: {name} inspected the _____."
            answer = lemma
            choices = [lemma, *distractors]
        elif family == "sentence_construction":
            prompt = f"Construct one grammatical sentence using '{lemma}' with its acquired meaning: {cue}."
            answer = self._construct_sentence(lemma, pos, name, obj)
            metadata["rubric"] = {
                "required_lemma": lemma, "required_surface": _past(lemma) if pos == "v" else lemma,
                "minimum_sentences": 1,
            }
        elif family == "sentence_transformation":
            if pos == "v":
                surface = _past(lemma)
                prompt = f"Make this sentence negative without changing its past time: {name} {surface} the {obj}."
                answer = f"{name} did not {lemma} the {obj}."
                explanation = "Past negation uses 'did not' followed by the base verb."
            else:
                answer = self._construct_sentence(lemma, pos, name, obj)
                pieces = re.findall(r"[A-Za-z']+|[.!?]", answer)
                prompt = "Unjumble every token into a grammatical sentence: " + " / ".join(reversed(pieces))
                metadata["tokens"] = pieces
                explanation = "The semantic roles determine subject, action, object and property order."
        elif family == "reading_comprehension":
            material = self._construct_sentence(lemma, pos, name, obj)
            if pos == "v":
                prompt = f"Read: {material}\nQuestion: What action did {name} perform?"
                answer = lemma
            elif pos in {"a", "s"}:
                prompt = f"Read: {material}\nQuestion: Which property described the {obj}?"
                answer = lemma
            elif pos == "r":
                prompt = f"Read: {material}\nQuestion: How did {name} work?"
                answer = lemma
            else:
                prompt = f"Read: {material}\nQuestion: What did {name} inspect?"
                answer = lemma
            choices = [answer, *distractors]
        elif family == "controlled_writing":
            prompt = f"Write two connected sentences explaining '{lemma}'. Use its acquired meaning ({cue}) and include 'because'."
            first = self._construct_sentence(lemma, pos, name, obj)
            answer = f"{first} This use is appropriate because {cue}."
            metadata["rubric"] = {
                "required_lemma": lemma, "required_surface": _past(lemma) if pos == "v" else lemma,
                "minimum_sentences": 2,
                "required_connector": "because",
            }
        else:
            prompt = f"Answer in English: What does '{lemma}' mean, and how could it be used?"
            example = self._construct_sentence(lemma, pos, name, obj)
            answer = f"{concept.get('native_gloss') or cue}. For example, {example}"
            metadata["rubric"] = {
                "required_lemma": lemma, "required_surface": _past(lemma) if pos == "v" else lemma,
                "minimum_feature_overlap": 0.4,
                "minimum_sentences": 2,
            }
        # Do not leak the answer through a fixed first-choice position.
        choices = list(dict.fromkeys(choices))
        if choices:
            offset = variant % len(choices)
            choices = choices[offset:] + choices[:offset]
        return {
            "concept_id": str(concept["concept_id"]), "lemma": lemma,
            "family": family, "activity_mode": mode, "variant": variant,
            "prompt": prompt, "choices": choices,
            "answer_key": answer, "explanation": explanation, "metadata": metadata,
        }

    @staticmethod
    def _construct_sentence(lemma: str, pos: str, name: str, obj: str) -> str:
        if pos == "v":
            return f"{name} {_past(lemma)} the {obj}."
        if pos in {"a", "s"}:
            return f"The {obj} was {lemma}."
        if pos == "r":
            return f"{name} worked {lemma}."
        return f"{name} inspected the {lemma}."

    def _store_exercise(self, built: Mapping[str, Any]) -> dict[str, Any]:
        exercise_id = _id("native_practice_exercise_", [built, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_practice_exercises VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (exercise_id, built["concept_id"], built["lemma"], built["family"],
                 built["activity_mode"], built["variant"], built["prompt"],
                 json.dumps(built["choices"]), built["answer_key"], built["explanation"],
                 json.dumps(built["metadata"]), 1, time.time()),
            )
        return {"exercise_id": exercise_id, **dict(built)}

    def _memory_match(self, prompt: str, choices: list[str], semantic_cue: str = "") -> str:
        # Score the supplied meaning, not scaffolding words such as "manner",
        # "sentence" or "associated" that appear in every exercise family.
        prompt_tokens = _tokens(semantic_cue) if semantic_cue else _tokens(prompt)
        best = (float("-inf"), choices[0] if choices else "")
        with self._connect() as connection:
            for choice in choices:
                rows = connection.execute(
                    """SELECT reference_definition,features_json,relations_json,part_of_speech
                       FROM acquired_concepts WHERE lemma=? ORDER BY updated_epoch DESC""",
                    (str(choice).strip().lower(),),
                ).fetchall()
                if not rows:
                    continue
                # Polysemous words can own several acquired capsules.  Score
                # every sense and use the best contextual fit instead of the
                # most recently updated (which is arbitrary for words such as
                # "day", "place" and "person").
                score = 0.0
                for row in rows:
                    material = str(row["reference_definition"])
                    material += " " + " ".join(json.loads(row["features_json"] or "[]"))
                    relations = json.loads(row["relations_json"] or "{}")
                    material += " " + " ".join(
                        x for values in relations.values() for x in values
                    )
                    overlap = len(prompt_tokens & _tokens(material))
                    score = max(score, overlap / max(1, len(prompt_tokens)))
                if score > best[0]:
                    best = (score, choice)
        return best[1]

    def _student_answer(self, exercise: Mapping[str, Any]) -> str:
        """Answer from acquired memory and native rules; never inspect answer_key."""
        prompt = str(exercise["prompt"])
        family = str(exercise["family"])
        choices = list(exercise.get("choices") or [])
        metadata = dict(exercise.get("metadata") or {})
        if family == "reading_comprehension":
            match = re.search(r"Read:\s*(.+?)\s*\nQuestion:\s*(.+)$", prompt, re.S)
            if not match:
                return ""
            material, question = match.group(1).strip(), match.group(2).strip()
            parsed = self.transfer.parse(material)
            frame = dict(parsed.get("frame") or {})
            lowered = question.lower()
            if "action" in lowered:
                return str(frame.get("action") or "")
            if "property" in lowered:
                clauses = list(parsed.get("clauses") or [])
                value = next((row.get("complement") for row in clauses
                              if row.get("complement")), None)
                return str(value or exercise.get("lemma") or "")
            if lowered.startswith("how did"):
                material_tokens = list(_tokens(material))
                with self._connect() as connection:
                    for token in material_tokens:
                        row = connection.execute(
                            """SELECT lemma FROM acquired_concepts
                               WHERE lemma=? AND part_of_speech='r' LIMIT 1""",
                            (token,),
                        ).fetchone()
                        if row:
                            return str(row["lemma"])
                return ""
            if lowered.startswith("what did"):
                return str(frame.get("object") or "")
            return str(self.transfer.answer(
                material, question, str(exercise.get("concept_id") or ""),
            )["answer"])
        if family in {"meaning_discrimination", "context_completion"}:
            if "grammatical group" in prompt:
                match = re.search(r"'([^']+)'", prompt)
                concept = self._concept_by_lemma(match.group(1)) if match else None
                pos = str((concept or {}).get("part_of_speech") or "")
                return {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective",
                        "r": "adverb"}.get(pos, "word")
            return self._memory_match(
                prompt, choices, str(metadata.get("semantic_cue") or ""),
            )
        target = re.search(r"'([^']+)'", prompt)
        lemma = target.group(1) if target else ""
        concept = self._concept_by_lemma(lemma)
        pos = str((concept or {}).get("part_of_speech") or "")
        variant = int(exercise.get("variant") or 0)
        name = NAMES[variant % len(NAMES)]
        obj = OBJECTS[(variant * 3) % len(OBJECTS)]
        if family == "sentence_construction":
            return self._construct_sentence(lemma, pos, name, obj)
        if family == "sentence_transformation":
            negation = re.search(
                r"Make this sentence negative.*?: ([A-Z][a-z]+) (\w+) the (\w+)", prompt,
            )
            if negation:
                surface = negation.group(2).lower()
                with self._connect() as connection:
                    row = connection.execute(
                        "SELECT lemma FROM morphology_forms WHERE surface=? AND feature LIKE '%past%' LIMIT 1",
                        (surface,),
                    ).fetchone()
                base = str(row["lemma"]) if row else (
                    surface[:-3] + "y" if surface.endswith("ied") else
                    surface[:-1] if surface.endswith("ed") and surface[:-1].endswith("e") else
                    surface[:-2] if surface.endswith("ed") else surface
                )
                return f"{negation.group(1)} did not {base} the {negation.group(3)}."
            tokens = re.findall(r"Unjumble.*?: (.*)", prompt)
            if tokens:
                supplied = [x.strip() for x in tokens[0].split("/")]
                return " ".join(reversed(supplied)).replace(" .", ".")
        if family == "controlled_writing":
            cue = self._cue(concept or {})
            return f"{self._construct_sentence(lemma, pos, name, obj)} This use is appropriate because {cue}."
        if family == "native_conversation":
            cue = self._cue(concept or {})
            return f"{(concept or {}).get('native_gloss') or cue}. For example, {self._construct_sentence(lemma, pos, name, obj)}"
        return self._memory_match(
            prompt, choices, str(metadata.get("semantic_cue") or ""),
        )

    def _concept_by_lemma(self, lemma: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM acquired_concepts WHERE lemma=? ORDER BY updated_epoch DESC LIMIT 1",
                (str(lemma).strip().lower(),),
            ).fetchone()
        return self._decode(row) if row else None

    @staticmethod
    def _grade(exercise: Mapping[str, Any], answer: str) -> tuple[float, bool]:
        family = str(exercise["family"])
        expected = str(exercise["answer_key"])
        metadata = dict(exercise.get("metadata") or {})
        if family in {"sentence_construction", "controlled_writing", "native_conversation"}:
            rubric = dict(metadata.get("rubric") or {})
            lemma = _normal(str(rubric.get("required_lemma") or ""))
            surface = _normal(str(rubric.get("required_surface") or lemma))
            tokens = _tokens(answer)
            lemma_tokens = _tokens(lemma)
            surface_tokens = _tokens(surface)
            normal_answer = _normal(answer)
            target = float(bool(
                lemma and (
                    lemma_tokens <= tokens or surface_tokens <= tokens
                    or lemma in normal_answer or surface in normal_answer
                )
            ))
            sentences = len(re.findall(r"[.!?](?:\s|$)", answer.strip()))
            sentence_score = min(1.0, sentences / max(1, int(rubric.get("minimum_sentences") or 1)))
            connector = str(rubric.get("required_connector") or "")
            connector_score = 1.0 if not connector or connector in tokens else 0.0
            score = round((target * .5) + (sentence_score * .3) + (connector_score * .2), 4)
            return score, score >= .8
        correct = _normal(answer) == _normal(expected)
        return (1.0 if correct else 0.0), correct

    def _due_obligations(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT * FROM native_english_practice_remediation
                   WHERE status='due' AND due_epoch<=? ORDER BY due_epoch LIMIT ?""",
                (time.time(), max(0, int(limit))),
            ).fetchall()]

    def _attempt(self, exercise: Mapping[str, Any]) -> dict[str, Any]:
        student_view = {key: exercise[key] for key in (
            "exercise_id", "concept_id", "lemma", "family", "activity_mode", "variant",
            "prompt", "choices", "metadata",
        )}
        answer = self._student_answer(student_view)
        score, correct = self._grade(exercise, answer)
        metadata = dict(exercise.get("metadata") or {})
        obligation_id = str(metadata.get("obligation_id") or "")
        reward = 2 if correct and obligation_id else 1 if correct else 0
        feedback = (f"Correct. {exercise['explanation']}" if correct else
                    f"Not yet. The verified answer is '{exercise['answer_key']}'. {exercise['explanation']}")
        now = time.time()
        attempt_id = _id("native_practice_attempt_", [exercise["exercise_id"], answer, now])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_practice_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (attempt_id, exercise["exercise_id"], exercise["concept_id"], exercise["family"],
                 answer, score, int(correct), reward, feedback, int(not correct), 0, now),
            )
            connection.execute(
                """INSERT INTO native_english_practice_progress(
                   concept_id,family,attempts,correct,rewards,corrections,retests_passed,
                   consecutive_passes,last_attempt_epoch,next_due_epoch)
                   VALUES(?,?,1,?,?,?, ?,?,?,?)
                   ON CONFLICT(concept_id,family) DO UPDATE SET
                   attempts=attempts+1,correct=correct+excluded.correct,
                   rewards=rewards+excluded.rewards,
                   corrections=corrections+excluded.corrections,
                   retests_passed=retests_passed+excluded.retests_passed,
                   consecutive_passes=CASE WHEN excluded.correct=1
                     THEN consecutive_passes+1 ELSE 0 END,
                   last_attempt_epoch=excluded.last_attempt_epoch,
                   next_due_epoch=excluded.next_due_epoch""",
                (exercise["concept_id"], exercise["family"], int(correct), reward,
                 int(not correct), int(correct and bool(obligation_id)),
                 int(correct), now, now + (86400 if correct else self.retry_delay_seconds)),
            )
            if obligation_id:
                if correct:
                    connection.execute(
                        "UPDATE native_english_practice_remediation SET status='cleared',cleared_epoch=? WHERE obligation_id=?",
                        (now, obligation_id),
                    )
                else:
                    connection.execute(
                        """UPDATE native_english_practice_remediation SET retry_count=retry_count+1,
                           wrong_answer=?,due_epoch=? WHERE obligation_id=?""",
                        (answer, now + min(3600, self.retry_delay_seconds * 2), obligation_id),
                    )
            elif not correct:
                existing = connection.execute(
                    """SELECT obligation_id FROM native_english_practice_remediation
                       WHERE concept_id=? AND family=? AND status='due'""",
                    (exercise["concept_id"], exercise["family"]),
                ).fetchone()
                if not existing:
                    new_id = _id("native_practice_remediation_", [attempt_id, exercise["concept_id"]])
                    connection.execute(
                        "INSERT INTO native_english_practice_remediation VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                        (new_id, exercise["concept_id"], exercise["lemma"], exercise["family"],
                         exercise["exercise_id"], answer, exercise["answer_key"],
                         exercise["explanation"], "due", 0,
                         now + self.retry_delay_seconds, now),
                    )
        return {
            "attempt_id": attempt_id, "exercise_id": exercise["exercise_id"],
            "concept_id": exercise["concept_id"], "lemma": exercise["lemma"],
            "family": exercise["family"],
            "activity_mode": exercise["activity_mode"], "answer": answer,
            "correct": correct, "score": score, "reward": reward,
            "feedback": feedback, "remedial_retry": bool(obligation_id),
            "correction_revealed_after_answer": not correct,
            "counts_as_mastery": False, "model_used": False,
        }

    def run_cycle(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(100, int(limit)))
        with self._connect() as connection:
            cycle_number = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_practice_cycles"
            ).fetchone()[0])
        results: list[dict[str, Any]] = []
        used: set[str] = set()
        with self._connect() as connection:
            due_count = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_practice_remediation "
                "WHERE status='due' AND due_epoch<=?", (time.time(),),
            ).fetchone()[0])
        # Drain a backlog instead of allowing new material to create failures
        # faster than old corrections can be verified. Preserve at least one
        # quarter of the batch for varied new practice.
        retry_slots = min(due_count, max(1, (limit * 3) // 4) if due_count else 0)
        obligations = self._due_obligations(retry_slots)
        scheduled_pairs: Counter[tuple[str, str]] = Counter()
        for obligation in obligations:
            concept = self._concept(str(obligation["concept_id"]))
            if not concept:
                continue
            built = self._build(
                concept, str(obligation["family"]), int(obligation["retry_count"]) + 101,
                obligation_id=str(obligation["obligation_id"]),
            )
            results.append(self._attempt(self._store_exercise(built)))
            used.add(str(concept["concept_id"]))
            scheduled_pairs[(str(concept["concept_id"]), str(obligation["family"]))] += 1
            if len(results) >= limit:
                break
        # Each concept/family receives only its required number of varied
        # attempts in a cycle. A failure creates a delayed obligation; it is
        # never hammered repeatedly just to fill the current batch.
        while len(results) < limit:
            remaining = limit - len(results)
            cohort = self._cohort_candidates(max(1, min(4, remaining)), exclude=used)
            if not cohort:
                break
            made_progress = False
            for concept in cohort:
                concept_id = str(concept["concept_id"])
                readiness = self._readiness(concept_id)
                for family in self._practice_package(readiness):
                    pair = (concept_id, family)
                    per_cycle_cap = int(TRANSFER_READINESS.get(family, 1))
                    if scheduled_pairs[pair] >= per_cycle_cap or len(results) >= limit:
                        continue
                    with self._connect() as connection:
                        prior_variants = int(connection.execute(
                            "SELECT COUNT(*) FROM native_english_practice_exercises "
                            "WHERE concept_id=? AND family=?", pair,
                        ).fetchone()[0])
                    variant = (cycle_number * limit) + len(results) + prior_variants
                    results.append(self._attempt(self._store_exercise(
                        self._build(concept, family, variant),
                    )))
                    scheduled_pairs[pair] += 1
                    made_progress = True
                used.add(concept_id)
            if not made_progress:
                break
        correct = sum(row["correct"] for row in results)
        rewards = sum(int(row["reward"]) for row in results)
        corrections = sum(not row["correct"] for row in results)
        retests = sum(row["remedial_retry"] for row in results)
        retests_passed = sum(row["remedial_retry"] and row["correct"] for row in results)
        detail = {
            "status": "completed", "attempted": len(results), "correct": correct,
            "rewards": rewards, "corrections": corrections, "retests": retests,
            "retests_passed": retests_passed,
            "due_before_cycle": due_count,
            "repeat_cap_per_concept_family": dict(TRANSFER_READINESS),
            "families": dict(Counter(row["family"] for row in results)),
            "activities": dict(Counter(row["activity_mode"] for row in results)),
            "results": results, "model_used_for_student_answers": False,
            "counts_as_mastery": False,
        }
        cycle_id = _id("native_practice_cycle_", [cycle_number, detail, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_practice_cycles VALUES(?,?,?,?,?,?,?,?,?)",
                (cycle_id, len(results), correct, rewards, corrections, retests,
                 retests_passed, json.dumps(detail), time.time()),
            )
        return {"cycle_id": cycle_id, **detail}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            totals = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(correct),0),COALESCE(SUM(reward),0)
                   FROM native_english_practice_attempts"""
            ).fetchone()
            due = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_practice_remediation WHERE status='due'"
            ).fetchone()[0])
            cleared = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_practice_remediation WHERE status='cleared'"
            ).fetchone()[0])
            recent = connection.execute(
                """SELECT COUNT(*),COALESCE(SUM(correct),0)
                   FROM native_english_practice_attempts WHERE created_epoch>?""",
                (time.time() - 3600,),
            ).fetchone()
            family_rows = connection.execute(
                """SELECT family,COUNT(*) attempts,SUM(correct) correct,SUM(reward) rewards
                   FROM native_english_practice_attempts GROUP BY family"""
            ).fetchall()
            recent_family_rows = connection.execute(
                """SELECT family,COUNT(*) attempts,SUM(correct) correct
                   FROM native_english_practice_attempts WHERE created_epoch>?
                   GROUP BY family""", (time.time() - 3600,),
            ).fetchall()
            due_family_rows = connection.execute(
                """SELECT family,COUNT(*) count FROM native_english_practice_remediation
                   WHERE status='due' GROUP BY family"""
            ).fetchall()
            activity_rows = connection.execute(
                "SELECT activity_mode,COUNT(*) count FROM native_english_practice_exercises GROUP BY activity_mode"
            ).fetchall()
            cycles = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_practice_cycles"
            ).fetchone()[0])
            readiness_rows = connection.execute(
                """SELECT concept_id,
                   SUM(CASE WHEN family='meaning_discrimination' AND correct>=2 THEN 1 ELSE 0 END)+
                   SUM(CASE WHEN family='context_completion' AND correct>=2 THEN 1 ELSE 0 END)+
                   SUM(CASE WHEN family='sentence_construction' AND correct>=2 THEN 1 ELSE 0 END)+
                   SUM(CASE WHEN family='sentence_transformation' AND correct>=1 THEN 1 ELSE 0 END)+
                   SUM(CASE WHEN family='reading_comprehension' AND correct>=1 THEN 1 ELSE 0 END) components
                   FROM native_english_practice_progress GROUP BY concept_id"""
            ).fetchall()
        attempts = int(totals[0] or 0)
        correct = int(totals[1] or 0)
        return {
            "cycles": cycles, "attempts": attempts, "correct": correct,
            "accuracy": round(correct / attempts, 4) if attempts else None,
            "recent_accuracy": round(int(recent[1] or 0) / int(recent[0]), 4)
            if int(recent[0]) else None,
            "rewards": int(totals[2] or 0), "corrections_due": due,
            "corrections_cleared": cleared, "attempts_last_hour": int(recent[0] or 0),
            "correct_last_hour": int(recent[1] or 0),
            "families": {str(row["family"]): {
                "attempts": int(row["attempts"]), "correct": int(row["correct"] or 0),
                "accuracy": round(int(row["correct"] or 0) / int(row["attempts"]), 4),
                "rewards": int(row["rewards"] or 0),
            } for row in family_rows},
            "recent_families": {str(row["family"]): {
                "attempts": int(row["attempts"]), "correct": int(row["correct"] or 0),
                "accuracy": round(int(row["correct"] or 0) / int(row["attempts"]), 4),
            } for row in recent_family_rows},
            "corrections_due_by_family": {
                str(row["family"]): int(row["count"]) for row in due_family_rows
            },
            "activities": {str(row["activity_mode"]): int(row["count"])
                           for row in activity_rows},
            "transfer_ready_concepts": sum(int(row["components"] or 0) >= 5
                                             for row in readiness_rows),
            "nearly_transfer_ready_concepts": sum(int(row["components"] or 0) == 4
                                                    for row in readiness_rows),
            "readiness_requirements": dict(TRANSFER_READINESS),
            "model_used_for_student_answers": False,
            "counts_as_mastery": False,
        }


__all__ = ["ACTIVITY_MODES", "FAMILIES", "TRANSFER_READINESS", "NativeEnglishPracticeGym"]
