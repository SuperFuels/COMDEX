# /workspaces/COMDEX/backend/modules/aion_learning/llm_weighting_runtime.py
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "aion.llm_weighting_runtime.v1"
DEFAULT_ACCURACY_LOG_PATH = Path(".runtime/COMDEX_MOVE/data/trading/llm_accuracy_log.jsonl")

_ALLOWED_BIAS = {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}
_ALLOWED_CONF = {"LOW", "MEDIUM", "HIGH"}


def _now_ts() -> float:
    return float(time.time())


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _safe_str(v: Any, default: str = "") -> str:
    s = str(v if v is not None else default).strip()
    return s


def _norm_key(v: Any) -> str:
    """
    Lightweight canonicalization for grouping dimensions.
    Keeps punctuation but uppercases/strips whitespace.
    """
    s = _safe_str(v).upper()
    return s


def _norm_bias(v: Any) -> str:
    s = _safe_str(v).upper()
    return s if s in _ALLOWED_BIAS else ""


def _norm_conf(v: Any, default: str = "MEDIUM") -> str:
    s = _safe_str(v, default).upper()
    return s if s in _ALLOWED_CONF else default


def _confidence_multiplier(conf: str) -> float:
    # deterministic/simple, non-risk-critical
    c = _norm_conf(conf, "MEDIUM")
    if c == "HIGH":
        return 1.15
    if c == "LOW":
        return 0.85
    return 1.0


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _iter_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not Path(path).exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except Exception:
            # non-breaking log reader
            continue
    return out


def _bool_or_none(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = _safe_str(v).lower()
    if s in {"true", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "0", "no", "n", "off"}:
        return False
    return None


def _safe_count(value: Any) -> int:
    try:
        i = int(value)
    except Exception:
        return 0
    return i if i > 0 else 0


def _score_bucket(score: Optional[float]) -> str:
    if not isinstance(score, (int, float)):
        return "unknown"
    s = float(score)
    if s >= 0.5:
        return "strong_positive"
    if s > 0.0:
        return "positive"
    if s == 0.0:
        return "flat"
    if s <= -0.5:
        return "strong_negative"
    return "negative"


def _top_k_counts(counts: Dict[str, int], k: int = 10) -> List[Tuple[str, int]]:
    items = [(str(key), int(val)) for key, val in counts.items()]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return items[: max(1, int(k))]


@dataclass
class LLMAccuracyRecord:
    llm_id: str

    # Existing Phase 3 dims
    pair: str = ""
    session: str = ""
    event_type: str = ""
    task_type: str = "directional_bias"

    # Existing directional task fields
    predicted_bias: str = ""
    actual_outcome_bias: str = ""
    correct: Optional[bool] = None

    # Extended P3B tracking dims / interpretations
    directional_bias_label: str = ""  # optional free-form bias label/category (beyond enum)
    level_prediction: str = ""        # e.g. "breakout", "hold", "sweep_then_reverse", "above_prior_high"
    level_actual: str = ""            # realized level behavior / tagged outcome
    level_correct: Optional[bool] = None

    reaction_interpretation: str = ""         # model interpretation, e.g. "news_spike_fade"
    actual_reaction_interpretation: str = ""  # realized/retrospective interpretation tag
    reaction_correct: Optional[bool] = None

    confidence: str = "MEDIUM"
    score: Optional[float] = None  # optional continuous scoring
    metadata: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=_now_ts)

    def validate(self) -> "LLMAccuracyRecord":
        self.llm_id = _safe_str(self.llm_id)
        if not self.llm_id:
            raise ValueError("llm_id is required")

        self.pair = _safe_str(self.pair)
        self.session = _safe_str(self.session)
        self.event_type = _safe_str(self.event_type)
        self.task_type = _safe_str(self.task_type, "directional_bias") or "directional_bias"

        # Directional bias enums remain bounded
        pb = _norm_bias(self.predicted_bias)
        ab = _norm_bias(self.actual_outcome_bias)
        self.predicted_bias = pb
        self.actual_outcome_bias = ab
        self.confidence = _norm_conf(self.confidence, "MEDIUM")

        # Free-form P3B dims (normalized for grouping)
        self.directional_bias_label = _safe_str(self.directional_bias_label)
        self.level_prediction = _safe_str(self.level_prediction)
        self.level_actual = _safe_str(self.level_actual)
        self.reaction_interpretation = _safe_str(self.reaction_interpretation)
        self.actual_reaction_interpretation = _safe_str(self.actual_reaction_interpretation)

        # Compute correctness when omitted
        if self.correct is None and pb and ab:
            self.correct = bool(pb == ab)
        else:
            self.correct = _bool_or_none(self.correct)

        if self.level_correct is None and self.level_prediction and self.level_actual:
            self.level_correct = bool(self.level_prediction == self.level_actual)
        else:
            self.level_correct = _bool_or_none(self.level_correct)

        if (
            self.reaction_correct is None
            and self.reaction_interpretation
            and self.actual_reaction_interpretation
        ):
            self.reaction_correct = bool(
                self.reaction_interpretation == self.actual_reaction_interpretation
            )
        else:
            self.reaction_correct = _bool_or_none(self.reaction_correct)

        if self.score is not None:
            s = _safe_float(self.score)
            if s < -1.0:
                s = -1.0
            if s > 1.0:
                s = 1.0
            self.score = s

        self.ts = _safe_float(self.ts, _now_ts())
        self.metadata = dict(self.metadata or {})
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": "llm_accuracy",
            "ts": float(self.ts),
            "llm_id": self.llm_id,
            "pair": self.pair,
            "session": self.session,
            "event_type": self.event_type,
            "task_type": self.task_type,
            "predicted_bias": self.predicted_bias,
            "actual_outcome_bias": self.actual_outcome_bias,
            "correct": self.correct,
            "directional_bias_label": self.directional_bias_label,
            "level_prediction": self.level_prediction,
            "level_actual": self.level_actual,
            "level_correct": self.level_correct,
            "reaction_interpretation": self.reaction_interpretation,
            "actual_reaction_interpretation": self.actual_reaction_interpretation,
            "reaction_correct": self.reaction_correct,
            "confidence": self.confidence,
            "score": self.score,
            "metadata": dict(self.metadata or {}),
        }


class LLMWeightingRuntime:
    """
    Phase 3 lightweight runtime:
    - logs LLM task performance (jsonl)
    - summarizes by llm / filters
    - synthesizes multi-LLM directional inputs with disagreement signaling
    - influences confidence/filtering only (not risk invariants)

    P3B expansion:
    - richer tracking dimensions and counters for pair/session/event_type/bias/level/reaction
    - non-breaking additive summary outputs
    """

    def __init__(self, accuracy_log_path: Path = DEFAULT_ACCURACY_LOG_PATH):
        self.accuracy_log_path = Path(accuracy_log_path)

    # ----------------------------
    # P3A / P3B: tracking
    # ----------------------------
    def log_llm_accuracy(
        self,
        *,
        llm_id: str,
        pair: str = "",
        session: str = "",
        event_type: str = "",
        task_type: str = "directional_bias",
        predicted_bias: str = "",
        actual_outcome_bias: str = "",
        correct: Optional[bool] = None,
        confidence: str = "MEDIUM",
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ts: Optional[float] = None,
        # P3B extended dimensions (optional / backward-compatible)
        directional_bias_label: str = "",
        level_prediction: str = "",
        level_actual: str = "",
        level_correct: Optional[bool] = None,
        reaction_interpretation: str = "",
        actual_reaction_interpretation: str = "",
        reaction_correct: Optional[bool] = None,
    ) -> Dict[str, Any]:
        rec = LLMAccuracyRecord(
            llm_id=llm_id,
            pair=pair,
            session=session,
            event_type=event_type,
            task_type=task_type,
            predicted_bias=predicted_bias,
            actual_outcome_bias=actual_outcome_bias,
            correct=correct,
            confidence=confidence,
            score=score,
            metadata=dict(metadata or {}),
            ts=float(ts) if ts is not None else _now_ts(),
            directional_bias_label=directional_bias_label,
            level_prediction=level_prediction,
            level_actual=level_actual,
            level_correct=level_correct,
            reaction_interpretation=reaction_interpretation,
            actual_reaction_interpretation=actual_reaction_interpretation,
            reaction_correct=reaction_correct,
        ).validate()

        row = rec.to_dict()
        _append_jsonl(self.accuracy_log_path, row)

        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "logged": row,
            "path": str(self.accuracy_log_path),
        }

    def _metric_counter_template(self) -> Dict[str, Any]:
        return {
            "n": 0,
            "correct_n": 0,
            "incorrect_n": 0,
            "unknown_n": 0,
            "accuracy": None,
        }

    def _metric_counter_add(self, bucket: Dict[str, Any], value: Optional[bool]) -> None:
        bucket["n"] = int(bucket.get("n", 0)) + 1
        if value is True:
            bucket["correct_n"] = int(bucket.get("correct_n", 0)) + 1
        elif value is False:
            bucket["incorrect_n"] = int(bucket.get("incorrect_n", 0)) + 1
        else:
            bucket["unknown_n"] = int(bucket.get("unknown_n", 0)) + 1

    def _metric_counter_finalize(self, bucket: Dict[str, Any]) -> None:
        denom = int(bucket.get("correct_n", 0)) + int(bucket.get("incorrect_n", 0))
        bucket["accuracy"] = (float(bucket["correct_n"]) / float(denom)) if denom > 0 else None

    def _build_dimension_breakdowns(
        self,
        matched: List[Dict[str, Any]],
        *,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Additive operational summary for P3B:
        counts and correctness rollups by common dimensions.
        """
        # Raw counts
        pair_counts: Dict[str, int] = {}
        session_counts: Dict[str, int] = {}
        event_type_counts: Dict[str, int] = {}
        task_type_counts: Dict[str, int] = {}
        predicted_bias_counts: Dict[str, int] = {}
        actual_bias_counts: Dict[str, int] = {}
        directional_bias_label_counts: Dict[str, int] = {}
        level_prediction_counts: Dict[str, int] = {}
        level_actual_counts: Dict[str, int] = {}
        reaction_interp_counts: Dict[str, int] = {}
        reaction_actual_counts: Dict[str, int] = {}
        score_bucket_counts: Dict[str, int] = {}

        # Accuracy buckets by dimension/value
        directional_by_pair: Dict[str, Dict[str, Any]] = {}
        directional_by_session: Dict[str, Dict[str, Any]] = {}
        directional_by_event_type: Dict[str, Dict[str, Any]] = {}
        directional_by_predicted_bias: Dict[str, Dict[str, Any]] = {}

        level_by_pair: Dict[str, Dict[str, Any]] = {}
        level_by_session: Dict[str, Dict[str, Any]] = {}
        level_by_event_type: Dict[str, Dict[str, Any]] = {}

        reaction_by_pair: Dict[str, Dict[str, Any]] = {}
        reaction_by_session: Dict[str, Dict[str, Any]] = {}
        reaction_by_event_type: Dict[str, Dict[str, Any]] = {}

        def _inc(d: Dict[str, int], key: str) -> None:
            d[key] = int(d.get(key, 0)) + 1

        def _acc(d: Dict[str, Dict[str, Any]], key: str, value: Optional[bool]) -> None:
            bucket = d.setdefault(key, self._metric_counter_template().copy())
            self._metric_counter_add(bucket, value)

        for r in matched:
            pair = _norm_key(r.get("pair")) or "(EMPTY)"
            session = _norm_key(r.get("session")) or "(EMPTY)"
            event_type = _norm_key(r.get("event_type")) or "(EMPTY)"
            task_type = _norm_key(r.get("task_type")) or "(EMPTY)"

            predicted_bias = _norm_key(r.get("predicted_bias")) or "(EMPTY)"
            actual_bias = _norm_key(r.get("actual_outcome_bias")) or "(EMPTY)"
            bias_label = _norm_key(r.get("directional_bias_label")) or "(EMPTY)"

            level_prediction = _norm_key(r.get("level_prediction")) or "(EMPTY)"
            level_actual = _norm_key(r.get("level_actual")) or "(EMPTY)"
            reaction_interp = _norm_key(r.get("reaction_interpretation")) or "(EMPTY)"
            reaction_actual = _norm_key(r.get("actual_reaction_interpretation")) or "(EMPTY)"

            _inc(pair_counts, pair)
            _inc(session_counts, session)
            _inc(event_type_counts, event_type)
            _inc(task_type_counts, task_type)
            _inc(predicted_bias_counts, predicted_bias)
            _inc(actual_bias_counts, actual_bias)
            _inc(directional_bias_label_counts, bias_label)
            _inc(level_prediction_counts, level_prediction)
            _inc(level_actual_counts, level_actual)
            _inc(reaction_interp_counts, reaction_interp)
            _inc(reaction_actual_counts, reaction_actual)
            _inc(score_bucket_counts, _score_bucket(r.get("score")))

            # Directional correctness rollups
            c_dir = _bool_or_none(r.get("correct"))
            _acc(directional_by_pair, pair, c_dir)
            _acc(directional_by_session, session, c_dir)
            _acc(directional_by_event_type, event_type, c_dir)
            _acc(directional_by_predicted_bias, predicted_bias, c_dir)

            # Level prediction correctness rollups
            c_level = _bool_or_none(r.get("level_correct"))
            _acc(level_by_pair, pair, c_level)
            _acc(level_by_session, session, c_level)
            _acc(level_by_event_type, event_type, c_level)

            # Reaction interpretation correctness rollups
            c_react = _bool_or_none(r.get("reaction_correct"))
            _acc(reaction_by_pair, pair, c_react)
            _acc(reaction_by_session, session, c_react)
            _acc(reaction_by_event_type, event_type, c_react)

        for d in (
            directional_by_pair,
            directional_by_session,
            directional_by_event_type,
            directional_by_predicted_bias,
            level_by_pair,
            level_by_session,
            level_by_event_type,
            reaction_by_pair,
            reaction_by_session,
            reaction_by_event_type,
        ):
            for bucket in d.values():
                self._metric_counter_finalize(bucket)

        def _sort_rollups(d: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
            keys = sorted(d.keys())
            return {k: d[k] for k in keys}

        return {
            "top_k": int(top_k),
            "counts": {
                "pair": _top_k_counts(pair_counts, top_k),
                "session": _top_k_counts(session_counts, top_k),
                "event_type": _top_k_counts(event_type_counts, top_k),
                "task_type": _top_k_counts(task_type_counts, top_k),
                "predicted_bias": _top_k_counts(predicted_bias_counts, top_k),
                "actual_outcome_bias": _top_k_counts(actual_bias_counts, top_k),
                "directional_bias_label": _top_k_counts(directional_bias_label_counts, top_k),
                "level_prediction": _top_k_counts(level_prediction_counts, top_k),
                "level_actual": _top_k_counts(level_actual_counts, top_k),
                "reaction_interpretation": _top_k_counts(reaction_interp_counts, top_k),
                "actual_reaction_interpretation": _top_k_counts(reaction_actual_counts, top_k),
                "score_bucket": _top_k_counts(score_bucket_counts, top_k),
            },
            "directional_correctness": {
                "by_pair": _sort_rollups(directional_by_pair),
                "by_session": _sort_rollups(directional_by_session),
                "by_event_type": _sort_rollups(directional_by_event_type),
                "by_predicted_bias": _sort_rollups(directional_by_predicted_bias),
            },
            "level_prediction_correctness": {
                "by_pair": _sort_rollups(level_by_pair),
                "by_session": _sort_rollups(level_by_session),
                "by_event_type": _sort_rollups(level_by_event_type),
            },
            "reaction_interpretation_correctness": {
                "by_pair": _sort_rollups(reaction_by_pair),
                "by_session": _sort_rollups(reaction_by_session),
                "by_event_type": _sort_rollups(reaction_by_event_type),
            },
        }

    def summarize_llm_accuracy(
        self,
        *,
        pair: Optional[str] = None,
        session: Optional[str] = None,
        event_type: Optional[str] = None,
        task_type: Optional[str] = None,
        llm_id: Optional[str] = None,
        lookback_rows: Optional[int] = None,
        include_breakdowns: bool = True,  # additive default-on for P3B
        top_k: int = 10,
    ) -> Dict[str, Any]:
        rows = _iter_jsonl(self.accuracy_log_path)
        if lookback_rows and lookback_rows > 0:
            rows = rows[-int(lookback_rows):]

        def _match(r: Dict[str, Any]) -> bool:
            if r.get("record_type") != "llm_accuracy":
                return False
            if pair and str(r.get("pair") or "") != pair:
                return False
            if session and str(r.get("session") or "") != session:
                return False
            if event_type and str(r.get("event_type") or "") != event_type:
                return False
            if task_type and str(r.get("task_type") or "") != task_type:
                return False
            if llm_id and str(r.get("llm_id") or "") != llm_id:
                return False
            return True

        matched = [r for r in rows if _match(r)]

        per_llm: Dict[str, Dict[str, Any]] = {}
        for r in matched:
            lid = str(r.get("llm_id") or "unknown")
            d = per_llm.setdefault(
                lid,
                {
                    "llm_id": lid,
                    "n": 0,
                    "correct_n": 0,
                    "incorrect_n": 0,
                    "unknown_n": 0,
                    "accuracy": None,
                    "avg_score": None,
                    "_score_sum": 0.0,
                    "_score_n": 0,
                    # additive P3B metrics
                    "level_correct_n": 0,
                    "level_incorrect_n": 0,
                    "level_unknown_n": 0,
                    "level_accuracy": None,
                    "reaction_correct_n": 0,
                    "reaction_incorrect_n": 0,
                    "reaction_unknown_n": 0,
                    "reaction_accuracy": None,
                    "pairs_seen": 0,
                    "sessions_seen": 0,
                    "event_types_seen": 0,
                    "_pairs_seen_set": set(),
                    "_sessions_seen_set": set(),
                    "_event_types_seen_set": set(),
                    "task_type_counts": {},
                    "predicted_bias_counts": {},
                },
            )
            d["n"] += 1

            c = r.get("correct")
            if c is True:
                d["correct_n"] += 1
            elif c is False:
                d["incorrect_n"] += 1
            else:
                d["unknown_n"] += 1

            c_level = _bool_or_none(r.get("level_correct"))
            if c_level is True:
                d["level_correct_n"] += 1
            elif c_level is False:
                d["level_incorrect_n"] += 1
            else:
                d["level_unknown_n"] += 1

            c_react = _bool_or_none(r.get("reaction_correct"))
            if c_react is True:
                d["reaction_correct_n"] += 1
            elif c_react is False:
                d["reaction_incorrect_n"] += 1
            else:
                d["reaction_unknown_n"] += 1

            if isinstance(r.get("score"), (int, float)):
                d["_score_sum"] += float(r["score"])
                d["_score_n"] += 1

            p = _safe_str(r.get("pair"))
            s = _safe_str(r.get("session"))
            e = _safe_str(r.get("event_type"))
            if p:
                d["_pairs_seen_set"].add(p)
            if s:
                d["_sessions_seen_set"].add(s)
            if e:
                d["_event_types_seen_set"].add(e)

            t = _safe_str(r.get("task_type")) or "(empty)"
            d["task_type_counts"][t] = int(d["task_type_counts"].get(t, 0)) + 1

            pb = _safe_str(r.get("predicted_bias")) or "(empty)"
            d["predicted_bias_counts"][pb] = int(d["predicted_bias_counts"].get(pb, 0)) + 1

        for d in per_llm.values():
            denom = d["correct_n"] + d["incorrect_n"]
            d["accuracy"] = (float(d["correct_n"]) / float(denom)) if denom > 0 else None
            d["avg_score"] = (d["_score_sum"] / d["_score_n"]) if d["_score_n"] > 0 else None
            d.pop("_score_sum", None)
            d.pop("_score_n", None)

            level_denom = d["level_correct_n"] + d["level_incorrect_n"]
            d["level_accuracy"] = (
                float(d["level_correct_n"]) / float(level_denom) if level_denom > 0 else None
            )

            react_denom = d["reaction_correct_n"] + d["reaction_incorrect_n"]
            d["reaction_accuracy"] = (
                float(d["reaction_correct_n"]) / float(react_denom) if react_denom > 0 else None
            )

            d["pairs_seen"] = len(d.pop("_pairs_seen_set", set()))
            d["sessions_seen"] = len(d.pop("_sessions_seen_set", set()))
            d["event_types_seen"] = len(d.pop("_event_types_seen_set", set()))
            d["task_type_counts"] = dict(sorted(d["task_type_counts"].items(), key=lambda kv: kv[0]))
            d["predicted_bias_counts"] = dict(
                sorted(d["predicted_bias_counts"].items(), key=lambda kv: kv[0])
            )

        out = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "filters": {
                "pair": pair,
                "session": session,
                "event_type": event_type,
                "task_type": task_type,
                "llm_id": llm_id,
                "lookback_rows": lookback_rows,
                "include_breakdowns": bool(include_breakdowns),
                "top_k": int(top_k),
            },
            "matched_rows": len(matched),
            "per_llm": dict(sorted(per_llm.items(), key=lambda kv: kv[0])),
        }

        if include_breakdowns:
            out["breakdowns"] = self._build_dimension_breakdowns(matched, top_k=top_k)

        return out

    def review_llm_accuracy(
        self,
        *,
        pair: Optional[str] = None,
        session: Optional[str] = None,
        event_type: Optional[str] = None,
        task_type: Optional[str] = None,
        llm_id: Optional[str] = None,
        lookback_rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        P3H operational audit-review wrapper around summarize_llm_accuracy().

        Adds:
        - mode="audit_review"
        - ops.topline summary
        - ops.flags (simple operational signals)
        - ops.recommendations (non-risk-critical suggestions)
        """
        summary = self.summarize_llm_accuracy(
            pair=pair,
            session=session,
            event_type=event_type,
            task_type=task_type,
            llm_id=llm_id,
            lookback_rows=lookback_rows,
        )

        # Preserve failure shape if summary ever fails
        if not bool(summary.get("ok", False)):
            out = dict(summary)
            out["mode"] = "audit_review"
            out["ops"] = {
                "topline": {
                    "matched_rows": int(summary.get("matched_rows") or 0),
                    "llm_count": len(dict(summary.get("per_llm") or {})),
                },
                "flags": ["summary_not_ok"],
                "recommendations": ["inspect_llm_accuracy_log_integrity"],
            }
            return out

        per_llm = dict(summary.get("per_llm") or {})
        matched_rows = int(summary.get("matched_rows") or 0)
        llm_count = len(per_llm)

        # simple aggregate stats for ops review
        known_acc = []
        low_acc_models: List[str] = []
        sparse_models: List[str] = []
        unknown_only_models: List[str] = []

        for lid, row in per_llm.items():
            n = int(row.get("n") or 0)
            unknown_n = int(row.get("unknown_n") or 0)
            acc = row.get("accuracy")

            if n < 3:
                sparse_models.append(lid)

            if unknown_n == n and n > 0:
                unknown_only_models.append(lid)

            if isinstance(acc, (int, float)):
                fa = float(acc)
                known_acc.append(fa)
                if n >= 3 and fa < 0.45:
                    low_acc_models.append(lid)

        mean_accuracy = (sum(known_acc) / len(known_acc)) if known_acc else None

        flags: List[str] = []
        recommendations: List[str] = []

        if matched_rows == 0:
            flags.append("no_matched_rows")
            recommendations.append("increase_lookback_or_relax_filters")

        if llm_count == 0:
            flags.append("no_llm_records")
            recommendations.append("verify_logging_pipeline")

        if sparse_models:
            flags.append("sparse_sample_models")
            recommendations.append("collect_more_samples_before_reweighting")

        if unknown_only_models:
            flags.append("unknown_correctness_records_present")
            recommendations.append("ensure_actual_outcome_bias_or_explicit_correct_is_logged")

        if low_acc_models:
            flags.append("low_accuracy_models")
            recommendations.append("review_prompts_or_downweight_underperformers")

        out = dict(summary)
        out["mode"] = "audit_review"
        out["ops"] = {
            "topline": {
                "matched_rows": matched_rows,
                "llm_count": llm_count,
                "mean_accuracy": mean_accuracy,
                "low_accuracy_model_count": len(low_acc_models),
                "sparse_model_count": len(sparse_models),
            },
            "flags": flags,
            "recommendations": recommendations,
            "details": {
                "low_accuracy_models": low_acc_models,
                "sparse_models": sparse_models,
                "unknown_only_models": unknown_only_models,
            },
        }
        return out

    # ----------------------------
    # P3C / P3D / P3E / P3F
    # ----------------------------
    def synthesise_llm_responses(
        self,
        *,
        pair: str,
        session: str,
        llm_pair: Dict[str, Any],
        event_type: str = "",
        task_type: str = "directional_bias",
    ) -> Dict[str, Any]:
        """
        Input shape (DMIP bridge compatible):
          {
            "claude_bias": "BULLISH",
            "gpt4_bias": "BEARISH",
            "confidence": "MEDIUM",           # optional shared fallback
            "claude_confidence": "HIGH",      # optional
            "gpt4_confidence": "LOW",         # optional
            ...
          }

        Returns a stable synthesis payload for DMIP consumption.
        """
        pair = _safe_str(pair)
        session = _safe_str(session)
        event_type = _safe_str(event_type)
        llm_pair = dict(llm_pair or {})

        # Canonical sources we know are already flowing in DMIP
        source_map = {
            "claude": {
                "bias": _norm_bias(llm_pair.get("claude_bias")),
                "confidence": _norm_conf(llm_pair.get("claude_confidence") or llm_pair.get("confidence"), "MEDIUM"),
            },
            "gpt4": {
                "bias": _norm_bias(llm_pair.get("gpt4_bias")),
                "confidence": _norm_conf(llm_pair.get("gpt4_confidence") or llm_pair.get("confidence"), "MEDIUM"),
            },
        }

        present = {k: v for k, v in source_map.items() if v["bias"]}
        if not present:
            return {
                "ok": True,
                "bias": "NEUTRAL",
                "confidence": "LOW",
                "agreement_flag": "none",
                "avoid": False,
                "reasons": ["no_llm_biases_present"],
                "weighted_scores": {},
                "sources": source_map,
            }

        # Pull empirical performance summary for weighting
        summary = self.summarize_llm_accuracy(
            pair=pair or None,
            session=session or None,
            event_type=event_type or None,
            task_type=task_type or None,
            lookback_rows=500,
            include_breakdowns=False,  # keep synthesis lean/fast
        )
        perf = dict(summary.get("per_llm") or {})

        # Weighting model (simple + bounded):
        # base 1.0, empirical factor in [0.5, 1.5] if accuracy available, conf multiplier [0.85, 1.15]
        weighted_scores: Dict[str, float] = {
            "BULLISH": 0.0,
            "BEARISH": 0.0,
            "NEUTRAL": 0.0,
            "AVOID": 0.0,
        }
        source_weights: Dict[str, float] = {}

        for lid, payload in present.items():
            acc = perf.get(lid, {}).get("accuracy")
            if isinstance(acc, (int, float)):
                empirical = max(0.5, min(1.5, 0.5 + float(acc)))  # acc 0.0->0.5, 1.0->1.5
            else:
                empirical = 1.0

            conf_mult = _confidence_multiplier(payload["confidence"])
            w = float(empirical * conf_mult)
            source_weights[lid] = w
            weighted_scores[payload["bias"]] += w

        # Agreement / disagreement classification
        unique_biases = sorted({p["bias"] for p in present.values() if p["bias"]})
        agreement_flag = "partial"
        avoid = False
        reasons: List[str] = []

        if len(present) == 1:
            agreement_flag = "partial"
            reasons.append("single_llm_input_partial")
        elif len(unique_biases) == 1:
            agreement_flag = "agree"
            reasons.append("llm_agreement")
        else:
            # Hard disagreement if directional conflict (bullish vs bearish)
            directional = set(unique_biases) & {"BULLISH", "BEARISH"}
            if directional == {"BULLISH", "BEARISH"}:
                agreement_flag = "hard_disagree"
                avoid = True
                reasons.append("llm_disagreement_pair_avoid")
            else:
                agreement_flag = "soft_disagree"
                reasons.append("llm_soft_disagreement")

        # Winner selection (weighting changes confidence/filtering only)
        best_bias, best_score = max(weighted_scores.items(), key=lambda kv: kv[1])

        # strict rule: hard disagreement => AVOID regardless of weighted winner
        if avoid:
            final_bias = "AVOID"
            final_conf = "LOW"
        else:
            final_bias = best_bias if best_score > 0 else "NEUTRAL"

            # confidence from margin
            total = sum(weighted_scores.values()) or 1.0
            ordered = sorted(weighted_scores.values(), reverse=True)
            top = ordered[0] if ordered else 0.0
            second = ordered[1] if len(ordered) > 1 else 0.0
            margin = (top - second) / total

            if agreement_flag == "agree" and margin >= 0.20:
                final_conf = "HIGH"
            elif margin >= 0.08:
                final_conf = "MEDIUM"
            else:
                final_conf = "LOW"

        return {
            "ok": True,
            "bias": final_bias,
            "confidence": final_conf,
            "agreement_flag": agreement_flag,
            "avoid": bool(avoid),
            "reasons": reasons,
            "weighted_scores": {k: round(v, 6) for k, v in weighted_scores.items() if v > 0},
            "source_weights": {k: round(v, 6) for k, v in source_weights.items()},
            "sources": source_map,
            "weighting_meta": {
                "pair": pair,
                "session": session,
                "event_type": event_type,
                "task_type": task_type,
                "matched_accuracy_rows": int(summary.get("matched_rows") or 0),
            },
        }

    def get_llm_weighted_bias(
        self,
        *,
        pair: str,
        session: str,
        llm_pair: Dict[str, Any],
        event_type: str = "",
        task_type: str = "directional_bias",
    ) -> Dict[str, Any]:
        return self.synthesise_llm_responses(
            pair=pair,
            session=session,
            llm_pair=llm_pair,
            event_type=event_type,
            task_type=task_type,
        )


# ----------------------------
# Module-level convenience API (for dmip_runtime import)
# ----------------------------

_default_runtime: Optional[LLMWeightingRuntime] = None


def _get_default_runtime() -> LLMWeightingRuntime:
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = LLMWeightingRuntime()
    return _default_runtime


def log_llm_accuracy(**kwargs: Any) -> Dict[str, Any]:
    return _get_default_runtime().log_llm_accuracy(**kwargs)


def summarize_llm_accuracy(**kwargs: Any) -> Dict[str, Any]:
    return _get_default_runtime().summarize_llm_accuracy(**kwargs)


def review_llm_accuracy(**kwargs: Any) -> Dict[str, Any]:
    return _get_default_runtime().review_llm_accuracy(**kwargs)


def synthesise_llm_responses(**kwargs: Any) -> Dict[str, Any]:
    return _get_default_runtime().synthesise_llm_responses(**kwargs)


def get_llm_weighted_bias(**kwargs: Any) -> Dict[str, Any]:
    return _get_default_runtime().get_llm_weighted_bias(**kwargs)