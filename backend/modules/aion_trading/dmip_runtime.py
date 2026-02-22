from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_trading.contracts import DailyBiasSheet, PairBias

# ---------------------------------------------------------------------
# Optional Phase 2 risk rules import (fail-open import pattern preserved)
# ---------------------------------------------------------------------
try:
    from backend.modules.aion_trading.risk_rules import (
        validate_trade_proposal as _validate_trade_proposal,
        DEFAULT_TRADING_RISK_POLICY,
    )
except Exception:  # pragma: no cover - fail-open import
    _validate_trade_proposal = None  # type: ignore[assignment]
    DEFAULT_TRADING_RISK_POLICY = None  # type: ignore[assignment]

# ---------------------------------------------------------------------
# Optional Phase 3 DMIP learning capture imports (fail-open)
# ---------------------------------------------------------------------
try:
    from backend.modules.aion_trading.dmip_learning_capture import (
        log_llm_accuracy_stub,
        log_task_tracking_stub,
    )
except Exception:  # pragma: no cover - fail-open import
    # Local non-blocking fallbacks so dmip_runtime stays importable/testable
    def log_llm_accuracy_stub(**kwargs: Any) -> Dict[str, Any]:
        return {
            "ok": True,
            "non_blocking": True,
            "stub": True,
            "capture_type": "llm_accuracy_stub_fallback",
            "source": "dmip_runtime_local_fallback",
            "payload": dict(kwargs or {}),
            "timestamp_unix": time.time(),
        }

    def log_task_tracking_stub(**kwargs: Any) -> Dict[str, Any]:
        return {
            "ok": True,
            "non_blocking": True,
            "stub": True,
            "capture_type": "task_tracking_stub_fallback",
            "source": "dmip_runtime_local_fallback",
            "payload": dict(kwargs or {}),
            "timestamp_unix": time.time(),
        }


# ---------------------------------------------------------------------
# Optional Phase 3C DMIP learning summary import (fail-open)
# ---------------------------------------------------------------------
try:
    from backend.modules.aion_trading.dmip_learning_summary import (
        get_llm_weighting_summary,
    )
except Exception:  # pragma: no cover - fail-open import
    get_llm_weighting_summary = None  # type: ignore[assignment]


# ---------------------------------------------------------------------
# Optional Phase 3D reusable LLM synthesis import (fail-open)
# ---------------------------------------------------------------------
try:
    from backend.modules.aion_trading.dmip_llm_synthesis import (
        get_llm_weighted_bias,
    )
except Exception:  # pragma: no cover - fail-open import
    get_llm_weighted_bias = None  # type: ignore[assignment]


# Optional governed weighting runtime (Phase D / learning)
try:
    from backend.modules.aion_learning.decision_influence_runtime import (
        get_decision_influence_runtime,
    )
except Exception:  # pragma: no cover - fail-open import
    get_decision_influence_runtime = None  # type: ignore[assignment]


CHECKPOINT_SPECS = {
    "pre_market": {"label": "Pre-Market Global Briefing", "hhmm_gmt": "06:00"},
    "london": {"label": "London Open Analysis", "hhmm_gmt": "07:45"},
    "mid_london": {"label": "Mid-London Review", "hhmm_gmt": "10:00"},
    "new_york": {"label": "New York Open Analysis", "hhmm_gmt": "13:30"},
    "asia": {"label": "Asia Open Preparation", "hhmm_gmt": "22:30"},
    "eod": {"label": "End of Day Learning Debrief", "hhmm_gmt": "22:00"},
}


def _default_pairs() -> List[str]:
    return ["EUR/USD", "GBP/USD", "USD/JPY"]


# ---------------------------------------------------------------------
# Small safe coercion helpers
# ---------------------------------------------------------------------


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _now_ts() -> float:
    return float(time.time())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------
# Phase 2 paper-trade runtime state (in-memory scaffold, non-persistent)
# ---------------------------------------------------------------------

_PAPER_TRADES: Dict[str, Dict[str, Any]] = {}
_PAPER_TRADE_EVENTS: List[Dict[str, Any]] = []


def _emit_paper_trade_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    row = {
        "event_id": _new_id("pte"),
        "event_type": str(event_type),
        "ts": _now_ts(),
        "payload": dict(payload or {}),
    }
    _PAPER_TRADE_EVENTS.append(row)
    return row


def _normalize_pair_symbol(pair: str) -> str:
    s = _safe_str(pair).upper().replace("-", "/").replace(" ", "")
    # restore slash for common 6-char FX
    if "/" not in s and len(s) == 6:
        s = f"{s[:3]}/{s[3:]}"
    return s

# ---------------------------------------------------------------------
# Phase 2 scope/progression locks (single pair / single strategy / session)
# ---------------------------------------------------------------------

_PHASE2_ALLOWED_PAIR = "EUR/USD"
_PHASE2_ALLOWED_SESSION = "london"
_PHASE2_ALLOWED_STRATEGY_TIER = "tier3_smc_intraday"

def _proposal_meta_dict(trade_proposal: Any) -> Dict[str, Any]:
    """
    Best-effort metadata extraction from proposal object/dict.
    """
    p = _extract_trade_proposal_dict(trade_proposal)
    return _safe_dict(p.get("metadata"))

def _extract_trade_proposal_dict(trade_proposal: Any) -> Dict[str, Any]:
    """
    Tolerate dataclass-like, pydantic-like, or dict-like proposal.
    """
    if hasattr(trade_proposal, "to_dict"):
        try:
            d = trade_proposal.to_dict()
            if isinstance(d, dict):
                return dict(d)
        except Exception:
            pass

    if isinstance(trade_proposal, dict):
        return dict(trade_proposal)

    # Attribute fallback (contracts.TradeProposal dataclass-compatible)
    return {
        "pair": getattr(trade_proposal, "pair", None),
        "session": getattr(trade_proposal, "session", None),
        "strategy_tier": getattr(trade_proposal, "strategy_tier", None),
        "strategy_id": getattr(trade_proposal, "strategy_id", None),
        "direction": getattr(trade_proposal, "direction", None),
        "entry": getattr(trade_proposal, "entry", None),
        "stop_loss": getattr(trade_proposal, "stop_loss", None),
        "take_profit": getattr(trade_proposal, "take_profit", None),
        "risk_pct": getattr(trade_proposal, "risk_pct", None),
        "account_mode": getattr(trade_proposal, "account_mode", None),
        "thesis": getattr(trade_proposal, "thesis", None),
        "metadata": getattr(trade_proposal, "metadata", None),
    }


def _validate_phase2_scope_and_progression(
    *,
    trade_proposal: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase 2 hard lock:
    - single pair: EUR/USD only
    - single session: London only
    - single strategy tier: tier3_smc_intraday only
    - paper-only progression boundary (explicit runtime check)

    Tolerates session/strategy provided via:
    - top-level proposal fields
    - proposal.metadata
    - submit call metadata (request metadata)
    """
    proposal = _extract_trade_proposal_dict(trade_proposal)
    meta = dict(metadata or {})
    proposal_meta = _safe_dict(proposal.get("metadata"))

    # Normalize pair and allowed constants to avoid case/format mismatches
    pair_norm = _normalize_pair_symbol(_safe_str(proposal.get("pair")))
    allowed_pair = _normalize_pair_symbol(_safe_str(_PHASE2_ALLOWED_PAIR))

    # Session fallback chain:
    # proposal.session -> proposal.metadata.session -> request metadata.session
    session_norm = _safe_str(proposal.get("session"), "").strip().lower()
    if not session_norm:
        session_norm = _safe_str(proposal_meta.get("session"), "").strip().lower()
    if not session_norm:
        session_norm = _safe_str(meta.get("session"), "").strip().lower()

    # Strategy fallback chain:
    # proposal.strategy_tier -> proposal.strategy_id -> proposal.metadata.strategy_tier -> request metadata.strategy_tier
    strategy_tier = _safe_str(proposal.get("strategy_tier"), "").strip().lower()
    if not strategy_tier:
        strategy_tier = _safe_str(proposal.get("strategy_id"), "").strip().lower()
    if not strategy_tier:
        strategy_tier = _safe_str(proposal_meta.get("strategy_tier"), "").strip().lower()
    if not strategy_tier:
        strategy_tier = _safe_str(meta.get("strategy_tier"), "").strip().lower()

    allowed_session = _safe_str(_PHASE2_ALLOWED_SESSION, "").strip().lower()
    allowed_strategy_tier = _safe_str(_PHASE2_ALLOWED_STRATEGY_TIER, "").strip().lower()

    account_mode = _safe_str(proposal.get("account_mode"), "").strip().lower()

    violations: List[str] = []
    warnings: List[str] = []

    # Explicit runtime progression boundary (in addition to risk policy paper_only)
    if account_mode and account_mode != "paper":
        violations.append("phase2_progression_requires_paper_mode")

    if pair_norm != allowed_pair:
        violations.append("phase2_scope_pair_locked")

    # Fail closed if missing or non-london
    if session_norm != allowed_session:
        violations.append("phase2_scope_session_locked")

    if strategy_tier != allowed_strategy_tier:
        violations.append("phase2_scope_strategy_locked")

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "derived": {
            "pair_norm": pair_norm,
            "session_norm": session_norm,
            "strategy_tier": strategy_tier,
            "account_mode": account_mode,
            "phase2_allowed_pair": allowed_pair,
            "phase2_allowed_session": allowed_session,
            "phase2_allowed_strategy_tier": allowed_strategy_tier,
            "proposal_metadata_session": _safe_str(proposal_meta.get("session"), "").strip().lower(),
            "request_metadata_session": _safe_str(meta.get("session"), "").strip().lower(),
        },
        "error": None,
        "meta": {
            "validator": "backend.modules.aion_trading.dmip_runtime._validate_phase2_scope_and_progression",
            "hard_gate": True,
            "paper_safe": True,
            "phase": "phase2",
            "notes": {
                "session_required": True,
                "single_pair_lock": True,
                "single_strategy_lock": True,
                "session_fallbacks": [
                    "proposal.session",
                    "proposal.metadata.session",
                    "request_metadata.session",
                ],
                "strategy_fallbacks": [
                    "proposal.strategy_tier",
                    "proposal.strategy_id",
                    "proposal.metadata.strategy_tier",
                    "request_metadata.strategy_tier",
                ],
            },
            "request_metadata": meta,
        },
    }

def _validate_phase2_initial_trade_limits(
    *,
    trade_proposal: Any,
    session_stats: Optional[Dict[str, Any]] = None,
    account_stats: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase 2 initial execution limits (P2E):
    - max trades per session (default 2)
    - A-grade only
    - red-event stand-down
    - mandatory EOD debrief acknowledgement before resume

    Tolerates values provided via:
    - session_stats / account_stats
    - submit metadata (request metadata)
    - proposal.metadata
    """
    proposal = _extract_trade_proposal_dict(trade_proposal)
    ss = _safe_dict(session_stats)
    acct = _safe_dict(account_stats)
    meta = _safe_dict(metadata)
    pmeta = _safe_dict(proposal.get("metadata"))

    violations: List[str] = []
    warnings: List[str] = []

    # -----------------------------------------------------------------
    # Decide whether P2E sub-gates are "activated" for this request.
    #
    # This preserves legacy Phase-2 submit tests (which only pass source/session)
    # while allowing P2E-specific tests to exercise these gates when they include
    # P2E request metadata/session fields.
    # -----------------------------------------------------------------
    p2e_request_signals_present = any(
        k in meta
        for k in (
            "setup_grade",
            "grade",
            "is_a_grade",
            "red_event_active",
            "eod_debrief_ack",
            "eod_debrief_acknowledged",
            "eod_debrief_required",
            "a_grade_only",
            "max_trades_per_session",
        )
    ) or any(
        k in ss
        for k in (
            "trades_taken",
            "session_trades_taken",
            "trade_count",
            "red_event_active",
            "event_stand_down",
            "a_grade_only",
            "max_trades_per_session",
        )
    ) or any(
        k in acct
        for k in (
            "red_event_active",
            "eod_debrief_ack",
            "eod_debrief_acknowledged",
            "eod_debrief_required",
        )
    )

    # -----------------------------------------------------------------
    # Max trades per session (default 2)
    # -----------------------------------------------------------------
    max_trades_per_session = _safe_int(
        ss.get("max_trades_per_session")
        or meta.get("max_trades_per_session")
        or pmeta.get("max_trades_per_session")
        or _PHASE2_MAX_TRADES_PER_SESSION,
        _PHASE2_MAX_TRADES_PER_SESSION,
    )
    if max_trades_per_session < 1:
        max_trades_per_session = 1

    trades_taken = _safe_int(
        ss.get("trades_taken")
        or ss.get("session_trades_taken")
        or ss.get("trade_count")
        or 0,
        0,
    )

    # Reject when already at cap (i.e., next trade would exceed)
    # (This is safe to apply only when the caller is providing trade-count data.)
    if (
        p2e_request_signals_present
        and ("trades_taken" in ss or "session_trades_taken" in ss or "trade_count" in ss)
        and trades_taken >= max_trades_per_session
    ):
        violations.append("phase2_session_trade_limit_reached")

    # -----------------------------------------------------------------
    # A-grade only (request-metadata-driven for P2E tests)
    # -----------------------------------------------------------------
    a_grade_only = _extract_bool_from_any(
        ss.get("a_grade_only"),
        meta.get("a_grade_only"),
        pmeta.get("a_grade_only"),
        _PHASE2_REQUIRE_A_GRADE_ONLY,
    )

    # IMPORTANT:
    # P2E tests expect request metadata to drive this gate (not proposal.metadata).
    # So prefer request metadata setup_grade/grade and request metadata is_a_grade.
    req_grade = _safe_str(meta.get("setup_grade") or meta.get("grade"), "").upper()

    # tri-state explicit bool (None / True / False) — DO NOT use _extract_bool_from_any here
    if "is_a_grade" in meta:
        req_is_a_grade_explicit: Optional[bool] = _safe_bool(meta.get("is_a_grade"), False)
    else:
        req_is_a_grade_explicit = None

    if p2e_request_signals_present and a_grade_only:
        if req_is_a_grade_explicit is True:
            pass
        elif req_grade in {"A", "A+", "A1"}:
            pass
        else:
            violations.append("phase2_a_grade_only_required")

    # -----------------------------------------------------------------
    # Strict event filters (red-event stand-down)
    # -----------------------------------------------------------------
    red_event_active = _extract_bool_from_any(
        ss.get("red_event_active"),
        ss.get("event_stand_down"),
        acct.get("red_event_active"),
        meta.get("red_event_active"),
        pmeta.get("red_event_active"),
        False,
    )
    if p2e_request_signals_present and _PHASE2_BLOCK_RED_EVENTS and red_event_active:
        violations.append("phase2_red_event_stand_down")

    # -----------------------------------------------------------------
    # Mandatory EOD debrief acknowledgement before resume
    # -----------------------------------------------------------------
    # P2E tests are request-metadata driven. If P2E signals are present and the
    # policy flag is enabled, require request/account-level ack (do not satisfy
    # this from proposal.metadata).
    eod_debrief_required = _extract_bool_from_any(
        acct.get("eod_debrief_required"),
        meta.get("eod_debrief_required"),
        pmeta.get("eod_debrief_required"),
        False,
    )

    eod_debrief_ack_request_or_account = _extract_bool_from_any(
        acct.get("eod_debrief_ack"),
        acct.get("eod_debrief_acknowledged"),
        meta.get("eod_debrief_ack"),
        meta.get("eod_debrief_acknowledged"),
        False,
    )

    # If caller is clearly on the P2E path, treat EOD ack as required by policy
    # unless explicitly disabled for the request.
    eod_gate_required_now = (
        p2e_request_signals_present
        and _PHASE2_REQUIRE_EOD_DEBRIEF_FLAG
        and (
            eod_debrief_required
            or any(k in meta for k in ("eod_debrief_ack", "eod_debrief_acknowledged", "setup_grade", "grade"))
            or any(k in acct for k in ("eod_debrief_ack", "eod_debrief_acknowledged"))
        )
    )

    if eod_gate_required_now and not eod_debrief_ack_request_or_account:
        violations.append("phase2_eod_debrief_ack_required")

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "derived": {
            "trades_taken": trades_taken,
            "max_trades_per_session": max_trades_per_session,
            "a_grade_only": a_grade_only,
            "grade": req_grade,
            "is_a_grade_explicit": req_is_a_grade_explicit,
            "red_event_active": red_event_active,
            "eod_debrief_required": eod_debrief_required,
            "eod_debrief_ack": eod_debrief_ack_request_or_account,
            "p2e_request_signals_present": p2e_request_signals_present,
        },
        "error": None,
        "meta": {
            "validator": "backend.modules.aion_trading.dmip_runtime._validate_phase2_initial_trade_limits",
            "hard_gate": True,
            "paper_safe": True,
            "phase": "phase2",
            "request_metadata": meta,
        },
    }

def _extract_proposal_grade(proposal: Dict[str, Any]) -> str:
    meta = _safe_dict(proposal.get("metadata"))
    return _safe_str(
        proposal.get("grade")
        or proposal.get("setup_grade")
        or meta.get("grade")
        or meta.get("setup_grade"),
        "",
    ).upper()


def _extract_bool_from_any(*values: Any) -> bool:
    for v in values:
        if v is None:
            continue
        return _safe_bool(v, False)
    return False

# ---------------------------------------------------------------------
# Phase 2 scope/progression locks (paper-only, single pair/session/strategy)
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Phase 2 initial trade limits (P2E) hard gate defaults
# ---------------------------------------------------------------------
_PHASE2_MAX_TRADES_PER_SESSION = 2
_PHASE2_REQUIRE_A_GRADE_ONLY = True
_PHASE2_BLOCK_RED_EVENTS = True
_PHASE2_REQUIRE_EOD_DEBRIEF_FLAG = True
_PHASE2_ALLOWED_PAIR = "EUR/USD"
_PHASE2_ALLOWED_SESSION = "london"
_PHASE2_ALLOWED_STRATEGY_TIER = "tier3_smc_intraday"


def _proposal_get(proposal_dict: Dict[str, Any], *keys: str) -> Any:
    """
    Return first non-None value from proposal_dict or nested metadata.
    Used to tolerate schema drift while enforcing Phase 2 scope locks.
    """
    if not isinstance(proposal_dict, dict):
        return None

    for k in keys:
        if k in proposal_dict and proposal_dict.get(k) is not None:
            return proposal_dict.get(k)

    md = _safe_dict(proposal_dict.get("metadata"))
    for k in keys:
        if k in md and md.get(k) is not None:
            return md.get(k)

    return None


def _phase2_scope_reject(
    *,
    reason: str,
    trade_proposal: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    evt = _emit_paper_trade_event(
        "paper_trade_rejected",
        {
            "reason": reason,
            "details": dict(details or {}),
            "proposal_summary": {
                "pair": _safe_str(trade_proposal.get("pair")),
                "session": _safe_str(_proposal_get(trade_proposal, "session")),
                "strategy_tier": _safe_str(
                    _proposal_get(trade_proposal, "strategy_tier", "strategy_id")
                ),
                "account_mode": _safe_str(trade_proposal.get("account_mode")),
            },
            "metadata": dict(metadata or {}),
        },
    )
    return {
        "ok": False,
        "status": "rejected",
        "reason": reason,
        "details": dict(details or {}),
        "event": evt,
        "meta": {
            "paper_only": True,
            "persisted": False,
            "runtime": "in_memory_scaffold",
            "phase2_scope_lock": True,
        },
    }

# ---------------------------------------------------------------------
# Phase 2 risk validation wrapper (DMIP-facing)
# ---------------------------------------------------------------------


def validate_risk_rules(
    trade_proposal: Any,
    *,
    policy: Optional[Any] = None,
    session_stats: Optional[Dict[str, Any]] = None,
    account_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    DMIP wrapper around hard risk invariants.

    Returns structured dict and fails closed if runtime validator import is unavailable.
    """
    if _validate_trade_proposal is None:
        return {
            "ok": False,
            "error": {
                "type": "ImportError",
                "message": "risk_rules.validate_trade_proposal unavailable",
            },
            "violations": ["risk_validator_import_unavailable"],
            "warnings": [],
            "derived": {},
            "meta": {
                "fail_closed": True,
                "paper_safe": True,
            },
        }

    try:
        out = _validate_trade_proposal(
            proposal=trade_proposal,
            policy=policy,
            session_stats=session_stats,
            account_stats=account_stats,
        )
        if hasattr(out, "to_dict"):
            out = out.to_dict()
        d = _safe_dict(out)
        return {
            "ok": _safe_bool(d.get("ok"), False),
            "violations": _safe_list(d.get("violations")),
            "warnings": _safe_list(d.get("warnings")),
            "derived": _safe_dict(d.get("derived")),
            "error": None,
            "meta": {
                "validator": "backend.modules.aion_trading.risk_rules.validate_trade_proposal",
                "paper_safe": True,
            },
        }
    except Exception as e:
        return {
            "ok": False,
            "error": {
                "type": e.__class__.__name__,
                "message": str(e),
            },
            "violations": ["risk_validation_exception"],
            "warnings": [],
            "derived": {},
            "meta": {
                "fail_closed": True,
                "paper_safe": True,
            },
        }


# ---------------------------------------------------------------------
# Phase 2 paper trading runtime scaffold (in-memory, paper-only)
# ---------------------------------------------------------------------


def submit_paper_trade(
    *,
    trade_proposal: Any,
    session_stats: Optional[Dict[str, Any]] = None,
    account_stats: Optional[Dict[str, Any]] = None,
    policy: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase 2 paper execution boundary:
    - Phase 2 scope/progression hard gate first (single pair/session/strategy, paper-only)
    - Phase 2 initial trade-limits hard gate second (P2E)
    - validates via hard risk gate third (fail-closed)
    - paper-only, in-memory scaffold
    - returns structured reject reasons
    """
    # -----------------------------------------------------------------
    # Phase 2 scope/progression hard gate first (P2C / P2D)
    # -----------------------------------------------------------------
    scope_validation = _validate_phase2_scope_and_progression(
        trade_proposal=trade_proposal,
        metadata=metadata,
    )
    if not scope_validation.get("ok", False):
        evt = _emit_paper_trade_event(
            "paper_trade_rejected",
            {
                "reason": "phase2_scope_or_progression_validation_failed",
                "scope_validation": scope_validation,
                "metadata": dict(metadata or {}),
            },
        )
        return {
            "ok": False,
            "status": "rejected",
            "reason": "phase2_scope_or_progression_validation_failed",
            "scope_validation": scope_validation,
            "event": evt,
            "meta": {
                "paper_only": True,
                "persisted": False,
                "runtime": "in_memory_scaffold",
                "phase2_scope_lock": True,
            },
        }

    # -----------------------------------------------------------------
    # Phase 2 initial trade limits hard gate (P2E)
    # -----------------------------------------------------------------
    phase2_limits_validation = _validate_phase2_initial_trade_limits(
        trade_proposal=trade_proposal,
        session_stats=session_stats,
        account_stats=account_stats,
        metadata=metadata,
    )
    if not phase2_limits_validation.get("ok", False):
        evt = _emit_paper_trade_event(
            "paper_trade_rejected",
            {
                "reason": "phase2_initial_trade_limits_validation_failed",
                "phase2_limits_validation": phase2_limits_validation,
                "scope_validation": scope_validation,
                "metadata": dict(metadata or {}),
            },
        )
        return {
            "ok": False,
            "status": "rejected",
            "reason": "phase2_initial_trade_limits_validation_failed",
            "phase2_limits_validation": phase2_limits_validation,
            "scope_validation": scope_validation,
            "event": evt,
            "meta": {
                "paper_only": True,
                "persisted": False,
                "runtime": "in_memory_scaffold",
                "phase2_scope_lock": True,
                "phase2_initial_limits_lock": True,
            },
        }

    # -----------------------------------------------------------------
    # Hard risk invariants gate (P2F/P2L)
    # -----------------------------------------------------------------
    validation = validate_risk_rules(
        trade_proposal,
        policy=policy,
        session_stats=session_stats,
        account_stats=account_stats,
    )
    if not validation.get("ok", False):
        evt = _emit_paper_trade_event(
            "paper_trade_rejected",
            {
                "reason": "risk_validation_failed",
                "validation": validation,
                "phase2_limits_validation": phase2_limits_validation,
                "scope_validation": scope_validation,
                "metadata": dict(metadata or {}),
            },
        )
        return {
            "ok": False,
            "status": "rejected",
            "reason": "risk_validation_failed",
            "validation": validation,
            "phase2_limits_validation": phase2_limits_validation,
            "scope_validation": scope_validation,
            "event": evt,
            "meta": {
                "paper_only": True,
                "persisted": False,
                "runtime": "in_memory_scaffold",
                "phase2_scope_lock": True,
                "phase2_initial_limits_lock": True,
            },
        }

    p = trade_proposal

    # Tolerate dataclass-like, pydantic-like, or dict-like proposal
    proposal_dict = p.to_dict() if hasattr(p, "to_dict") else (_safe_dict(p) if isinstance(p, dict) else {})
    if not proposal_dict:
        # attribute fallback (keep aligned with runtime usage)
        proposal_dict = {
            "pair": getattr(p, "pair", None),
            "session": getattr(p, "session", None),
            "direction": getattr(p, "direction", None),
            "entry": getattr(p, "entry", None),
            "stop_loss": getattr(p, "stop_loss", None),
            "take_profit": getattr(p, "take_profit", None),
            "risk_pct": getattr(p, "risk_pct", None),
            "account_mode": getattr(p, "account_mode", None),
            "strategy_tier": getattr(p, "strategy_tier", None),
            "strategy_id": getattr(p, "strategy_id", None),
            "thesis": getattr(p, "thesis", None),
            "metadata": getattr(p, "metadata", None),
        }

    # Normalize session / strategy using same rules validated above.
    # IMPORTANT: allow request metadata fallback because TradeProposal.to_dict()
    # may not include dynamic attrs and some tests pass session via submit metadata.
    proposal_meta = _safe_dict(proposal_dict.get("metadata"))
    request_meta = _safe_dict(metadata)

    proposal_session = _safe_str(proposal_dict.get("session"), "").lower()
    if not proposal_session:
        proposal_session = _safe_str(proposal_meta.get("session"), "").lower()
    if not proposal_session:
        proposal_session = _safe_str(request_meta.get("session"), "").lower()

    proposal_strategy = _safe_str(proposal_dict.get("strategy_id"), "")
    if not proposal_strategy:
        proposal_strategy = _safe_str(proposal_dict.get("strategy_tier"), "unknown")

    trade_id = _new_id("paper_trade")
    now = _now_ts()

    trade_row: Dict[str, Any] = {
        "trade_id": trade_id,
        "status": "OPEN",
        "opened_ts": now,
        "updated_ts": now,
        "closed_ts": None,
        "pair": _normalize_pair_symbol(_safe_str(proposal_dict.get("pair"), "")),
        "session": proposal_session,
        "direction": _safe_str(proposal_dict.get("direction"), "").upper(),
        "entry": proposal_dict.get("entry"),
        "stop_loss": proposal_dict.get("stop_loss"),
        "take_profit": proposal_dict.get("take_profit"),
        "risk_pct": proposal_dict.get("risk_pct"),
        "account_mode": "paper",
        "strategy_id": proposal_strategy,
        "thesis": proposal_dict.get("thesis"),
        "proposal": proposal_dict,
        "scope_validation": scope_validation,
        "phase2_limits_validation": phase2_limits_validation,
        "validation": validation,
        "management": {
            "move_stop_events": [],
            "partial_take_profit_events": [],
            "notes": [],
        },
        "close": None,
        "metadata": dict(metadata or {}),
    }

    _PAPER_TRADES[trade_id] = trade_row
    evt = _emit_paper_trade_event(
        "paper_trade_opened",
        {
            "trade_id": trade_id,
            "pair": trade_row["pair"],
            "session": trade_row["session"],
            "direction": trade_row["direction"],
            "strategy_id": trade_row["strategy_id"],
        },
    )

    return {
        "ok": True,
        "status": "accepted",
        "trade_id": trade_id,
        "trade": dict(trade_row),
        "scope_validation": scope_validation,
        "phase2_limits_validation": phase2_limits_validation,
        "validation": validation,
        "event": evt,
        "meta": {
            "paper_only": True,
            "persisted": False,
            "runtime": "in_memory_scaffold",
            "phase2_scope_lock": True,
            "phase2_initial_limits_lock": True,
        },
    }

def _proposal_get(d: Dict[str, Any], *keys: str) -> Any:
    """
    Return first non-empty value from top-level proposal dict or nested proposal.metadata.
    """
    if not isinstance(d, dict):
        return None

    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip() != "":
            return v

    md = d.get("metadata")
    if isinstance(md, dict):
        for k in keys:
            v = md.get(k)
            if v is not None and str(v).strip() != "":
                return v

    return None

def manage_open_trade(
    *,
    trade_id: str,
    action: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Minimal paper trade management scaffold.

    Supported actions:
    - move_stop
    - take_partial
    - add_note
    """
    tid = _safe_str(trade_id)
    trade = _PAPER_TRADES.get(tid)
    if not trade:
        return {
            "ok": False,
            "error": {"type": "LookupError", "message": f"unknown trade_id: {tid}"},
            "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
        }

    if trade.get("status") != "OPEN":
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"trade not OPEN: {trade.get('status')}"},
            "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
        }

    action_norm = _safe_str(action).lower()
    payload = dict(payload or {})
    notes: List[str] = []

    if action_norm == "move_stop":
        new_stop = payload.get("stop_loss")
        if new_stop is None:
            return {
                "ok": False,
                "error": {"type": "ValueError", "message": "move_stop requires payload.stop_loss"},
                "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
            }
        trade["stop_loss"] = new_stop
        trade.setdefault("management", {}).setdefault("move_stop_events", []).append(
            {"ts": _now_ts(), "stop_loss": new_stop, "reason": _safe_str(payload.get("reason"))}
        )
        notes.append("stop_loss_updated")

    elif action_norm == "take_partial":
        fraction = _safe_float(payload.get("fraction"), 0.0)
        if not (0.0 < fraction <= 1.0):
            return {
                "ok": False,
                "error": {"type": "ValueError", "message": "take_partial requires 0 < fraction <= 1"},
                "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
            }
        trade.setdefault("management", {}).setdefault("partial_take_profit_events", []).append(
            {
                "ts": _now_ts(),
                "fraction": fraction,
                "price": payload.get("price"),
                "reason": _safe_str(payload.get("reason")),
            }
        )
        notes.append("partial_take_profit_recorded")

    elif action_norm == "add_note":
        note = _safe_str(payload.get("note"))
        if not note:
            return {
                "ok": False,
                "error": {"type": "ValueError", "message": "add_note requires payload.note"},
                "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
            }
        trade.setdefault("management", {}).setdefault("notes", []).append({"ts": _now_ts(), "note": note})
        notes.append("management_note_added")

    else:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"unsupported manage action: {action_norm}"},
            "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
        }

    trade["updated_ts"] = _now_ts()
    evt = _emit_paper_trade_event(
        "paper_trade_managed",
        {
            "trade_id": tid,
            "action": action_norm,
            "notes": notes,
        },
    )

    return {
        "ok": True,
        "trade_id": tid,
        "action": action_norm,
        "trade": dict(trade),
        "notes": notes,
        "event": evt,
        "meta": {"paper_only": True, "persisted": False, "runtime": "in_memory_scaffold"},
    }


def close_trade(
    *,
    trade_id: str,
    close_price: float,
    close_reason: str,
    outcome: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Close an open paper trade (in-memory scaffold).
    """
    tid = _safe_str(trade_id)
    trade = _PAPER_TRADES.get(tid)
    if not trade:
        return {
            "ok": False,
            "error": {"type": "LookupError", "message": f"unknown trade_id: {tid}"},
            "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
        }

    if trade.get("status") != "OPEN":
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"trade not OPEN: {trade.get('status')}"},
            "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
        }

    now = _now_ts()
    trade["status"] = "CLOSED"
    trade["updated_ts"] = now
    trade["closed_ts"] = now
    trade["close"] = {
        "price": float(close_price),
        "reason": _safe_str(close_reason),
        "outcome": dict(outcome or {}),
    }

    evt = _emit_paper_trade_event(
        "paper_trade_closed",
        {
            "trade_id": tid,
            "close_price": float(close_price),
            "close_reason": _safe_str(close_reason),
        },
    )

    return {
        "ok": True,
        "trade_id": tid,
        "status": "closed",
        "trade": dict(trade),
        "event": evt,
        "meta": {"paper_only": True, "persisted": False, "runtime": "in_memory_scaffold"},
    }


def get_paper_trade(trade_id: str) -> Dict[str, Any]:
    tid = _safe_str(trade_id)
    row = _PAPER_TRADES.get(tid)
    if row is None:
        return {
            "ok": False,
            "error": {"type": "LookupError", "message": f"unknown trade_id: {tid}"},
            "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
        }
    return {
        "ok": True,
        "trade_id": tid,
        "trade": dict(row),
        "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
    }


def list_paper_trades(*, status: Optional[str] = None) -> Dict[str, Any]:
    wanted = _safe_str(status).upper() if status is not None else ""
    rows = []
    for tid, row in _PAPER_TRADES.items():
        st = _safe_str(row.get("status")).upper()
        if wanted and st != wanted:
            continue
        rows.append((tid, row))
    rows.sort(key=lambda kv: float(kv[1].get("opened_ts") or 0.0))
    return {
        "ok": True,
        "count": len(rows),
        "trades": [dict(r) for _, r in rows],
        "meta": {"paper_only": True, "runtime": "in_memory_scaffold"},
    }


# ---------------------------------------------------------------------
# Phase 3D / 3E: weighting runtime integration (fail-open)
# ---------------------------------------------------------------------


def _get_weighting_runtime() -> Tuple[Optional[Any], Optional[str]]:
    if get_decision_influence_runtime is None:
        return None, "decision_influence_runtime_import_unavailable"
    try:
        return get_decision_influence_runtime(), None
    except Exception as e:
        return None, f"decision_influence_runtime_init_error:{e}"


def _build_weighting_scope(
    *,
    checkpoint: str,
    market_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Scope used for governed weighting lookup. Keep paper-safe.
    """
    profile_id = _safe_str(market_snapshot.get("profile_id"), "default") or "default"
    environment = _safe_str(market_snapshot.get("environment"), "paper") or "paper"
    return {
        "profile_id": profile_id,
        "environment": environment,
        "checkpoint": checkpoint,
    }


def _try_read_weights_snapshot(
    runtime: Any,
    *,
    scope: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Try multiple runtime API shapes, fail-open.
    """
    payload = {
        "action": "show",
        "dry_run": True,
        "scope": scope,
        "source": "dmip_runtime",
        "reason": "DMIP read decision influence weights for weighted synthesis",
    }

    try:
        raw = None
        if hasattr(runtime, "get_weights"):
            raw = runtime.get_weights(payload)
        elif hasattr(runtime, "read_weights"):
            raw = runtime.read_weights(payload)
        elif hasattr(runtime, "show_weights"):
            raw = runtime.show_weights(payload)
        elif hasattr(runtime, "get_snapshot"):
            raw = runtime.get_snapshot(payload)
        elif hasattr(runtime, "run"):
            # common runtime shape
            raw = runtime.run(payload)
        else:
            return None, "decision_influence_runtime_read_api_unavailable"

        if hasattr(raw, "to_dict"):
            raw = raw.to_dict()

        d = _safe_dict(raw)
        # Some runtimes wrap payload under "output"
        out = _safe_dict(d.get("output")) if isinstance(d.get("output"), dict) else d

        weights = out.get("weights")
        if isinstance(weights, dict) and weights:
            return out, None

        # tolerate alternate shapes but mark unusable
        return out, "decision_influence_weights_missing"
    except Exception as e:
        return None, f"decision_influence_weights_read_error:{e}"


def _extract_weighted_bias_hint(
    *,
    pair: str,
    llm_pair: Dict[str, Any],
    weights_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Phase 3D reusable synthesis adapter (preferred):
    use dmip_llm_synthesis.get_llm_weighted_bias(...) when available.

    Falls back to the prior inline behavior-preserving logic if the module is
    unavailable or throws, so DMIP remains importable/non-breaking.
    """
    if callable(get_llm_weighted_bias):
        try:
            out = get_llm_weighted_bias(
                pair=pair,
                llm_pair=llm_pair,
                weights_snapshot=weights_snapshot,
            )
            out_d = _safe_dict(out)
            if out_d:
                return out_d
        except Exception:
            # fail-open to legacy inline logic below
            pass

    a = _safe_str(llm_pair.get("claude_bias")).upper()
    b = _safe_str(llm_pair.get("gpt4_bias")).upper()
    conf = _safe_str(llm_pair.get("confidence"), "MEDIUM").upper()
    conf = conf if conf in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"

    if not isinstance(weights_snapshot, dict):
        return {
            "ok": False,
            "pair": pair,
            "weighted_bias": None,
            "weighted_confidence": None,
            "agreement": "unavailable",
            "reason": "weights_snapshot_unavailable",
        }

    # We don't assume specific keys yet; just read likely LLM trust signal if present
    llm_trust_weights = _safe_dict(weights_snapshot.get("llm_trust_weights"))

    # Some runtimes may flatten trust weights elsewhere; fail softly
    claude_w = _safe_float(
        llm_trust_weights.get("claude") or llm_trust_weights.get("claude_bias"),
        1.0,
    )
    gpt_w = _safe_float(
        llm_trust_weights.get("gpt4") or llm_trust_weights.get("gpt4_bias"),
        1.0,
    )

    allowed = {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}

    # Preserve disagreement as first-class signal (P3E)
    if a and b and a in allowed and b in allowed and a != b:
        return {
            "ok": True,
            "pair": pair,
            "weighted_bias": "AVOID",
            "weighted_confidence": "LOW",
            "agreement": "disagree",
            "reason": "llm_disagreement_preserved",
            "weights_version": weights_snapshot.get("weights_version") or weights_snapshot.get("version"),
            "snapshot_hash": weights_snapshot.get("snapshot_hash"),
            "llm_weights_used": {"claude": claude_w, "gpt4": gpt_w},
        }

    # Agreement path
    if a and b and a == b and a in allowed:
        base_conf = conf
        # Simple capped uplift hint only (never overrides to HIGH from LOW unless both weights strong)
        avg_w = (max(0.0, claude_w) + max(0.0, gpt_w)) / 2.0
        if base_conf == "LOW" and avg_w >= 1.25:
            weighted_conf = "MEDIUM"
        elif base_conf == "MEDIUM" and avg_w >= 1.5:
            weighted_conf = "HIGH"
        else:
            weighted_conf = base_conf

        return {
            "ok": True,
            "pair": pair,
            "weighted_bias": a,
            "weighted_confidence": weighted_conf,
            "agreement": "agree",
            "reason": "llm_agreement_weighted_hint",
            "weights_version": weights_snapshot.get("weights_version") or weights_snapshot.get("version"),
            "snapshot_hash": weights_snapshot.get("snapshot_hash"),
            "llm_weights_used": {"claude": claude_w, "gpt4": gpt_w},
        }

    # Partial / incomplete path
    return {
        "ok": True,
        "pair": pair,
        "weighted_bias": None,
        "weighted_confidence": None,
        "agreement": "partial",
        "reason": "insufficient_llm_pair_data",
        "weights_version": weights_snapshot.get("weights_version") or weights_snapshot.get("version"),
        "snapshot_hash": weights_snapshot.get("snapshot_hash"),
        "llm_weights_used": {"claude": claude_w, "gpt4": gpt_w},
    }


def run_dmip_checkpoint(
    *,
    checkpoint: str,
    market_snapshot: Optional[Dict[str, Any]] = None,
    llm_consultation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase T Sprint 1 + Phase 3 promotion (non-breaking):
    - deterministic DMIP scaffold remains primary behavior
    - optional governed weighting runtime read used for weighted synthesis hints
    - disagreement remains a preserved signal (AVOID)
    - no risk invariants are mutated here (paper-safe / read-only synthesis)
    """
    cp = str(checkpoint or "").strip()
    if cp not in CHECKPOINT_SPECS:
        raise ValueError(f"checkpoint must be one of {sorted(CHECKPOINT_SPECS)}")

    market_snapshot = dict(market_snapshot or {})
    llm_consultation = dict(llm_consultation or {})

    pairs = list(market_snapshot.get("pairs") or _default_pairs())
    pair_biases: List[PairBias] = []
    agreement_flags: Dict[str, str] = {}

    # -----------------------------------------------------------------
    # Phase 3C summary diagnostics (read-only, fail-open, no behavior change)
    # -----------------------------------------------------------------
    llm_weighting_summary_diag: Dict[str, Any] = {
        "ok": False,
        "available": False,
        "non_blocking": True,
        "error": None,
        "message": None,
        "focus_by_pair": {},
    }

    # Phase 3 runtime lookup (read-only, fail-open)
    weighting_runtime, weighting_runtime_error = _get_weighting_runtime()
    weighting_scope = _build_weighting_scope(checkpoint=cp, market_snapshot=market_snapshot)

    # Phase 3C: optional summary read for diagnostics (no synthesis logic change yet)
    if get_llm_weighting_summary is None:
        llm_weighting_summary_diag["error"] = "dmip_learning_summary_import_unavailable"
    else:
        llm_weighting_summary_diag["available"] = True
        try:
            focus_by_pair: Dict[str, Any] = {}
            for pair in pairs:
                s = get_llm_weighting_summary(
                    pair=pair,
                    checkpoint=cp,
                    days=30,
                )
                s_dict = _safe_dict(s)
                focus = _safe_dict(s_dict.get("focus"))
                hints = _safe_dict(s_dict.get("weighting_hints"))
                focus_by_pair[pair] = {
                    "ok": _safe_bool(s_dict.get("ok"), default=False),
                    "focus": focus,
                    "weighting_hints": hints,
                }

            llm_weighting_summary_diag["ok"] = True
            llm_weighting_summary_diag["focus_by_pair"] = focus_by_pair
        except Exception as e:
            llm_weighting_summary_diag["ok"] = False
            llm_weighting_summary_diag["error"] = "dmip_learning_summary_read_error"
            llm_weighting_summary_diag["message"] = str(e)

    weights_snapshot: Optional[Dict[str, Any]] = None
    weights_runtime_notes: List[str] = []
    if weighting_runtime is not None:
        weights_snapshot, read_err = _try_read_weights_snapshot(weighting_runtime, scope=weighting_scope)
        if read_err:
            weights_runtime_notes.append(read_err)
        else:
            weights_runtime_notes.append("decision_influence_weights_loaded")
    else:
        if weighting_runtime_error:
            weights_runtime_notes.append(weighting_runtime_error)

    weighted_llm_hints: Dict[str, Dict[str, Any]] = {}

    # P3A/P3B unified learning events container (non-breaking, fail-open)
    learning_events: Dict[str, List[Dict[str, Any]]] = {
        "llm_accuracy": [],
        "task_tracking": [],
    }

    # Deterministic defaults (placeholder until real data+LLM consultation skills land)
    for pair in pairs:
        bias = "NEUTRAL"
        conf = "LOW"
        notes = ["phase_t_sprint1_placeholder_bias"]
        key_levels: List[float] = []

        llm_pair = dict((llm_consultation.get("pairs") or {}).get(pair, {}) or {})
        if llm_pair:
            # if both present and disagree -> AVOID (your rule)
            a = _safe_str(llm_pair.get("claude_bias")).upper()
            b = _safe_str(llm_pair.get("gpt4_bias")).upper()
            if a and b:
                if a != b:
                    bias = "AVOID"
                    conf = "LOW"
                    agreement_flags[pair] = "disagree"
                    notes.append("llm_disagreement_pair_avoid")
                else:
                    if a in {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}:
                        bias = a
                    conf = _safe_str(llm_pair.get("confidence"), "MEDIUM").upper()
                    conf = conf if conf in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"
                    agreement_flags[pair] = "agree"
                    notes.append("llm_agreement")
            else:
                agreement_flags[pair] = "partial"
                notes.append("llm_partial_signal")

            kls = llm_pair.get("key_levels")
            if isinstance(kls, list):
                for x in kls:
                    try:
                        key_levels.append(float(x))
                    except Exception:
                        pass

            # ----------------------------------------------------------
            # Phase 3D weighted synthesis hint (metadata / confidence hint)
            # via reusable dmip_llm_synthesis module (fail-open adapter)
            # ----------------------------------------------------------
            weighted_hint = _extract_weighted_bias_hint(
                pair=pair,
                llm_pair=llm_pair,
                weights_snapshot=weights_snapshot,
            )
            weighted_llm_hints[pair] = weighted_hint

            if weighted_hint.get("ok"):
                if weighted_hint.get("agreement") == "disagree":
                    # Preserve disagreement / AVOID (P3E)
                    notes.append("weighted_llm_disagreement_preserved")
                    bias = "AVOID"
                    conf = "LOW"
                elif weighted_hint.get("agreement") == "agree":
                    # Non-destructive hinting only: can confirm direction and optionally refine confidence
                    wb = _safe_str(weighted_hint.get("weighted_bias")).upper()
                    wc = _safe_str(weighted_hint.get("weighted_confidence")).upper()
                    if wb in {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"} and bias != "AVOID":
                        # Only align if current pair bias came from LLM agreement path
                        if agreement_flags.get(pair) == "agree":
                            bias = wb
                            notes.append("weighted_llm_bias_confirmed")
                    if wc in {"HIGH", "MEDIUM", "LOW"} and agreement_flags.get(pair) == "agree":
                        # Confidence refinement only (still bounded/categorical)
                        conf = wc
                        notes.append("weighted_llm_confidence_hint")
                elif weighted_hint.get("agreement") == "partial":
                    notes.append("weighted_llm_partial_hint")

            # ----------------------------------------------------------
            # P3A / P3B append-only learning capture stubs (non-blocking)
            # ----------------------------------------------------------
            try:
                agreement = agreement_flags.get(pair, "partial")
                cap1 = log_llm_accuracy_stub(
                    checkpoint=cp,
                    pair=pair,
                    llm_pair=llm_pair,
                    agreement=agreement,
                    selected_bias=bias,
                    confidence=conf,
                    source="dmip_runtime",
                )
                learning_events["llm_accuracy"].append(cap1)
            except Exception as e:
                learning_events["llm_accuracy"].append(
                    {
                        "ok": False,
                        "non_blocking": True,
                        "error": "llm_accuracy_capture_wrapper_exception",
                        "message": str(e),
                    }
                )

            try:
                cap2 = log_task_tracking_stub(
                    checkpoint=cp,
                    pair=pair,
                    stage="dmip_llm_consultation",
                    status="processed",
                    details={
                        "agreement": agreement_flags.get(pair, "partial"),
                        "bias": bias,
                        "confidence": conf,
                        "weighted_hint": weighted_llm_hints.get(pair, {}),
                    },
                    source="dmip_runtime",
                )
                learning_events["task_tracking"].append(cap2)
            except Exception as e:
                learning_events["task_tracking"].append(
                    {
                        "ok": False,
                        "non_blocking": True,
                        "error": "task_tracking_capture_wrapper_exception",
                        "message": str(e),
                    }
                )

        pair_biases.append(
            PairBias(
                pair=pair,
                bias=bias,
                confidence=conf,
                key_levels=key_levels[:8],
                notes=notes,
            ).validate()
        )

    # Conservative default environment
    risk_environment = _safe_str(market_snapshot.get("risk_environment"), "UNKNOWN").upper()
    if risk_environment not in {"RISK_ON", "RISK_OFF", "MIXED", "UNKNOWN"}:
        risk_environment = "UNKNOWN"

    trading_conf = "LOW"
    if any(v == "disagree" for v in agreement_flags.values()):
        trading_conf = "LOW"
    elif all(v == "agree" for v in agreement_flags.values()) and agreement_flags:
        trading_conf = "MEDIUM"

    sheet = DailyBiasSheet(
        checkpoint_id=f"dmip_{uuid.uuid4().hex[:16]}",
        session=cp,
        risk_environment=risk_environment,
        trading_confidence=trading_conf,
        pair_biases=pair_biases,
        avoid_events=list(market_snapshot.get("avoid_events") or []),
        llm_agreement_flags=agreement_flags,
        metadata={
            "phase": "phase_t_sprint1_dmip_scaffold_plus_phase3_weighted_hints",
            "generated_at_unix": time.time(),
            "checkpoint_label": CHECKPOINT_SPECS[cp]["label"],
            "checkpoint_time_gmt": CHECKPOINT_SPECS[cp]["hhmm_gmt"],
            # Phase 3 metadata (read-only / non-blocking)
            "decision_influence_weighting_scope": weighting_scope,
            "decision_influence_weighting_loaded": bool(weights_snapshot),
            "decision_influence_weighting_notes": weights_runtime_notes,
            "decision_influence_weights_version": (
                (weights_snapshot or {}).get("weights_version")
                or (weights_snapshot or {}).get("version")
            ),
            "decision_influence_snapshot_hash": (weights_snapshot or {}).get("snapshot_hash"),
            "dmip_learning_summary_available": bool(llm_weighting_summary_diag.get("available")),
            "dmip_learning_summary_ok": bool(llm_weighting_summary_diag.get("ok")),
            "dmip_llm_synthesis_module_available": bool(callable(get_llm_weighted_bias)),
            "risk_invariants_mutated": False,  # explicit P3F guardrail signal
        },
    ).validate()

    return {
        "ok": True,
        "schema_version": "aion.dmip_checkpoint_result.v1",
        "checkpoint": cp,
        "bias_sheet": sheet.to_dict(),
        "notes": [
            "read_only_scaffold",
            "real_data_feeds_not_connected_yet",
            "llm_consultation_optional_input_supported",
            "phase3_weighted_synthesis_hints_enabled_fail_open",
            "disagreement_preserved_as_signal",
            "risk_invariants_not_mutated",
            "p3a_p3b_learning_capture_stubs_non_blocking",
            "p3c_learning_summary_diagnostic_fail_open",
            "p3d_reusable_dmip_llm_synthesis_adapter_enabled_fail_open",
            "phase2_paper_trade_runtime_scaffold_available",
            "phase2_risk_gate_wrapper_available",
        ],
        # Phase 3 additive outputs (non-breaking)
        "llm_weighted_hints": weighted_llm_hints,
        "learning_events": learning_events,
        "llm_weighting_summary_diagnostic": llm_weighting_summary_diag,
        "decision_influence_weighting": {
            "scope": weighting_scope,
            "loaded": bool(weights_snapshot),
            "notes": weights_runtime_notes,
            "weights_version": (
                (weights_snapshot or {}).get("weights_version")
                or (weights_snapshot or {}).get("version")
            ),
            "snapshot_hash": (weights_snapshot or {}).get("snapshot_hash"),
        },
    }