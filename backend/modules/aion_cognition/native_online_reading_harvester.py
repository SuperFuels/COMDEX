"""Bounded online acquisition for Aion's native reading academy.

Remote files are temporary transport objects, never a permanent book cache.
The verified extracted text is handed to the reading academy and the raw file
is deleted before this operation returns.
"""
from __future__ import annotations

from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Callable, Mapping
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from backend.modules.aion_cognition.sqlite_connection import connect as sqlite_connect
from backend.modules.aion_cognition.native_document_ingestion import NativeDocumentExtractor


DEFAULT_CATALOG_URL = "https://www.gutenberg.org/ebooks/search.opds/?sort_order=downloads"
DEFAULT_SUBJECT_CATALOGS = (
    # Keep OPDS queries deliberately short.  Gutenberg's search endpoint can
    # time out on long OR-like query strings; the local classifier and later
    # reading exams provide the finer-grained distinction.
    ("science", "science"),
    ("history", "history"),
    ("engineering", "engineering"),
    ("philosophy", "philosophy"),
    ("economics", "economics"),
    ("literature", "literature"),
)
USER_AGENT = "AionNativeReader/1.0 (+local curriculum reader)"
ATOM = "{http://www.w3.org/2005/Atom}"
ACQUISITION_REL = "http://opds-spec.org/acquisition"


class _ReadableHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "svg", "noscript"}:
            self.ignored += 1
        elif not self.ignored and tag in {"p", "div", "article", "section", "h1", "h2", "h3", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "svg", "noscript"} and self.ignored:
            self.ignored -= 1
        elif not self.ignored and tag in {"p", "div", "article", "section", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)

    def text(self) -> str:
        value = "".join(self.parts)
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n\s*\n\s*\n+", "\n\n", value)
        return value.strip()


FetchResult = tuple[bytes, str, str]
Fetcher = Callable[[str, int], FetchResult]
Ingest = Callable[..., Mapping[str, Any]]


class NativeOnlineReadingHarvester:
    def __init__(self, *, database_path: Path | str, extractor: NativeDocumentExtractor,
                 ingest: Ingest, fetcher: Fetcher | None = None,
                 catalog_url: str = DEFAULT_CATALOG_URL,
                 max_download_bytes: int = 20_000_000,
                 retry_delay_seconds: float = 600.0) -> None:
        self.database_path = Path(database_path)
        self.extractor = extractor
        self.ingest = ingest
        self.fetcher = fetcher or self._fetch
        self.catalog_url = catalog_url
        self.catalogs = (
            [(catalog_url, "general")]
            if catalog_url != DEFAULT_CATALOG_URL else
            [(f"https://www.gutenberg.org/ebooks/search.opds/?query={quote_plus(query)}",
              subject) for subject, query in DEFAULT_SUBJECT_CATALOGS]
        )
        self.max_download_bytes = max(100_000, int(max_download_bytes))
        self.retry_delay_seconds = max(30.0, float(retry_delay_seconds))
        # Stage even temporary EPUB/PDF bytes beside the learning database. In
        # production this is the SD card, so the Mac's system disk is not used.
        self.temporary_root = self.database_path.parent / "transient_online_reading"
        self.temporary_root.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS native_online_reading_sources(
                    online_id TEXT PRIMARY KEY,url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,author TEXT NOT NULL,subject TEXT NOT NULL,
                    media_type TEXT NOT NULL,status TEXT NOT NULL,
                    source_id TEXT NOT NULL DEFAULT '',bytes_downloaded INTEGER NOT NULL DEFAULT 0,
                    raw_deleted INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',
                    discovered_epoch REAL NOT NULL,updated_epoch REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS native_online_reading_runtime(
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    last_attempt_epoch REAL NOT NULL DEFAULT 0,
                    raw_bytes_downloaded INTEGER NOT NULL DEFAULT 0,
                    raw_bytes_deleted INTEGER NOT NULL DEFAULT 0,
                    temporary_files_retained INTEGER NOT NULL DEFAULT 0,
                    catalog_index INTEGER NOT NULL DEFAULT 0
                );
                INSERT OR IGNORE INTO native_online_reading_runtime(singleton)
                    VALUES(1);
                """
            )
            columns = {str(row[1]) for row in connection.execute(
                "PRAGMA table_info(native_online_reading_runtime)"
            ).fetchall()}
            if "catalog_index" not in columns:
                connection.execute(
                    "ALTER TABLE native_online_reading_runtime ADD COLUMN catalog_index INTEGER NOT NULL DEFAULT 0"
                )

    @staticmethod
    def _fetch(url: str, max_bytes: int) -> FetchResult:
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        with urlopen(request, timeout=25) as response:
            length = int(response.headers.get("Content-Length") or 0)
            if length > max_bytes:
                raise ValueError("online_source_too_large")
            payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise ValueError("online_source_too_large")
            content_type = str(response.headers.get_content_type() or "application/octet-stream")
            return payload, content_type, str(response.geturl())

    @staticmethod
    def _id(url: str) -> str:
        return "online_reading_" + hashlib.sha256(url.encode()).hexdigest()[:24]

    def _record_candidate(self, *, url: str, title: str, author: str,
                          subject: str, media_type: str) -> bool:
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO native_online_reading_sources
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (self._id(url), url, title[:300], author[:300], subject[:120],
                 media_type[:120], "discovered", "", 0, 0, "", now, now),
            )
        return cursor.rowcount > 0

    def discover(self, *, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT catalog_index FROM native_online_reading_runtime WHERE singleton=1"
            ).fetchone()
            catalog_index = int(row[0] or 0) % len(self.catalogs)
            connection.execute(
                "UPDATE native_online_reading_runtime SET catalog_index=? WHERE singleton=1",
                ((catalog_index + 1) % len(self.catalogs),),
            )
        catalog_url, catalog_subject = self.catalogs[catalog_index]
        payload, _, final_url = self.fetcher(catalog_url, 2_000_000)
        root = ET.fromstring(payload)
        discovered: list[dict[str, Any]] = []
        for entry in root.findall(f"{ATOM}entry"):
            title = (entry.findtext(f"{ATOM}title") or "Untitled").strip()
            author = (entry.findtext(f"{ATOM}content") or "Unknown").strip()
            detail = next((link.get("href") for link in entry.findall(f"{ATOM}link")
                           if link.get("rel") == "subsection"), None)
            if not detail:
                continue
            detail_url = urljoin(final_url, detail)
            # Search feeds begin with navigation entries named Authors,
            # Subjects and Bookshelves.  They are catalogues, not books, and
            # following them as acquisition records can produce 403s or loops.
            if not re.search(r"/ebooks/\d+\.opds(?:\?|$)", detail_url):
                continue
            try:
                detail_payload, _, detail_final = self.fetcher(detail_url, 1_000_000)
            except Exception:
                # A single transient Gutenberg item must not abort the entire
                # subject discovery pass. Continue to the next independent
                # catalogue entry and let a later cycle retry naturally.
                continue
            detail_root = ET.fromstring(detail_payload)
            links = [link for link in detail_root.iter(f"{ATOM}link")
                     if link.get("rel") == ACQUISITION_REL]
            preferred = next((link for link in links
                              if link.get("type") == "application/epub+zip"
                              and "noimages" in str(link.get("href") or "")), None)
            if preferred is None:
                preferred = next((link for link in links
                                  if link.get("type") == "application/epub+zip"), None)
            if preferred is None:
                continue
            acquisition_url = urljoin(detail_final, str(preferred.get("href") or ""))
            detail_terms = " ".join(
                str(category.get("term") or category.get("label") or "")
                for category in detail_root.iter(f"{ATOM}category")
            )
            classified_subject = self._classify_subject(
                title, f"{author} {detail_terms}", catalog_subject,
            )
            if (catalog_subject not in {"general", "literature"}
                    and classified_subject != catalog_subject):
                continue
            inserted = self._record_candidate(
                url=acquisition_url, title=title, author=author,
                subject=classified_subject,
                media_type="application/epub+zip",
            )
            # Existing completed/queued books do not consume the discovery
            # budget. Continue through the catalogue until genuinely new
            # reading is found instead of rediscovering the same top five.
            if not inserted:
                continue
            discovered.append({"url": acquisition_url, "title": title, "author": author})
            if len(discovered) >= max(1, int(limit)):
                break
        return discovered

    @staticmethod
    def _classify_subject(title: str, description: str, catalog_subject: str) -> str:
        """Keep source families useful for cross-domain examinations.

        The catalogue that found a book is the primary signal.  Title and
        description cues refine the broad/popular feed without claiming a
        subject from the prose after Aion has seen it.
        """
        text = f"{title} {description}".lower()
        if "fiction" in text or any(term in text for term in (
            "horror tales", "gothic", "romance", "novel", "drama",
        )):
            return "literature"
        cues = {
            "engineering": ("engineer", "mechanic", "electric", "machine", "technology"),
            "science": ("science", "biology", "physics", "chemistry", "astronomy", "nature"),
            "history": ("history", "historical", "civilization", "ancient", "biography"),
            "philosophy": ("philosophy", "logic", "ethics", "psychology"),
            "economics": ("economics", "economy", "finance", "commerce", "wealth"),
        }
        for subject, terms in cues.items():
            if any(term in text for term in terms):
                return subject
        if catalog_subject != "general":
            return catalog_subject
        return "literature"

    @staticmethod
    def _strip_distribution_wrapper(text: str) -> str:
        start = re.search(r"\*{3}\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*{3}",
                          text, re.I)
        end = re.search(r"\*{3}\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*{3}",
                        text, re.I)
        left = start.end() if start else 0
        right = end.start() if end and end.start() > left else len(text)
        return text[left:right].strip()

    def _extract(self, *, payload: bytes, content_type: str, url: str,
                 title: str, author: str) -> dict[str, Any]:
        lowered = content_type.lower()
        suffix = Path(urlparse(url).path).suffix.lower()
        if "html" in lowered or suffix in {".html", ".htm"}:
            parser = _ReadableHTML()
            parser.feed(payload.decode("utf-8", errors="replace"))
            text = parser.text()
            return {"text": text, "format": "html", "method": "html_readable_text",
                    "document_title": title, "document_author": author,
                    "page_count": 0,
                    "quality": {"score": 1.0, "character_count": len(text)}}
        if lowered.startswith("text/") or suffix in {".txt", ".text", ".md"}:
            text = payload.decode("utf-8", errors="replace")
            return {"text": text, "format": "text", "method": "online_text",
                    "document_title": title, "document_author": author,
                    "page_count": 0,
                    "quality": {"score": 1.0, "character_count": len(text)}}
        extension = ".epub" if "epub" in lowered else ".pdf" if "pdf" in lowered else suffix
        if extension not in {".epub", ".pdf"}:
            raise ValueError("unsupported_online_media_type")
        required_free = max(100_000_000, len(payload) * 3)
        if shutil.disk_usage(self.temporary_root).free < required_free:
            raise ValueError("online_reading_storage_guard")
        with tempfile.TemporaryDirectory(
            prefix="aion-online-reading-", dir=self.temporary_root,
        ) as temporary:
            path = Path(temporary) / f"source{extension}"
            path.write_bytes(payload)
            extraction = self.extractor.extract(path)
        extraction["document_title"] = extraction.get("document_title") or title
        extraction["document_author"] = extraction.get("document_author") or author
        return extraction

    def ingest_url(self, url: str, *, title: str = "Online reading",
                   author: str = "Unknown", subject: str = "general") -> dict[str, Any]:
        clean_url = str(url or "").strip()
        if not clean_url.startswith(("https://", "http://")):
            raise ValueError("unsupported_online_url")
        payload, content_type, final_url = self.fetcher(clean_url, self.max_download_bytes)
        extraction = self._extract(
            payload=payload, content_type=content_type, url=final_url,
            title=title, author=author,
        )
        extraction["text"] = self._strip_distribution_wrapper(str(extraction["text"]))
        outcome = self.ingest(
            title=str(extraction.get("document_title") or title),
            author=str(extraction.get("document_author") or author),
            text=extraction["text"], subject=subject, license_name="online-source",
            source_ref=final_url, extraction=extraction,
        )
        online_id = self._id(clean_url)
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO native_online_reading_sources
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(url) DO UPDATE SET status='queued',source_id=excluded.source_id,
                   bytes_downloaded=excluded.bytes_downloaded,raw_deleted=1,error='',
                   updated_epoch=excluded.updated_epoch""",
                (online_id, clean_url, str(outcome.get("title") or title)[:300], author[:300],
                 subject[:120], content_type[:120], "queued",
                 str(outcome.get("source_id") or ""), len(payload), 1, "", now, now),
            )
            connection.execute(
                """UPDATE native_online_reading_runtime SET last_attempt_epoch=?,
                   raw_bytes_downloaded=raw_bytes_downloaded+?,
                   raw_bytes_deleted=raw_bytes_deleted+?,temporary_files_retained=0
                   WHERE singleton=1""", (now, len(payload), len(payload)),
            )
        return {**dict(outcome), "online": True, "url": final_url,
                "raw_bytes_downloaded": len(payload), "raw_file_deleted": True}

    def harvest_once(self) -> dict[str, Any]:
        now = time.time()
        with self._connect() as connection:
            runtime = connection.execute(
                "SELECT last_attempt_epoch FROM native_online_reading_runtime WHERE singleton=1"
            ).fetchone()
            queued = connection.execute(
                """SELECT * FROM native_online_reading_sources
                   WHERE status='discovered'
                   ORDER BY CASE WHEN subject='literature' THEN 1 ELSE 0 END,
                            discovered_epoch LIMIT 1"""
            ).fetchone()
            if not queued:
                # A download/extraction can fail under temporary storage
                # pressure. Once the cooldown has elapsed, retry that source
                # rather than abandoning the book forever.
                queued = connection.execute(
                    """SELECT * FROM native_online_reading_sources
                       WHERE status='failed' AND updated_epoch<=?
                       ORDER BY updated_epoch LIMIT 1""",
                    (now - self.retry_delay_seconds,),
                ).fetchone()
                if queued:
                    connection.execute(
                        """UPDATE native_online_reading_sources
                           SET status='discovered',error='',updated_epoch=?
                           WHERE online_id=?""",
                        (now, queued["online_id"]),
                    )
                    queued = connection.execute(
                        "SELECT * FROM native_online_reading_sources WHERE online_id=?",
                        (queued["online_id"],),
                    ).fetchone()
        if not queued and float(runtime[0] or 0) > time.time() - self.retry_delay_seconds:
            return {"status": "cooldown", "imported": 0}
        try:
            if not queued:
                self.discover(limit=5)
                with self._connect() as connection:
                    queued = connection.execute(
                        """SELECT * FROM native_online_reading_sources
                           WHERE status='discovered'
                           ORDER BY CASE WHEN subject='literature' THEN 1 ELSE 0 END,
                                    discovered_epoch LIMIT 1"""
                    ).fetchone()
            if not queued:
                raise ValueError("online_catalog_has_no_supported_books")
            outcome = self.ingest_url(
                str(queued["url"]), title=str(queued["title"]),
                author=str(queued["author"]), subject=str(queued["subject"]),
            )
            return {"status": "imported", "imported": 1, "source": outcome}
        except Exception as exc:
            now = time.time()
            with self._connect() as connection:
                connection.execute(
                    "UPDATE native_online_reading_runtime SET last_attempt_epoch=? WHERE singleton=1",
                    (now,),
                )
                if queued:
                    connection.execute(
                        """UPDATE native_online_reading_sources SET status='failed',error=?,
                           updated_epoch=? WHERE online_id=?""",
                        (f"{type(exc).__name__}: {exc}"[:2000], now, queued["online_id"]),
                    )
            return {"status": "failed", "imported": 0,
                    "error": f"{type(exc).__name__}: {exc}"}

    def metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            sources = connection.execute(
                """SELECT COUNT(*),SUM(CASE WHEN status='queued' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)
                   FROM native_online_reading_sources"""
            ).fetchone()
            runtime = connection.execute(
                "SELECT * FROM native_online_reading_runtime WHERE singleton=1"
            ).fetchone()
        return {
            "enabled": True,
            "sources_discovered": int(sources[0] or 0),
            "sources_imported": int(sources[1] or 0),
            "sources_failed": int(sources[2] or 0),
            "raw_bytes_downloaded": int(runtime["raw_bytes_downloaded"] or 0),
            "raw_bytes_deleted": int(runtime["raw_bytes_deleted"] or 0),
            "temporary_files_retained": sum(1 for _ in self.temporary_root.iterdir()),
            "temporary_directory": str(self.temporary_root),
            "last_attempt_epoch": float(runtime["last_attempt_epoch"] or 0),
            "catalog_url": self.catalog_url,
            "catalogs": [{"url": url, "subject": subject}
                         for url, subject in self.catalogs],
            "next_catalog_index": int(runtime["catalog_index"] or 0),
        }


__all__ = ["NativeOnlineReadingHarvester", "DEFAULT_CATALOG_URL",
           "DEFAULT_SUBJECT_CATALOGS"]
