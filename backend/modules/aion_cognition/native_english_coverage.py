"""Install and measure broad native-English coverage on Aion's SD store."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterable

from backend.modules.aion_cognition.native_english_transfer import NativeEnglishTransfer, _normal
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


def _sense_id(lemma: str, pos: str, definition: str) -> str:
    raw = json.dumps([lemma, pos, definition], ensure_ascii=False).encode()
    return "lexical_sense_" + hashlib.sha256(raw).hexdigest()[:24]


def _regular_verb_forms(lemma: str) -> list[tuple[str, str]]:
    if not lemma.isalpha() or len(lemma) < 2:
        return []
    if lemma.endswith("e"):
        past, gerund = lemma + "d", lemma[:-1] + "ing"
    elif lemma.endswith("y") and len(lemma) > 2 and lemma[-2] not in "aeiou":
        past, gerund = lemma[:-1] + "ied", lemma + "ing"
    else:
        past, gerund = lemma + "ed", lemma + "ing"
    third = lemma[:-1] + "ies" if lemma.endswith("y") and lemma[-2] not in "aeiou" else (
        lemma + "es" if lemma.endswith(("s", "x", "z", "ch", "sh", "o")) else lemma + "s"
    )
    return [(past, "past"), (past, "past_participle"),
            (gerund, "present_participle"), (third, "third_person_singular")]


def install_wordnet_foundation(
    *, repo_root: Path | str,
    corpus_root: Path | str = "/Volumes/TESSARISQ38/TessarisLearning/AION/corpora",
) -> dict[str, Any]:
    """Populate sense-level and morphology tables from the local WordNet corpus."""
    import nltk
    nltk.data.path.insert(0, str(Path(corpus_root)))
    from nltk.corpus import wordnet as wn

    lexical = NativeLexicalIntelligence(repo_root=Path(repo_root))
    now = time.time()
    sense_rows: list[tuple[Any, ...]] = []
    verb_lemmas: set[str] = set()
    synsets = 0
    for synset in wn.all_synsets():
        synsets += 1
        pos = str(synset.pos())
        definition = " ".join(str(synset.definition()).split())
        examples = json.dumps([" ".join(str(item).split()) for item in synset.examples()])
        for lemma_obj in synset.lemmas():
            lemma = " ".join(str(lemma_obj.name()).lower().replace("_", " ").split())
            if not lemma:
                continue
            if pos == "v":
                verb_lemmas.add(lemma)
            sense_rows.append((_sense_id(lemma, pos, definition), lemma, pos, definition,
                               examples, "princeton_wordnet_3.0", synset.name(), 1, now))
    with lexical._connect() as connection:
        connection.executemany(
            """INSERT INTO lexical_senses(
               sense_id,lemma,part_of_speech,definition,examples_json,source,source_ref,
               verified,created_epoch) VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(lemma,part_of_speech,definition) DO UPDATE SET
               examples_json=excluded.examples_json,verified=1""", sense_rows,
        )
        morphology_rows: list[tuple[Any, ...]] = []
        for lemma in verb_lemmas:
            for surface, feature in _regular_verb_forms(lemma):
                morphology_rows.append((surface, lemma, "v", feature,
                                        "aion_regular_morphology_v1", 1))
        for pos, exception_map in wn._exception_map.items():
            for surface, lemmas in exception_map.items():
                for lemma in lemmas:
                    morphology_rows.append((surface.replace("_", " "),
                                            lemma.replace("_", " "), pos,
                                            "irregular", "princeton_wordnet_3.0", 1))
        connection.executemany(
            """INSERT OR REPLACE INTO morphology_forms(
               surface,lemma,part_of_speech,feature,source,verified) VALUES(?,?,?,?,?,?)""",
            morphology_rows,
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES('sense_inventory_installed_epoch',?)",
            (str(now),),
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES('sense_inventory_source',?)",
            ("princeton_wordnet_3.0",),
        )
    return {"status": "installed", "synsets": synsets, "senses": len(sense_rows),
            "verb_lemmas": len(verb_lemmas), "morphology_forms": len(morphology_rows),
            "database_path": str(lexical.database_path), "corpus_root": str(corpus_root)}


COVERAGE_CASES: tuple[dict[str, str], ...] = (
    {"category": "currency_quantity", "sentence": "The price per gallon was £8.",
     "question": "How much was a gallon?", "expected": "£8"},
    {"category": "currency_quantity", "sentence": "The ticket cost €40 per person.",
     "question": "How much was the ticket?", "expected": "€40"},
    {"category": "currency_quantity", "sentence": "The rate per hour was $4.25.",
     "question": "How much was the hourly rate?", "expected": "$4.25"},
    {"category": "numeric_quantity", "sentence": "The laboratory received 18 samples.",
     "question": "How many samples were received?", "expected": "18"},
    {"category": "irregular_morphology", "sentence": "Yesterday, Kellan went to the laboratory.",
     "question": "What action happened?", "expected": "go"},
    {"category": "irregular_morphology", "sentence": "Yesterday, Kellan got the report.",
     "question": "What action happened?", "expected": "get"},
    {"category": "regular_morphology", "sentence": "Yesterday, Kellan repaired the robot.",
     "question": "What action happened?", "expected": "repair"},
    {"category": "regular_morphology", "sentence": "Yesterday, Zara carried the parcel.",
     "question": "What action happened?", "expected": "carry"},
    {"category": "semantic_roles", "sentence": "After lunch, Xanthe inspected the machine in the workshop.",
     "question": "Who performed the action?", "expected": "Xanthe"},
    {"category": "semantic_roles", "sentence": "After lunch, Xanthe inspected the machine in the workshop.",
     "question": "Where did the action happen?", "expected": "in the workshop"},
    {"category": "tense_negation", "sentence": "Niko did not open the message.",
     "question": "Is the action negated?", "expected": "yes"},
    {"category": "tense_negation", "sentence": "Amara will verify the report.",
     "question": "What tense is the sentence?", "expected": "future"},
    {"category": "causal_question", "sentence": "Mira waited because the laboratory was closed.",
     "question": "Why did Mira wait?", "expected": "the laboratory was closed"},
    {"category": "spelling_resilience", "sentence": "Wehn I went to the garage, the price per gallon was £8.",
     "question": "How much was a gallon?", "expected": "£8"},
    {"category": "temporal_roles", "sentence": "Last Thursday, Mireya polished the telescope in the observatory.",
     "question": "Who polished the telescope?", "expected": "Mireya"},
    {"category": "advanced_discourse_construction", "kind": "word_order",
     "sentence": "rerouted which the experiment an failed Amara recently pump coolant instead through had she abandon auxiliary not been the after valve backup did installed",
     "question": "", "expected": "After the backup pump, which had been recently installed, failed, Amara did not abandon the experiment; instead, she rerouted the coolant through an auxiliary valve."},
)


def expanded_coverage_cases(rounds: int = 50) -> tuple[dict[str, str], ...]:
    """Create a broad deterministic regression matrix, not a mastery claim."""
    names = ("Amina", "Borek", "Cyra", "Dario", "Elif", "Farah", "Galen", "Hana",
             "Ivo", "Juno", "Kavi", "Liora", "Marek", "Nia", "Orin", "Pia")
    objects = ("report", "parcel", "machine", "message", "sample", "invoice", "sensor", "document")
    places = ("laboratory", "workshop", "library", "garage", "station", "office", "garden", "archive")
    regular = (("inspect", "inspected"), ("repair", "repaired"), ("calculate", "calculated"),
               ("verify", "verified"), ("open", "opened"), ("paint", "painted"),
               ("move", "moved"), ("carry", "carried"))
    irregular = (("go", "went"), ("get", "got"), ("make", "made"), ("take", "took"),
                 ("give", "gave"), ("write", "wrote"), ("eat", "ate"), ("drink", "drank"),
                 ("see", "saw"), ("come", "came"), ("run", "ran"), ("buy", "bought"),
                 ("bring", "brought"), ("think", "thought"), ("choose", "chose"),
                 ("speak", "spoke"))
    currencies = (("£", "GBP"), ("$", "USD"), ("€", "EUR"), ("¥", "JPY"))
    units = ("gallon", "litre", "kilogram", "person", "hour", "item")
    rows: list[dict[str, str]] = []
    for index in range(max(1, rounds)):
        name = names[index % len(names)]
        obj = objects[(index * 3) % len(objects)]
        place = places[(index * 5) % len(places)]
        base, past = regular[index % len(regular)]
        irregular_base, irregular_past = irregular[index % len(irregular)]
        symbol, _ = currencies[index % len(currencies)]
        unit = units[index % len(units)]
        value = index % 37 + 1
        decimal = f"{value}.{(index * 7) % 100:02d}"
        rows.extend((
            {"category": "currency_quantity", "sentence": f"The price per {unit} was {symbol}{decimal}.",
             "question": f"How much was the price per {unit}?", "expected": f"{symbol}{decimal}"},
            {"category": "numeric_quantity", "sentence": f"The laboratory received {value} samples.",
             "question": "How many samples were received?", "expected": str(value)},
            {"category": "regular_morphology", "sentence": f"Yesterday, {name} {past} the {obj}.",
             "question": "What action happened?", "expected": base},
            {"category": "irregular_morphology", "sentence": f"Yesterday, {name} {irregular_past} the {obj}.",
             "question": "What action happened?", "expected": irregular_base},
            {"category": "semantic_roles", "sentence": f"After lunch, {name} {past} the {obj} in the {place}.",
             "question": "Who performed the action?", "expected": name},
            {"category": "location_time", "sentence": f"Before dinner, {name} {past} the {obj} in the {place}.",
             "question": "Where did the action happen?", "expected": f"in the {place}"},
            {"category": "tense_negation", "sentence": f"{name} did not {base} the {obj}.",
             "question": "Is the action negated?", "expected": "yes"},
            {"category": "causal_question", "sentence": f"{name} waited because the {place} was closed.",
             "question": f"Why did {name} wait?", "expected": f"the {place} was closed"},
        ))
    return tuple(rows)


class NativeEnglishCoverage:
    def __init__(self, *, repo_root: Path | str,
                 lexical: NativeLexicalIntelligence | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.transfer = NativeEnglishTransfer(repo_root=self.repo_root, lexical=self.lexical)
        self.database_path = self.lexical.database_path
        with self.lexical._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_english_coverage_results (
                    run_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sentence TEXT NOT NULL,
                    question TEXT NOT NULL,
                    expected TEXT NOT NULL,
                    actual TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_epoch REAL NOT NULL,
                    PRIMARY KEY(run_id,case_id)
                );
                """
            )

    def run(self, cases: Iterable[dict[str, str]] = COVERAGE_CASES) -> dict[str, Any]:
        now = time.time()
        run_id = "english_coverage_" + hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:20]
        results: list[dict[str, Any]] = []
        for index, case in enumerate(cases):
            result = (
                self.transfer.order_words(case["sentence"])
                if case.get("kind") == "word_order"
                else self.transfer.answer(case["sentence"], case["question"])
            )
            passed = _normal(result["answer"]) == _normal(case["expected"])
            row = {"case_id": f"case_{index + 1:04d}", **case,
                   "actual": result["answer"], "passed": passed,
                   "confidence": float(result["confidence"]), "detail": result}
            results.append(row)
        with self.lexical._connect() as connection:
            connection.executemany(
                "INSERT INTO native_english_coverage_results VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                [(run_id, row["case_id"], row["category"], row["sentence"], row["question"],
                  row["expected"], row["actual"], int(row["passed"]), row["confidence"],
                  json.dumps(row["detail"]), now) for row in results],
            )
        categories: dict[str, dict[str, Any]] = {}
        for row in results:
            bucket = categories.setdefault(row["category"], {"tested": 0, "passed": 0})
            bucket["tested"] += 1
            bucket["passed"] += int(row["passed"])
        for bucket in categories.values():
            bucket["accuracy"] = round(bucket["passed"] / bucket["tested"], 4)
        passed_count = sum(int(row["passed"]) for row in results)
        return {"run_id": run_id, "tested": len(results), "passed": passed_count,
                "accuracy": round(passed_count / len(results), 4) if results else None,
                "categories": categories,
                "failures": [{key: row[key] for key in (
                    "case_id", "category", "sentence", "question", "expected", "actual",
                )} for row in results if not row["passed"]],
                "model_used": False, "template_answers_used": False}

    def metrics(self) -> dict[str, Any]:
        with self.lexical._connect() as connection:
            senses = int(connection.execute("SELECT COUNT(*) FROM lexical_senses").fetchone()[0])
            lemmas = int(connection.execute(
                "SELECT COUNT(DISTINCT lemma) FROM lexical_senses"
            ).fetchone()[0])
            multi_pos = int(connection.execute(
                "SELECT COUNT(*) FROM (SELECT lemma FROM lexical_senses GROUP BY lemma "
                "HAVING COUNT(DISTINCT part_of_speech)>1)"
            ).fetchone()[0])
            morphology = int(connection.execute(
                "SELECT COUNT(*) FROM morphology_forms"
            ).fetchone()[0])
            latest = connection.execute(
                "SELECT run_id,MAX(created_epoch) epoch FROM native_english_coverage_results"
            ).fetchone()
            rows = []
            if latest and latest["run_id"]:
                rows = connection.execute(
                    """SELECT category,COUNT(*) tested,SUM(passed) passed,
                       AVG(confidence) confidence FROM native_english_coverage_results
                       WHERE run_id=? GROUP BY category ORDER BY category""",
                    (latest["run_id"],),
                ).fetchall()
        categories = {str(row["category"]): {
            "tested": int(row["tested"]), "passed": int(row["passed"] or 0),
            "accuracy": round(int(row["passed"] or 0) / int(row["tested"]), 4),
            "average_confidence": round(float(row["confidence"] or 0), 4),
        } for row in rows}
        return {"lexical_senses": senses, "sense_lemmas": lemmas,
                "multi_part_of_speech_lemmas": multi_pos,
                "morphology_forms": morphology, "latest_run": latest["run_id"] if latest else None,
                "latest_categories": categories,
                "claim_boundary": "Coverage is reported per tested category, never inferred from dictionary size."}


__all__ = ["COVERAGE_CASES", "NativeEnglishCoverage", "expanded_coverage_cases",
           "install_wordnet_foundation"]
