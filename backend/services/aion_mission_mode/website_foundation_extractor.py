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
MAX_STYLESHEET_BYTES = 400_000
MAX_STYLESHEETS = 8


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
        self.images: list[dict[str, str]] = []
        self.icons: list[str] = []
        self.meta_images: list[str] = []
        self.stylesheets: list[str] = []
        self.style_fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current_tag = tag.lower()
        self.current_href = ""
        attr_map = {str(key or "").lower(): str(value or "") for key, value in attrs}

        if self.current_tag in {"script", "style", "noscript", "svg", "canvas"}:
            self.skip_depth += 1

        if self.current_tag == "a":
            for key, value in attrs:
                if key and key.lower() == "href" and value:
                    href = urljoin(self.base_url, value)
                    self.current_href = href
                    self.links.append(href)

        if self.current_tag == "img" and attr_map.get("src"):
            self.images.append({
                "url": urljoin(self.base_url, attr_map["src"]),
                "alt": normalise_space(attr_map.get("alt")),
                "class": normalise_space(attr_map.get("class")),
                "id": normalise_space(attr_map.get("id")),
            })

        if self.current_tag == "link" and attr_map.get("href"):
            rel = attr_map.get("rel", "").lower()
            href = urljoin(self.base_url, attr_map["href"])
            if "icon" in rel:
                self.icons.append(href)
            if "stylesheet" in rel:
                self.stylesheets.append(href)

        if self.current_tag == "meta":
            property_name = (attr_map.get("property") or attr_map.get("name") or "").lower()
            if property_name in {"og:image", "twitter:image", "twitter:image:src"} and attr_map.get("content"):
                self.meta_images.append(urljoin(self.base_url, attr_map["content"]))

        if attr_map.get("style"):
            self.style_fragments.append(attr_map["style"])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self.skip_depth:
            self.skip_depth -= 1
        self.current_tag = ""
        self.current_href = ""

    def handle_data(self, data: str) -> None:
        if self.current_tag == "style":
            self.style_fragments.append(str(data or ""))
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


def extract_css_custom_properties(css: str) -> list[dict[str, str]]:
    """Return bounded semantic colour tokens declared by the site.

    Raw hexadecimal discovery is useful provenance, but CSS custom-property
    names carry the role information needed to distinguish a brand accent from
    an error colour, form border, or widget colour.
    """
    tokens: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, value in re.findall(
        r"(--[a-zA-Z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b",
        css or "",
    ):
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append({"name": name, "value": value.upper()})
        if len(tokens) >= 40:
            break
    return tokens


def clean_font_family(value: Any) -> str:
    first = str(value or "").split(",", 1)[0].strip().strip("'\"")
    return normalise_space(first)


def extract_font_roles(css: str) -> dict[str, str]:
    body_font = ""
    heading_font = ""
    supporting_font = ""
    for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css or ""):
        match = re.search(r"font-family\s*:\s*([^;}{]+)", declarations, flags=re.I)
        if not match:
            continue
        family = clean_font_family(match.group(1))
        selector_text = normalise_space(selector).lower()
        if not family:
            continue
        if not body_font and re.search(r"(^|,)\s*(html\s+)?body(\s|,|$)", selector_text):
            body_font = family
        if not heading_font and re.search(r"(^|[\s,])(h1|h2)([\s,:.#]|$)", selector_text):
            heading_font = family
        if not supporting_font and any(term in selector_text for term in ("nav", "label", "button", "subtitle", "section-label")):
            supporting_font = family
    return {
        "heading": heading_font,
        "body": body_font,
        "supporting": supporting_font,
    }


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


def collect_website_evidence_from_html(
    url: str,
    html: str,
    supplemental_css: str = "",
) -> dict[str, Any]:
    target = normalise_url(url)
    parser = VisibleWebsiteParser(target)
    parser.feed(html or "")

    text = normalise_space(" ".join(parser.visible_text))
    visible_lines = dedupe(parser.visible_text)

    evidence_text = "\n".join(visible_lines)
    if len(evidence_text) > MAX_EVIDENCE_CHARS:
        evidence_text = evidence_text[:MAX_EVIDENCE_CHARS]

    logo_candidates: list[str] = []
    for image in parser.images:
        descriptor = " ".join([
            image.get("url", ""), image.get("alt", ""), image.get("class", ""), image.get("id", ""),
        ]).lower()
        if any(term in descriptor for term in ("logo", "brand", "wordmark", "logomark")):
            logo_candidates.append(image.get("url", ""))

    css_evidence = "\n".join([*parser.style_fragments, str(supplemental_css or "")])
    colour_candidates = dedupe(
        [value.upper() for value in re.findall(r"#[0-9a-fA-F]{3,8}\b", css_evidence)]
    )[:24]
    font_candidates = dedupe([
        clean_font_family(value)
        for value in re.findall(r"font-family\s*:\s*([^;}{]+)", css_evidence, flags=re.I)
    ])[:16]

    return {
        "url": target,
        "domain": urlparse(target).netloc,
        "title": parser.title,
        "headings": dedupe(parser.headings)[:80],
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "social_links": extract_social_links(parser.links),
        "logo_candidates": dedupe(logo_candidates)[:12],
        "icon_candidates": dedupe(parser.icons)[:12],
        "social_image_candidates": dedupe(parser.meta_images)[:12],
        "colour_candidates": colour_candidates,
        "font_candidates": font_candidates,
        "css_custom_properties": extract_css_custom_properties(css_evidence),
        "font_roles": extract_font_roles(css_evidence),
        "stylesheet_urls": dedupe(parser.stylesheets)[:24],
        "links": dedupe(parser.links)[:120],
        "visible_text": evidence_text,
        "visible_text_length": len(text),
        "live_external_side_effect": False,
    }


def collect_website_evidence(url: str, timeout_seconds: int = 12) -> dict[str, Any]:
    target = normalise_url(url)
    html = fetch_website_html(target, timeout_seconds=timeout_seconds)
    initial = collect_website_evidence_from_html(target, html)
    target_host = (urlparse(target).hostname or "").lower()
    css_chunks: list[str] = []

    for stylesheet_url in initial.get("stylesheet_urls", [])[:MAX_STYLESHEETS]:
        parsed = urlparse(str(stylesheet_url or ""))
        stylesheet_host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"}:
            continue
        if stylesheet_host != target_host and stylesheet_host != "fonts.googleapis.com":
            continue

        try:
            request = Request(
                stylesheet_url,
                headers={
                    "User-Agent": "AIONBusinessFoundationScanner/1.0 (+read-only evidence collection)",
                    "Accept": "text/css,*/*;q=0.1",
                },
            )
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read(MAX_STYLESHEET_BYTES + 1)
                if len(raw) > MAX_STYLESHEET_BYTES:
                    continue
                charset = response.headers.get_content_charset() or "utf-8"
                css_chunks.append(raw.decode(charset, errors="replace"))
        except Exception:
            continue

    if not css_chunks:
        return initial

    return collect_website_evidence_from_html(
        target,
        html,
        supplemental_css="\n".join(css_chunks),
    )
