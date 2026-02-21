#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


_WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def _norm_set(items: Sequence[str] | None) -> set[str]:
    out: set[str] = set()
    for x in items or []:
        if not x:
            continue
        out.add(str(x).strip().lower())
    return out


@dataclass
class RetrievedConcept:
    concept_label: str
    score: float
    record: Dict[str, Any]
    reasons: List[str]


class TeachingRetriever:
    """
    Tiny deterministic retriever for Phase 0.2:
    scores concepts using:
      - intent exact match
      - topic token overlap
      - user text keyword overlap
      - tag overlap
      - optional phrase hints
    """

    def __init__(self, *, min_score: float = 1.0) -> None:
        self.min_score = float(min_score)

    def retrieve_best(
        self,
        *,
        user_text: str,
        intent: Optional[str],
        topic: Optional[str],
        concepts: Dict[str, Dict[str, Any]],
    ) -> Optional[RetrievedConcept]:
        ranked = self.retrieve_ranked(
            user_text=user_text,
            intent=intent,
            topic=topic,
            concepts=concepts,
        )
        return ranked[0] if ranked else None

    def retrieve_ranked(
        self,
        *,
        user_text: str,
        intent: Optional[str],
        topic: Optional[str],
        concepts: Dict[str, Dict[str, Any]],
    ) -> List[RetrievedConcept]:
        user_tokens = set(_tokenize(user_text))
        topic_tokens = set(_tokenize(topic or ""))
        norm_intent = (intent or "").strip().lower()

        out: List[RetrievedConcept] = []
        for label, rec in (concepts or {}).items():
            if not isinstance(rec, dict):
                continue

            score = 0.0
            reasons: List[str] = []

            hints = rec.get("routing_hints") or {}
            if not isinstance(hints, dict):
                hints = {}

            hint_intents = _norm_set(hints.get("intents"))
            hint_topics = _norm_set(hints.get("topic_keywords"))
            hint_phrases = _norm_set(hints.get("phrases"))
            rec_tags = _norm_set(rec.get("tags"))

            # 1) Intent match (strong)
            if norm_intent and norm_intent in hint_intents:
                score += 2.0
                reasons.append(f"intent:{norm_intent}")

            # 2) Topic keyword overlap
            topic_overlap = topic_tokens.intersection(hint_topics)
            if topic_overlap:
                bonus = min(2.0, 0.5 * len(topic_overlap))
                score += bonus
                reasons.append(f"topic_overlap:{sorted(topic_overlap)}")

            # 3) User text keyword overlap (stronger signal than topic tokens)
            user_overlap = user_tokens.intersection(hint_topics)
            if user_overlap:
                bonus = min(3.0, 0.75 * len(user_overlap))
                score += bonus
                reasons.append(f"user_keyword_overlap:{sorted(user_overlap)}")

            # 4) Tag overlap with user/topic tokens
            tag_overlap = rec_tags.intersection(user_tokens.union(topic_tokens))
            if tag_overlap:
                bonus = min(1.5, 0.5 * len(tag_overlap))
                score += bonus
                reasons.append(f"tag_overlap:{sorted(tag_overlap)}")

            # 5) Phrase hints exact-substring
            lowered_user = (user_text or "").lower()
            phrase_hits = [p for p in hint_phrases if p and p in lowered_user]
            if phrase_hits:
                bonus = min(2.5, 1.25 * len(phrase_hits))
                score += bonus
                reasons.append(f"phrase_hits:{phrase_hits}")

            # 6) Tiny fallback for concept label tokens appearing in user text
            label_tokens = set(_tokenize(label))
            label_overlap = label_tokens.intersection(user_tokens)
            if label_overlap:
                score += min(1.0, 0.25 * len(label_overlap))
                reasons.append(f"label_overlap:{sorted(label_overlap)}")

            if score >= self.min_score:
                out.append(
                    RetrievedConcept(
                        concept_label=label,
                        score=round(score, 3),
                        record=rec,
                        reasons=reasons,
                    )
                )

        out.sort(key=lambda x: (x.score, x.concept_label), reverse=True)
        return out