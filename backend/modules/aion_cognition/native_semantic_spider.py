"""Bounded local semantic crawler for Aion's native English acquisition.

The crawler traverses definitions and thesaurus relations as a graph.  Reading
never counts as competence: each completed page is handed to the existing
closed-book Word Wall before concepts can be promoted.  Wikipedia is an
optional, tightly capped and locally cached context source.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time
from typing import Any, Iterable
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.modules.aion_cognition.sqlite_connection import connect as sqlite_connect
from backend.modules.aion_cognition.native_lexical_intelligence import (
    NativeLexicalIntelligence, STOPWORDS,
)
from backend.modules.aion_cognition.native_wordwall_learning import NativeWordwallLearning


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
DEFAULT_SEEDS = ("language", "meaning", "context", "reason", "knowledge", "explain")


def _id(prefix: str, *parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()[:24]


class NativeSemanticSpider:
    """Single-writer, capped semantic frontier persisted in Aion's SD database."""

    def __init__(
        self, *, repo_root: Path | str,
        lexical: NativeLexicalIntelligence | None = None,
        wikipedia_enabled: bool | None = None,
        macos_dictionary_enabled: bool | None = None,
        words_per_page: int = 8,
        max_open_pages: int = 4,
        max_discoveries_per_page: int = 16,
        max_frontier: int = 64,
        wikipedia_words_per_page: int = 2,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.lexical = lexical or NativeLexicalIntelligence(repo_root=self.repo_root)
        self.database_path = self.lexical.database_path
        self.wordwall = NativeWordwallLearning(repo_root=self.repo_root, lexical=self.lexical)
        self.wikipedia_enabled = (
            os.getenv("AION_SEMANTIC_SPIDER_WIKIPEDIA", "1") not in {"0", "false", "False"}
            if wikipedia_enabled is None else bool(wikipedia_enabled)
        )
        self.macos_dictionary_enabled = (
            os.getenv("AION_SEMANTIC_SPIDER_MACOS_DICTIONARY", "1") not in {"0", "false", "False"}
            if macos_dictionary_enabled is None else bool(macos_dictionary_enabled)
        )
        self.macos_dictionary_reader = Path(__file__).with_name("macos_dictionary_lookup.swift")
        self.words_per_page = max(2, min(24, int(words_per_page)))
        self.max_open_pages = max(1, min(8, int(max_open_pages)))
        self.max_discoveries_per_page = max(2, min(48, int(max_discoveries_per_page)))
        self.max_frontier = max(self.words_per_page, min(256, int(max_frontier)))
        self.wikipedia_words_per_page = max(0, min(4, int(wikipedia_words_per_page)))
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
                CREATE TABLE IF NOT EXISTS semantic_spider_state (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    running INTEGER NOT NULL DEFAULT 0,
                    seed TEXT NOT NULL DEFAULT '',
                    pages_completed INTEGER NOT NULL DEFAULT 0,
                    words_read INTEGER NOT NULL DEFAULT 0,
                    discoveries INTEGER NOT NULL DEFAULT 0,
                    tests_attempted INTEGER NOT NULL DEFAULT 0,
                    tests_correct INTEGER NOT NULL DEFAULT 0,
                    current_page_id TEXT,
                    current_word TEXT NOT NULL DEFAULT '',
                    last_error TEXT,
                    busy INTEGER NOT NULL DEFAULT 0,
                    lease_epoch REAL,
                    updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_spider_pages (
                    page_id TEXT PRIMARY KEY,
                    page_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    words_json TEXT NOT NULL DEFAULT '[]',
                    discoveries_json TEXT NOT NULL DEFAULT '[]',
                    source_counts_json TEXT NOT NULL DEFAULT '{}',
                    test_json TEXT NOT NULL DEFAULT '{}',
                    created_epoch REAL NOT NULL,
                    completed_epoch REAL
                );
                CREATE TABLE IF NOT EXISTS semantic_spider_frontier (
                    lemma TEXT PRIMARY KEY,
                    parent_lemma TEXT NOT NULL DEFAULT '',
                    relation TEXT NOT NULL DEFAULT 'seed',
                    depth INTEGER NOT NULL DEFAULT 0,
                    priority REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'queued',
                    created_epoch REAL NOT NULL,
                    updated_epoch REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS semantic_spider_frontier_queue
                    ON semantic_spider_frontier(status,priority DESC,created_epoch,lemma);
                CREATE TABLE IF NOT EXISTS semantic_spider_events (
                    event_id TEXT PRIMARY KEY,
                    page_id TEXT,
                    event_type TEXT NOT NULL,
                    from_word TEXT NOT NULL DEFAULT '',
                    to_word TEXT NOT NULL DEFAULT '',
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_spider_wikipedia_cache (
                    lemma TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    url TEXT NOT NULL,
                    fetched_epoch REAL NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO semantic_spider_state(singleton,updated_epoch) VALUES(1,?)",
                (time.time(),),
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(semantic_spider_state)")}
            if "busy" not in columns:
                connection.execute("ALTER TABLE semantic_spider_state ADD COLUMN busy INTEGER NOT NULL DEFAULT 0")
            if "lease_epoch" not in columns:
                connection.execute("ALTER TABLE semantic_spider_state ADD COLUMN lease_epoch REAL")
            self._migrate_legacy_page_tests(connection)
            self._reconcile_state(connection)

    def _migrate_legacy_page_tests(self, connection: sqlite3.Connection) -> None:
        """Quarantine old page results that tested the global queue, not the page."""
        rows = connection.execute(
            "SELECT page_id,words_json,test_json FROM semantic_spider_pages WHERE status='tested'"
        ).fetchall()
        for row in rows:
            words = json.loads(row["words_json"] or "[]")
            result = json.loads(row["test_json"] or "{}")
            if (
                result.get("page_certified") is True
                and str(result.get("certification_kind") or "").endswith(
                    "exact_page_closed_book_v1"
                )
            ):
                continue
            requested = list(dict.fromkeys(
                str(word.get("lemma") or "").strip().lower() for word in words
                if str(word.get("lemma") or "").strip()
            ))
            tested = list(dict.fromkeys(
                str(lemma or "").strip().lower()
                for lemma in (result.get("tested_lemmas") or result.get("lemmas") or [])
                if str(lemma or "").strip()
            ))
            exact = bool(
                requested and len(tested) == len(requested)
                and set(tested) == set(requested)
                and int(result.get("attempted") or 0) == len(requested)
            )
            integrity = (
                result.get("expected_withheld") is True
                and result.get("model_used") is False
                and result.get("cloud_used") is False
            )
            if exact and integrity:
                result.update({
                    "requested_lemmas": requested, "tested_lemmas": tested,
                    "coverage_count": len(requested), "coverage_total": len(requested),
                    "coverage_ratio": 1.0, "page_certified": True,
                    "certification_kind": result.get("certification_kind")
                    or "migrated_exact_page_closed_book_v1",
                })
                connection.execute(
                    "UPDATE semantic_spider_pages SET test_json=? WHERE page_id=?",
                    (json.dumps(result), row["page_id"]),
                )
            else:
                result.update({
                    "page_certified": False,
                    "legacy_uncertified": True,
                    "certification_reason": "historical_global_queue_test_did_not_cover_this_page",
                    "requested_lemmas": requested,
                    "tested_lemmas": tested,
                    "coverage_count": len(set(requested) & set(tested)),
                    "coverage_total": len(requested),
                    "coverage_ratio": round(
                        len(set(requested) & set(tested)) / len(requested), 4
                    ) if requested else 0.0,
                })
                connection.execute(
                    """UPDATE semantic_spider_pages
                       SET status='legacy_uncertified',test_json=? WHERE page_id=?""",
                    (json.dumps(result), row["page_id"]),
                )

    def _reconcile_state(self, connection: sqlite3.Connection) -> None:
        """Rebuild aggregate counters and retire pages orphaned by an interrupted caller."""
        state = connection.execute(
            "SELECT current_page_id FROM semantic_spider_state WHERE singleton=1"
        ).fetchone()
        current_page_id = str(state["current_page_id"] or "") if state else ""
        if current_page_id:
            connection.execute(
                "UPDATE semantic_spider_pages SET status='interrupted' "
                "WHERE status='reading' AND page_id<>?", (current_page_id,),
            )
        tested = connection.execute(
            "SELECT test_json FROM semantic_spider_pages WHERE status='tested'"
        ).fetchall()
        attempted = correct = 0
        for row in tested:
            result = json.loads(row["test_json"] or "{}")
            if result.get("page_certified") is not True:
                continue
            attempted += int(result.get("attempted") or 0)
            correct += int(result.get("correct") or 0)
        certified_count = sum(
            json.loads(row["test_json"] or "{}").get("page_certified") is True
            for row in tested
        )
        connection.execute(
            """UPDATE semantic_spider_state SET pages_completed=?,tests_attempted=?,tests_correct=?,
               busy=CASE WHEN lease_epoch>? THEN busy ELSE 0 END,updated_epoch=? WHERE singleton=1""",
            (certified_count, attempted, correct, time.time() - 30, time.time()),
        )

    def _event(self, connection: sqlite3.Connection, event_type: str, *,
               page_id: str | None = None, from_word: str = "", to_word: str = "",
               detail: dict[str, Any] | None = None) -> None:
        now = time.time()
        connection.execute(
            "INSERT INTO semantic_spider_events VALUES(?,?,?,?,?,?,?)",
            (_id("spider_event_", event_type, page_id, from_word, to_word, time.time_ns()),
             page_id, event_type, from_word, to_word, json.dumps(detail or {}), now),
        )

    def _queue(self, connection: sqlite3.Connection, lemma: str, *, parent: str = "",
               relation: str = "discovered", depth: int = 0, priority: float = 0.0) -> bool:
        clean = " ".join(str(lemma).lower().replace("_", " ").split())
        if not clean or clean in STOPWORDS or len(clean) < 3 or not self.lexical.lookup_senses(clean):
            return False
        queued = int(connection.execute(
            "SELECT COUNT(*) FROM semantic_spider_frontier WHERE status='queued'"
        ).fetchone()[0])
        if queued >= self.max_frontier:
            return False
        now = time.time()
        before = connection.total_changes
        connection.execute(
            """INSERT OR IGNORE INTO semantic_spider_frontier
               VALUES(?,?,?,?,?,'queued',?,?)""",
            (clean, parent, relation, depth, float(priority), now, now),
        )
        return connection.total_changes > before

    def start(self, seed: str = "language") -> dict[str, Any]:
        clean = " ".join(str(seed or "language").lower().split())
        if not self.lexical.lookup_senses(clean):
            clean = next((word for word in DEFAULT_SEEDS if self.lexical.lookup_senses(word)), "language")
        with self._connect() as connection:
            self._queue(connection, clean, relation="owner_seed", priority=100.0)
            connection.execute(
                "UPDATE semantic_spider_state SET running=1,seed=?,last_error=NULL,updated_epoch=? WHERE singleton=1",
                (clean, time.time()),
            )
            self._event(connection, "crawler_started", to_word=clean,
                        detail={"caps": self.caps()})
        return self.status()

    def pause(self) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "UPDATE semantic_spider_state SET running=0,updated_epoch=? WHERE singleton=1",
                (time.time(),),
            )
            self._event(connection, "crawler_paused")
        return self.status()

    def caps(self) -> dict[str, int]:
        return {"max_open_pages": self.max_open_pages, "words_per_page": self.words_per_page,
                "max_discoveries_per_page": self.max_discoveries_per_page,
                "max_frontier": self.max_frontier,
                "wikipedia_words_per_page": self.wikipedia_words_per_page}

    def _new_page(self, connection: sqlite3.Connection, seed: str) -> str:
        number = int(connection.execute(
            "SELECT COALESCE(MAX(page_number),0)+1 FROM semantic_spider_pages"
        ).fetchone()[0])
        page_id = _id("semantic_page_", number, seed, time.time_ns())
        now = time.time()
        connection.execute(
            "INSERT INTO semantic_spider_pages VALUES(?,?,'reading',?,'[]','[]','{}','{}',?,NULL)",
            (page_id, number, seed, now),
        )
        connection.execute(
            "UPDATE semantic_spider_state SET current_page_id=?,updated_epoch=? WHERE singleton=1",
            (page_id, now),
        )
        self._event(connection, "page_opened", page_id=page_id, to_word=seed,
                    detail={"page_number": number})
        return page_id

    def _wikipedia(self, lemma: str) -> dict[str, Any] | None:
        if not self.wikipedia_enabled:
            return None
        with self._connect() as connection:
            cached = connection.execute(
                "SELECT title,summary,url,fetched_epoch FROM semantic_spider_wikipedia_cache WHERE lemma=?",
                (lemma,),
            ).fetchone()
            if cached:
                return {**dict(cached), "cached": True}
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(lemma.replace(' ', '_'))}"
        request = Request(url, headers={"User-Agent": "Tessaris-Aion-Semantic-Spider/1.0"})
        try:
            with urlopen(request, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
            summary = " ".join(str(payload.get("extract") or "").split())[:1600]
            if not summary:
                return None
            item = {"title": str(payload.get("title") or lemma), "summary": summary,
                    "url": str((payload.get("content_urls") or {}).get("desktop", {}).get("page") or url),
                    "fetched_epoch": time.time(), "cached": False}
            with self._connect() as connection:
                connection.execute(
                    "INSERT OR REPLACE INTO semantic_spider_wikipedia_cache VALUES(?,?,?,?,?)",
                    (lemma, item["title"], summary, item["url"], item["fetched_epoch"]),
                )
            return item
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            return None

    def _macos_definition(self, lemma: str) -> str:
        """Read Dictionary.app's local Dictionary Services without UI automation."""
        if (not self.macos_dictionary_enabled or not self.macos_dictionary_reader.is_file()
                or shutil.which("xcrun") is None):
            return ""
        try:
            completed = subprocess.run(
                ["xcrun", "swift", str(self.macos_dictionary_reader), lemma],
                capture_output=True, text=True, timeout=8, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return " ".join(completed.stdout.split())[:5000] if completed.returncode == 0 else ""

    def _discover(self, lemma: str, definition: str, wikipedia: dict[str, Any] | None) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        for token in WORD_RE.findall(definition):
            clean = token.lower()
            if clean == lemma or clean in STOPWORDS or not self.lexical.lookup_senses(clean):
                continue
            candidates.setdefault(clean, {"lemma": clean, "relation": "definition_word", "weight": .72})
        for relation in self.lexical.related(lemma, limit=18):
            target = str(relation.get("target_lemma") or "").lower()
            if target and target != lemma and self.lexical.lookup_senses(target):
                candidates[target] = {"lemma": target,
                    "relation": str(relation.get("relation") or "related"),
                    "weight": min(.99, abs(float(relation.get("strength") or .5)))}
        if wikipedia:
            for token in WORD_RE.findall(str(wikipedia.get("summary") or "")):
                clean = token.lower()
                if clean == lemma or clean in STOPWORDS or not self.lexical.lookup_senses(clean):
                    continue
                candidates.setdefault(clean, {"lemma": clean,
                    "relation": "wikipedia_context", "weight": .45})
        return sorted(candidates.values(), key=lambda row: (-row["weight"], row["lemma"]))[
            :self.max_discoveries_per_page]

    def step(self, *, force: bool = False) -> dict[str, Any]:
        """Read exactly one word, then persist before allowing the next step."""
        finish_existing: tuple[str, list[str]] | None = None
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            state = connection.execute("SELECT * FROM semantic_spider_state WHERE singleton=1").fetchone()
            if not state["running"] and not force:
                return {"status": "paused", **self.status()}
            if bool(state["busy"]) and float(state["lease_epoch"] or 0) > time.time() - 30:
                return {"status": "busy", **self.status()}
            current_page = connection.execute(
                "SELECT * FROM semantic_spider_pages WHERE page_id=? AND status='reading'",
                (state["current_page_id"],),
            ).fetchone() if state["current_page_id"] else None
            if current_page:
                current_words = json.loads(current_page["words_json"] or "[]")
                if len(current_words) >= self.words_per_page:
                    connection.execute(
                        "UPDATE semantic_spider_state SET busy=1,lease_epoch=?,updated_epoch=? WHERE singleton=1",
                        (time.time(), time.time()),
                    )
                    finish_existing = (
                        str(current_page["page_id"]),
                        [str(word["lemma"]) for word in current_words],
                    )
            if finish_existing:
                row = None
            else:
                row = connection.execute(
                    """SELECT * FROM semantic_spider_frontier WHERE status='queued'
                       ORDER BY priority DESC,created_epoch,lemma LIMIT 1"""
                ).fetchone()
            if not row and not finish_existing:
                for seed in DEFAULT_SEEDS:
                    self._queue(connection, seed, relation="automatic_seed", priority=10)
                row = connection.execute(
                    "SELECT * FROM semantic_spider_frontier WHERE status='queued' ORDER BY priority DESC LIMIT 1"
                ).fetchone()
            if not row and not finish_existing:
                connection.execute(
                    "UPDATE semantic_spider_state SET running=0,busy=0,last_error='frontier_empty',updated_epoch=? WHERE singleton=1",
                    (time.time(),),
                )
                return {"status": "frontier_empty", **self.status()}
            if finish_existing:
                pass
            else:
                connection.execute(
                    "UPDATE semantic_spider_state SET busy=1,lease_epoch=?,updated_epoch=? WHERE singleton=1",
                    (time.time(), time.time()),
                )
                lemma = str(row["lemma"])
                page_id = state["current_page_id"]
                page = connection.execute(
                    "SELECT * FROM semantic_spider_pages WHERE page_id=? AND status='reading'", (page_id,)
                ).fetchone() if page_id else None
                if not page:
                    page_id = self._new_page(connection, lemma)
                    page = connection.execute(
                        "SELECT * FROM semantic_spider_pages WHERE page_id=?", (page_id,)
                    ).fetchone()
                page_words = json.loads(page["words_json"] or "[]")
                wikipedia_count = sum(bool(word.get("wikipedia")) for word in page_words)
                connection.execute(
                    "UPDATE semantic_spider_frontier SET status='reading',updated_epoch=? WHERE lemma=?",
                    (time.time(), lemma),
                )
                connection.execute(
                    "UPDATE semantic_spider_state SET current_word=?,updated_epoch=? WHERE singleton=1",
                    (lemma, time.time()),
                )

        if finish_existing:
            page_id, lemmas = finish_existing
            test = self._complete_page(page_id, lemmas)
            return {"status": "page_completed", "word": None, "test": test, **self.status()}

        try:
            entry = self.lexical.lookup(lemma) or {}
            lexical_definition = str(entry.get("definition") or "")
            macos_definition = self._macos_definition(lemma)
            definition = macos_definition or lexical_definition
            wiki = self._wikipedia(lemma) if wikipedia_count < self.wikipedia_words_per_page else None
            discovered = self._discover(lemma, definition, wiki)
            encounters = self.wordwall.encounter(lemma, teacher_lesson_id="semantic_spider")
            acquisition_stage = encounters[0].get("stage") if encounters else None
        except Exception as exc:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE semantic_spider_frontier SET status='queued',updated_epoch=? WHERE lemma=?",
                    (time.time(), lemma),
                )
                connection.execute(
                    "UPDATE semantic_spider_state SET busy=0,last_error=?,updated_epoch=? WHERE singleton=1",
                    (f"{type(exc).__name__}:{exc}"[:500], time.time()),
                )
            return {"status": "error", **self.status()}

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            page = connection.execute("SELECT * FROM semantic_spider_pages WHERE page_id=?", (page_id,)).fetchone()
            words = json.loads(page["words_json"] or "[]")
            all_discoveries = json.loads(page["discoveries_json"] or "[]")
            source_counts = json.loads(page["source_counts_json"] or "{}")
            dictionary_source = "macos_dictionary_services" if macos_definition else "local_lexical_dictionary"
            word = {"lemma": lemma, "definition": definition,
                    "lexical_definition": lexical_definition,
                    "part_of_speech": entry.get("part_of_speech"),
                    "sources": [dictionary_source, "local_thesaurus_graph"] + (["wikipedia_cached" if wiki and wiki.get("cached") else "wikipedia"] if wiki else []),
                    "wikipedia": wiki, "discovered": discovered,
                    "acquisition_stage": acquisition_stage, "read_epoch": time.time()}
            words.append(word)
            source_counts[dictionary_source] = int(source_counts.get(dictionary_source) or 0) + 1
            source_counts["local_thesaurus_graph"] = int(source_counts.get("local_thesaurus_graph") or 0) + 1
            if wiki:
                source_counts["wikipedia"] = int(source_counts.get("wikipedia") or 0) + 1
            newly_queued = 0
            seen = {str(item.get("lemma")) for item in all_discoveries}
            for item in discovered:
                if item["lemma"] not in seen:
                    all_discoveries.append(item)
                    seen.add(item["lemma"])
                newly_queued += int(self._queue(
                    connection, item["lemma"], parent=lemma, relation=item["relation"],
                    depth=int(row["depth"]) + 1, priority=float(item["weight"]),
                ))
            connection.execute(
                """UPDATE semantic_spider_pages SET words_json=?,discoveries_json=?,source_counts_json=?
                   WHERE page_id=?""",
                (json.dumps(words), json.dumps(all_discoveries[:self.max_discoveries_per_page]),
                 json.dumps(source_counts), page_id),
            )
            connection.execute(
                "UPDATE semantic_spider_frontier SET status='read',updated_epoch=? WHERE lemma=?",
                (time.time(), lemma),
            )
            page_complete = len(words) >= self.words_per_page
            connection.execute(
                """UPDATE semantic_spider_state SET words_read=words_read+1,
                   discoveries=discoveries+?,current_word=?,busy=?,updated_epoch=? WHERE singleton=1""",
                (newly_queued, lemma, int(page_complete), time.time()),
            )
            self._event(connection, "word_read", page_id=page_id,
                        from_word=str(row["parent_lemma"] or ""), to_word=lemma,
                        detail={"sources": word["sources"], "newly_queued": newly_queued,
                                "definition": definition[:240]})

        test = None
        if page_complete:
            test = self._complete_page(page_id, [word["lemma"] for word in words])
        return {"status": "page_completed" if page_complete else "word_read",
                "word": word, "test": test, **self.status()}

    def _complete_page(self, page_id: str, lemmas: list[str]) -> dict[str, Any]:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT status,test_json FROM semantic_spider_pages WHERE page_id=?", (page_id,)
            ).fetchone()
            if existing and existing["status"] == "tested":
                connection.execute(
                    "UPDATE semantic_spider_state SET busy=0,updated_epoch=? WHERE singleton=1",
                    (time.time(),),
                )
                return json.loads(existing["test_json"] or "{}")
        test = self.wordwall.run_exact_cycle(
            lemmas=lemmas[:self.words_per_page],
            teacher_lesson_id=f"semantic_spider:{page_id}",
        )
        now = time.time()
        with self._connect() as connection:
            page = connection.execute(
                "SELECT page_number FROM semantic_spider_pages WHERE page_id=?", (page_id,)
            ).fetchone()
            certified = test.get("page_certified") is True
            connection.execute(
                """UPDATE semantic_spider_pages SET status=?,test_json=?,completed_epoch=?
                   WHERE page_id=?""",
                ("tested" if certified else "reading", json.dumps(test),
                 now if certified else None, page_id),
            )
            if certified:
                connection.execute(
                    """UPDATE semantic_spider_state SET pages_completed=pages_completed+1,
                       tests_attempted=tests_attempted+?,tests_correct=tests_correct+?,
                       current_page_id=NULL,busy=0,last_error=NULL,updated_epoch=? WHERE singleton=1""",
                    (int(test.get("attempted") or 0), int(test.get("correct") or 0), now),
                )
            else:
                connection.execute(
                    """UPDATE semantic_spider_state SET running=0,busy=0,
                       last_error='page_test_incomplete',updated_epoch=? WHERE singleton=1""",
                    (now,),
                )
            self._event(connection, "page_tested", page_id=page_id,
                        detail={"page_number": int(page["page_number"]),
                                "attempted": test.get("attempted"),
                                "correct": test.get("correct"),
                                "coverage_count": test.get("coverage_count"),
                                "coverage_total": test.get("coverage_total"),
                                "page_certified": certified,
                                "model_used": False})
        return test

    def cycle(self, *, steps: int = 1) -> dict[str, Any]:
        outcome: dict[str, Any] = {}
        for _ in range(max(1, min(self.words_per_page, int(steps)))):
            outcome = self.step(force=True)
            if outcome.get("status") in {"busy", "frontier_empty", "page_completed"}:
                break
        return outcome or self.status()

    def _apple_sources(self) -> dict[str, Any]:
        root = Path("/System/Library/AssetsV2/com_apple_MobileAsset_DictionaryServices_dictionary3macOS")
        dictionaries = list(root.glob("*.asset/AssetData/*.dictionary")) if root.is_dir() else []
        names = sorted({path.stem for path in dictionaries})
        return {"dictionary_assets_found": bool(names), "assets": names,
                "macos_dictionary_services": bool(
                    self.macos_dictionary_enabled and self.macos_dictionary_reader.is_file()
                    and shutil.which("xcrun")
                ),
                "thesaurus_mode": "local_lexical_relation_graph",
                "wikipedia_mode": "network_cached" if self.wikipedia_enabled else "disabled",
                "wikipedia_note": "The Dictionary app Wikipedia tab is network-backed; fetched summaries are capped and cached locally."}

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            state = dict(connection.execute(
                "SELECT * FROM semantic_spider_state WHERE singleton=1"
            ).fetchone())
            queued = int(connection.execute(
                "SELECT COUNT(*) FROM semantic_spider_frontier WHERE status='queued'"
            ).fetchone()[0])
            open_pages = int(connection.execute(
                "SELECT COUNT(*) FROM semantic_spider_pages WHERE status='reading'"
            ).fetchone()[0])
            pages = [dict(row) for row in connection.execute(
                "SELECT * FROM semantic_spider_pages ORDER BY page_number DESC LIMIT ?",
                (self.max_open_pages,),
            ).fetchall()]
            events = [dict(row) for row in connection.execute(
                "SELECT * FROM semantic_spider_events ORDER BY created_epoch DESC LIMIT 30"
            ).fetchall()]
        for page in pages:
            for key, fallback in (("words_json", "[]"), ("discoveries_json", "[]"),
                                  ("source_counts_json", "{}"), ("test_json", "{}")):
                page[key.removesuffix("_json")] = json.loads(page.pop(key) or fallback)
        for event in events:
            event["detail"] = json.loads(event.pop("detail_json") or "{}")
        attempted = int(state["tests_attempted"] or 0)
        return {"schema_version": "aion.semantic_spider.v1", "running": bool(state["running"]),
                "seed": state["seed"], "current_word": state["current_word"],
                "pages_completed": int(state["pages_completed"]),
                "words_read": int(state["words_read"]), "discoveries": int(state["discoveries"]),
                "tests_attempted": attempted, "tests_correct": int(state["tests_correct"]),
                "test_accuracy": round(int(state["tests_correct"]) / attempted, 4) if attempted else None,
                "frontier_queued": queued, "open_pages": open_pages, "pages": pages,
                "events": events, "caps": self.caps(), "sources": self._apple_sources(),
                "storage": str(self.database_path), "model_used_for_tests": False,
                "last_error": state["last_error"], "updated_epoch": state["updated_epoch"]}


__all__ = ["NativeSemanticSpider"]
