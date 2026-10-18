from pathlib import Path

from backend.modules.aion_cognition.native_document_ingestion import NativeDocumentExtractor
from backend.modules.aion_cognition.native_online_reading_harvester import (
    NativeOnlineReadingHarvester,
)


def test_online_text_is_ingested_without_retaining_the_download(tmp_path: Path):
    received = {}

    def ingest(**kwargs):
        received.update(kwargs)
        return {"status": "queued", "source_id": "source-1", "title": kwargs["title"]}

    def fetch(url: str, max_bytes: int):
        assert max_bytes >= 100_000
        return (
            b"CHAPTER ONE\n\nLeona examined the evidence carefully. "
            b"She recorded the result before sunrise.",
            "text/plain", url,
        )

    harvester = NativeOnlineReadingHarvester(
        database_path=tmp_path / "native.sqlite3",
        extractor=NativeDocumentExtractor(repo_root=tmp_path),
        ingest=ingest, fetcher=fetch,
    )

    result = harvester.ingest_url(
        "https://example.test/book.txt", title="Test Book", author="Owner",
    )
    metrics = harvester.metrics()

    assert result["raw_file_deleted"] is True
    assert received["text"].startswith("CHAPTER ONE")
    assert received["source_ref"] == "https://example.test/book.txt"
    assert metrics["raw_bytes_downloaded"] == metrics["raw_bytes_deleted"]
    assert metrics["temporary_files_retained"] == 0


def test_opds_catalog_discovers_a_supported_book(tmp_path: Path):
    feed = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Example Book</title><content type="text">A. Writer</content>
      <link rel="subsection" href="/ebooks/7.opds"/></entry>
    </feed>'''
    detail = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <link rel="http://opds-spec.org/acquisition" type="application/epub+zip"
            href="https://example.test/7.epub.noimages"/>
    </entry></feed>'''

    def fetch(url: str, max_bytes: int):
        return ((detail, "application/atom+xml", url) if url.endswith("7.opds")
                else (feed, "application/atom+xml", "https://example.test/search.opds"))

    harvester = NativeOnlineReadingHarvester(
        database_path=tmp_path / "native.sqlite3",
        extractor=NativeDocumentExtractor(repo_root=tmp_path),
        ingest=lambda **kwargs: {}, fetcher=fetch,
        catalog_url="https://example.test/search.opds",
    )

    found = harvester.discover(limit=1)

    assert found == [{
        "url": "https://example.test/7.epub.noimages",
        "title": "Example Book", "author": "A. Writer",
    }]
    assert harvester.metrics()["sources_discovered"] == 1


def test_catalog_skips_existing_books_and_discovers_the_next_title(tmp_path: Path):
    feed = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>First Book</title><content type="text">A. Writer</content>
      <link rel="subsection" href="/ebooks/1.opds"/></entry>
      <entry><title>Second Book</title><content type="text">B. Writer</content>
      <link rel="subsection" href="/ebooks/2.opds"/></entry>
    </feed>'''

    def fetch(url: str, max_bytes: int):
        if url.endswith(".opds") and not url.endswith("search.opds"):
            number = "1" if url.endswith("1.opds") else "2"
            detail = f'''<?xml version="1.0"?>
            <feed xmlns="http://www.w3.org/2005/Atom"><entry>
              <link rel="http://opds-spec.org/acquisition" type="application/epub+zip"
                    href="https://example.test/{number}.epub.noimages"/>
            </entry></feed>'''.encode()
            return detail, "application/atom+xml", url
        return feed, "application/atom+xml", "https://example.test/search.opds"

    harvester = NativeOnlineReadingHarvester(
        database_path=tmp_path / "native.sqlite3",
        extractor=NativeDocumentExtractor(repo_root=tmp_path),
        ingest=lambda **kwargs: {}, fetcher=fetch,
        catalog_url="https://example.test/search.opds",
    )

    assert harvester.discover(limit=1)[0]["title"] == "First Book"
    assert harvester.discover(limit=1)[0]["title"] == "Second Book"
    assert harvester.metrics()["sources_discovered"] == 2
