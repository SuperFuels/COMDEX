from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.modules.aion_trading.contracts import DailyBiasSheet, PairBias


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


def run_dmip_checkpoint(
    *,
    checkpoint: str,
    market_snapshot: Optional[Dict[str, Any]] = None,
    llm_consultation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase T Sprint 1:
    - read-only scaffold
    - deterministic bias sheet generation
    - no external calls required yet
    """
    cp = str(checkpoint or "").strip()
    if cp not in CHECKPOINT_SPECS:
        raise ValueError(f"checkpoint must be one of {sorted(CHECKPOINT_SPECS)}")

    market_snapshot = dict(market_snapshot or {})
    llm_consultation = dict(llm_consultation or {})

    pairs = list(market_snapshot.get("pairs") or _default_pairs())
    pair_biases: List[PairBias] = []
    agreement_flags: Dict[str, str] = {}

    # Deterministic defaults (placeholder until real data+LLM consultation skills land)
    for pair in pairs:
        bias = "NEUTRAL"
        conf = "LOW"
        notes = ["phase_t_sprint1_placeholder_bias"]
        key_levels = []

        llm_pair = dict((llm_consultation.get("pairs") or {}).get(pair, {}) or {})
        if llm_pair:
            # if both present and disagree -> AVOID (your rule)
            a = str(llm_pair.get("claude_bias") or "").upper().strip()
            b = str(llm_pair.get("gpt4_bias") or "").upper().strip()
            if a and b:
                if a != b:
                    bias = "AVOID"
                    conf = "LOW"
                    agreement_flags[pair] = "disagree"
                    notes.append("llm_disagreement_pair_avoid")
                else:
                    if a in {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}:
                        bias = a
                    conf = str(llm_pair.get("confidence") or "MEDIUM").upper()
                    conf = conf if conf in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"
                    agreement_flags[pair] = "agree"
                    notes.append("llm_agreement")
            else:
                agreement_flags[pair] = "partial"

            kls = llm_pair.get("key_levels")
            if isinstance(kls, list):
                for x in kls:
                    try:
                        key_levels.append(float(x))
                    except Exception:
                        pass

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
    risk_environment = str(market_snapshot.get("risk_environment") or "UNKNOWN").upper()
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
            "phase": "phase_t_sprint1_dmip_scaffold",
            "generated_at_unix": time.time(),
            "checkpoint_label": CHECKPOINT_SPECS[cp]["label"],
            "checkpoint_time_gmt": CHECKPOINT_SPECS[cp]["hhmm_gmt"],
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
        ],
    }