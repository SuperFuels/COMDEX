# /workspaces/COMDEX/backend/modules/aion_equities/openai_trade_decision_runtime.py
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Optional, Tuple

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore
from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore
from backend.modules.aion_equities.openai_context_packet_builder import OpenAIContextPacketBuilder
from backend.modules.aion_equities.openai_response_mapper import map_openai_trade_review_response


# -----------------------------
# EV + Kelly helpers
# -----------------------------
def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip()
            if not s:
                return None
            # tolerate "25%", "0.25", "  0.25 "
            s = s.replace("%", "").strip()
            return float(s)
        return float(x)
    except Exception:
        return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _dig(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _first_float(d: Dict[str, Any], paths: Tuple[Tuple[str, ...], ...]) -> Optional[float]:
    for p in paths:
        v = _as_float(_dig(d, p))
        if v is not None:
            return v
    return None


def _compute_trade_math(
    *,
    decision_notes: Dict[str, Any],
    execution_instruction: Dict[str, Any],
    kelly_scale: float,
    max_size_percent: float,
) -> Dict[str, Any]:
    """
    Computes:
      EV_pct = p_confirm*gain_pct - p_break*loss_pct

    Kelly (fraction of capital):
      b = gain/loss
      f_full = (b*p - q)/b
      f_scaled = clamp(f_full*kelly_scale, 0..1)
      suggested_size_percent = min(max_size_percent, f_scaled*100)

    Inputs can be located anywhere inside decision_notes/execution_instruction.
    We probe a few common aliases for compatibility.
    """
    dn = decision_notes if isinstance(decision_notes, dict) else {}
    ei = execution_instruction if isinstance(execution_instruction, dict) else {}
    combined: Dict[str, Any] = {}
    combined.update(deepcopy(dn))
    combined.update(deepcopy(ei))

    p_confirm = _first_float(
        combined,
        (
            ("probability_confirm",),
            ("p_confirm",),
            ("prob_confirm",),
            ("trade_metrics", "probability_confirm"),
            ("thesis_metrics", "probability_confirm"),
            ("decision", "probability_confirm"),
        ),
    )
    p_break = _first_float(
        combined,
        (
            ("probability_break",),
            ("p_break",),
            ("prob_break",),
            ("trade_metrics", "probability_break"),
            ("thesis_metrics", "probability_break"),
            ("decision", "probability_break"),
        ),
    )
    gain_pct = _first_float(
        combined,
        (
            ("expected_gain_pct",),
            ("expected_upside_pct",),
            ("gain_pct",),
            ("trade_metrics", "expected_gain_pct"),
            ("decision", "expected_gain_pct"),
        ),
    )
    loss_pct = _first_float(
        combined,
        (
            ("expected_loss_pct",),
            ("expected_downside_pct",),
            ("loss_pct",),
            ("trade_metrics", "expected_loss_pct"),
            ("decision", "expected_loss_pct"),
        ),
    )
    conviction = _first_float(
        combined,
        (
            ("conviction_score",),
            ("conviction",),
            ("trade_metrics", "conviction_score"),
            ("thesis_metrics", "conviction_score"),
        ),
    )

    missing = []
    if p_confirm is None:
        missing.append("probability_confirm")
    if p_break is None:
        missing.append("probability_break")
    if gain_pct is None:
        missing.append("expected_gain_pct")
    if loss_pct is None:
        missing.append("expected_loss_pct")

    ev_pct: Optional[float] = None
    kelly_full: Optional[float] = None
    kelly_scaled: Optional[float] = None
    suggested_size_percent: Optional[float] = None

    if not missing:
        p = _clamp(float(p_confirm), 0.0, 1.0)
        q = _clamp(float(p_break), 0.0, 1.0)
        g = float(gain_pct)
        l = abs(float(loss_pct))

        ev_pct = (p * g) - (q * l)

        if g > 0.0 and l > 0.0:
            b = g / l
            # full Kelly
            kelly_full = ((b * p) - q) / b

            # optional conviction multiplier if present (0..1)
            if conviction is not None:
                kelly_full = kelly_full * _clamp(float(conviction), 0.0, 1.0)

            kelly_scaled = _clamp(kelly_full * float(kelly_scale), 0.0, 1.0)
            suggested_size_percent = min(float(max_size_percent), kelly_scaled * 100.0)

    return {
        "inputs": {
            "probability_confirm": p_confirm,
            "probability_break": p_break,
            "expected_gain_pct": gain_pct,
            "expected_loss_pct": loss_pct,
            "conviction_score": conviction,
        },
        "missing_inputs": missing,
        "expected_value_pct": ev_pct,
        "kelly_full_fraction": kelly_full,
        "kelly_scaled_fraction": kelly_scaled,
        "kelly_scale": float(kelly_scale),
        "suggested_size_percent": suggested_size_percent,
        "max_size_percent_cap": float(max_size_percent),
    }


class OpenAITradeDecisionRuntime:
    """
    Thin runtime that:
    - builds the OpenAI context packet
    - calls the OpenAI client
    - maps the structured response into decision/execution payloads
    - injects EV + (modified) Kelly sizing into both artifacts
    - optionally persists decision_notes + execution_instruction if stores are provided
    """

    def __init__(
        self,
        *,
        context_packet_builder: OpenAIContextPacketBuilder,
        openai_client: Callable[[Dict[str, Any]], Dict[str, Any]],
        decision_notes_store: Optional[DecisionNotesStore] = None,
        execution_instruction_store: Optional[ExecutionInstructionStore] = None,
        # NEW knobs (safe defaults)
        kelly_scale: float = 0.5,  # half-Kelly default (use 0.25 for quarter-Kelly)
        max_size_percent: float = 25.0,  # hard cap, independent of guardrails
        apply_kelly_when_missing_size: bool = True,  # only fill size_percent if absent/invalid
        **_: Any,
    ):
        self.context_packet_builder = context_packet_builder
        self.openai_client = openai_client
        self.decision_notes_store = decision_notes_store
        self.execution_instruction_store = execution_instruction_store

        self.kelly_scale = float(kelly_scale)
        self.max_size_percent = float(max_size_percent)
        self.apply_kelly_when_missing_size = bool(apply_kelly_when_missing_size)

    def run_trade_decision(
        self,
        *,
        company_ref: str,
        proposal_id: str,
        review_id: str,
        thesis_ref: Optional[str] = None,
        proposal_packet: Optional[Dict[str, Any]] = None,
        current_business_status: Optional[Dict[str, Any]] = None,
        company_intelligence_pack: Optional[Dict[str, Any]] = None,
        operating_brief_id: Optional[str] = None,
        operating_brief_version: Optional[str] = None,
        generated_by: str = "aion_equities.openai_trade_decision_runtime",
        **_: Any,
    ) -> Dict[str, Any]:
        context_packet = self.context_packet_builder.build_context_packet(
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            proposal_packet=deepcopy(proposal_packet or {}),
            current_business_status=deepcopy(current_business_status or {}),
            company_intelligence_pack=deepcopy(company_intelligence_pack or {}),
            operating_brief_id=operating_brief_id,
            operating_brief_version=operating_brief_version,
            generated_by=generated_by,
        )

        raw_response = self.openai_client(deepcopy(context_packet))

        mapped = map_openai_trade_review_response(
            deepcopy(raw_response),
            company_ref=company_ref,
            proposal_id=proposal_id,
            review_id=review_id,
            thesis_ref=thesis_ref,
            generated_by=generated_by,
        )

        decision_notes_payload = deepcopy(mapped["decision_notes_payload"])
        execution_instruction_payload = deepcopy(mapped["execution_instruction_payload"])

        decision_notes = deepcopy(decision_notes_payload.get("decision_notes", {}))
        execution_instruction = deepcopy(execution_instruction_payload.get("execution_instruction", {}))

        # -----------------------------
        # Inject EV + Kelly sizing
        # -----------------------------
        trade_math = _compute_trade_math(
            decision_notes=decision_notes,
            execution_instruction=execution_instruction,
            kelly_scale=self.kelly_scale,
            max_size_percent=self.max_size_percent,
        )

        if isinstance(decision_notes, dict):
            decision_notes.setdefault("trade_math", deepcopy(trade_math))

        if isinstance(execution_instruction, dict):
            execution_instruction.setdefault("trade_math", deepcopy(trade_math))

            if self.apply_kelly_when_missing_size:
                cur_size = _as_float(execution_instruction.get("size_percent"))
                if cur_size is None or cur_size <= 0.0:
                    ksp = trade_math.get("suggested_size_percent")
                    if isinstance(ksp, (int, float)) and float(ksp) > 0.0:
                        execution_instruction["size_percent"] = float(ksp)

        # Write back so persistence includes injected fields
        decision_notes_payload["decision_notes"] = deepcopy(decision_notes)
        execution_instruction_payload["execution_instruction"] = deepcopy(execution_instruction)

        decision_notes_ref: Optional[str] = None
        execution_instruction_ref: Optional[str] = None
        saved_notes: Optional[Dict[str, Any]] = None
        saved_instruction: Optional[Dict[str, Any]] = None

        if self.decision_notes_store is not None:
            saved_notes = self.decision_notes_store.save_decision_notes(**decision_notes_payload)
            decision_notes_ref = saved_notes.get("decision_notes_id")

        if self.execution_instruction_store is not None:
            saved_instruction = self.execution_instruction_store.save_execution_instruction(
                **execution_instruction_payload
            )
            execution_instruction_ref = saved_instruction.get("execution_instruction_id")

        out: Dict[str, Any] = {
            "review_id": review_id,
            "company_ref": company_ref,
            "proposal_id": proposal_id,
            "thesis_ref": thesis_ref,
            "context_packet": deepcopy(context_packet),
            "raw_response": deepcopy(raw_response),
            "raw_openai_response": deepcopy(raw_response),
            "decision_notes_payload": decision_notes_payload,
            "execution_instruction_payload": execution_instruction_payload,
            "decision_notes": decision_notes,
            "execution_instruction": execution_instruction,
            "trade_math": deepcopy(trade_math),
        }

        if decision_notes_ref:
            out["decision_notes_ref"] = decision_notes_ref
        if execution_instruction_ref:
            out["execution_instruction_ref"] = execution_instruction_ref
        if saved_notes is not None:
            out["saved_decision_notes"] = saved_notes
        if saved_instruction is not None:
            out["saved_execution_instruction"] = saved_instruction

        return out

    def run_review(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Legacy compatibility alias expected by orchestrator/tests.
        """
        return self.run_trade_decision(**kwargs)


__all__ = [
    "OpenAITradeDecisionRuntime",
]