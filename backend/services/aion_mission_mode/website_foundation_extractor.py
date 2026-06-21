"""AION Phase 24B — Universal website evidence collector.

This module only collects public website evidence.
It does not decide business meaning with hardcoded industry keywords.
The LLM extractor turns this evidence into a Business Foundation.
"""

from __future__ import annotations

from html.parser import HTMLParser
import re
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


MAX_HTML_BYTES = 1_500_000
MAX_EVIDENCE_CHARS = 60_000


class VisibleWebsiteParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.skip_depth = 0
        self.current_tag = ""
        self.current_href = ""
        self.title = ""
        self.headings: list[str] = []
        self.visible_text: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current_tag = tag.lower()
        self.current_href = ""

        if self.current_tag in {"script", "style", "noscript", "svg", "canvas"}:
            self.skip_depth += 1

        if self.current_tag == "a":
            for key, value in attrs:
                if key and key.lower() == "href" and value:
                    href = urljoin(self.base_url, value)
                    self.current_href = href
                    self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self.skip_depth:
            self.skip_depth -= 1
        self.current_tag = ""
        self.current_href = ""

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return

        value = normalise_space(data)
        if not value:
            return

        if self.current_tag == "title":
            self.title = normalise_space(f"{self.title} {value}")

        if self.current_tag in {"h1", "h2", "h3", "h4"}:
            self.headings.append(value)

        if self.current_href:
            self.visible_text.append(f"{value} [{self.current_href}]")
        else:
            self.visible_text.append(value)


def normalise_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalise_url(url: str) -> str:
    value = normalise_space(url)
    if not value:
        return ""
    if not re.match(r"^https?://", value, flags=re.I):
        value = "https://" + value
    return value


def dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = normalise_space(item)
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def fetch_website_html(url: str, timeout_seconds: int = 12) -> str:
    target = normalise_url(url)
    if not target:
        raise ValueError("Website URL is required")

    request = Request(
        target,
        headers={
            "User-Agent": "AIONBusinessFoundationScanner/1.0 (+read-only evidence collection)",
            "Accept": "text/html,application/xhtml+xml,text/plain",
        },
    )

    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read(MAX_HTML_BYTES)
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def extract_emails(text: str) -> list[str]:
    return dedupe(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, flags=re.I))


def extract_phones(text: str) -> list[str]:
    matches = re.findall(r"(?:\+\d{1,3}[\s().-]?)?(?:\d[\s().-]?){8,16}", text)
    phones: list[str] = []
    for match in matches:
        value = normalise_space(match)
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 9:
            phones.append(value)
    return dedupe(phones)


def extract_social_links(links: list[str]) -> list[str]:
    social_hosts = (
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "tiktok.com",
        "youtube.com",
        "x.com",
        "twitter.com",
        "pinterest.com",
        "google.com/maps",
        "g.page",
    )
    return [
        link for link in dedupe(links)
        if any(host in link.lower() for host in social_hosts)
    ]


def collect_website_evidence_from_html(url: str, html: str) -> dict[str, Any]:
    target = normalise_url(url)
    parser = VisibleWebsiteParser(target)
    parser.feed(html or "")

    text = normalise_space(" ".join(parser.visible_text))
    visible_lines = dedupe(parser.visible_text)

    evidence_text = "\n".join(visible_lines)
    if len(evidence_text) > MAX_EVIDENCE_CHARS:
        evidence_text = evidence_text[:MAX_EVIDENCE_CHARS]

    return {
        "url": target,
        "domain": urlparse(target).netloc,
        "title": parser.title,
        "headings": dedupe(parser.headings)[:80],
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "social_links": extract_social_links(parser.links),
        "links": dedupe(parser.links)[:120],
        "visible_text": evidence_text,
        "visible_text_length": len(text),
        "live_external_side_effect": False,
    }


def collect_website_evidence(url: str, timeout_seconds: int = 12) -> dict[str, Any]:
    target = normalise_url(url)
    html = fetch_website_html(target, timeout_seconds=timeout_seconds)
    return collect_website_evidence_from_html(target, html)
