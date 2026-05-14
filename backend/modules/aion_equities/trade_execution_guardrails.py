from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


class TradeExecutionGuardrails:
    """
    Hard validation layer before any execution path.

    Default rules locked:
    - no leverage
    - no margin
    - human approval required
    - size must not exceed configured cap
    - instruction must not be expired
    """

    def __init__(
        self,
        *,
        max_size_percent: float = 35.0,
        allow_leverage: bool = False,
        require_human_approval: bool = True,
    ):
        self.max_size_percent = float(max_size_percent)
        self.allow_leverage = bool(allow_leverage)
        self.require_human_approval = bool(require_human_approval)

    def evaluate(
        self,
        *,
        execution_instruction: Dict[str, Any],
        current_business_status: Optional[Dict[str, Any]] = None,
        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility wrapper used by OpenAITradeReviewPipeline.
        Maps to validate_instruction() and returns the shape expected by tests.
        """
        _ = company_intelligence_pack  # reserved for future rules

        res = self.validate_instruction(
            execution_instruction_payload={"execution_instruction": deepcopy(execution_instruction or {})},
            business_status=current_business_status or {},
            as_of=as_of,
        )

        approved = res.get("status") == "pass"
        return {
            "approved": bool(approved),
            "checked_at": res.get("checked_at"),
            "violations": list(res.get("failures") or []),
            "warnings": list(res.get("warnings") or []),
            "status": res.get("status"),
            "guardrail_summary": res.get("guardrail_summary") or {},
        }

    def validate_instruction(
        self,
        *,
        execution_instruction_payload: Dict[str, Any],
        business_status: Optional[Dict[str, Any]] = None,
        as_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        as_of = as_of or _utc_now_iso()
        now_dt = _parse_iso_utc(as_of)

        payload = deepcopy(execution_instruction_payload)
        instruction = deepcopy(payload.get("execution_instruction") or {})
        business_status = deepcopy(business_status or {})

        failures: List[str] = []
        warnings: List[str] = []

        approve_trade = bool(instruction.get("approve_trade", False))
        size_percent = _safe_float(instruction.get("size_percent"), 0.0)
        required_human_approval = bool(instruction.get("required_human_approval", False))
        stop_style = str(instruction.get("stop_style") or "").strip().lower()
        trade_type = str(instruction.get("trade_type") or "").strip().lower()
        expires_at = instruction.get("expires_at")

        leverage_requested = bool(instruction.get("use_leverage", False))
        margin_requested = bool(instruction.get("use_margin", False))

        if not approve_trade:
            failures.append("instruction_not_approved")

        if not self.allow_leverage and leverage_requested:
            failures.append("leverage_not_allowed")

        if not self.allow_leverage and margin_requested:
            failures.append("margin_not_allowed")

        if size_percent <= 0.0:
            failures.append("invalid_size_percent")

        if size_percent > self.max_size_percent:
            failures.append("size_exceeds_guardrail_cap")

        if self.require_human_approval and not required_human_approval:
            failures.append("human_approval_flag_missing")

        expiry_dt = _parse_iso_utc(expires_at)
        if expiry_dt is not None and now_dt is not None and expiry_dt < now_dt:
            failures.append("instruction_expired")

        if trade_type == "fundamental_long" and stop_style == "hard_price_stop":
            warnings.append("fundamental_long_should_prefer_thesis_based_stop")

        free_cash = _safe_float(business_status.get("free_cash"), 0.0)
        total_capital = _safe_float(business_status.get("total_capital"), 0.0)
        max_capital_allowed = _safe_float(instruction.get("max_capital_allowed"), 0.0)

        if total_capital > 0.0 and max_capital_allowed > total_capital:
            failures.append("max_capital_exceeds_total_capital")

        if free_cash > 0.0 and max_capital_allowed > 0.0 and max_capital_allowed > free_cash:
            warnings.append("max_capital_exceeds_current_free_cash")

        status = "pass" if not failures else "fail"

        return {
            "status": status,
            "checked_at": as_of,
            "failures": failures,
            "warnings": warnings,
            "guardrail_summary": {
                "approve_trade": approve_trade,
                "size_percent": size_percent,
                "max_size_percent": self.max_size_percent,
                "required_human_approval": required_human_approval,
                "allow_leverage": self.allow_leverage,
            },
        }


__all__ = [
    "TradeExecutionGuardrails",
]