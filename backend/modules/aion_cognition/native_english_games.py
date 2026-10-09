"""Interactive, model-free English games with verified corrective learning."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
import time
from typing import Any, Mapping

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


FAMILIES = (
    "sentence_unscramble", "missing_word", "tense_transform",
    "negation_transform", "sentence_comprehension", "grammar_repair",
)
NAMES = ("Mira", "Jonah", "Leila", "Owen", "Nora", "Felix", "Ava", "Ravi")
NOUNS = ("person", "robot", "scientist", "teacher", "engineer", "student")
OBJECTS = ("result", "answer", "report", "machine", "sample", "message")
PLACES = ("laboratory", "office", "workshop", "library", "garden", "station")
VERBS = (
    ("calculate", "calculated", "calculates"),
    ("inspect", "inspected", "inspects"),
    ("repair", "repaired", "repairs"),
    ("carry", "carried", "carries"),
    ("open", "opened", "opens"),
    ("verify", "verified", "verifies"),
)
PROPERTIES = ("correct", "calm", "ready", "safe", "clear", "reliable")
VERB_CONTEXTS = {
    "calculate": ("To find the total", "the numbers"),
    "inspect": ("To check for damage", "the sample"),
    "repair": ("To make it work again", "the machine"),
    "carry": ("To move it by hand", "the parcel"),
    "open": ("To enter the room", "the door"),
    "verify": ("To confirm it is correct", "the answer"),
}


def _id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _normal(value: str) -> str:
    text = re.sub(r"[^a-z0-9' ]+", " ", str(value or "").lower())
    return " ".join(text.split())


def _sentence(value: str) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return text
    return text[0].upper() + text[1:] + ("" if text[-1] in ".?!" else ".")


class NativeEnglishGames:
    """Generate games, run Aion's native attempt, grade, explain and remediate."""

    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
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
                CREATE TABLE IF NOT EXISTS native_english_games (
                    game_id TEXT PRIMARY KEY,
                    family TEXT NOT NULL,
                    difficulty INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    choices_json TEXT NOT NULL,
                    answer_key TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    rule_tag TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_english_game_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    player TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    FOREIGN KEY(game_id) REFERENCES native_english_games(game_id)
                );
                CREATE TABLE IF NOT EXISTS native_english_game_corrections (
                    correction_id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    wrong_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    rule_tag TEXT NOT NULL,
                    source TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    created_epoch REAL NOT NULL,
                    FOREIGN KEY(game_id) REFERENCES native_english_games(game_id)
                );
                CREATE TABLE IF NOT EXISTS native_english_remediation (
                    rule_tag TEXT PRIMARY KEY,
                    family TEXT NOT NULL,
                    failures INTEGER NOT NULL DEFAULT 0,
                    successful_retries INTEGER NOT NULL DEFAULT 0,
                    last_reason TEXT NOT NULL,
                    next_due_epoch REAL NOT NULL,
                    updated_epoch REAL NOT NULL
                );
                """
            )

    def _counter(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM native_english_games").fetchone()[0])

    def _build(self, family: str, difficulty: int, index: int) -> dict[str, Any]:
        family = family if family in FAMILIES else FAMILIES[index % len(FAMILIES)]
        difficulty = min(5, max(1, int(difficulty)))
        rng = random.Random(index * 7919 + difficulty * 101 + FAMILIES.index(family))
        name = NAMES[index % len(NAMES)]
        noun = NOUNS[(index + difficulty) % len(NOUNS)]
        obj = OBJECTS[(index * 3 + difficulty) % len(OBJECTS)]
        place = PLACES[(index * 5 + difficulty) % len(PLACES)]
        base, past, present = VERBS[(index * 7 + difficulty) % len(VERBS)]
        prop = PROPERTIES[(index * 2 + difficulty) % len(PROPERTIES)]
        choices: list[str] = []
        metadata: dict[str, Any] = {"sealed_answer": True}

        if family == "sentence_unscramble":
            if difficulty == 1:
                answer = f"The {noun} is {prop}."
            elif difficulty == 2:
                answer = f"{name} {past} the {obj}."
            elif difficulty == 3:
                answer = f"The {noun} will {base} the {obj}."
            elif difficulty == 4:
                answer = f"The {noun} did not {base} the {obj}."
            else:
                answer = f"Before lunch, {name} {past} the {obj} in the {place}."
            tokens = re.findall(r"[A-Za-z']+|[,?.!]", answer)
            shuffled = tokens[:]
            while shuffled == tokens:
                rng.shuffle(shuffled)
            prompt = "Put these tokens into a grammatical sentence."
            choices = shuffled
            explanation = "English normally orders the subject before the verb and the object after it; auxiliaries and negation remain with the verb phrase."
            rule = f"word_order_d{difficulty}"
            metadata.update({"tokens": shuffled, "answer_tokens": tokens})
        elif family == "missing_word":
            answer = base
            clue, target = VERB_CONTEXTS[base]
            prompt = f"Choose the missing word: {clue}, the {noun} will _____ {target}."
            distractors = [row[0] for row in VERBS if row[0] != base]
            choices = [answer, *rng.sample(distractors, 3)]
            rng.shuffle(choices)
            explanation = "After the modal verb 'will', English uses the base form of the verb."
            rule = "modal_plus_base_verb"
        elif family == "tense_transform":
            answer = f"{name} {past} the {obj}."
            prompt = f"Change this sentence to the past tense: {name} will {base} the {obj}."
            choices = [answer, f"{name} {present} the {obj}.", f"{name} did {past} the {obj}.",
                       f"{name} will {past} the {obj}."]
            rng.shuffle(choices)
            explanation = f"The past-tense form of '{base}' is '{past}'; the future auxiliary 'will' is removed."
            rule = f"past_tense:{base}"
        elif family == "negation_transform":
            answer = f"{name} did not {base} the {obj}."
            prompt = f"Make this past-tense sentence negative: {name} {past} the {obj}."
            choices = [answer, f"{name} not {past} the {obj}.", f"{name} did not {past} the {obj}.",
                       f"{name} does not {base} the {obj}."]
            rng.shuffle(choices)
            explanation = "Past-tense negation uses 'did not' followed by the base verb, not the past verb."
            rule = "past_negation_did_not_base"
        elif family == "sentence_comprehension":
            prompt = (f"Read: Before lunch, {name} {past} the {obj} in the {place}.\n"
                      "Question: Where did the action happen?")
            answer = f"in the {place}"
            choices = [answer, "before lunch", f"the {obj}", name]
            rng.shuffle(choices)
            explanation = f"The phrase 'in the {place}' expresses location; 'before lunch' expresses time."
            rule = "semantic_role:location"
        else:
            answer = f"Yesterday {name} {past} the {obj}."
            prompt = f"Repair the grammar: Yesterday {name} {base} the {obj}."
            choices = [answer, f"Yesterday {name} {present} the {obj}.",
                       f"Yesterday {name} did {past} the {obj}.", f"Yesterday {name} will {base} the {obj}."]
            rng.shuffle(choices)
            explanation = "'Yesterday' places the event in the past, so the main verb needs its past-tense form."
            rule = f"time_marker_past:{base}"
        return {"family": family, "difficulty": difficulty, "prompt": prompt,
                "choices": choices, "answer": answer, "explanation": explanation,
                "rule_tag": rule, "metadata": metadata}

    def new_game(self, *, family: str = "mixed", difficulty: int = 1) -> dict[str, Any]:
        index = self._counter()
        built = self._build(family, difficulty, index)
        game_id = _id("native_english_game_", [built, index, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_games VALUES(?,?,?,?,?,?,?,?,?,?)",
                (game_id, built["family"], built["difficulty"], built["prompt"],
                 json.dumps(built["choices"]), built["answer"], built["explanation"],
                 built["rule_tag"], json.dumps(built["metadata"]), time.time()),
            )
        return {"game_id": game_id, "family": built["family"],
                "difficulty": built["difficulty"], "prompt": built["prompt"],
                "choices": built["choices"], "response_mode": (
                    "token_order" if built["family"] == "sentence_unscramble" else "selected"
                ), "answer_withheld": True}

    def _game(self, game_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM native_english_games WHERE game_id=?", (game_id,),
            ).fetchone()
        if not row:
            return None
        value = dict(row)
        value["choices"] = json.loads(value.pop("choices_json"))
        value["metadata"] = json.loads(value.pop("metadata_json"))
        return value

    def _aion_answer(self, game: Mapping[str, Any]) -> str:
        """Student route sees prompt/choices and learned corrections, never answer_key."""
        with self._connect() as connection:
            learned = connection.execute(
                "SELECT correct_answer FROM native_english_game_corrections "
                "WHERE game_id=? AND verified=1 ORDER BY created_epoch DESC LIMIT 1",
                (game["game_id"],),
            ).fetchone()
        if learned:
            return str(learned["correct_answer"])
        prompt, family = str(game["prompt"]), str(game["family"])
        choices = [str(item) for item in game["choices"]]
        if family == "sentence_unscramble":
            words = choices
            punctuation = next((x for x in words if x in {".", "?", "!"}), ".")
            comma = "," in words
            clean = [x for x in words if x not in {".", "?", "!", ","}]
            lower = {x.lower(): x for x in clean}
            name = next((x for x in clean if x in NAMES), "")
            noun = next((x for x in clean if x.lower() in NOUNS), "")
            obj = next((x for x in clean if x.lower() in OBJECTS), "")
            place = next((x for x in clean if x.lower() in PLACES), "")
            prop = next((x for x in clean if x.lower() in PROPERTIES), "")
            base = next((x for x in clean if x.lower() in {row[0] for row in VERBS}), "")
            past = next((x for x in clean if x.lower() in {row[1] for row in VERBS}), "")
            if "before" in lower and "lunch" in lower and all((name, past, obj, place)):
                text = f"Before lunch, {name} {past.lower()} the {obj.lower()} in the {place.lower()}"
            elif "is" in lower and noun and prop:
                text = f"The {noun.lower()} is {prop.lower()}"
            elif "will" in lower and noun and base and obj:
                text = f"The {noun.lower()} will {base.lower()} the {obj.lower()}"
            elif "did" in lower and "not" in lower and noun and base and obj:
                text = f"The {noun.lower()} did not {base.lower()} the {obj.lower()}"
            elif name and past and obj:
                text = f"{name} {past.lower()} the {obj.lower()}"
            else:
                text = " ".join(clean)
            return _sentence(text.rstrip(".?!") + punctuation)
        if family == "missing_word":
            return next((base for base, (clue, _) in VERB_CONTEXTS.items()
                         if clue.lower() in prompt.lower() and base in choices), choices[0])
        if family == "tense_transform":
            return next((x for x in choices if " will " not in x and " did " not in x and
                         re.search(r"\b(?:ed|ied)\b|\w+ed\b", x.lower())), choices[0])
        if family == "negation_transform":
            return next((x for x in choices if re.search(r"\bdid not [a-z]+\b", x.lower()) and
                         not re.search(r"\bdid not [a-z]+ed\b", x.lower())), choices[0])
        if family == "sentence_comprehension":
            match = re.search(r"\bin the ([a-z]+)", prompt, re.I)
            return f"in the {match.group(1)}" if match else choices[0]
        if family == "grammar_repair":
            match = re.search(r"Repair the grammar: Yesterday ([A-Z][a-z]+) ([a-z]+) the ([a-z]+)", prompt)
            if match:
                base = match.group(2)
                past = next((p for b, p, _ in VERBS if b == base), base + "ed")
                return f"Yesterday {match.group(1)} {past} the {match.group(3)}."
        return choices[0] if choices else ""

    def submit(self, *, game_id: str, answer: str | None = None,
               player: str = "human") -> dict[str, Any]:
        game = self._game(game_id)
        if not game:
            return {"status": "not_found", "game_id": game_id}
        player = "aion" if player == "aion" else "human"
        student_view = {key: game[key] for key in (
            "game_id", "family", "difficulty", "prompt", "choices",
        )}
        supplied = self._aion_answer(student_view) if player == "aion" else str(answer or "")
        correct = _normal(supplied) == _normal(str(game["answer_key"]))
        attempt_id = _id("native_english_game_attempt_", [game_id, player, supplied, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_game_attempts VALUES(?,?,?,?,?,?,?)",
                (attempt_id, game_id, player, supplied, int(correct), 0, time.time()),
            )
        correction = None
        if not correct and player == "aion":
            correction = self._learn_verified_correction(game, supplied)
        elif player == "aion":
            self._record_retry(game, success=True)
        return {
            "status": "graded", "attempt_id": attempt_id, "game_id": game_id,
            "player": player, "answer": supplied, "correct": correct,
            "correct_answer": str(game["answer_key"]), "explanation": str(game["explanation"]),
            "rule_tag": str(game["rule_tag"]), "correction": correction,
            "learning": {
                "mistake_recorded": bool(correction),
                "verified_correction_stored": bool(correction),
                "related_retry_scheduled": bool(correction),
                "counts_as_vocabulary_mastery": False,
            },
            "integrity": {"answer_withheld_from_student": True, "model_used": False,
                          "cloud_used": False, "next_token_prediction": False},
        }

    def _record_retry(self, game: Mapping[str, Any], *, success: bool) -> None:
        now = time.time()
        with self._connect() as connection:
            if success:
                connection.execute(
                    "UPDATE native_english_remediation SET successful_retries=successful_retries+1,"
                    "updated_epoch=? WHERE rule_tag=?", (now, game["rule_tag"]),
                )

    def _learn_verified_correction(self, game: Mapping[str, Any], wrong: str) -> dict[str, Any]:
        now = time.time()
        payload = [game["game_id"], wrong, game["answer_key"], time.time_ns()]
        correction_id = _id("native_english_correction_", payload)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_game_corrections VALUES(?,?,?,?,?,?,?,?,?)",
                (correction_id, game["game_id"], wrong, game["answer_key"],
                 game["explanation"], game["rule_tag"], "sealed_game_answer_key", 1, now),
            )
            connection.execute(
                """INSERT INTO native_english_remediation(
                   rule_tag,family,failures,successful_retries,last_reason,next_due_epoch,updated_epoch
                   ) VALUES(?,?,1,0,?,?,?) ON CONFLICT(rule_tag) DO UPDATE SET
                   failures=failures+1,last_reason=excluded.last_reason,
                   next_due_epoch=excluded.next_due_epoch,updated_epoch=excluded.updated_epoch""",
                (game["rule_tag"], game["family"], game["explanation"], now + 300, now),
            )
        return {"correction_id": correction_id, "source": "sealed_game_answer_key",
                "verified": True, "reason": game["explanation"], "retry_due_epoch": now + 300}

    def propose_correction(self, *, game_id: str, answer: str, reason: str = "") -> dict[str, Any]:
        """Accept owner feedback only when the sealed key independently verifies it."""
        game = self._game(game_id)
        if not game:
            return {"status": "not_found", "game_id": game_id}
        verified = _normal(answer) == _normal(str(game["answer_key"]))
        if not verified:
            return {"status": "rejected_unverified", "verified": False,
                    "message": "The proposed correction does not match the independent answer key.",
                    "correct_answer": game["answer_key"], "explanation": game["explanation"]}
        correction = self._learn_verified_correction(game, "owner correction")
        return {"status": "accepted", "verified": True, "correction": correction,
                "correct_answer": game["answer_key"],
                "explanation": reason.strip() or game["explanation"]}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            games = int(connection.execute("SELECT COUNT(*) FROM native_english_games").fetchone()[0])
            attempts = int(connection.execute("SELECT COUNT(*) FROM native_english_game_attempts").fetchone()[0])
            correct = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_game_attempts WHERE correct=1"
            ).fetchone()[0])
            corrections = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_game_corrections WHERE verified=1"
            ).fetchone()[0])
            remediation = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_remediation WHERE failures>successful_retries"
            ).fetchone()[0])
        return {"games_created": games, "attempts": attempts, "correct": correct,
                "accuracy": round(correct / attempts, 4) if attempts else None,
                "verified_corrections": corrections, "remediation_rules_due": remediation,
                "model_used": False}


__all__ = ["FAMILIES", "NativeEnglishGames"]
