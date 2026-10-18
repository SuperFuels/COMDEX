from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class SpoilerAwareSceneExplanation:
    """Explain only owner-observed scene evidence, never a future plot synopsis."""

    _future_markers = re.compile(
        r"\b(later|eventually|in the end|at the end|turns out|will reveal|will discover|the killer|dies|death of|finale)\b",
        re.I,
    )

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "live" / "latest_scene_explanation.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _playback_boundary(live_context: Dict[str, Any]) -> Dict[str, Any]:
        playback = dict(live_context.get("playback") or {})
        position, duration = playback.get("position"), playback.get("duration")
        numeric = isinstance(position, (int, float)) and isinstance(duration, (int, float)) and duration > 0
        return {
            "known": numeric,
            "position": position if numeric else None,
            "duration": duration if numeric else None,
            "progress_percent": round(float(position) / float(duration) * 100, 1) if numeric else None,
            "policy": "never_use_evidence_beyond_observed_scene",
        }

    @staticmethod
    def _observed_evidence(live_context: Dict[str, Any], screen: Dict[str, Any]) -> list[Dict[str, Any]]:
        evidence: list[Dict[str, Any]] = []
        for value in list(live_context.get("recent_transcripts") or [])[-4:]:
            text = " ".join(str(value).split())[:320]
            if text:
                evidence.append({"kind": "local_recent_dialogue", "text": text})
        subtitles = list((screen.get("subtitles") or {}).get("lines") or [])[-3:]
        for value in subtitles:
            text = " ".join(str(value).split())[:320]
            if text:
                evidence.append({"kind": "owner_captured_subtitle", "text": text})
        summary = " ".join(str(screen.get("summary") or "").split())[:400]
        if summary:
            evidence.append({"kind": "owner_captured_scene_summary", "text": summary})
        corrections = list(screen.get("corrections") or [])[-3:]
        for item in corrections:
            if isinstance(item, dict) and str(item.get("value") or "").strip():
                evidence.append({"kind": "owner_correction", "text": str(item["value"])[:320]})
        return evidence[-8:]

    def _local_explanation(
        self,
        evidence: list[Dict[str, Any]],
        kind: str,
        *,
        audience: str,
        detail_level: str,
        learning_subject: str,
    ) -> Dict[str, Any] | None:
        if os.getenv("AION_LOCAL_LLM_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
            return None
        model = os.getenv("AION_LOCAL_GEMMA_MODEL", os.getenv("OLLAMA_MODEL", "gemma4:e2b"))
        base_url = os.getenv("AION_OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "uncertainty", "observed_facts", "accessibility_summary", "learning_activity"],
            "properties": {
                "answer": {"type": "string", "maxLength": 600},
                "uncertainty": {"type": "string", "maxLength": 240},
                "observed_facts": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 220}},
                "accessibility_summary": {"type": "string", "maxLength": 400},
                "learning_activity": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["subject", "prompt", "answer"],
                    "properties": {
                        "subject": {"type": "string", "maxLength": 40},
                        "prompt": {"type": "string", "maxLength": 300},
                        "answer": {"type": "string", "maxLength": 400},
                    },
                },
            },
        }
        payload = {
            "model": model,
            "stream": False,
            "format": schema,
            "system": (
                "You explain a television scene using ONLY the supplied owner-observed evidence. "
                "Never use plot knowledge, programme summaries, future events, endings, character fate, or facts not in the evidence. "
                "If the evidence is insufficient, say exactly what is missing. Explain dialogue meaning plainly and concisely. "
                "For jokes or cultural references, distinguish evidence from interpretation and do not invent an origin, date or person. "
                "For a child audience, use calm age-appropriate language and do not introduce mature detail absent from the evidence. "
                "The accessibility summary must describe only visible structured evidence and must not identify people. "
                "Create a learning activity only when requested; otherwise return empty strings for its fields."
            ),
            "prompt": (
                f"Request kind: {kind}\nAudience: {audience}\nDetail level: {detail_level}\n"
                f"Learning subject: {learning_subject or 'none'}\nObserved evidence:\n"
                f"{json.dumps(evidence, ensure_ascii=False)}"
            ),
            "options": {"temperature": 0.0, "num_predict": 420},
        }
        request = urllib.request.Request(
            f"{base_url}/api/generate",
            data=canonical_bytes(payload),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = json.loads(response.read(500_001))
            result = json.loads(str(raw.get("response") or "{}"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            return None
        answer = " ".join(str(result.get("answer") or "").split())[:600]
        if not answer or self._future_markers.search(answer):
            return None
        uncertainty = " ".join(str(result.get("uncertainty") or "").split())[:240]
        facts = [" ".join(str(value).split())[:220] for value in list(result.get("observed_facts") or [])[:5] if str(value).strip()]
        accessibility_summary = " ".join(str(result.get("accessibility_summary") or "").split())[:400]
        activity = dict(result.get("learning_activity") or {})
        learning_activity = {
            "subject": " ".join(str(activity.get("subject") or "").split())[:40],
            "prompt": " ".join(str(activity.get("prompt") or "").split())[:300],
            "answer": " ".join(str(activity.get("answer") or "").split())[:400],
        }
        if self._future_markers.search(accessibility_summary) or any(
            self._future_markers.search(value) for value in learning_activity.values()
        ):
            return None
        return {
            "answer": answer,
            "uncertainty": uncertainty,
            "facts": facts,
            "accessibility_summary": accessibility_summary,
            "learning_activity": learning_activity,
        }

    def explain(
        self,
        *,
        live_context: Dict[str, Any],
        screen_understanding: Dict[str, Any] | None,
        request_kind: str = "scene",
        audience: str = "general",
        detail_level: str = "normal",
        learning_subject: str = "",
    ) -> Dict[str, Any]:
        audience = audience if audience in {"general", "child"} else "general"
        detail_level = detail_level if detail_level in {"simple", "normal", "detailed"} else "normal"
        learning_subject = learning_subject if learning_subject in {"science", "history", "language"} else ""
        screen = dict(screen_understanding or {})
        evidence = self._observed_evidence(live_context, screen)
        boundary = self._playback_boundary(live_context)
        local = self._local_explanation(
            evidence,
            request_kind,
            audience=audience,
            detail_level=detail_level,
            learning_subject=learning_subject,
        ) if evidence else None
        if local:
            answer = str(local["answer"])
            uncertainty = str(local["uncertainty"])
            facts = list(local["facts"])
            accessibility_summary = str(local["accessibility_summary"])
            learning_activity = dict(local["learning_activity"])
            provider = "aion_local_gemma_observed_evidence"
            confidence = min(0.9, 0.52 + len(evidence) * 0.06)
        elif evidence:
            latest = str(evidence[-1]["text"])
            if request_kind in {"joke", "reference", "cultural_context"}:
                answer = f"I captured this line or scene: {latest} I cannot verify the joke or cultural reference from that evidence alone."
            elif request_kind == "accessibility":
                answer = f"Visual description from the permitted observation: {latest}"
            elif request_kind == "learning":
                answer = f"Using only this observed scene: {latest} I prepared a short {learning_subject or 'learning'} question on your phone."
            else:
                answer = (
                    f"From the part Pilot actually observed: {latest}"
                    if request_kind == "dialogue"
                    else f"Pilot captured this current-scene evidence: {latest} I cannot safely add unobserved plot details."
                )
            if audience == "child":
                answer = f"In simple words: {answer}"
            uncertainty = "A local explanation model was unavailable, so Pilot preserved the evidence without guessing."
            facts = [str(item["text"]) for item in evidence[-3:]]
            accessibility_summary = latest if request_kind == "accessibility" else ""
            learning_activity = {
                "subject": learning_subject,
                "prompt": f"What {learning_subject or 'idea'} can you identify from this observed scene?",
                "answer": f"Use only this evidence in your answer: {latest}",
            } if request_kind == "learning" else {"subject": "", "prompt": "", "answer": ""}
            provider = "aion_deterministic_observed_evidence"
            confidence = 0.5
        else:
            answer = "I do not have enough current-scene evidence to explain that without risking a spoiler. Capture the screen or ask again immediately after the dialogue."
            uncertainty = "No recent dialogue, subtitle, scene capture, or owner correction was available."
            facts = []
            accessibility_summary = ""
            learning_activity = {"subject": "", "prompt": "", "answer": ""}
            provider = "honest_limitation"
            confidence = 0.0
        record: Dict[str, Any] = {
            "schema_version": "pilot.scene-explanation.v1",
            "explanation_id": f"explanation_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "request_kind": request_kind,
            "audience": audience,
            "detail_level": detail_level,
            "learning_subject": learning_subject or None,
            "spoiler_policy": "observed_evidence_only",
            "playback_boundary": boundary,
            "answer": answer,
            "uncertainty": uncertainty,
            "observed_facts": facts,
            "accessibility_summary": accessibility_summary,
            "learning_activity": learning_activity,
            "evidence_kinds": sorted({str(item["kind"]) for item in evidence}),
            "provider": provider,
            "confidence": round(confidence, 3),
            "future_plot_sources_used": False,
            "internet_plot_search_used": False,
            "presentation": {"playback_preserved": True, "spoken_summary": True, "private_phone_detail": True},
        }
        record["evidence_hash"] = canonical_hash({"context": live_context.get("context_hash"), "evidence": evidence})
        record["record_hash"] = canonical_hash(record)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.replace(temporary, self.path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
