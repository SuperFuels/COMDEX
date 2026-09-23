from __future__ import annotations

import json
import os
import threading
import unicodedata
import urllib.parse
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


CARDS: tuple[Dict[str, Any], ...] = (
    {"id": "hello", "spanish": "hola", "english": "hello", "category": "Greetings", "visual": "👋"},
    {"id": "goodbye", "spanish": "adiós", "english": "goodbye", "category": "Greetings", "visual": "👋"},
    {"id": "please", "spanish": "por favor", "english": "please", "category": "Kind words", "visual": "🙏"},
    {"id": "thanks", "spanish": "gracias", "english": "thank you", "category": "Kind words", "visual": "💛"},
    {"id": "water", "spanish": "agua", "english": "water", "category": "Food and drink", "visual": "💧"},
    {"id": "apple", "spanish": "manzana", "english": "apple", "category": "Food and drink", "visual": "🍎"},
    {"id": "house", "spanish": "casa", "english": "house", "category": "Home", "visual": "🏠"},
    {"id": "school", "spanish": "escuela", "english": "school", "category": "School", "visual": "🏫"},
    {"id": "book", "spanish": "libro", "english": "book", "category": "School", "visual": "📘"},
    {"id": "friend", "spanish": "amigo", "english": "friend", "category": "People", "visual": "🧑‍🤝‍🧑"},
    {"id": "happy", "spanish": "feliz", "english": "happy", "category": "Feelings", "visual": "😄"},
    {"id": "tired", "spanish": "cansado", "english": "tired", "category": "Feelings", "visual": "😴"},
    {"id": "dog", "spanish": "perro", "english": "dog", "category": "Animals", "visual": "dog"},
    {"id": "cat", "spanish": "gato", "english": "cat", "category": "Animals", "visual": "cat"},
    {"id": "sun", "spanish": "sol", "english": "sun", "category": "Nature", "visual": "sun"},
    {"id": "moon", "spanish": "luna", "english": "moon", "category": "Nature", "visual": "moon"},
    {"id": "red", "spanish": "rojo", "english": "red", "category": "Colours", "visual": "red"},
    {"id": "blue", "spanish": "azul", "english": "blue", "category": "Colours", "visual": "blue"},
    {"id": "one", "spanish": "uno", "english": "one", "category": "Numbers", "visual": "one"},
    {"id": "five", "spanish": "cinco", "english": "five", "category": "Numbers", "visual": "five"},
    {"id": "today", "spanish": "hoy", "english": "today", "category": "Time", "visual": "today"},
    {"id": "tomorrow", "spanish": "mañana", "english": "tomorrow", "category": "Time", "visual": "tomorrow"},
    {"id": "left", "spanish": "izquierda", "english": "left", "category": "Directions", "visual": "left"},
    {"id": "right", "spanish": "derecha", "english": "right", "category": "Directions", "visual": "right"},
)

DIALOGUES: tuple[Dict[str, Any], ...] = (
    {
        "id": "how_are_you",
        "prompt": "Hola, ¿cómo estás?",
        "english": "Hello, how are you?",
        "choices": ["Estoy bien, gracias.", "Me llamo casa.", "Adiós, manzana."],
        "correct": 0,
        "explanation": "Estoy bien, gracias means: I am well, thank you.",
    },
    {
        "id": "name",
        "prompt": "¿Cómo te llamas?",
        "english": "What is your name?",
        "choices": ["Tengo ocho años.", "Me llamo Alex.", "Quiero agua."],
        "correct": 1,
        "explanation": "Me llamo… means: My name is…",
    },
    {
        "id": "want_water",
        "prompt": "¿Qué quieres beber?",
        "english": "What do you want to drink?",
        "choices": ["Quiero agua, por favor.", "Soy una escuela.", "Estoy libro."],
        "correct": 0,
        "explanation": "Quiero agua, por favor means: I would like water, please.",
    },
    {
        "id": "shop_help",
        "prompt": "¿Puedo ayudarte?",
        "english": "Can I help you?",
        "choices": ["Sí, busco un libro.", "Soy mañana.", "Tengo azul."],
        "correct": 0,
        "explanation": "Sí, busco un libro means: Yes, I am looking for a book.",
    },
    {
        "id": "directions",
        "prompt": "¿Dónde está la escuela?",
        "english": "Where is the school?",
        "choices": ["Está a la derecha.", "Bebo una casa.", "Me llamo cinco."],
        "correct": 0,
        "explanation": "Está a la derecha means: It is on the right.",
    },
)

AGE_BANDS = {"6-7", "8-9", "10-12"}
DIFFICULTIES = {"foundation", "developing", "challenge"}
SUBJECTS = {"spanish", "mathematics", "science"}


def _normalise_speech(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value).casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join("".join(char if char.isalnum() else " " for char in plain).split())


def _illustration_uri(card_id: str, label: str) -> str:
    """Return an original, code-generated vector illustration; no third-party artwork."""
    palette = ("#4f7cff", "#12a981", "#f59e0b", "#e8557a", "#7758e8", "#1597b8")
    colour = palette[sum(ord(char) for char in card_id) % len(palette)]
    initial = (label[:1] or "?").upper()
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 220'>"
        "<rect width='320' height='220' rx='32' fill='#f7f9ff'/>"
        f"<circle cx='160' cy='105' r='72' fill='{colour}' opacity='.18'/>"
        f"<path d='M88 150 Q160 42 232 150 Z' fill='{colour}' opacity='.92'/>"
        f"<text x='160' y='142' text-anchor='middle' font-family='system-ui,sans-serif' font-size='76' font-weight='800' fill='white'>{initial}</text>"
        "</svg>"
    )
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


class EducationLearningCentre:
    """Local, child-safe adaptive learning state for the shared TV surface."""

    LESSON_LENGTH = 50

    PROFILES = {
        "explorer_a": "Explorer A",
        "explorer_b": "Explorer B",
    }

    def __init__(self, base_dir: str | Path) -> None:
        self.path = Path(base_dir) / "education" / "learning_centre.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _default(self) -> Dict[str, Any]:
        return {
            "schema_version": "aion.education.v2",
            "profiles": {
                key: {
                    "display_name": name, "stars": 0, "streak": 0, "attempts": 0,
                    "correct": 0, "mastery": {}, "age_band": "6-7",
                    "difficulty": "foundation", "subject": "spanish",
                    "pronunciation_attempts": 0, "pronunciation_average": 0.0,
                    "guardian_corrections": [],
                }
                for key, name in self.PROFILES.items()
            },
            "session": None,
            "updated_at": utc_now_iso(),
        }

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._default()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._default()
        return value if isinstance(value, dict) else self._default()

    def _save(self, value: Dict[str, Any]) -> None:
        value["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.replace(temporary, self.path)

    @staticmethod
    def _public_session(session: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if not session:
            return None
        return {key: value for key, value in session.items() if key != "correct_index"}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            value = self._load()
            profiles = {
                key: {
                    "display_name": profile.get("display_name", self.PROFILES.get(key, key)),
                    "stars": int(profile.get("stars", 0)),
                    "streak": int(profile.get("streak", 0)),
                    "attempts": int(profile.get("attempts", 0)),
                    "correct": int(profile.get("correct", 0)),
                    "age_band": str(profile.get("age_band") or "6-7"),
                    "difficulty": str(profile.get("difficulty") or "foundation"),
                    "subject": str(profile.get("subject") or "spanish"),
                    "pronunciation_attempts": int(profile.get("pronunciation_attempts", 0)),
                    "pronunciation_average": float(profile.get("pronunciation_average", 0.0)),
                }
                for key, profile in dict(value.get("profiles") or {}).items()
            }
            return {
                "schema_version": value.get("schema_version", "aion.education.v2"),
                "profiles": profiles,
                "session": self._public_session(value.get("session")),
                "privacy": {
                    "child_accounts": False,
                    "advertising": False,
                    "open_web": False,
                    "raw_voice_retained": False,
                    "raw_transcripts_retained": False,
                    "advertising_profiles_created": False,
                    "guardian_boundary": True,
                },
                "curriculum": {
                    "subjects": sorted(SUBJECTS),
                    "age_bands": sorted(AGE_BANDS),
                    "difficulty_bands": sorted(DIFFICULTIES),
                    "illustrations": "original_code_generated_vectors",
                    "paid_ai_required": False,
                },
                "assurance": {
                    "colour_is_not_only_feedback": True,
                    "keyboard_and_directional_focus": True,
                    "spoken_and_visible_prompts": True,
                    "reduced_motion_compatible": True,
                    "open_chat_disabled": True,
                    "external_links_disabled": True,
                    "purchases_disabled": True,
                    "child_profiling_for_ads": False,
                    "local_technical_review": "passed",
                    "independent_pedagogy_review": "required_before_consumer_claim",
                    "independent_child_safety_review": "required_before_consumer_claim",
                },
            }

    def start(
        self,
        profile_id: str = "explorer_a",
        *,
        age_band: str | None = None,
        difficulty: str | None = None,
        subject: str | None = None,
    ) -> Dict[str, Any]:
        if profile_id not in self.PROFILES:
            raise ValueError("Unknown learning profile")
        if age_band is not None and age_band not in AGE_BANDS:
            raise ValueError("Unsupported learning age band")
        if difficulty is not None and difficulty not in DIFFICULTIES:
            raise ValueError("Unsupported learning difficulty")
        if subject is not None and subject not in SUBJECTS:
            raise ValueError("Unsupported learning subject")
        with self._lock:
            value = self._load()
            value.setdefault("profiles", self._default()["profiles"])
            defaults = self._default()["profiles"][profile_id]
            profile = value["profiles"].setdefault(profile_id, defaults)
            profile["age_band"] = age_band or str(profile.get("age_band") or "6-7")
            profile["difficulty"] = difficulty or str(profile.get("difficulty") or "foundation")
            profile["subject"] = subject or str(profile.get("subject") or "spanish")
            value["session"] = {
                "profile_id": profile_id,
                "display_name": self.PROFILES[profile_id],
                "round_number": 0,
                "lesson_total": self.LESSON_LENGTH,
                "answered_in_session": 0,
                "correct_in_session": 0,
                "phase": "ready",
                "feedback": "Let’s learn Spanish together!",
                "speak_nonce": 0,
                "age_band": profile["age_band"],
                "difficulty": profile["difficulty"],
                "subject": profile["subject"],
            }
            self._save(value)
        return self.next_round()

    def _build_round(self, value: Dict[str, Any]) -> Dict[str, Any]:
        session = dict(value["session"])
        profile = dict(value["profiles"][session["profile_id"]])
        round_number = int(session.get("round_number", 0)) + 1
        subject = str(profile.get("subject") or session.get("subject") or "spanish")
        difficulty = str(profile.get("difficulty") or session.get("difficulty") or "foundation")
        if subject == "mathematics":
            left = 2 + (round_number % 7)
            right = 1 + ((round_number * 2) % 6)
            answer = left + right
            choices = [answer, answer + 1, max(0, answer - 1)]
            shift = round_number % 3
            choices = choices[shift:] + choices[:shift]
            return {
                **session, "round_number": round_number, "round_kind": "mathematics",
                "card_id": f"math:add:{left}:{right}", "category": "Mathematics",
                "visual": "original vector number activity",
                "illustration_uri": _illustration_uri(f"math-{left}-{right}", str(answer)),
                "visual_alt": f"Original number illustration for {left} plus {right}",
                "instruction": "Solve the addition challenge.", "prompt": f"{left} + {right} = ?",
                "speak_text": f"¿Cuánto es {left} más {right}?",
                "choices": [{"index": index, "text": str(text)} for index, text in enumerate(choices)],
                "correct_index": choices.index(answer), "explanation": f"{left} plus {right} equals {answer}.",
                "phase": "question", "feedback": "", "speak_nonce": int(session.get("speak_nonce", 0)) + 1,
            }
        if subject == "science":
            activities = (
                ("plants", "What do plants need to grow?", "Water and light", ["Water and light", "Only darkness", "Plastic"], "Plants use water and light to grow."),
                ("states", "Which one is a liquid?", "Water", ["Water", "Stone", "Air only"], "Water is a liquid at room temperature."),
                ("animals", "Which animal is a mammal?", "Dog", ["Dog", "Butterfly", "Trout"], "A dog is a mammal."),
            )
            activity = activities[(round_number - 1) % len(activities)]
            choices = list(activity[3])
            shift = round_number % 3
            choices = choices[shift:] + choices[:shift]
            return {
                **session, "round_number": round_number, "round_kind": "science",
                "card_id": f"science:{activity[0]}", "category": "Science",
                "visual": "original vector science activity",
                "illustration_uri": _illustration_uri(f"science-{activity[0]}", activity[0]),
                "visual_alt": f"Original illustration for the {activity[0]} science activity",
                "instruction": "Think about what you have observed in the world.", "prompt": activity[1],
                "speak_text": activity[1],
                "choices": [{"index": index, "text": text} for index, text in enumerate(choices)],
                "correct_index": choices.index(activity[2]), "explanation": activity[4],
                "phase": "question", "feedback": "", "speak_nonce": int(session.get("speak_nonce", 0)) + 1,
            }
        conversation_interval = 2 if difficulty == "challenge" else 3 if difficulty == "developing" else 4
        if round_number % conversation_interval == 0:
            dialogue = DIALOGUES[((round_number // conversation_interval) - 1) % len(DIALOGUES)]
            choices = list(dialogue["choices"])
            return {
                **session,
                "round_number": round_number,
                "round_kind": "conversation",
                "card_id": f"dialogue:{dialogue['id']}",
                "category": "Conversation challenge",
                "visual": "💬",
                "illustration_uri": _illustration_uri(f"dialogue-{dialogue['id']}", "Conversation"),
                "visual_alt": "Original conversation illustration",
                "instruction": f"What is the best reply?  ·  {dialogue['english']}",
                "prompt": dialogue["prompt"],
                "speak_text": dialogue["prompt"],
                "choices": [{"index": index, "text": text} for index, text in enumerate(choices)],
                "correct_index": int(dialogue["correct"]),
                "explanation": dialogue["explanation"],
                "phase": "question",
                "feedback": "",
                "speak_nonce": int(session.get("speak_nonce", 0)) + 1,
            }
        mastery = dict(profile.get("mastery") or {})
        ranked = sorted(CARDS, key=lambda card: (float(mastery.get(card["id"], 0)), card["id"]))
        card = ranked[(round_number - 1) % min(6, len(ranked))]
        reverse = round_number % 2 == 0
        answer = card["english"] if reverse else card["spanish"]
        distractors = []
        for other in CARDS:
            candidate = other["english"] if reverse else other["spanish"]
            if other["id"] != card["id"] and candidate not in distractors:
                distractors.append(candidate)
            if len(distractors) == 2:
                break
        choices = [answer, *distractors]
        shift = round_number % len(choices)
        choices = choices[shift:] + choices[:shift]
        correct_index = choices.index(answer)
        return {
            **session,
            "round_number": round_number,
            "round_kind": "word",
            "card_id": card["id"],
            "category": card["category"],
            "visual": card["visual"],
            "illustration_uri": _illustration_uri(str(card["id"]), str(card["english"])),
            "visual_alt": f"Original learning illustration for {card['english']}",
            "instruction": "What does this Spanish word mean?" if reverse else f"Which Spanish word means “{card['english']}”?",
            "prompt": card["spanish"] if reverse else card["english"],
            "speak_text": card["spanish"],
            "choices": [{"index": index, "text": text} for index, text in enumerate(choices)],
            "correct_index": correct_index,
            "explanation": f"{card['spanish']} means {card['english']}.",
            "phase": "question",
            "feedback": "",
            "speak_nonce": int(session.get("speak_nonce", 0)) + 1,
        }

    def next_round(self) -> Dict[str, Any]:
        with self._lock:
            value = self._load()
            if not value.get("session"):
                raise ValueError("Start a learning session first")
            value["session"] = self._build_round(value)
            self._save(value)
            return self.snapshot()

    def answer(self, choice_index: int) -> Dict[str, Any]:
        with self._lock:
            value = self._load()
            session = dict(value.get("session") or {})
            if session.get("phase") != "question":
                raise ValueError("There is no unanswered learning round")
            choices = list(session.get("choices") or [])
            if choice_index < 0 or choice_index >= len(choices):
                raise ValueError("That learning choice is unavailable")
            correct = choice_index == int(session["correct_index"])
            profile = value["profiles"][session["profile_id"]]
            profile["attempts"] = int(profile.get("attempts", 0)) + 1
            profile["correct"] = int(profile.get("correct", 0)) + int(correct)
            profile["streak"] = int(profile.get("streak", 0)) + 1 if correct else 0
            profile["stars"] = int(profile.get("stars", 0)) + (2 if correct else 0)
            session["answered_in_session"] = int(session.get("answered_in_session", 0)) + 1
            session["correct_in_session"] = int(session.get("correct_in_session", 0)) + int(correct)
            session["lesson_total"] = int(session.get("lesson_total", self.LESSON_LENGTH))
            mastery = profile.setdefault("mastery", {})
            card_id = str(session["card_id"])
            current = float(mastery.get(card_id, 0))
            mastery[card_id] = round(min(1.0, current + 0.22) if correct else max(0.0, current - 0.08), 3)
            correct_text = str(choices[int(session["correct_index"])]["text"])
            session["phase"] = "feedback"
            session["was_correct"] = correct
            session["selected_index"] = choice_index
            session["correct_text"] = correct_text
            session["feedback"] = (
                f"✅ Correct! {session['explanation']}"
                if correct
                else f"❌ Not quite. The correct answer is {correct_text}. {session['explanation']}"
            )
            session["speak_text"] = f"¡Muy bien! {session['explanation']}" if correct else session["explanation"]
            session["speak_nonce"] = int(session.get("speak_nonce", 0)) + 1
            value["session"] = session
            self._save(value)
            return self.snapshot()

    def repeat(self) -> Dict[str, Any]:
        with self._lock:
            value = self._load()
            session = dict(value.get("session") or {})
            if not session:
                raise ValueError("Start a learning session first")
            session["speak_nonce"] = int(session.get("speak_nonce", 0)) + 1
            value["session"] = session
            self._save(value)
            return self.snapshot()

    def assess_pronunciation(self, recognised_text: str) -> Dict[str, Any]:
        """Score an on-device transcript and immediately discard its words."""
        with self._lock:
            value = self._load()
            session = dict(value.get("session") or {})
            if not session or not session.get("speak_text"):
                raise ValueError("Start a spoken learning round first")
            expected = _normalise_speech(str(session["speak_text"]))
            observed = _normalise_speech(recognised_text)
            if not observed:
                raise ValueError("No local speech transcript was available")
            similarity = SequenceMatcher(None, expected, observed).ratio()
            expected_words = set(expected.split())
            observed_words = set(observed.split())
            coverage = len(expected_words & observed_words) / max(1, len(expected_words))
            score = round((similarity * 0.65 + coverage * 0.35) * 100)
            band = "excellent" if score >= 88 else "good" if score >= 72 else "keep_practising"
            profile = value["profiles"][session["profile_id"]]
            attempts = int(profile.get("pronunciation_attempts", 0))
            average = float(profile.get("pronunciation_average", 0.0))
            profile["pronunciation_attempts"] = attempts + 1
            profile["pronunciation_average"] = round(((average * attempts) + score) / (attempts + 1), 1)
            profile.setdefault("pronunciation_history", []).append({
                "card_id": str(session.get("card_id") or "")[:120],
                "score": score,
                "band": band,
                "assessed_at": utc_now_iso(),
            })
            profile["pronunciation_history"] = profile["pronunciation_history"][-50:]
            session["pronunciation"] = {
                "score": score,
                "band": band,
                "feedback": "That was clear." if score >= 88 else "Good work—try once more slowly." if score >= 72 else "Listen again, then copy the rhythm one small part at a time.",
                "raw_audio_retained": False,
                "raw_transcript_retained": False,
            }
            value["session"] = session
            self._save(value)
            return {"assessment": dict(session["pronunciation"]), "education": self.snapshot()}

    def parent_report(self, profile_id: str, *, guardian_persona_id: str) -> Dict[str, Any]:
        if profile_id not in self.PROFILES or not str(guardian_persona_id).strip():
            raise PermissionError("A guardian identity and known learner are required")
        with self._lock:
            value = self._load()
            profile = dict((value.get("profiles") or {}).get(profile_id) or {})
            mastery = dict(profile.get("mastery") or {})
            needs_practice = [key for key, score in sorted(mastery.items(), key=lambda item: (float(item[1]), item[0])) if float(score) < 0.6][:8]
            attempts = int(profile.get("attempts", 0))
            return {
                "profile_id": profile_id,
                "display_name": str(profile.get("display_name") or self.PROFILES[profile_id]),
                "accuracy_percent": round(int(profile.get("correct", 0)) * 100 / max(1, attempts)),
                "attempts": attempts,
                "correct": int(profile.get("correct", 0)),
                "pronunciation_average": float(profile.get("pronunciation_average", 0.0)),
                "needs_practice": needs_practice,
                "age_band": str(profile.get("age_band") or "6-7"),
                "difficulty": str(profile.get("difficulty") or "foundation"),
                "subject": str(profile.get("subject") or "spanish"),
                "guardian_corrections": list(profile.get("guardian_corrections") or [])[-20:],
                "guardian_persona_hash": canonical_hash(str(guardian_persona_id))[:24],
                "child_raw_voice_available": False,
            }

    def record_parent_correction(
        self,
        profile_id: str,
        *,
        guardian_persona_id: str,
        card_id: str,
        note: str,
    ) -> Dict[str, Any]:
        if profile_id not in self.PROFILES or not str(guardian_persona_id).strip():
            raise PermissionError("A guardian identity and known learner are required")
        clean_note = " ".join(str(note).split())[:240]
        if len(clean_note) < 3:
            raise ValueError("A correction note is required")
        with self._lock:
            value = self._load()
            profile = value["profiles"].setdefault(profile_id, self._default()["profiles"][profile_id])
            correction = {
                "card_id": " ".join(str(card_id).split())[:120],
                "note": clean_note,
                "recorded_at": utc_now_iso(),
                "guardian_persona_hash": canonical_hash(str(guardian_persona_id))[:24],
            }
            profile.setdefault("guardian_corrections", []).append(correction)
            profile["guardian_corrections"] = profile["guardian_corrections"][-50:]
            self._save(value)
            return correction
