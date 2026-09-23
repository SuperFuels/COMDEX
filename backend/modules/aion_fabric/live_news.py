from __future__ import annotations

import json
import os
import re
import threading
import urllib.parse
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveNewsIntelligence:
    """Compile source-labelled fact checks without inventing overlay authority."""

    VERDICTS = {"Supported", "Misleading", "False", "Disputed", "Unverifiable"}
    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "live"
        self.path = self.root / "latest_fact_check.json"
        self.history_path = self.root / "fact_check_history.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _verdict(cls, research: Dict[str, Any]) -> str:
        explicit = str(research.get("verdict") or "").strip().title()
        if explicit in cls.VERDICTS:
            return explicit
        first = re.split(r"[\s:—-]+", str(research.get("answer") or "").strip(), maxsplit=1)[0].title()
        return first if first in cls.VERDICTS else "Unverifiable"

    @staticmethod
    def _source_class(url: str) -> str:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host.endswith(".gov") or ".gov." in host or host in {"europa.eu", "who.int", "un.org", "oecd.org"}:
            return "government_or_intergovernmental"
        if host.endswith((".edu", ".ac.uk", ".ac.es")):
            return "academic"
        return "publisher_or_organization"

    @staticmethod
    def _source_quality(source_class: str, url: str) -> tuple[float, str]:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if source_class == "government_or_intergovernmental":
            return 0.95, "Primary government or intergovernmental source"
        if source_class == "academic":
            return 0.9, "Academic institution source"
        if host.endswith(("reuters.com", "apnews.com", "bbc.com", "bbc.co.uk")):
            return 0.82, "Established publisher with formal editorial controls"
        return 0.62, "Publisher or organization; verify its primary evidence and incentives"

    @staticmethod
    def _bounded_statement(context: Dict[str, Any], screen: Dict[str, Any]) -> tuple[str, str]:
        statement = " ".join(str(context.get("recent_statement") or "").split()).strip()[:500]
        if statement:
            return statement, "ephemeral_local_transcript"
        corrections = list(screen.get("corrections") or [])
        corrected = next(
            (" ".join(str(item.get("value") or "").split())[:500] for item in reversed(corrections)
             if item.get("field") in {"subtitle", "scene"} and str(item.get("value") or "").strip()),
            "",
        )
        if corrected:
            return corrected, "owner_correction"
        subtitles = list((screen.get("subtitles") or {}).get("lines") or [])
        return (" ".join(str(subtitles[-1]).split())[:500], "owner_captured_subtitle") if subtitles else ("", "missing")

    def compile(
        self,
        *,
        live_context: Dict[str, Any],
        research: Dict[str, Any],
        screen_understanding: Dict[str, Any] | None = None,
        latency_ms: int | None = None,
    ) -> Dict[str, Any]:
        screen = dict(screen_understanding or {})
        statement, statement_source = self._bounded_statement(live_context, screen)
        if not statement:
            raise ValueError("A fact-check requires a captured statement")
        items = [dict(item) for item in list(research.get("items") or [])[:5] if isinstance(item, dict)]
        sources = []
        for index, item in enumerate(items, 1):
            url = str(item.get("url") or "")
            if not url.startswith("https://"):
                continue
            source_class = self._source_class(url)
            quality_score, quality_basis = self._source_quality(source_class, url)
            sources.append({
                "index": index,
                "title": str(item.get("title") or "Evidence source")[:160],
                "url": url[:1000],
                "source_class": source_class,
                "quality_score": quality_score,
                "quality_basis": quality_basis,
                "reason": str(item.get("reason") or "")[:300],
            })
        valid_indexes = {item["index"] for item in sources}
        verdict = self._verdict(research)
        claims = []
        for item in list(research.get("claims") or [])[:4]:
            if not isinstance(item, dict):
                continue
            claim_verdict = str(item.get("verdict") or "Unverifiable").title()
            if claim_verdict not in self.VERDICTS:
                claim_verdict = "Unverifiable"
            claims.append({
                "claim": " ".join(str(item.get("claim") or "").split())[:320],
                "verdict": claim_verdict,
                "explanation": " ".join(str(item.get("explanation") or "").split())[:500],
                "confidence": round(max(0.0, min(float(item.get("confidence") or 0), 1.0)), 3),
                "source_indexes": sorted({int(value) for value in list(item.get("source_indexes") or []) if isinstance(value, int) and value in valid_indexes}),
                "date_scope": " ".join(str(item.get("date_scope") or "").split())[:160],
            })
        if not claims:
            claims = [{
                "claim": statement,
                "verdict": verdict,
                "explanation": " ".join(str(research.get("answer") or "").split())[:500],
                "confidence": round(max(0.0, min(float(research.get("confidence") or 0), 1.0)), 3),
                "source_indexes": sorted(valid_indexes),
                "date_scope": "",
            }]
        confidence = round(max(0.0, min(float(research.get("confidence") or 0), 1.0)), 3)
        if research.get("provider") == "safe_search_handoff":
            verdict = "Unverifiable"
            confidence = 0.0
        timeline = [{
            "event": "statement_captured",
            "at": live_context.get("created_at") or utc_now_iso(),
            "source": statement_source,
            "detail": statement,
        }]
        for correction in list(screen.get("corrections") or [])[-10:]:
            if not isinstance(correction, dict):
                continue
            timeline.append({
                "event": "owner_correction",
                "at": correction.get("created_at"),
                "source": str(correction.get("field") or "scene"),
                "detail": str(correction.get("value") or "")[:240],
            })
        timeline.append({
            "event": "evidence_researched",
            "at": research.get("created_at") or utc_now_iso(),
            "source": str(research.get("provider") or "unknown"),
            "detail": f"{len(sources)} sanitized HTTPS sources",
        })
        answer = " ".join(str(research.get("answer") or "").split()).strip()[:700]
        verdicts_by_claim: Dict[str, set[str]] = {}
        for claim in claims:
            key = re.sub(r"\W+", " ", str(claim.get("claim") or "").lower()).strip()
            if key:
                verdicts_by_claim.setdefault(key, set()).add(str(claim.get("verdict") or "Unverifiable"))
        contradictions = [
            {"claim_key": key[:240], "verdicts": sorted(verdicts)}
            for key, verdicts in verdicts_by_claim.items()
            if len(verdicts) > 1
        ]
        disputed_claims = [
            {"claim": claim["claim"], "source_indexes": claim["source_indexes"], "explanation": claim["explanation"]}
            for claim in claims if claim["verdict"] == "Disputed"
        ]
        source_quality_mean = round(sum(float(item["quality_score"]) for item in sources) / len(sources), 3) if sources else 0.0
        record: Dict[str, Any] = {
            "schema_version": "pilot.live-news.v2",
            "fact_check_id": f"fact_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "statement": statement,
            "statement_source": statement_source,
            "verdict": verdict,
            "confidence": confidence,
            "summary": answer,
            "claims": claims,
            "context_notes": [" ".join(str(value).split())[:280] for value in list(research.get("context_notes") or [])[:5] if str(value).strip()],
            "sources": sources,
            "contradiction_analysis": {
                "contradictions_detected": len(contradictions),
                "contradictions": contradictions,
                "disputed_claims": disputed_claims,
                "model_cannot_create_source_disagreement": True,
            },
            "performance": {
                "latency_ms": max(0, int(latency_ms or 0)),
                "source_count": len(sources),
                "mean_source_quality": source_quality_mean,
                "quality_measured_outside_model": True,
            },
            "correction_timeline": timeline,
            "research_provider": research.get("provider"),
            "evidence_status": "researched" if sources and research.get("provider") != "safe_search_handoff" else "insufficient_or_handoff",
            "presentation": {
                "spoken_summary_preserves_playback": True,
                "private_phone_full_evidence": True,
                "third_party_tv_overlay_supported": False,
                "overlay_limitation": "LG reserves toast overlays for system applications; the gateway must not claim this authority.",
                "canvas_fallback_replaces_programme": True,
            },
            "privacy": {
                "raw_audio_retained": False,
                "source_pixels_retained": False,
                "raw_provider_response_retained": False,
                "private_identity_projected_to_tv": False,
            },
        }
        record["evidence_hash"] = canonical_hash(record)
        with self._lock:
            self._save(record)
            history = self.history()
            history.append({
                "fact_check_id": record["fact_check_id"],
                "created_at": record["created_at"],
                "statement": record["statement"],
                "verdict": record["verdict"],
                "confidence": record["confidence"],
                "evidence_hash": record["evidence_hash"],
            })
            temporary = self.history_path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(history[-50:]))
            os.replace(temporary, self.history_path)
        return record

    def follow_up(self, kind: str) -> Dict[str, Any]:
        """Answer evidence follow-ups deterministically from the frozen record."""
        kind = re.sub(r"[^a-z_]+", "_", str(kind).lower()).strip("_")
        if kind not in {"evidence", "disagreement", "difference"}:
            raise ValueError("Unknown fact-check follow-up")
        record = self.latest()
        if not record:
            raise LookupError("No completed fact-check is available")
        sources = list(record.get("sources") or [])
        claims = list(record.get("claims") or [])
        analysis = dict(record.get("contradiction_analysis") or {})
        if kind == "evidence":
            if sources:
                strongest = sorted(sources, key=lambda item: float(item.get("quality_score") or 0), reverse=True)[:3]
                answer = (
                    f"The {record.get('verdict', 'Unverifiable').lower()} verdict uses {len(sources)} retained sources. "
                    "The strongest are " + "; ".join(str(item.get("title") or "Evidence source") for item in strongest) + "."
                )
            else:
                answer = "No source evidence was retained, so the verdict remains unverifiable."
        elif kind == "disagreement":
            disputed = list(analysis.get("disputed_claims") or [])
            contradictions = list(analysis.get("contradictions") or [])
            if disputed:
                answer = "Disagreement is established for: " + "; ".join(str(item.get("claim") or "") for item in disputed[:3]) + "."
            elif contradictions:
                answer = "The retained evidence contains conflicting verdicts for the same normalized claim."
            else:
                answer = "No named source disagreement is established in the retained evidence. I will not invent an opposing source."
        else:
            date_scopes = [str(item.get("date_scope") or "").strip() for item in claims if str(item.get("date_scope") or "").strip()]
            notes = [str(value).strip() for value in list(record.get("context_notes") or []) if str(value).strip()]
            differing_verdicts = sorted({str(item.get("verdict") or "Unverifiable") for item in claims})
            details = []
            if len(set(date_scopes)) > 1:
                details.append("the claims use different dates or measurement periods")
            if len(differing_verdicts) > 1:
                details.append("the decomposed claims receive different verdicts")
            if notes:
                details.append(notes[0])
            answer = "The important difference is that " + "; ".join(details) + "." if details else "The retained evidence does not establish a precise difference in definitions, dates, populations, or measurement periods."
        result = {
            "schema_version": "pilot.live-news-follow-up.v1",
            "follow_up_id": f"fact_followup_{uuid4().hex}",
            "fact_check_id": record.get("fact_check_id"),
            "kind": kind,
            "answer": answer[:700],
            "verdict": record.get("verdict"),
            "sources": sources[:5],
            "claims": claims[:4],
            "created_at": utc_now_iso(),
            "playback_preserved": True,
            "derived_without_model": True,
        }
        result["evidence_hash"] = canonical_hash(result)
        return result

    def _save(self, value: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.replace(temporary, self.path)

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def history(self) -> list[Dict[str, Any]]:
        if not self.history_path.exists():
            return []
        try:
            value = json.loads(self.history_path.read_text(encoding="utf-8"))
            return [dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []
