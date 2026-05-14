from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.modules.aion_learning.contracts import (
    AionLearningContextView,
    AionLearningQuery,
    AionLearningReport,
    AionLearningSummary,
    AionLearningWeaknessSignal,
    AionRewardBreakdown,
)


def _dict(v: Any) -> Dict[str, Any]:
    return dict(v) if isinstance(v, dict) else {}


def _list(v: Any) -> List[Any]:
    return list(v) if isinstance(v, list) else []


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _safe_bool(v: Any, default: bool = False) -> bool:
    try:
        return bool(v)
    except Exception:
        return default


def _now_ts() -> float:
    return time.time()


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


@dataclass
class LearningPaths:
    events_path: str
    weaknesses_path: str


class AionLearningRuntime:
    """
    Phase D learning runtime.

    Sprint 1:
      - append learning events
      - derive weakness clusters

    Sprint 2:
      - typed query/read APIs
      - reward decomposition (process vs outcome)
      - reports + read-only learning context view
    """

    def __init__(
        self,
        data_root: Optional[str] = None,
        weakness_fail_threshold: int = 2,
        weakness_min_fail_rate: float = 0.5,
    ) -> None:
        self.data_root = str(data_root or ".runtime/COMDEX_MOVE/data")
        learning_dir = os.path.join(self.data_root, "learning")
        self.paths = LearningPaths(
            events_path=os.path.join(learning_dir, "aion_learning_events.jsonl"),
            weaknesses_path=os.path.join(learning_dir, "aion_weakness_signals.json"),
        )
        self.weakness_fail_threshold = max(1, int(weakness_fail_threshold))
        self.weakness_min_fail_rate = max(0.0, min(float(weakness_min_fail_rate), 1.0))

    # ------------------------------------------------------------------
    # File IO helpers
    # ------------------------------------------------------------------

    def _append_jsonl(self, path: str, row: Dict[str, Any]) -> None:
        _ensure_parent(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        out: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        d = json.loads(s)
                        if isinstance(d, dict):
                            out.append(d)
                    except Exception:
                        continue
        except Exception:
            return []
        return out

    def _write_json(self, path: str, data: Any) -> None:
        _ensure_parent(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _read_json(self, path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    # ------------------------------------------------------------------
    # Sprint 2 reward decomposition
    # ------------------------------------------------------------------

    def _compute_reward_breakdown(
        self,
        *,
        ok: bool,
        error_code: Optional[str],
        latency_ms: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AionRewardBreakdown:
        """
        Simple deterministic baseline reward model (Sprint 2).
        Keep easy to reason about; improve later with domain shaping.
        """
        md = _dict(metadata)

        # Outcome score: did the action succeed?
        outcome_score = 1.0 if bool(ok) else 0.0

        # Process score (baseline)
        process_score = 1.0

        # Penalize policy / routing / missing skill errors differently than execution errors
        code = str(error_code or "").strip()

        if code == "skill_not_found":
            process_score = 0.10
        elif code == "skill_policy_blocked":
            # blocked can actually be "good policy behavior", but for skill success process
            # we treat as low execution utility while still non-zero
            process_score = 0.35
        elif code == "skill_execution_error":
            process_score = 0.25
        elif not ok:
            process_score = 0.30

        # Latency shaping (lightweight; avoid overfitting)
        lat = max(0, int(latency_ms or 0))
        if lat > 5000:
            process_score -= 0.20
        elif lat > 2000:
            process_score -= 0.12
        elif lat > 1000:
            process_score -= 0.07
        elif lat > 500:
            process_score -= 0.03

        # Optional hints from metadata (Sprint 2, read-only usage)
        if bool(md.get("dry_run", False)):
            # dry_run is useful but not a full outcome
            outcome_score = max(outcome_score, 0.5)
            process_score = max(process_score, 0.9)

        # Normalize
        process_score = max(0.0, min(1.0, process_score))
        outcome_score = max(0.0, min(1.0, outcome_score))

        w_process = 0.6
        w_outcome = 0.4
        reward_score = (w_process * process_score) + (w_outcome * outcome_score)

        return AionRewardBreakdown(
            process_score=process_score,
            outcome_score=outcome_score,
            reward_score=reward_score,
            weighting={"process": w_process, "outcome": w_outcome},
            metadata={
                "latency_ms": lat,
                "error_code": code or None,
                "phase": "phase_d_sprint2_reward_decomposition",
            },
        ).validate()

    # ------------------------------------------------------------------
    # Sprint 1 core API (kept, enhanced with reward fields)
    # ------------------------------------------------------------------

    def record_skill_run(
        self,
        *,
        skill_id: str,
        skill_run_id: str,
        ok: bool,
        error_code: Optional[str] = None,
        latency_ms: int = 0,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Append one learning event. Non-breaking additive event shape.
        """
        skill_id = str(skill_id or "").strip()
        skill_run_id = str(skill_run_id or "").strip()
        if not skill_id:
            skill_id = "unknown_skill"
        if not skill_run_id:
            skill_run_id = f"learnrun_{uuid.uuid4().hex[:16]}"

        meta = _dict(metadata)
        ts = _now_ts()

        reward = self._compute_reward_breakdown(
            ok=bool(ok),
            error_code=error_code,
            latency_ms=int(latency_ms or 0),
            metadata=meta,
        )

        event = {
            "schema_version": "aion.learning_event.v2",
            "timestamp": ts,
            "event_id": f"levent_{uuid.uuid4().hex[:16]}",
            "event_type": "skill_run",
            "skill_id": skill_id,
            "skill_run_id": skill_run_id,
            "ok": bool(ok),
            "error_code": (str(error_code) if error_code else None),
            "latency_ms": max(0, int(latency_ms or 0)),
            "session_id": (str(session_id) if session_id else None),
            "turn_id": (str(turn_id) if turn_id else None),
            "reward": reward.to_dict(),
            "metadata": meta,
        }

        self._append_jsonl(self.paths.events_path, event)
        self._refresh_weakness_signals()
        return event

    # ------------------------------------------------------------------
    # Reads / summaries
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        events = self._read_jsonl(self.paths.events_path)
        if limit is not None:
            limit = max(1, int(limit))
            return events[-limit:]
        return events

    def get_weakness_signals(self) -> List[Dict[str, Any]]:
        data = self._read_json(self.paths.weaknesses_path, {"signals": []})
        signals = data.get("signals", []) if isinstance(data, dict) else []
        return [dict(x) for x in signals if isinstance(x, dict)]

    def get_summary(self) -> Dict[str, Any]:
        """
        Backward-compatible dict summary (Sprint 1 callers).
        """
        summary = self.build_summary(AionLearningQuery(limit=5000))
        return summary.to_dict()

    def build_summary(self, query: Optional[AionLearningQuery] = None) -> AionLearningSummary:
        q = (query or AionLearningQuery()).validate()
        events = self.query_events(q)

        total = len(events)
        ok_count = sum(1 for e in events if bool(e.get("ok")))
        fail_count = total - ok_count

        latencies = [max(0, _safe_int(e.get("latency_ms"), 0)) for e in events]
        avg_latency_ms = (sum(latencies) / len(latencies)) if latencies else 0.0

        process_scores: List[float] = []
        outcome_scores: List[float] = []
        reward_scores: List[float] = []

        by_skill: Dict[str, Dict[str, Any]] = {}
        by_error_code: Dict[str, int] = {}

        for e in events:
            sid = str(e.get("skill_id") or "unknown")
            ok = bool(e.get("ok"))
            ec = e.get("error_code")
            reward = _dict(e.get("reward"))

            if reward:
                ps = _safe_float(reward.get("process_score"), 0.0)
                os_ = _safe_float(reward.get("outcome_score"), 0.0)
                rs = _safe_float(reward.get("reward_score"), 0.0)
            else:
                # Backward-compat fallback for Sprint 1 events (no reward field)
                fallback_rb = self._compute_reward_breakdown(
                    ok=bool(e.get("ok")),
                    error_code=(str(e.get("error_code")) if e.get("error_code") else None),
                    latency_ms=max(0, _safe_int(e.get("latency_ms"), 0)),
                    metadata=_dict(e.get("metadata")),
                )
                ps = float(fallback_rb.process_score)
                os_ = float(fallback_rb.outcome_score)
                rs = float(fallback_rb.reward_score)

            process_scores.append(ps)
            outcome_scores.append(os_)
            reward_scores.append(rs)

            slot = by_skill.setdefault(
                sid,
                {
                    "count": 0,
                    "ok": 0,
                    "fail": 0,
                    "avg_latency_ms": 0.0,
                    "avg_process_score": 0.0,
                    "avg_outcome_score": 0.0,
                    "avg_reward_score": 0.0,
                    "_latencies": [],
                    "_ps": [],
                    "_os": [],
                    "_rs": [],
                },
            )
            slot["count"] += 1
            if ok:
                slot["ok"] += 1
            else:
                slot["fail"] += 1
            slot["_latencies"].append(max(0, _safe_int(e.get("latency_ms"), 0)))
            slot["_ps"].append(ps)
            slot["_os"].append(os_)
            slot["_rs"].append(rs)

            if ec:
                key = str(ec)
                by_error_code[key] = by_error_code.get(key, 0) + 1

        for sid, slot in by_skill.items():
            lats = slot.pop("_latencies", [])
            pss = slot.pop("_ps", [])
            oss = slot.pop("_os", [])
            rss = slot.pop("_rs", [])
            slot["avg_latency_ms"] = (sum(lats) / len(lats)) if lats else 0.0
            slot["avg_process_score"] = (sum(pss) / len(pss)) if pss else 0.0
            slot["avg_outcome_score"] = (sum(oss) / len(oss)) if oss else 0.0
            slot["avg_reward_score"] = (sum(rss) / len(rss)) if rss else 0.0

        return AionLearningSummary(
            total_events=total,
            ok_count=ok_count,
            fail_count=fail_count,
            avg_latency_ms=avg_latency_ms,
            avg_process_score=(sum(process_scores) / len(process_scores)) if process_scores else 0.0,
            avg_outcome_score=(sum(outcome_scores) / len(outcome_scores)) if outcome_scores else 0.0,
            avg_reward_score=(sum(reward_scores) / len(reward_scores)) if reward_scores else 0.0,
            by_skill=by_skill,
            by_error_code=by_error_code,
            generated_at_ts=_now_ts(),
            metadata={"phase": "phase_d_sprint2"},
        ).validate()

    # ------------------------------------------------------------------
    # Sprint 2 typed query/report APIs
    # ------------------------------------------------------------------

    def query_events(self, query: Optional[AionLearningQuery] = None) -> List[Dict[str, Any]]:
        q = (query or AionLearningQuery()).validate()
        events = self._read_jsonl(self.paths.events_path)

        out: List[Dict[str, Any]] = []
        for e in events:
            if not isinstance(e, dict):
                continue

            if q.skill_id and str(e.get("skill_id") or "") != q.skill_id:
                continue
            if q.error_code and str(e.get("error_code") or "") != q.error_code:
                continue
            if q.ok is not None and bool(e.get("ok")) != bool(q.ok):
                continue
            if q.since_ts is not None and _safe_float(e.get("timestamp"), 0.0) < float(q.since_ts):
                continue

            mf = q.metadata_filters or {}
            if mf:
                event_meta = _dict(e.get("metadata"))
                matched_all = True
                for k, v in mf.items():
                    if event_meta.get(k) != v:
                        matched_all = False
                        break
                if not matched_all:
                    continue

            out.append(e)

        # return most recent N
        if q.limit and len(out) > q.limit:
            out = out[-q.limit:]
        return out

    def query_weaknesses(self, query: Optional[AionLearningQuery] = None) -> List[AionLearningWeaknessSignal]:
        q = (query or AionLearningQuery()).validate()
        raw = self.get_weakness_signals()

        out: List[AionLearningWeaknessSignal] = []
        for s in raw:
            try:
                ws = AionLearningWeaknessSignal.from_dict(s)
            except Exception:
                continue

            if q.skill_id and ws.skill_id != q.skill_id:
                continue
            if q.error_code and ws.error_code != q.error_code:
                continue
            out.append(ws)

        # sort by severity/confidence/count desc
        severity_rank = {"high": 3, "medium": 2, "low": 1}
        out.sort(
            key=lambda x: (
                severity_rank.get(x.severity, 0),
                float(x.confidence),
                int(x.count),
            ),
            reverse=True,
        )

        if q.limit and len(out) > q.limit:
            out = out[: q.limit]
        return out

    def build_report(self, query: Optional[AionLearningQuery] = None) -> AionLearningReport:
        q = (query or AionLearningQuery()).validate()
        events = self.query_events(q)
        summary = self.build_summary(q)
        weaknesses: List[AionLearningWeaknessSignal] = self.query_weaknesses(q) if q.include_weaknesses else []

        report = AionLearningReport(
            report_id=f"alr_{uuid.uuid4().hex[:16]}",
            query=q.to_dict(),
            summary=summary.to_dict(),
            top_weaknesses=[w.to_dict() for w in weaknesses[:10]],
            recent_events=events[-20:],
            generated_at_ts=_now_ts(),
            metadata={
                "phase": "phase_d_sprint2",
                "read_only": True,
            },
        ).validate()
        return report

    def get_learning_context_view(
        self,
        *,
        topic: Optional[str] = None,
        query: Optional[AionLearningQuery] = None,
        max_weakness_hints: int = 5,
    ) -> AionLearningContextView:
        """
        Read-only orchestrator-facing learning context (Sprint 2).
        Stable interface for future writable permissions.
        """
        q = (query or AionLearningQuery(limit=200, include_weaknesses=True)).validate()
        report = self.build_report(q)

        weaknesses = [
            AionLearningWeaknessSignal.from_dict(x)
            for x in _list(report.top_weaknesses)
            if isinstance(x, dict)
        ]

        weakness_hints: List[str] = []
        cautions: List[str] = []
        refs: List[str] = []

        for w in weaknesses[: max(1, int(max_weakness_hints))]:
            label = w.skill_id or "unknown_skill"
            code = w.error_code or "unknown_error"
            weakness_hints.append(f"{label}:{code} fail_rate={w.fail_rate:.2f} count={w.count}")
            refs.append(w.weakness_id)

            if w.severity == "high":
                cautions.append(f"High repeated failure risk observed for {label} ({code}).")
            elif w.severity == "medium":
                cautions.append(f"Moderate failure cluster observed for {label} ({code}).")

        s = _dict(report.summary)
        compact_summary = {
            "total_events": _safe_int(s.get("total_events"), 0),
            "ok_count": _safe_int(s.get("ok_count"), 0),
            "fail_count": _safe_int(s.get("fail_count"), 0),
            "avg_reward_score": round(_safe_float(s.get("avg_reward_score"), 0.0), 4),
            "avg_process_score": round(_safe_float(s.get("avg_process_score"), 0.0), 4),
            "avg_outcome_score": round(_safe_float(s.get("avg_outcome_score"), 0.0), 4),
        }

        return AionLearningContextView(
            topic=(str(topic).strip() if topic else None),
            summary=compact_summary,
            weakness_hints=weakness_hints,
            recommended_cautions=cautions,
            evidence_refs=refs,
            writable=False,
            metadata={
                "report_id": report.report_id,
                "phase": "phase_d_sprint2",
                "read_only": True,
            },
        ).validate()

    # ------------------------------------------------------------------
    # Weakness clustering (Sprint 1 baseline, preserved)
    # ------------------------------------------------------------------

    def _refresh_weakness_signals(self) -> None:
        events = self._read_jsonl(self.paths.events_path)

        # Aggregate per (skill_id, error_code)
        buckets: Dict[str, Dict[str, Any]] = {}
        per_skill_totals: Dict[str, int] = {}

        for e in events:
            if not isinstance(e, dict):
                continue
            sid = str(e.get("skill_id") or "unknown_skill")
            ec = str(e.get("error_code") or "")
            ok = bool(e.get("ok"))
            lat = max(0, _safe_int(e.get("latency_ms"), 0))

            per_skill_totals[sid] = per_skill_totals.get(sid, 0) + 1

            if ok:
                continue
            if not ec:
                ec = "unknown_error"

            k = f"{sid}::{ec}"
            b = buckets.setdefault(
                k,
                {
                    "skill_id": sid,
                    "error_code": ec,
                    "count": 0,
                    "fail_count": 0,
                    "latencies": [],
                },
            )
            b["count"] += 1
            b["fail_count"] += 1
            b["latencies"].append(lat)

        signals: List[Dict[str, Any]] = []
        for _, b in buckets.items():
            sid = str(b["skill_id"])
            ec = str(b["error_code"])
            fail_count = int(b["fail_count"])
            total_for_skill = max(1, int(per_skill_totals.get(sid, fail_count)))
            fail_rate = fail_count / float(total_for_skill)
            avg_latency = (
                sum(b["latencies"]) / len(b["latencies"]) if b.get("latencies") else 0.0
            )

            if fail_count < self.weakness_fail_threshold:
                continue
            if fail_rate < self.weakness_min_fail_rate:
                continue

            severity = "low"
            if fail_count >= 5 or fail_rate >= 0.90:
                severity = "high"
            elif fail_count >= 3 or fail_rate >= 0.70:
                severity = "medium"

            confidence = min(1.0, (fail_count / max(1.0, float(self.weakness_fail_threshold))) * 0.5 + (fail_rate * 0.5))

            weakness = AionLearningWeaknessSignal(
                weakness_id=f"weak_{sid}_{ec}".replace(":", "_").replace("/", "_"),
                kind="skill_error_cluster",
                skill_id=sid,
                error_code=ec,
                count=fail_count,
                fail_rate=fail_rate,
                avg_latency_ms=avg_latency,
                confidence=confidence,
                severity=severity,
                summary=(
                    f"Repeated failures detected for {sid} ({ec}): "
                    f"{fail_count}/{total_for_skill} failed (fail_rate={fail_rate:.2f})."
                ),
                metadata={
                    "total_count_for_skill": total_for_skill,
                    "phase": "phase_d_sprint1_failure_clustering",
                },
            ).validate()

            signals.append(weakness.to_dict())

        # sort strongest first
        severity_rank = {"high": 3, "medium": 2, "low": 1}
        signals.sort(
            key=lambda x: (
                severity_rank.get(str(x.get("severity")), 0),
                _safe_float(x.get("confidence"), 0.0),
                _safe_int(x.get("count"), 0),
            ),
            reverse=True,
        )

        payload = {
            "schema_version": "aion.learning_weakness_report.v1",
            "generated_at_ts": _now_ts(),
            "signals": signals,
            "metadata": {
                "phase": "phase_d_sprint1_failure_clustering",
                "weakness_fail_threshold": self.weakness_fail_threshold,
                "weakness_min_fail_rate": self.weakness_min_fail_rate,
            },
        }
        self._write_json(self.paths.weaknesses_path, payload)


_GLOBAL_AION_LEARNING_RUNTIME: Optional[AionLearningRuntime] = None


def get_aion_learning_runtime(data_root: Optional[str] = None) -> AionLearningRuntime:
    global _GLOBAL_AION_LEARNING_RUNTIME
    if _GLOBAL_AION_LEARNING_RUNTIME is None:
        _GLOBAL_AION_LEARNING_RUNTIME = AionLearningRuntime(data_root=data_root)
    return _GLOBAL_AION_LEARNING_RUNTIME