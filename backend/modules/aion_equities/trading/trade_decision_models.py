# /workspaces/COMDEX/backend/modules/aion_equities/trading/trade_decision_models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.modules.aion_equities.trading.expected_value import EVInputs, EVResult, ExpectedValueCalculator


@dataclass
class TradeDecisionInputs:
    """
    Minimal structured inputs that should exist (or be inferred) for a trade decision.

    Probabilities expressed as 0..1.
    Gain/loss expressed as percent moves (e.g., +18 means +18%).
    """
    probability_confirm: float
    probability_break: float
    expected_gain_pct: float
    expected_loss_pct: float
    conviction_score: Optional[float] = None  # 0..1 optional


@dataclass
class TradeDecisionMath:
    """
    Normalized math outputs you want to store on both decision_notes + execution_instruction.
    """
    expected_value_pct: Optional[float] = None
    kelly_full_fraction: Optional[float] = None
    kelly_scaled_fraction: Optional[float] = None
    suggested_size_percent: Optional[float] = None

    kelly_scale: float = 0.5
    max_size_percent_cap: float = 25.0

    inputs: Dict[str, Any] = field(default_factory=dict)
    missing_inputs: list[str] = field(default_factory=list)


@dataclass
class TradeDecisionPacket:
    """
    Canonical packet you can attach into:
      - decision_notes["trade_math"]
      - execution_instruction["trade_math"]

    Keep this small + stable; anything else stays in raw OpenAI response.
    """
    review_id: str
    company_ref: str
    proposal_id: str
    thesis_ref: Optional[str] = None

    trade_math: TradeDecisionMath = field(default_factory=TradeDecisionMath)

    # optional passthrough (debug / audit)
    raw: Dict[str, Any] = field(default_factory=dict)


class TradeDecisionMathBuilder:
    """
    One place to compute EV + Kelly and return your normalized TradeDecisionMath.
    """

    def __init__(self, *, kelly_scale: float = 0.5, max_size_percent: float = 25.0):
        self.calculator = ExpectedValueCalculator(
            kelly_scale=float(kelly_scale),
            max_size_percent=float(max_size_percent),
        )

    def build(self, inp: TradeDecisionInputs) -> TradeDecisionMath:
        ev_inp = EVInputs(
            probability_confirm=float(inp.probability_confirm),
            probability_break=float(inp.probability_break),
            expected_gain_pct=float(inp.expected_gain_pct),
            expected_loss_pct=float(inp.expected_loss_pct),
            conviction_score=float(inp.conviction_score) if inp.conviction_score is not None else None,
        )

        res: EVResult = self.calculator.compute(ev_inp)

        return TradeDecisionMath(
            expected_value_pct=res.expected_value_pct,
            kelly_full_fraction=res.kelly_full_fraction,
            kelly_scaled_fraction=res.kelly_scaled_fraction,
            suggested_size_percent=res.suggested_size_percent,
            kelly_scale=res.kelly_scale,
            max_size_percent_cap=res.max_size_percent_cap,
            inputs={
                "probability_confirm": res.inputs.probability_confirm,
                "probability_break": res.inputs.probability_break,
                "expected_gain_pct": res.inputs.expected_gain_pct,
                "expected_loss_pct": res.inputs.expected_loss_pct,
                "conviction_score": res.inputs.conviction_score,
            },
            missing_inputs=[],
        )

    def build_from_dict(self, d: Dict[str, Any]) -> TradeDecisionMath:
        """
        Best-effort: if missing inputs, returns TradeDecisionMath with missing_inputs populated.
        """
        missing: list[str] = []
        for k in ("probability_confirm", "probability_break", "expected_gain_pct", "expected_loss_pct"):
            if k not in d and (
                (k == "probability_confirm" and "p_confirm" not in d)
                or (k == "probability_break" and "p_break" not in d)
                or (k == "expected_gain_pct" and "expected_upside_pct" not in d)
                or (k == "expected_loss_pct" and "expected_downside_pct" not in d)
            ):
                missing.append(k)

        ev_res = self.calculator.compute_from_dict(d)
        if ev_res is None:
            return TradeDecisionMath(
                expected_value_pct=None,
                kelly_full_fraction=None,
                kelly_scaled_fraction=None,
                suggested_size_percent=None,
                kelly_scale=float(self.calculator.kelly_scale),
                max_size_percent_cap=float(self.calculator.max_size_percent),
                inputs={k: d.get(k) for k in ("probability_confirm", "probability_break", "expected_gain_pct", "expected_loss_pct", "conviction_score", "p_confirm", "p_break", "expected_upside_pct", "expected_downside_pct") if k in d},
                missing_inputs=missing or ["unparseable_inputs"],
            )

        return TradeDecisionMath(
            expected_value_pct=ev_res.expected_value_pct,
            kelly_full_fraction=ev_res.kelly_full_fraction,
            kelly_scaled_fraction=ev_res.kelly_scaled_fraction,
            suggested_size_percent=ev_res.suggested_size_percent,
            kelly_scale=ev_res.kelly_scale,
            max_size_percent_cap=ev_res.max_size_percent_cap,
            inputs={
                "probability_confirm": ev_res.inputs.probability_confirm,
                "probability_break": ev_res.inputs.probability_break,
                "expected_gain_pct": ev_res.inputs.expected_gain_pct,
                "expected_loss_pct": ev_res.inputs.expected_loss_pct,
                "conviction_score": ev_res.inputs.conviction_score,
            },
            missing_inputs=[],
        )