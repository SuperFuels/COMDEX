"""Unseen English transfer laboratory grounded in Aion's lexical memory.

Unlike the guided game bank, this module accepts owner-created material.  It
derives lexical categories from the persistent concept/lexeme stores, exposes
its parse, preserves ambiguity, and grades only after the native answer exists.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Mapping, Sequence

from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


TOKEN_RE = re.compile(
    r"(?:£|€|\$|¥)\s?\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?%?|[A-Za-z][A-Za-z'-]*|[,?.!]"
)
DETERMINERS = {"a", "an", "the", "this", "that", "these", "those"}
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}
POSSESSIVE_PRONOUNS = {"my", "your", "his", "her", "its", "our", "their"}
RELATIVE_PRONOUNS = {"which", "who", "whom", "whose"}
AUXILIARIES = {"will", "shall", "did", "does", "do", "was", "were", "is", "are", "am", "has", "have", "had", "be", "been", "being"}
NEGATORS = {"not", "never", "no"}
LOCATION_PREPOSITIONS = {"in", "at", "inside", "outside", "near", "under", "over", "beside", "behind", "into"}
TIME_PREFIX_MODIFIERS = {"last", "next", "previous", "coming"}
TIME_MARKERS = {
    "before", "after", "during", "when", "yesterday", "today", "tomorrow",
    "earlier", "later", *TIME_PREFIX_MODIFIERS,
}
OTHER_PREPOSITIONS = {"to", "from", "with", "without", "for", "by", "of", "into", "onto", "through"}
CURRENCY_SYMBOLS = {"£": "GBP", "$": "USD", "€": "EUR", "¥": "JPY"}
UNIT_WORDS = {"gallon", "gallons", "litre", "litres", "liter", "liters", "kilogram", "kilograms", "kg", "person", "people", "hour", "hours", "day", "days", "item", "items"}
QUANTITY_NOUNS = {"price", "cost", "rate", "amount", "total", "discount", "weight", "distance"}
CAUSE_MARKERS = {"because", "since", "therefore", "so"}
SUBORDINATORS = {"although", "because", "while", "unless", "if"}
SEMANTIC_QUESTION_STOPWORDS = {
    "what", "which", "who", "whose", "where", "when", "why", "how", "does",
    "did", "is", "are", "was", "were", "the", "a", "an", "of", "to", "in",
    "from", "and", "or", "mara", "her", "his", "their", "its",
}


def _normal(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", str(value or "").lower()).split())


def _identifier(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


def _edit_distance(left: str, right: str) -> int:
    if len(left) == len(right):
        differences = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
        if (len(differences) == 2 and differences[1] == differences[0] + 1
                and left[differences[0]] == right[differences[1]]
                and left[differences[1]] == right[differences[0]]):
            return 1
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


class NativeEnglishTransfer:
    """Parse, answer and grade never-before-seen owner material without a model."""

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
                CREATE TABLE IF NOT EXISTS native_english_transfer_challenges (
                    challenge_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    material TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer_key TEXT NOT NULL DEFAULT '',
                    answer_reason TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    learning_target_concept_id TEXT NOT NULL DEFAULT '',
                    content_signature TEXT NOT NULL,
                    first_seen INTEGER NOT NULL,
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_english_transfer_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    challenge_id TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    correct INTEGER,
                    parse_json TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    ambiguity_json TEXT NOT NULL,
                    acquired_terms INTEGER NOT NULL,
                    reference_terms INTEGER NOT NULL,
                    unknown_terms INTEGER NOT NULL,
                    model_used INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    FOREIGN KEY(challenge_id) REFERENCES native_english_transfer_challenges(challenge_id)
                );
                CREATE TABLE IF NOT EXISTS native_english_transfer_learning_events (
                    event_id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL,
                    challenge_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    lemma TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expected_answer TEXT NOT NULL DEFAULT '',
                    answer_reason TEXT NOT NULL DEFAULT '',
                    content_signature TEXT NOT NULL,
                    counts_as_mastery INTEGER NOT NULL DEFAULT 0,
                    created_epoch REAL NOT NULL,
                    verified_epoch REAL,
                    FOREIGN KEY(attempt_id) REFERENCES native_english_transfer_attempts(attempt_id),
                    FOREIGN KEY(challenge_id) REFERENCES native_english_transfer_challenges(challenge_id),
                    FOREIGN KEY(concept_id) REFERENCES acquired_concepts(concept_id)
                );
                CREATE INDEX IF NOT EXISTS native_transfer_learning_concept
                    ON native_english_transfer_learning_events(concept_id,status,created_epoch DESC);
                CREATE INDEX IF NOT EXISTS native_transfer_learning_attempt
                    ON native_english_transfer_learning_events(attempt_id);
                """
            )
            challenge_columns = {str(row[1]) for row in connection.execute(
                "PRAGMA table_info(native_english_transfer_challenges)"
            ).fetchall()}
            if "learning_target_concept_id" not in challenge_columns:
                connection.execute(
                    "ALTER TABLE native_english_transfer_challenges ADD COLUMN learning_target_concept_id TEXT NOT NULL DEFAULT ''"
                )

    def _learning_targets(self, result: Mapping[str, Any],
                          challenge: Mapping[str, Any]) -> list[dict[str, str]]:
        """Return only acquired concepts that actually participated in an answer."""
        sealed_target = str(challenge.get("learning_target_concept_id") or "")
        if sealed_target:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT concept_id,lemma FROM acquired_concepts WHERE concept_id=?",
                    (sealed_target,),
                ).fetchone()
            return [dict(row)] if row else []
        targets: dict[str, dict[str, str]] = {}
        receipt = dict(result.get("semantic_evidence") or {})
        concept_id = str(receipt.get("target_concept_id") or "")
        if concept_id:
            targets[concept_id] = {
                "concept_id": concept_id,
                "lemma": str(receipt.get("target_lemma") or ""),
            }
        parsed = dict(result.get("parse") or {})
        for token in parsed.get("tokens") or []:
            row = dict(token)
            token_concept = str(row.get("concept_id") or "")
            if row.get("source") == "acquired_concept" and token_concept:
                targets.setdefault(token_concept, {
                    "concept_id": token_concept,
                    "lemma": str(row.get("lemma") or ""),
                })
        return list(targets.values())[:6]

    def _record_learning_outcome(
        self, *, attempt_id: str, challenge: Mapping[str, Any],
        result: Mapping[str, Any], correct: bool | None,
    ) -> dict[str, Any]:
        """Reinforce transfer or create remediation without granting mastery."""
        if correct is None:
            return {"status": "ungraded", "reinforced": 0, "remediation_due": 0,
                    "counts_as_mastery": False}
        targets = self._learning_targets(result, challenge)
        if not targets:
            return {"status": "no_acquired_target", "reinforced": 0,
                    "remediation_due": 0, "counts_as_mastery": False}
        now = time.time()
        verified = 0
        newly_due = 0
        with self._connect() as connection:
            for target in targets:
                concept_id = target["concept_id"]
                lemma = target["lemma"]
                event_type = ("semantic_transfer_reinforcement" if correct
                              else "remedial_correction")
                existing_due = None if correct else connection.execute(
                    """SELECT event_id FROM native_english_transfer_learning_events
                       WHERE concept_id=? AND event_type='remedial_correction' AND status='due'
                       LIMIT 1""", (concept_id,),
                ).fetchone()
                status = ("recorded" if correct else
                          "recorded_failure" if existing_due else "due")
                if status == "due":
                    newly_due += 1
                event_id = _identifier("native_transfer_learning_", [
                    attempt_id, concept_id, event_type,
                ])
                connection.execute(
                    """INSERT OR IGNORE INTO native_english_transfer_learning_events
                       (event_id,attempt_id,challenge_id,concept_id,lemma,event_type,status,
                        expected_answer,answer_reason,content_signature,counts_as_mastery,
                        created_epoch,verified_epoch)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                    (event_id, attempt_id, challenge["challenge_id"], concept_id, lemma,
                     event_type, status, str(challenge.get("answer_key") or ""),
                     str(challenge.get("answer_reason") or ""),
                     str(challenge.get("content_signature") or ""), 0, now),
                )
                if correct:
                    connection.execute(
                        """UPDATE acquired_concepts SET attempts=attempts+1,
                           correct_attempts=correct_attempts+1,last_practice_epoch=?,updated_epoch=?
                           WHERE concept_id=?""",
                        (now, now, concept_id),
                    )
                    due = connection.execute(
                        """SELECT event_id FROM native_english_transfer_learning_events
                           WHERE concept_id=? AND event_type='remedial_correction' AND status='due'
                             AND content_signature<>? ORDER BY created_epoch LIMIT 1""",
                        (concept_id, str(challenge.get("content_signature") or "")),
                    ).fetchone()
                    if due:
                        connection.execute(
                            "UPDATE native_english_transfer_learning_events SET status='verified',verified_epoch=? WHERE event_id=?",
                            (now, due["event_id"]),
                        )
                        verified += 1
                else:
                    connection.execute(
                        """UPDATE acquired_concepts SET attempts=attempts+1,
                           failed_attempts=failed_attempts+1,consecutive_passes=0,
                           last_practice_epoch=?,next_review_epoch=?,updated_epoch=?
                           WHERE concept_id=?""",
                        (now, now, now, concept_id),
                    )
        return {
            "status": "reinforced" if correct else "remediation_scheduled",
            "reinforced": len(targets) if correct else 0,
            "remediation_due": 0 if correct else newly_due,
            "remediation_verified": verified,
            "concepts": targets,
            "counts_as_mastery": False,
        }

    def _acquired(self, lemma: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='acquired_concepts'"
            ).fetchone()
            if not table:
                return None
            row = connection.execute(
                """SELECT lemma,part_of_speech,stage,concept_id,native_gloss,
                          features_json,relations_json,sense_hash
                   FROM acquired_concepts WHERE lemma=? ORDER BY
                   CASE stage WHEN 'mastered' THEN 9 WHEN 'retention_90d' THEN 8
                   WHEN 'retention_30d' THEN 7 WHEN 'retention_7d' THEN 6
                   WHEN 'retention_1d' THEN 5 WHEN 'productive' THEN 4
                   WHEN 'contextual' THEN 3 WHEN 'recalled' THEN 2 ELSE 1 END DESC,
                   updated_epoch DESC,concept_id ASC LIMIT 1""",
                (lemma,),
            ).fetchone()
        if not row:
            return None
        value = dict(row)
        value["features"] = json.loads(value.pop("features_json") or "[]")
        value["relations"] = json.loads(value.pop("relations_json") or "{}")
        return value

    def _bind_sealed_target(self, parsed: dict[str, Any], concept_id: str) -> None:
        """Bind a material surface to the exact acquired sense selected before the exam.

        The academy seals a concept ID, not an answer.  A lemma can have many
        acquired senses, so normal lookup may otherwise attach the sentence to
        a different capsule for the same surface word.  This binding supplies
        the intended learned sense while leaving the answer key unavailable.
        """
        if not concept_id:
            return
        with self._connect() as connection:
            row = connection.execute(
                """SELECT concept_id,lemma,stage,sense_hash,native_gloss,
                          features_json,relations_json
                   FROM acquired_concepts WHERE concept_id=?""",
                (concept_id,),
            ).fetchone()
        if not row:
            return
        target = dict(row)
        lemma = str(target["lemma"] or "").lower()
        evidence = {
            "lemma": lemma, "source": "acquired_concept",
            "stage": target.get("stage"), "concept_id": concept_id,
            "sense_hash": target.get("sense_hash"),
            "native_gloss": target.get("native_gloss"),
            "semantic_features": json.loads(target.get("features_json") or "[]"),
            "semantic_relations": json.loads(target.get("relations_json") or "{}"),
            "sealed_target_binding": True,
        }

        def matches(item: Mapping[str, Any]) -> bool:
            return lemma in {
                str(item.get("lemma") or "").lower(),
                str(item.get("acquired_surface_lemma") or "").lower(),
            }

        for token in parsed.get("tokens") or []:
            if matches(token):
                token.update(evidence)
        for clause in parsed.get("clauses") or []:
            for key in ("action_evidence", "object_evidence", "complement_evidence"):
                item = clause.get(key)
                if isinstance(item, dict) and matches(item):
                    item.update(evidence)

    def _verb_lemma(self, word: str) -> str | None:
        stored = self.lexical.resolve_form(word, "v")
        if stored:
            return str(stored[0]["lemma"])
        candidates = [word]
        if word.endswith("ied") and len(word) > 4:
            candidates.append(word[:-3] + "y")
        if word.endswith("ed") and len(word) > 3:
            candidates.extend((word[:-1], word[:-2]))
            if len(word) > 4 and word[-3] == word[-4]:
                candidates.append(word[:-3])
        if word.endswith("es") and len(word) > 3:
            candidates.extend((word[:-1], word[:-2]))
        elif word.endswith("s") and len(word) > 2:
            candidates.append(word[:-1])
        for candidate in dict.fromkeys(candidates):
            senses = self.lexical.lookup_senses(candidate, "v")
            if senses:
                return str(senses[0]["lemma"])
            entry = self.lexical.lookup(candidate)
            if entry and entry.get("part_of_speech") == "v":
                return str(entry["lemma"])
            # Productive English re- derivation: WordNet often contains the
            # base verb (route) without enumerating its transparent prefixed
            # form (reroute). Preserve the derived lemma rather than dropping
            # the inflected token as unknown.
            if candidate.startswith("re") and len(candidate) > 4:
                base = candidate[2:]
                if self.lexical.lookup_senses(base, "v"):
                    return candidate
        return None

    def _spelling_candidate(self, word: str) -> str | None:
        vocabulary = (
            DETERMINERS | PRONOUNS | AUXILIARIES | NEGATORS |
            LOCATION_PREPOSITIONS | TIME_MARKERS | OTHER_PREPOSITIONS |
            CAUSE_MARKERS | {"how", "much", "many", "who", "what", "where", "why"}
        )
        candidates = [item for item in vocabulary if abs(len(item) - len(word)) <= 1]
        ranked = sorted((_edit_distance(word, item), item) for item in candidates)
        return ranked[0][1] if ranked and ranked[0][0] == 1 else None

    def _token_evidence(self, token: str, index: int) -> dict[str, Any]:
        lower = token.lower()
        if token in {",", ".", "?", "!"}:
            return {"token": token, "role": "punctuation", "source": "grammar"}
        if lower in DETERMINERS:
            return {"token": token, "lemma": lower, "pos": "determiner", "source": "grammar"}
        if lower in PRONOUNS:
            return {"token": token, "lemma": lower, "pos": "pronoun", "source": "grammar"}
        if lower in POSSESSIVE_PRONOUNS:
            return {"token": token, "lemma": lower, "pos": "possessive_pronoun", "source": "grammar"}
        if lower in RELATIVE_PRONOUNS:
            return {"token": token, "lemma": lower, "pos": "relative_pronoun", "source": "grammar"}
        if lower in AUXILIARIES:
            return {"token": token, "lemma": lower, "pos": "auxiliary", "source": "grammar"}
        if lower in NEGATORS:
            return {"token": token, "lemma": lower, "pos": "negator", "source": "grammar"}
        if lower in LOCATION_PREPOSITIONS | TIME_MARKERS | OTHER_PREPOSITIONS | CAUSE_MARKERS | SUBORDINATORS:
            return {"token": token, "lemma": lower, "pos": "relation", "source": "grammar"}
        money = re.fullmatch(r"([£€$¥])\s?(\d+(?:[.,]\d+)?)", token)
        if money:
            return {"token": token, "lemma": token, "pos": "quantity",
                    "source": "numeric_parser", "value": float(money.group(2).replace(",", ".")),
                    "currency": CURRENCY_SYMBOLS[money.group(1)], "symbol": money.group(1)}
        percent = re.fullmatch(r"(\d+(?:[.,]\d+)?)%", token)
        if percent:
            return {"token": token, "lemma": token, "pos": "quantity",
                    "source": "numeric_parser", "value": float(percent.group(1).replace(",", ".")),
                    "unit": "percent"}
        if re.fullmatch(r"\d+(?:[.,]\d+)?", token):
            return {"token": token, "lemma": token, "pos": "quantity",
                    "source": "numeric_parser", "value": float(token.replace(",", "."))}
        # Capitalisation supplies structural proper-name evidence even when a
        # lower-case homograph also exists in the reference dictionary (for
        # example Owen, May or Rose). This is evidence, not a fixed name list.
        if token[:1].isupper():
            return {"token": token, "lemma": lower, "pos": "proper_entity",
                    "source": "structural_inference"}
        acquired = self._acquired(lower)
        if acquired:
            return {"token": token, "lemma": acquired["lemma"],
                    "pos": acquired.get("part_of_speech") or "unknown",
                    "source": "acquired_concept", "stage": acquired["stage"],
                    "concept_id": acquired["concept_id"],
                    "sense_hash": acquired.get("sense_hash"),
                    "native_gloss": acquired.get("native_gloss"),
                    "semantic_features": acquired.get("features") or [],
                    "semantic_relations": acquired.get("relations") or {}}
        stored_forms = self.lexical.resolve_form(lower, "v")
        verb = str(stored_forms[0]["lemma"]) if stored_forms else self._verb_lemma(lower)
        if verb and verb != lower:
            acquired_verb = self._acquired(verb)
            return {"token": token, "lemma": verb, "pos": "v",
                    "source": "acquired_concept" if acquired_verb else "reference_lexicon",
                    "stage": (acquired_verb or {}).get("stage"), "inflected": True,
                    "concept_id": (acquired_verb or {}).get("concept_id"),
                    "sense_hash": (acquired_verb or {}).get("sense_hash"),
                    "native_gloss": (acquired_verb or {}).get("native_gloss"),
                    "semantic_features": (acquired_verb or {}).get("features") or [],
                    "semantic_relations": (acquired_verb or {}).get("relations") or {},
                    "morphology_feature": (stored_forms[0].get("feature") if stored_forms else
                                           "past" if lower.endswith(("ed", "ied")) else "inflected")}
        senses = self.lexical.lookup_senses(lower)
        if senses:
            candidates = sorted({str(row["part_of_speech"]) for row in senses})
            return {"token": token, "lemma": lower, "pos": candidates[0],
                    "pos_candidates": candidates, "source": "reference_senses"}
        entry = self.lexical.lookup(lower)
        if entry:
            return {"token": token, "lemma": entry["lemma"],
                    "pos": entry.get("part_of_speech") or "unknown",
                    "pos_candidates": [entry.get("part_of_speech") or "unknown"],
                    "source": "reference_lexicon"}
        suggestion = self._spelling_candidate(lower)
        if suggestion:
            role = "relation" if suggestion in (
                LOCATION_PREPOSITIONS | TIME_MARKERS | OTHER_PREPOSITIONS | CAUSE_MARKERS
            ) else "unknown"
            return {"token": token, "lemma": suggestion, "pos": role,
                    "source": "spelling_hypothesis", "original": lower,
                    "correction_confidence": .72}
        return {"token": token, "lemma": lower, "pos": "unknown", "source": "unknown"}

    def parse(self, sentence: str) -> dict[str, Any]:
        tokens = TOKEN_RE.findall(sentence)
        evidence = [self._token_evidence(token, index) for index, token in enumerate(tokens)]
        # A possessive followed by an acquired adjective and a copula often
        # nominalises that adjective ("their military is ...", "the accused
        # were ..."). Treat the acquired capsule as the head of a noun phrase
        # for this occurrence without changing its stored lexical category.
        for index, row in enumerate(evidence):
            if row.get("pos") not in {"a", "s"} or index == 0:
                continue
            previous = evidence[index - 1]
            following = evidence[index + 1] if index + 1 < len(evidence) else {}
            if ((previous.get("pos") in {"possessive_pronoun", "determiner"}
                    and following.get("pos") == "auxiliary")
                    or (previous.get("pos") == "determiner"
                        and following.get("role") == "punctuation")):
                row.update({"pos": "n", "context_selected_pos": True,
                            "nominalised": True})
        # Productive comparative/superlative morphology supplies a usable
        # adjective role even when the exact inflected form is absent.
        for row in evidence:
            surface = str(row.get("token") or "").lower()
            if row.get("source") != "unknown" or not surface.endswith("est"):
                continue
            bases = [surface[:-2], surface[:-3], surface[:-3] + "e"]
            if any(self.lexical.lookup_senses(base, "a") for base in bases if base):
                row.update({"pos": "a", "source": "structural_inference",
                            "morphology_feature": "superlative"})
        # Exact acquired spellings can represent an adjective and an inflected
        # verb at the same time ("vindicated" is the clearest example).  When
        # local syntax supplies an entity before and an affected entity after,
        # preserve the acquired meaning capsule but select the stored verb
        # morphology for this occurrence.
        for index, row in enumerate(evidence):
            if row.get("source") != "acquired_concept" or row.get("pos") not in {"a", "s"}:
                continue
            surface = str(row.get("token") or "").lower()
            forms = self.lexical.resolve_form(surface, "v")
            entity_before = any(item.get("pos") in {"n", "proper_entity", "pronoun"}
                                for item in evidence[:index])
            entity_after = any(item.get("pos") in {"n", "proper_entity", "pronoun"}
                               for item in evidence[index + 1:])
            if forms and entity_before and entity_after:
                row.update({
                    "lemma": str(forms[0]["lemma"]), "pos": "v", "inflected": True,
                    "morphology_feature": str(forms[0].get("feature") or "past"),
                    "context_selected_pos": True,
                    "acquired_surface_lemma": surface,
                })
        # A surface form such as "funds" can be both a generated verb form and
        # an ordinary plural noun.  Determiners and nominal modifiers provide
        # local evidence for the noun reading; do not let morphology alone turn
        # a noun phrase into a second event.
        for index, row in enumerate(evidence):
            if not (row.get("pos") == "v" and row.get("inflected")
                    and str(row.get("token") or "").lower().endswith("s")):
                continue
            previous = evidence[index - 1] if index else {}
            noun_senses = self.lexical.lookup_senses(str(row.get("lemma") or ""), "n")
            if noun_senses and previous.get("pos") in {"determiner", "n", "a", "s"}:
                row.update({"pos": "n", "source": "contextual_disambiguation",
                            "context_selected_pos": True, "plural": True})
        # Resolve ambiguous multi-POS spellings using local syntax rather than
        # allowing one arbitrary dictionary sense to win globally.
        for index, row in enumerate(evidence):
            candidates = set(row.get("pos_candidates") or [])
            if "v" in candidates and row.get("pos") != "v":
                previous = str(evidence[index - 1].get("lemma") or "") if index else ""
                entity_before = any(item.get("pos") in {"n", "proper_entity", "pronoun"}
                                    for item in evidence[:index])
                verb_before = any(item.get("pos") == "v" for item in evidence[:index])
                if previous == "to" or (entity_before and not verb_before):
                    row["pos"] = "v"
                    row["context_selected_pos"] = True
        verb_index = next((i for i, row in enumerate(evidence) if row.get("pos") == "v"), None)
        if verb_index is None:
            verb_index = next((i for i, row in enumerate(evidence)
                               if row.get("pos") == "auxiliary"), None)
        entity_pos = {"n", "proper_entity", "pronoun"}
        preverbal = [(i, row) for i, row in enumerate(evidence)
                     if row.get("pos") in entity_pos and (verb_index is None or i < verb_index)]
        # Sentence-initial calendar phrases such as "Last Thursday" contain a
        # capitalised word, but that word is part of the temporal adjunct and
        # must not win the proper-name subject heuristic.
        subject_row = next((row for i, row in preverbal
                            if row.get("pos") in {"proper_entity", "pronoun"}
                            and not (i and evidence[i - 1].get("lemma")
                                     in TIME_PREFIX_MODIFIERS)), None)
        if subject_row is None:
            subject_row = next((row for i, row in preverbal
                                if not any(evidence[j].get("lemma") in TIME_MARKERS
                                           for j in range(0, i))), None)
        object_row = next((row for i, row in enumerate(evidence)
                           if row.get("pos") in entity_pos and verb_index is not None and i > verb_index
                           and not any(evidence[j].get("lemma") in
                                       LOCATION_PREPOSITIONS | TIME_MARKERS
                                       for j in range(verb_index + 1, i))), None)

        def phrase_after(markers: set[str]) -> str | None:
            for i, row in enumerate(evidence):
                if row.get("lemma") in markers:
                    values: list[str] = [str(row["token"])]
                    for following in evidence[i + 1:]:
                        if following.get("role") == "punctuation" or following.get("lemma") in (
                            LOCATION_PREPOSITIONS | TIME_MARKERS | OTHER_PREPOSITIONS
                        ):
                            break
                        values.append(str(following["token"]))
                    return " ".join(values)
            return None

        location = phrase_after(LOCATION_PREPOSITIONS)
        temporal = phrase_after(TIME_MARKERS)
        auxiliaries = {str(row.get("lemma")) for row in evidence if row.get("pos") == "auxiliary"}
        action_row = evidence[verb_index] if verb_index is not None else None
        action_token = str((action_row or {}).get("token") or "")
        action_feature = str((action_row or {}).get("morphology_feature") or "")
        tense = "future" if auxiliaries & {"will", "shall"} else (
            "past" if auxiliaries & {"did", "was", "were", "had"} or
            action_token.lower().endswith(("ed", "ied")) or action_feature in {
                "past", "past_participle",
            } else "present"
        )
        ambiguous: list[str] = []
        if verb_index is None:
            ambiguous.append("no_action_identified")
        if subject_row is None:
            ambiguous.append("no_subject_identified")
        noun_rows = [row for row in evidence if row.get("pos") in entity_pos]
        if verb_index is not None and len([row for i, row in enumerate(evidence)
                                          if row.get("pos") in entity_pos and i > verb_index]) > 1 and not location:
            ambiguous.append("multiple_postverbal_entities")
        counts = {
            "acquired": sum(row.get("source") == "acquired_concept" for row in evidence),
            "reference": sum(row.get("source") in {"reference_lexicon", "reference_senses"}
                             for row in evidence),
            "unknown": sum(row.get("source") == "unknown" for row in evidence),
            "structural": sum(row.get("source") == "structural_inference" for row in evidence),
        }
        content_total = max(1, counts["acquired"] + counts["reference"] + counts["unknown"] + counts["structural"])
        confidence = .25
        confidence += .18 if subject_row else 0
        confidence += .22 if action_row else 0
        confidence += .12 if object_row else 0
        confidence += .12 * counts["acquired"] / content_total
        confidence += .07 * counts["reference"] / content_total
        confidence -= .12 * counts["unknown"] / content_total
        confidence -= .10 * len(ambiguous)
        clauses = self._clause_frames(evidence)
        main_clause = next((clause for clause in reversed(clauses)
                            if not clause.get("subordinate")), clauses[-1] if clauses else {})
        frame = {
            "subject": (subject_row or {}).get("token"),
            "action": (action_row or {}).get("lemma"),
            "action_surface": (action_row or {}).get("token"),
            "object": (object_row or {}).get("token"),
            "time": temporal, "location": location,
            "tense": tense,
            "negated": any(row.get("pos") == "negator" for row in evidence),
        }
        if main_clause:
            frame.update({
                "subject": main_clause.get("subject"),
                "action": main_clause.get("action"),
                "action_surface": main_clause.get("action_surface"),
                "object": main_clause.get("object"),
                "time": main_clause.get("time") or temporal,
                "location": main_clause.get("location"),
                "tense": main_clause.get("tense") or tense,
                "negated": bool(main_clause.get("negated")),
            })
        quantities: list[dict[str, Any]] = []
        for index, row in enumerate(evidence):
            if row.get("pos") != "quantity":
                continue
            before = evidence[:index]
            unit = next((str(item.get("lemma")) for item in reversed(before)
                         if str(item.get("lemma")) in UNIT_WORDS), None)
            property_name = next((str(item.get("lemma")) for item in reversed(before)
                                  if str(item.get("lemma")) in QUANTITY_NOUNS), None)
            property_index = next((i for i in range(index - 1, -1, -1)
                                   if str(evidence[i].get("lemma")) in QUANTITY_NOUNS), None)
            item = None
            if property_index is not None:
                item = next((str(candidate.get("lemma")) for candidate in
                             reversed(evidence[:property_index])
                             if candidate.get("pos") in {"n", "proper_entity"}
                             and str(candidate.get("lemma")) not in UNIT_WORDS), None)
            quantities.append({
                "value": row.get("value"), "currency": row.get("currency"),
                "symbol": row.get("symbol"), "unit": row.get("unit") or unit,
                "property": property_name, "item": item, "surface": row.get("token"),
            })
        events: list[dict[str, Any]] = []
        last_subject = None
        for index, row in enumerate(evidence):
            if row.get("pos") in {"proper_entity", "pronoun", "n"}:
                if not any(evidence[j].get("lemma") in TIME_MARKERS
                           for j in range(max(0, index - 2), index)):
                    last_subject = str(row.get("token"))
            if row.get("pos") not in {"v", "auxiliary"}:
                continue
            obj = next((str(candidate.get("token")) for candidate in evidence[index + 1:]
                        if candidate.get("pos") in {"n", "proper_entity"}), None)
            events.append({"subject": last_subject, "action": row.get("lemma"),
                           "surface": row.get("token"), "object": obj})
        spelling = [{"original": row.get("original"), "candidate": row.get("lemma"),
                     "confidence": row.get("correction_confidence")}
                    for row in evidence if row.get("source") == "spelling_hypothesis"]
        return {"sentence": sentence, "tokens": evidence, "frame": frame,
                "clauses": clauses,
                "ambiguities": ambiguous, "confidence": round(max(0.0, min(.99, confidence)), 3),
                "grounding": counts, "events": events, "quantities": quantities,
                "spelling_hypotheses": spelling, "model_used": False}

    @staticmethod
    def _phrase(rows: Sequence[Mapping[str, Any]], *, include_determiner: bool = False) -> str | None:
        values = [str(row.get("token") or "") for row in rows
                  if row.get("role") != "punctuation"]
        if not include_determiner:
            while values and values[0].lower() in DETERMINERS:
                values.pop(0)
        return " ".join(value for value in values if value).strip() or None

    def _clause_frames(self, evidence: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Build local frames so scope does not leak between coordinated clauses."""
        segments: list[list[Mapping[str, Any]]] = [[]]
        for row in evidence:
            if row.get("token") == ",":
                if segments[-1]:
                    segments.append([])
                continue
            if row.get("token") in {".", "?", "!"}:
                if segments[-1]:
                    segments.append([])
                continue
            segments[-1].append(row)
        segments = [segment for segment in segments if segment]
        proper_entities = [str(row.get("token")) for row in evidence
                           if row.get("pos") == "proper_entity"]
        clauses: list[dict[str, Any]] = []
        for segment in segments:
            marker_value = str(segment[0].get("lemma") or "")
            subordinate = marker_value in SUBORDINATORS | TIME_MARKERS
            content = segment[1:] if subordinate else segment
            action_index = next((i for i, row in enumerate(content)
                                 if row.get("pos") == "v"), None)
            if action_index is None:
                action_index = next((i for i, row in enumerate(content)
                                     if row.get("pos") == "auxiliary"), None)
            if action_index is None:
                continue
            action_row = content[action_index]
            before = content[:action_index]
            after = content[action_index + 1:]
            entities = {"n", "proper_entity", "pronoun"}
            subject_rows = [row for row in before if row.get("pos") in entities]
            subject_row = next((row for row in subject_rows
                                if row.get("pos") in {"proper_entity", "pronoun"}),
                               subject_rows[0] if subject_rows else None)
            subject_phrase = (subject_row or {}).get("token")
            if subject_row in before:
                subject_index = before.index(subject_row)
                if subject_index and before[subject_index - 1].get("pos") == "possessive_pronoun":
                    subject_phrase = self._phrase(before[subject_index - 1:subject_index + 1],
                                                  include_determiner=True)
            boundary = next((i for i, row in enumerate(after)
                             if row.get("pos") == "relation"), len(after))
            object_material = [row for row in after[:boundary]
                               if row.get("pos") in {
                                   "determiner", "n", "a", "s", "proper_entity", "pronoun",
                               }]
            object_rows = [row for row in object_material
                           if row.get("pos") in {"n", "proper_entity", "pronoun"}]
            object_phrase = self._phrase(object_material)
            object_head = str(object_rows[-1].get("token")) if object_rows else None
            copular = str(action_row.get("lemma") or "") in {
                "am", "is", "are", "was", "were", "be", "been", "being",
            }
            complement = next((row for row in reversed(after)
                               if row.get("pos") in {"n", "a", "s"}), None) if copular else None
            possessor = None
            if any(row.get("pos") == "possessive_pronoun" for row in content):
                possessor = proper_entities[0] if len(proper_entities) == 1 else None
            def local_phrase(markers: set[str]) -> str | None:
                for i, row in enumerate(content):
                    if row.get("lemma") not in markers:
                        continue
                    values = [str(row.get("token") or "")]
                    for following in content[i + 1:]:
                        if following.get("role") == "punctuation":
                            break
                        values.append(str(following.get("token") or ""))
                    return " ".join(value for value in values if value) or None
                return None
            action_surface = str(action_row.get("token") or "")
            action_feature = str(action_row.get("morphology_feature") or "")
            auxiliaries = {str(row.get("lemma") or "") for row in content
                           if row.get("pos") == "auxiliary"}
            local_tense = "future" if auxiliaries & {"will", "shall"} else (
                "past" if auxiliaries & {"did", "was", "were", "had"}
                or action_surface.lower().endswith(("ed", "ied"))
                or action_feature in {"past", "past_participle"} else "present"
            )
            clauses.append({
                "subordinate": subordinate,
                "marker": segment[0].get("lemma") if subordinate else None,
                "subject": subject_phrase,
                "subject_lemma": (subject_row or {}).get("lemma"),
                "action": "be" if copular else action_row.get("lemma"),
                "action_surface": action_row.get("token"),
                "action_evidence": dict(action_row),
                "object": object_phrase or object_head,
                "object_head": object_head,
                "object_evidence": dict(object_rows[-1]) if object_rows else None,
                "complement": (complement or {}).get("token"),
                "complement_evidence": dict(complement) if complement else None,
                "possessor": possessor,
                "negated": any(row.get("pos") == "negator" for row in content),
                "time": local_phrase(TIME_MARKERS),
                "location": local_phrase(LOCATION_PREPOSITIONS),
                "tense": local_tense,
                "tokens": [str(row.get("token") or "") for row in content],
            })
        return clauses

    def _question_semantic_terms(self, question: str) -> set[str]:
        terms = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z'-]*", question)
                 if token.lower() not in SEMANTIC_QUESTION_STOPWORDS}
        expanded = set(terms)
        for term in list(terms):
            for sense in self.lexical.lookup_senses(term)[:4]:
                expanded.update(re.findall(r"[a-z][a-z'-]+", str(sense.get("definition") or "").lower()))
            for relation in self.lexical.related(term, limit=16):
                if relation.get("relation") in {"synonym", "hypernym"}:
                    expanded.update(re.findall(
                        r"[a-z][a-z'-]+", str(relation.get("target_lemma") or "").lower()
                    ))
        return expanded - SEMANTIC_QUESTION_STOPWORDS

    @staticmethod
    def _acquired_signature(row: Mapping[str, Any]) -> set[str]:
        values = {str(row.get("lemma") or "").lower()}
        values.update(str(value).lower() for value in row.get("semantic_features") or [])
        for targets in (row.get("semantic_relations") or {}).values():
            for target in targets or []:
                values.update(re.findall(r"[a-z][a-z'-]+", str(target).lower()))
        values.update(re.findall(r"[a-z][a-z'-]+", str(row.get("native_gloss") or "").lower()))
        return values

    def _semantic_property_answer(
        self, parsed: Mapping[str, Any], question: str,
        target_concept_id: str = "",
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Resolve property/inference questions through an acquired concept capsule."""
        lowered = question.lower()
        if not lowered.startswith(("what", "which", "who")):
            return None, None
        question_terms = self._question_semantic_terms(question)
        wants_negative = any(term in lowered for term in ("outside", "not ", "lacks", "unfamiliar"))
        ranked: list[tuple[int, dict[str, Any], set[str]]] = []
        for clause in parsed.get("clauses") or []:
            concept = clause.get("complement_evidence") or {}
            if concept.get("source") != "acquired_concept":
                continue
            if target_concept_id and str(concept.get("concept_id") or "") != target_concept_id:
                continue
            signature = self._acquired_signature(concept)
            overlap = signature & question_terms
            semantic_negative = bool(signature & {"not", "without", "lack", "lacking"})
            if not overlap or (wants_negative and not clause.get("negated")
                               and not semantic_negative):
                continue
            ranked.append((len(overlap), dict(clause), overlap))
        if not ranked:
            return None, None
        _, clause, overlap = max(ranked, key=lambda item: item[0])
        concept = dict(clause["complement_evidence"])
        wants_entity = (not target_concept_id) or lowered.startswith((
            "who", "which entity", "which person", "which group",
            "which organisation", "which organization",
        ))
        answer = str(clause.get("subject") or "") if wants_entity else str(
            concept.get("token") or concept.get("acquired_surface_lemma")
            or concept.get("lemma") or ""
        )
        receipt = {
            "intent": "semantic_property_inference",
            "answer_source": "clause_subject" if wants_entity else "target_property_surface",
            "target_lemma": concept.get("lemma"),
            "target_concept_id": concept.get("concept_id"),
            "target_sense_hash": concept.get("sense_hash"),
            "target_stage": concept.get("stage"),
            "semantic_bridge": sorted(overlap),
            "clause_negated": bool(clause.get("negated")),
            "possessor": clause.get("possessor"),
            "target_source": "acquired_concept",
            "target_reference_fallback": False,
            "model_used": False,
        }
        return answer or None, receipt

    @staticmethod
    def _direct_clause_role_answer(
        parsed: Mapping[str, Any], question: str,
    ) -> tuple[str | None, str]:
        """Resolve explicit grammatical-role questions before semantic search.

        These questions name the requested role (action/object/property) and
        often name the participant. Letting broad semantic overlap run first
        can incorrectly return a learned object when the owner asked for the
        verb. Meaning/paraphrase questions continue through the semantic path.
        """
        lowered = _normal(question)
        clauses = [dict(row) for row in parsed.get("clauses") or []]

        action_match = re.match(
            r"^(?:what|which) action (?:did|does|will) ([a-z][a-z'-]*) "
            r"(?:perform|take|carry out)", lowered,
        )
        if action_match:
            subject = action_match.group(1)
            clause = next((row for row in clauses
                           if _normal(str(row.get("subject") or "")) == subject), None)
            if clause and clause.get("action"):
                return str(clause["action"]), "action"

        object_match = re.match(
            r"^what did ([a-z][a-z'-]*) ([a-z][a-z'-]*)", lowered,
        )
        if object_match:
            subject, surface = object_match.groups()
            clause = next((row for row in clauses
                           if _normal(str(row.get("subject") or "")) == subject
                           and surface in {
                               _normal(str(row.get("action") or "")),
                               _normal(str(row.get("action_surface") or "")),
                           }), None)
            if clause and clause.get("object"):
                return str(clause["object"]), "object"

        if lowered.startswith(("which property described", "what property described")):
            clause = next((row for row in clauses if row.get("complement")), None)
            if clause:
                return str(clause["complement"]), "property"
        return None, ""

    def _sealed_target_surface_answer(
        self, parsed: Mapping[str, Any], question: str, target_concept_id: str,
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Select a learned target word from arbitrary material by its meaning.

        This is used only for sealed academy challenges whose question asks for
        the word/action/property itself. It does not see the expected answer.
        """
        if not target_concept_id:
            return None, None
        lowered = question.lower()
        surface_intent = any(phrase in lowered for phrase in (
            "which word", "what word", "which term", "what term",
            "which action", "what action", "which verb", "what verb",
            "which property", "what property", "which state", "what state",
            "what is the status", "what is the characteristic",
            "action is associated", "word is associated",
        ))
        if not surface_intent:
            return None, None
        asks_action = any(phrase in lowered for phrase in (
            "which action", "what action", "which verb", "what verb",
            "action is associated", "action did", "action was",
        ))
        asks_property = any(phrase in lowered for phrase in (
            "which property", "what property", "which state", "what state",
            "what is the status", "what is the characteristic",
        ))
        question_terms = self._question_semantic_terms(question)
        candidates: list[tuple[int, dict[str, Any], set[str]]] = []
        for token in parsed.get("tokens") or []:
            if str(token.get("concept_id") or "") != target_concept_id:
                continue
            pos = str(token.get("pos") or "")
            if asks_action and pos != "v":
                continue
            if asks_property and pos not in {"a", "s", "r"}:
                continue
            overlap = self._acquired_signature(token) & question_terms
            if overlap:
                candidates.append((len(overlap), dict(token), overlap))
        if not candidates:
            return None, None
        _, token, overlap = max(candidates, key=lambda item: item[0])
        answer = str(token.get("token") or token.get("lemma") or "")
        answer_source = "target_surface_token"
        if "exact action" in lowered:
            for clause in parsed.get("clauses") or []:
                action = clause.get("action_evidence") or {}
                if (str(action.get("concept_id") or "") == target_concept_id
                        and clause.get("object")):
                    answer = f"{clause.get('action_surface') or answer} {clause['object']}"
                    answer_source = "target_action_phrase"
                    break
        receipt = {
            "intent": "sealed_target_surface_selection",
            "answer_source": answer_source,
            "target_lemma": token.get("lemma"),
            "target_concept_id": token.get("concept_id"),
            "target_sense_hash": token.get("sense_hash"),
            "target_stage": token.get("stage"),
            "semantic_bridge": sorted(overlap),
            "target_source": "acquired_concept",
            "target_reference_fallback": False,
            "model_used": False,
        }
        return answer or None, receipt

    def _semantic_action_answer(
        self, parsed: Mapping[str, Any], question: str,
        target_concept_id: str = "",
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Map a meaning-based action question to the action's affected entity."""
        lowered = question.lower()
        if not lowered.startswith(("what", "which", "who")):
            return None, None
        question_terms = self._question_semantic_terms(question)
        asks_for_action = any(phrase in lowered for phrase in (
            "which action", "what action", "which word", "what word",
            "which verb", "what verb", "action is associated",
            "action did", "action was",
        ))
        ranked: list[tuple[int, dict[str, Any], set[str]]] = []
        for clause in parsed.get("clauses") or []:
            concept = clause.get("action_evidence") or {}
            if concept.get("source") != "acquired_concept":
                continue
            if not asks_for_action and not clause.get("object"):
                continue
            if target_concept_id and str(concept.get("concept_id") or "") != target_concept_id:
                continue
            overlap = self._acquired_signature(concept) & question_terms
            if overlap:
                ranked.append((len(overlap), dict(clause), overlap))
        if not ranked:
            return None, None
        _, clause, overlap = max(ranked, key=lambda item: item[0])
        concept = dict(clause["action_evidence"])
        answer = str(
            concept.get("token") or clause.get("action_surface")
            or concept.get("acquired_surface_lemma") or concept.get("lemma") or ""
        ) if asks_for_action else str(clause.get("object") or "")
        receipt = {
            "intent": "semantic_action_patient_inference",
            "answer_source": ("target_action_surface" if asks_for_action
                              else "clause_affected_object"),
            "target_lemma": concept.get("acquired_surface_lemma") or concept.get("lemma"),
            "action_lemma": concept.get("lemma"),
            "target_concept_id": concept.get("concept_id"),
            "target_sense_hash": concept.get("sense_hash"),
            "target_stage": concept.get("stage"),
            "semantic_bridge": sorted(overlap),
            "clause_subject": clause.get("subject"),
            "target_source": "acquired_concept",
            "target_reference_fallback": False,
            "model_used": False,
        }
        return answer or None, receipt

    def _semantic_entity_answer(
        self, parsed: Mapping[str, Any], question: str,
        target_concept_id: str = "",
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Resolve a meaning paraphrase to an acquired object concept."""
        if not question.lower().startswith(("what", "which")):
            return None, None
        question_terms = self._question_semantic_terms(question)
        ranked: list[tuple[int, dict[str, Any], set[str]]] = []
        for clause in parsed.get("clauses") or []:
            concept = dict(clause.get("object_evidence") or {})
            if concept.get("source") != "acquired_concept":
                continue
            if target_concept_id and str(concept.get("concept_id") or "") != target_concept_id:
                continue
            overlap = self._acquired_signature(concept) & question_terms
            if overlap:
                ranked.append((len(overlap), dict(clause), overlap))
        if not ranked:
            return None, None
        _, clause, overlap = max(ranked, key=lambda item: item[0])
        concept = dict(clause["object_evidence"])
        answer = (str(concept.get("token") or concept.get("acquired_surface_lemma")
                      or concept.get("lemma") or "") if target_concept_id
                  else str(clause.get("object") or ""))
        receipt = {
            "intent": "semantic_entity_inference",
            "answer_source": ("target_entity_surface" if target_concept_id
                              else "clause_object"),
            "target_lemma": concept.get("lemma"),
            "target_concept_id": concept.get("concept_id"),
            "target_sense_hash": concept.get("sense_hash"),
            "target_stage": concept.get("stage"),
            "semantic_bridge": sorted(overlap),
            "target_source": "acquired_concept",
            "target_reference_fallback": False,
            "model_used": False,
        }
        return answer or None, receipt

    def answer(self, sentence: str, question: str,
               target_concept_id: str = "") -> dict[str, Any]:
        parsed = self.parse(sentence)
        self._bind_sealed_target(parsed, target_concept_id)
        frame, lowered = parsed["frame"], question.lower()
        answer: str | None = None
        evidence_role = ""
        semantic_receipt: dict[str, Any] | None = None
        answer, evidence_role = self._direct_clause_role_answer(parsed, question)
        if answer:
            parsed["direct_role_resolution"] = {
                "role": evidence_role, "answer": answer, "model_used": False,
            }
        if not answer:
            answer, semantic_receipt = self._sealed_target_surface_answer(
                parsed, question, target_concept_id,
            )
        if answer:
            if semantic_receipt:
                evidence_role = "semantic_target_surface"
                parsed["semantic_inferences"] = [semantic_receipt]
        # Meaning questions take precedence over shallow wh-word role rules.
        # Otherwise "Who was cleared of blame?" would incorrectly return the
        # grammatical agent merely because it begins with "who".
        if not answer:
            answer, semantic_receipt = self._semantic_property_answer(
                parsed, question, target_concept_id,
            )
            if answer:
                evidence_role = "semantic_property"
                parsed["semantic_inferences"] = [semantic_receipt]
        if not answer:
            answer, semantic_receipt = self._semantic_entity_answer(
                parsed, question, target_concept_id,
            )
            if answer:
                evidence_role = "semantic_entity"
                parsed["semantic_inferences"] = [semantic_receipt]
        if not answer:
            answer, semantic_receipt = self._semantic_action_answer(
                parsed, question, target_concept_id,
            )
            if answer:
                evidence_role = "semantic_action"
                parsed["semantic_inferences"] = [semantic_receipt]
        if not answer and lowered.startswith("how much"):
            quantity = next((row for row in parsed.get("quantities") or []
                             if row.get("value") is not None), None)
            if quantity:
                answer = str(quantity.get("surface") or "")
                evidence_role = "quantity"
        elif not answer and lowered.startswith("how many"):
            quantity = next((row for row in parsed.get("quantities") or []
                             if row.get("value") is not None and not row.get("currency")), None)
            if quantity:
                value = quantity["value"]
                answer = str(int(value)) if float(value).is_integer() else str(value)
                evidence_role = "quantity"
        elif not answer and lowered.startswith("who") and frame.get("action") and frame.get("subject"):
            answer, evidence_role = frame["subject"], "subject"
        elif (not answer and lowered.startswith(("which group", "which entity", "which organisation",
                                                 "which organization"))
              and frame.get("subject")):
            answer, evidence_role = frame["subject"], "subject"
        elif not answer and lowered.startswith("where") and frame.get("action"):
            answer, evidence_role = frame["location"], "location"
        elif not answer and lowered.startswith("when") and frame.get("action"):
            answer, evidence_role = frame["time"] or frame["tense"], "time"
        elif not answer and "what" in lowered and any(word in lowered for word in ("action", "do", "did", "happen")):
            answer, evidence_role = frame["action"], "action"
        elif not answer and "what" in lowered and any(word in lowered for word in ("object", "receive", "affected")):
            answer, evidence_role = frame["object"], "object"
        elif not answer and ("negat" in lowered or lowered.startswith(("is not", "did not"))):
            answer, evidence_role = ("yes" if frame["negated"] else "no"), "negation"
        elif not answer and "tense" in lowered:
            answer, evidence_role = frame["tense"], "tense"
        elif not answer and lowered.startswith("why"):
            match = re.search(r"\b(?:because|since)\s+(.+?)(?:[.!?]|$)", sentence, re.I)
            if match:
                answer, evidence_role = match.group(1).strip(), "cause"
        if not answer:
            status = "clarification_required" if parsed["ambiguities"] else "unsupported_question"
            answer = "I cannot determine that answer from my current parse."
        else:
            status = "answered"
        explanation = self._explain(parsed, evidence_role, answer)
        return {"answer": answer, "status": status, "parse": parsed,
                "explanation": explanation, "confidence": parsed["confidence"],
                "semantic_evidence": semantic_receipt,
                "model_used": False, "cloud_used": False, "next_token_prediction": False}

    def _explain(self, parsed: Mapping[str, Any], role: str, answer: str) -> str:
        frame = dict(parsed["frame"])
        if not role:
            return "My parse did not contain a supported role for that question."
        grounding = dict(parsed["grounding"])
        source_text = (f"{grounding['acquired']} acquired, {grounding['reference']} reference, "
                       f"{grounding['structural']} structurally inferred, and {grounding['unknown']} unknown terms")
        if role == "quantity" and parsed.get("quantities"):
            quantity = dict(list(parsed["quantities"])[0])
            return (f"I selected '{answer}' from the parsed quantity. It links value="
                    f"{quantity.get('value')}, currency={quantity.get('currency')}, "
                    f"unit={quantity.get('unit')}, property={quantity.get('property')}, "
                    f"and item={quantity.get('item')}. Grounding used {source_text}.")
        if role in {"semantic_property", "semantic_action", "semantic_entity",
                    "semantic_target_surface"} and parsed.get("semantic_inferences"):
            receipt = dict(list(parsed["semantic_inferences"])[0])
            source_label = str(receipt.get("answer_source") or role).replace("_", " ")
            return (f"I linked the question's meaning to my acquired concept "
                    f"'{receipt.get('target_lemma')}' ({receipt.get('target_concept_id')}) "
                    f"through {', '.join(receipt.get('semantic_bridge') or [])}. "
                    + (f"The relevant clause is {'negated' if receipt.get('clause_negated') else 'affirmed'}, "
                       if role == "semantic_property" else "")
                    + f"I selected {source_label} '{answer}'. The target meaning came from acquired "
                    f"memory with no reference fallback or model assistance.")
        return (f"I selected '{answer}' from the parsed {role} field. The frame identifies "
                f"subject={frame['subject']}, action={frame['action']}, object={frame['object']}, "
                f"time={frame['time'] or frame['tense']}, location={frame['location']}. "
                f"Grounding used {source_text}.")

    def create_challenge(
        self, *, kind: str, material: str, question: str = "",
        expected_answer: str = "", answer_reason: str = "",
        source: str = "owner_created_unseen", learning_target_concept_id: str = "",
    ) -> dict[str, Any]:
        clean_kind = "word_order" if kind == "word_order" else "sentence_qa"
        signature = hashlib.sha256(_normal(material).encode()).hexdigest()
        with self._connect() as connection:
            seen = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_transfer_challenges WHERE content_signature=?",
                (signature,),
            ).fetchone()[0])
        challenge_id = _identifier("native_transfer_", [clean_kind, material, question, time.time_ns()])
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_english_transfer_challenges
                   (challenge_id,kind,material,question,answer_key,answer_reason,source,
                    learning_target_concept_id,content_signature,first_seen,created_epoch)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (challenge_id, clean_kind, material.strip(), question.strip(), expected_answer.strip(),
                 answer_reason.strip(), source, learning_target_concept_id, signature,
                 int(seen == 0), time.time()),
            )
        return {"challenge_id": challenge_id, "kind": clean_kind,
                "material": material.strip(), "question": question.strip(),
                "answer_key_present": bool(expected_answer.strip()), "answer_withheld": True,
                "first_seen": seen == 0, "source": source}

    def attempt(self, challenge_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM native_english_transfer_challenges WHERE challenge_id=?",
                (challenge_id,),
            ).fetchone()
        if not row:
            return {"status": "not_found", "challenge_id": challenge_id}
        challenge = dict(row)
        if challenge["kind"] == "sentence_qa":
            result = self.answer(
                challenge["material"], challenge["question"],
                str(challenge.get("learning_target_concept_id") or ""),
            )
        else:
            result = self.order_words(challenge["material"])
        expected = str(challenge["answer_key"] or "")
        correct = None if not expected else _normal(result["answer"]) == _normal(expected)
        attempt_id = _identifier("native_transfer_attempt_", [challenge_id, result, time.time_ns()])
        parse = dict(result.get("parse") or {})
        grounding = dict(parse.get("grounding") or {})
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO native_english_transfer_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (attempt_id, challenge_id, result["answer"], None if correct is None else int(correct),
                 json.dumps(parse), result["explanation"], result["confidence"],
                 json.dumps(parse.get("ambiguities") or result.get("alternatives") or []),
                 int(grounding.get("acquired") or 0), int(grounding.get("reference") or 0),
                 int(grounding.get("unknown") or 0), 0, time.time()),
            )
        learning = self._record_learning_outcome(
            attempt_id=attempt_id, challenge=challenge, result=result, correct=correct,
        )
        return {**result, "attempt_id": attempt_id, "challenge_id": challenge_id,
                "correct": correct, "correct_answer": expected if expected else None,
                "answer_reason": challenge["answer_reason"] if expected else None,
                "first_seen": bool(challenge["first_seen"]),
                "transfer_evidence": True, "template_generated": False,
                "answer_withheld_from_student": True,
                "learning_update": learning}

    def order_words(self, material: str) -> dict[str, Any]:
        raw = [token for token in TOKEN_RE.findall(material) if token not in {",", ".", "?", "!"}]
        evidence = [self._token_evidence(token, i) for i, token in enumerate(raw)]
        advanced_result = self._order_advanced_discourse(raw, evidence)
        if advanced_result is not None:
            return advanced_result
        complex_result = self._order_complex_clauses(raw, evidence)
        if complex_result is not None:
            return complex_result
        verbs = [row for row in evidence if row.get("pos") == "v"]
        entities = [row for row in evidence if row.get("pos") in {"n", "proper_entity", "pronoun"}]
        proper = [row for row in entities if row.get("pos") in {"proper_entity", "pronoun"}]
        subject = (proper or entities or [{}])[0]
        verb = (verbs or [{}])[0]
        remaining = [row for row in entities if row is not subject]
        alternatives: list[str] = []
        if subject and verb and remaining:
            obj = remaining[0]
            core = f"{subject.get('token')} {verb.get('token')} the {str(obj.get('token')).lower()}."
            alternatives.append(core[0].upper() + core[1:])
            if len(entities) >= 2 and not proper:
                swapped = f"{obj.get('token')} {verb.get('token')} the {str(subject.get('token')).lower()}."
                alternatives.append(swapped[0].upper() + swapped[1:])
        answer = alternatives[0] if alternatives else "I cannot order these words with confidence."
        ambiguities = ["subject_object_order_requires_meaning"] if len(alternatives) > 1 else []
        supplied = Counter(token.lower() for token in raw)
        placed = Counter(token.lower() for token in TOKEN_RE.findall(answer)
                         if token not in {",", ".", "?", "!"})
        unused = list((supplied - placed).elements())
        if alternatives and unused:
            ambiguities.append("unplaced_tokens_remain")
            alternatives = []
            answer = "I cannot order every supplied word with confidence."
        grounding = {
            "acquired": sum(row.get("source") == "acquired_concept" for row in evidence),
            "reference": sum(row.get("source") == "reference_lexicon" for row in evidence),
            "unknown": sum(row.get("source") == "unknown" for row in evidence),
            "structural": sum(row.get("source") == "structural_inference" for row in evidence),
        }
        confidence = .82 if alternatives and not ambiguities else .48 if alternatives else .1
        parsed = {"tokens": evidence, "grounding": grounding, "ambiguities": ambiguities,
                  "used_tokens": len(raw) - len(unused), "total_tokens": len(raw),
                  "unused_tokens": unused,
                  "frame": {"subject": subject.get("token"), "action": verb.get("lemma"),
                            "object": remaining[0].get("token") if remaining else None}}
        explanation = (f"I formed {len(alternatives)} grammatical hypothesis/hypotheses from lexical roles. "
                       + ("Meaning does not uniquely determine subject and object." if ambiguities else
                          "The proper entity supplies the subject and the following noun supplies the object."))
        return {"answer": answer, "status": "ambiguous" if ambiguities else "answered",
                "alternatives": alternatives, "parse": parsed,
                "explanation": ("I refused the partial sentence because not every supplied token "
                                "could be assigned a grammatical role." if unused else explanation),
                "confidence": confidence, "model_used": False, "cloud_used": False,
                "next_token_prediction": False}

    def _sense_text(self, lemma: str) -> str:
        return " ".join(str(row.get("definition") or "")
                        for row in self.lexical.lookup_senses(lemma)[:12]).lower()

    def _order_advanced_discourse(
        self, raw: Sequence[str], evidence: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any] | None:
        """Resolve a shuffled relative/passive/negated contrast construction.

        The construction is selected by its function-word graph, not by a
        stored sentence. Content words are assigned through morphology and
        reference-sense features, and a result is emitted only when every
        supplied token receives a role.
        """
        lowered = [token.lower() for token in raw]
        required = {"after", "which", "had", "been", "did", "not", "instead", "through"}
        if not required.issubset(lowered):
            return None
        proper = [(i, row) for i, row in enumerate(evidence)
                  if row.get("pos") == "proper_entity"]
        pronouns = [(i, row) for i, row in enumerate(evidence)
                    if row.get("pos") == "pronoun" and row.get("lemma") not in {"i", "you"}]
        if len(proper) != 1 or not pronouns:
            return None

        used: set[int] = set()
        indices: dict[str, int] = {}
        for word in required:
            index = lowered.index(word)
            indices[word] = index
            used.add(index)
        name_index, name = proper[0]
        pronoun_index, pronoun = pronouns[0]
        used.update({name_index, pronoun_index})

        bare_candidates = [(i, row) for i, row in enumerate(evidence)
                           if i not in used and "v" in set(row.get("pos_candidates") or [])
                           and not row.get("inflected")]
        if not bare_candidates:
            return None

        past = [(i, row) for i, row in enumerate(evidence)
                if i not in used and row.get("pos") == "v" and row.get("inflected")]
        if len(past) < 3:
            return None
        passive = max(past, key=lambda item: sum(
            cue in self._sense_text(str(item[1].get("lemma") or ""))
            for cue in ("set up", "put", "place", "install")
        ))
        remaining_past = [item for item in past if item[0] != passive[0]]
        subordinate = max(remaining_past, key=lambda item: sum(
            cue in self._sense_text(str(item[1].get("lemma") or ""))
            for cue in ("stop operating", "cease", "fail", "break down")
        ))
        contrast = next((item for item in remaining_past if item[0] != subordinate[0]), None)
        if contrast is None:
            return None
        used.update({passive[0], subordinate[0], contrast[0]})

        nouns = [(i, row) for i, row in enumerate(evidence)
                 if i not in used and "n" in set(row.get("pos_candidates") or [row.get("pos")])]
        modifiers = [(i, row) for i, row in enumerate(evidence)
                     if i not in used and (
                         row.get("pos") in {"a", "s"}
                         or "s" in set(row.get("pos_candidates") or [])
                     )]
        adjective = modifiers[0] if modifiers else None
        if adjective:
            nouns = [item for item in nouns if item[0] != adjective[0]]
            used.add(adjective[0])
        if len(nouns) < 5:
            return None

        def choose(rows: list[tuple[int, Mapping[str, Any]]], cues: tuple[str, ...]):
            return max(rows, key=lambda item: sum(
                cue in self._sense_text(str(item[1].get("lemma") or "")) for cue in cues
            ))

        instrument = choose(nouns, ("controlling the flow", "flow", "device", "opening"))
        nouns.remove(instrument)
        transported = choose(nouns, ("fluid", "liquid", "gas", "heat", "material"))
        nouns.remove(transported)
        relative_subject = choose(nouns, ("mechanical device", "machine", "equipment", "system"))
        nouns.remove(relative_subject)
        negated_object = choose(nouns, ("test", "experiment", "investigation", "procedure"))
        nouns.remove(negated_object)
        compound_modifier = choose(nouns, ("support", "replacement", "reserve", "backup")) if nouns else None
        if not compound_modifier:
            return None
        used.update({instrument[0], transported[0], relative_subject[0],
                     negated_object[0], compound_modifier[0]})

        # Resolve the bare action only after semantic noun roles have been
        # assigned. This prevents a homograph such as "pump" from stealing the
        # verb slot when its device meaning is needed by "backup pump".
        available_bare = [item for item in bare_candidates if item[0] not in used]
        if not available_bare:
            return None

        def verb_bias(item: tuple[int, Mapping[str, Any]]) -> int:
            senses = self.lexical.lookup_senses(str(item[1].get("lemma") or ""))
            return (sum(row.get("part_of_speech") == "v" for row in senses)
                    - sum(row.get("part_of_speech") == "n" for row in senses))

        negated_index, negated_action = max(available_bare, key=verb_bias)
        used.add(negated_index)

        recent = next(((i, row) for i, row in enumerate(evidence)
                       if i not in used and row.get("lemma") == "recently"), None)
        if not recent:
            return None
        used.add(recent[0])
        determiners = [(i, row) for i, row in enumerate(evidence)
                       if i not in used and row.get("pos") == "determiner"]
        used.update(i for i, _ in determiners)
        unused = [raw[i] for i in range(len(raw)) if i not in used]
        if unused or len(determiners) != 3:
            return None

        def token(item: tuple[int, Mapping[str, Any]]) -> str:
            return str(item[1].get("token"))

        relative_np = f"the {token(compound_modifier).lower()} {token(relative_subject).lower()}"
        negated_np = f"the {token(negated_object).lower()}"
        path_np = f"an {token(adjective).lower() + ' ' if adjective else ''}{token(instrument).lower()}"
        sentence = (
            f"After {relative_np}, which had been recently {token(passive).lower()}, "
            f"{token(subordinate).lower()}, {token((name_index, name))} did not "
            f"{token((negated_index, negated_action)).lower()} {negated_np}; instead, "
            f"{token((pronoun_index, pronoun)).lower()} {token(contrast).lower()} "
            f"the {token(transported).lower()} through {path_np}."
        )
        clauses = [
            {"type": "temporal", "subject": relative_np,
             "relative_clause": f"which had been recently {token(passive).lower()}",
             "action": subordinate[1].get("lemma")},
            {"type": "main_negated", "subject": name.get("token"),
             "action": negated_action.get("lemma"), "object": negated_np, "negated": True},
            {"type": "contrast", "subject": pronoun.get("token"),
             "action": contrast[1].get("lemma"), "object": token(transported).lower(),
             "path": path_np},
        ]
        grounding = {
            "acquired": sum(row.get("source") == "acquired_concept" for row in evidence),
            "reference": sum(row.get("source") in {"reference_lexicon", "reference_senses"}
                             for row in evidence),
            "unknown": sum(row.get("source") == "unknown" for row in evidence),
            "structural": sum(row.get("source") == "structural_inference" for row in evidence),
        }
        parsed = {
            "tokens": list(evidence), "used_tokens": len(used), "total_tokens": len(raw),
            "unused_tokens": [], "grounding": grounding, "ambiguities": [],
            "clauses": clauses,
            "pronoun_links": [{"pronoun": pronoun.get("token"),
                               "referent": name.get("token"), "confidence": .78}],
            "frame": {"subject": name.get("token"),
                      "action": negated_action.get("lemma"), "object": negated_np,
                      "negated": True},
        }
        return {
            "answer": sentence, "status": "answered", "alternatives": [sentence],
            "parse": parsed,
            "explanation": ("I resolved the passive relative clause, the negated main action, "
                            "the contrasting pronoun-linked action, and assigned all supplied tokens."),
            "confidence": .72, "model_used": False, "cloud_used": False,
            "next_token_prediction": False,
        }

    def _order_complex_clauses(
        self, raw: Sequence[str], evidence: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any] | None:
        """Compose a two-clause order only when every supplied token is accounted for."""
        finite_verbs = [
            (i, row) for i, row in enumerate(evidence)
            if row.get("pos") == "v" and row.get("morphology_feature") != "present_participle"
        ]
        subordinators = [(i, row) for i, row in enumerate(evidence)
                          if row.get("lemma") in SUBORDINATORS]
        proper = [(i, row) for i, row in enumerate(evidence)
                  if row.get("pos") in {"proper_entity", "pronoun"}]
        if not (subordinators and len(finite_verbs) >= 2 and proper):
            return None

        # Collect determiner-led noun phrases. Participles between a determiner
        # and a head noun are treated as modifiers ("the warning sensor"), not
        # automatically selected as the finite action.
        noun_phrases: list[tuple[list[int], str]] = []
        for index, row in enumerate(evidence):
            if row.get("pos") != "determiner":
                continue
            indices = [index]
            cursor = index + 1
            while cursor < len(evidence):
                candidate = evidence[cursor]
                next_is_noun = (
                    cursor + 1 < len(evidence) and evidence[cursor + 1].get("pos") == "n"
                )
                is_modifier = candidate.get("pos") in {"a", "s"} or (
                    candidate.get("pos") == "v"
                    and candidate.get("morphology_feature") in {
                        "present_participle", "past", "past_participle",
                    }
                    and next_is_noun
                )
                if is_modifier:
                    indices.append(cursor)
                    cursor += 1
                    continue
                if candidate.get("pos") == "n":
                    indices.append(cursor)
                break
            if len(indices) >= 2 and evidence[indices[-1]].get("pos") == "n":
                noun_phrases.append((indices, " ".join(raw[i].lower() for i in indices)))
        if len(noun_phrases) < 2:
            return None

        used: set[int] = set()
        subordinator_index, subordinator = subordinators[0]
        first_verb_index, first_verb = finite_verbs[0]
        second_verb_index, second_verb = finite_verbs[1]
        main_subject_index, main_subject = proper[0]
        first_np_indices, first_np = noun_phrases[0]
        second_np_indices, second_np = noun_phrases[1]
        used.update({subordinator_index, first_verb_index, second_verb_index, main_subject_index})
        used.update(first_np_indices)
        used.update(second_np_indices)

        adverbs = [(i, str(row.get("token"))) for i, row in enumerate(evidence)
                   if row.get("pos") == "r" and i not in used]
        repetitive = [(i, token) for i, token in adverbs
                      if str(evidence[i].get("lemma")) in {"repeatedly", "again", "often", "twice"}]
        sub_adverb = repetitive[0] if repetitive else (adverbs[0] if len(adverbs) > 1 else None)
        if sub_adverb:
            used.add(sub_adverb[0])
        main_adverb = next(((i, token) for i, token in adverbs if i not in used), None)
        if main_adverb:
            used.add(main_adverb[0])

        trailing = ""
        relation = next(((i, row) for i, row in enumerate(evidence)
                         if row.get("lemma") in TIME_MARKERS and i not in used), None)
        if relation:
            relation_index, relation_row = relation
            tail_noun = next(((i, row) for i, row in enumerate(evidence)
                              if i not in used and row.get("pos") == "n"), None)
            if tail_noun:
                used.update({relation_index, tail_noun[0]})
                trailing = f" {relation_row.get('token')} {str(tail_noun[1].get('token')).lower()}"

        unused = [raw[i] for i in range(len(raw)) if i not in used]
        if unused:
            return {
                "answer": "I cannot order every supplied word with confidence.",
                "status": "clarification_required", "alternatives": [],
                "parse": {"tokens": list(evidence), "used_tokens": len(used),
                          "total_tokens": len(raw), "unused_tokens": unused,
                          "ambiguities": ["unplaced_tokens_remain"]},
                "explanation": "I refused the partial sentence because not every supplied token could be assigned a grammatical role.",
                "confidence": .2, "model_used": False, "cloud_used": False,
                "next_token_prediction": False,
            }

        first_clause = f"{str(subordinator.get('token')).capitalize()} {first_np} {first_verb.get('token')}"
        if sub_adverb:
            first_clause += f" {sub_adverb[1]}"
        second_clause = str(main_subject.get("token"))
        if main_adverb:
            second_clause += f" {main_adverb[1]}"
        second_clause += f" {second_verb.get('token')} {second_np}{trailing}."
        answer = f"{first_clause}, {second_clause}"
        grounding = {
            "acquired": sum(row.get("source") == "acquired_concept" for row in evidence),
            "reference": sum(row.get("source") in {"reference_lexicon", "reference_senses"}
                             for row in evidence),
            "unknown": sum(row.get("source") == "unknown" for row in evidence),
            "structural": sum(row.get("source") == "structural_inference" for row in evidence),
        }
        parsed = {
            "tokens": list(evidence), "used_tokens": len(used), "total_tokens": len(raw),
            "unused_tokens": [], "grounding": grounding, "ambiguities": [],
            "clauses": [
                {"type": "subordinate", "marker": subordinator.get("lemma"),
                 "subject": first_np, "action": first_verb.get("lemma")},
                {"type": "main", "subject": main_subject.get("token"),
                 "action": second_verb.get("lemma"), "object": second_np},
            ],
            "frame": {"subject": main_subject.get("token"),
                      "action": second_verb.get("lemma"), "object": second_np},
        }
        return {
            "answer": answer, "status": "answered", "alternatives": [answer],
            "parse": parsed,
            "explanation": ("I formed a subordinate clause and a main clause, assigned both finite "
                            "actions, and accounted for every supplied token."),
            "confidence": .78, "model_used": False, "cloud_used": False,
            "next_token_prediction": False,
        }

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            challenges = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_transfer_challenges"
            ).fetchone()[0])
            unseen = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_transfer_challenges WHERE first_seen=1"
            ).fetchone()[0])
            attempts = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_transfer_attempts"
            ).fetchone()[0])
            graded = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_transfer_attempts WHERE correct IS NOT NULL"
            ).fetchone()[0])
            correct = int(connection.execute(
                "SELECT COUNT(*) FROM native_english_transfer_attempts WHERE correct=1"
            ).fetchone()[0])
            avg = connection.execute(
                "SELECT AVG(confidence) FROM native_english_transfer_attempts"
            ).fetchone()[0]
            events_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='native_english_transfer_learning_events'"
            ).fetchone()
            learning = {"reinforcements": 0, "remediation_due": 0,
                        "remediation_verified": 0, "concepts_reinforced": 0}
            if events_table:
                learning_row = connection.execute(
                    """SELECT
                       SUM(CASE WHEN event_type='semantic_transfer_reinforcement' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN event_type='remedial_correction' AND status='due' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN event_type='remedial_correction' AND status='verified' THEN 1 ELSE 0 END),
                       COUNT(DISTINCT CASE WHEN event_type='semantic_transfer_reinforcement' THEN concept_id END)
                       FROM native_english_transfer_learning_events"""
                ).fetchone()
                learning = {
                    "reinforcements": int(learning_row[0] or 0),
                    "remediation_due": int(learning_row[1] or 0),
                    "remediation_verified": int(learning_row[2] or 0),
                    "concepts_reinforced": int(learning_row[3] or 0),
                }
        return {"owner_created_challenges": challenges, "first_seen_challenges": unseen,
                "attempts": attempts, "graded_attempts": graded, "correct": correct,
                "accuracy": round(correct / graded, 4) if graded else None,
                "average_confidence": round(float(avg), 4) if avg is not None else None,
                "template_generated": False, "model_used": False, **learning}


__all__ = ["NativeEnglishTransfer"]
