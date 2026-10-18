"""Provider-neutral AION tool orchestration for connected chat models.

Models propose or consume tool results; they never own credentials, browser
sessions, approval policy, or execution.  This module deliberately has no
Qwen/OpenAI/Gemini branches so an approved connection receives the same
capabilities regardless of where its weights are hosted.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Mapping


_CURRENT_INFORMATION_PATTERNS = (
    r"\bsearch(?: the)? web\b",
    r"\blook (?:it|this|that) up\b",
    r"\bfind (?:out|recent|latest|current|today|online)\b",
    r"\b(?:latest|recent|today(?:'s)?|current|up[- ]to[- ]date|real[- ]time)\b",
    r"\bnews|coverage|sources?|citations?|online\b",
)


def requires_current_web_evidence(prompt: str) -> bool:
    """Return true only when the newest user turn asks for current web evidence."""
    newest_turn = str(prompt or "").rsplit("\n\nUser:", 1)[-1].strip().casefold()
    return any(re.search(pattern, newest_turn) for pattern in _CURRENT_INFORMATION_PATTERNS)


def web_research_query(prompt: str) -> str:
    """Remove chat command phrasing while preserving the subject being researched."""
    query = str(prompt or "").rsplit("\n\nUser:", 1)[-1].strip()
    query = re.sub(r"^(?:please\s+)?search(?:\s+the)?\s+web\s+(?:and\s+)?", "", query, flags=re.I)
    query = re.sub(r"^(?:please\s+)?look\s+(?:this|that|it)\s+up\s+(?:and\s+)?", "", query, flags=re.I)
    query = re.sub(r"^find\s+(?:out\s+)?(?:anything\s+)?", "", query, flags=re.I)
    return " ".join(query.split()).strip()[:500]


@dataclass(frozen=True)
class ModelToolContext:
    prompt: str
    evidence: tuple[Mapping[str, Any], ...]
    tool_name: str = "web.search_and_read"
    provider_neutral: bool = True

    def render_for_model(self) -> str:
        sources: list[str] = []
        for index, item in enumerate(self.evidence[:4], start=1):
            title = str(item.get("title") or f"Source {index}").strip()
            url = str(item.get("url") or "").strip()
            published = str(item.get("published_at") or item.get("date") or "date unavailable").strip()
            # Small local models commonly have a 4K context window. AION keeps
            # each source concise so citations fit alongside governed business
            # context and the model can still produce an answer.
            excerpt = str(item.get("content") or item.get("summary") or "").strip()[:1_000]
            sources.append(
                f"[{index}] {title}\nURL: {url}\nPublished: {published}\nEvidence: {excerpt}"
            )
        evidence_block = "\n\n".join(sources) or "No verified web evidence was returned."
        return (
            "AION performed a governed, read-only web research step for this request. "
            "Use only the evidence below for current claims. Do not say that you cannot browse. "
            "If the evidence is insufficient, say exactly what remains unknown. Cite factual claims "
            "inline as [1], [2], and finish with a Sources list containing the supplied URLs.\n\n"
            f"USER REQUEST\n{self.prompt}\n\nVERIFIED WEB EVIDENCE\n{evidence_block}"
        )


class ConnectedModelToolRuntime:
    """Run AION-owned read tools and prepare results for any approved model."""

    def __init__(self, *, evidence_search: Callable[[str], list[Mapping[str, Any]]]) -> None:
        self._evidence_search = evidence_search

    def prepare(self, prompt: str) -> ModelToolContext | None:
        if not requires_current_web_evidence(prompt):
            return None
        evidence = tuple(self._evidence_search(web_research_query(prompt))[:5])
        return ModelToolContext(prompt=str(prompt or ""), evidence=evidence)
