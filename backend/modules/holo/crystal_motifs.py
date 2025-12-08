# backend/modules/holo/crystal_motifs.py
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Sequence, Tuple


@dataclass
class Motif:
    """
    A repeated workflow / habit pattern extracted from glyph traces.

    We keep this deliberately simple:
      - steps: sequence of symbolic ops (e.g. "open_file", "run_tests", ...)
      - support: how many times this pattern appears in the trace
      - strength: normalised support [0, 1]
      - sqi: optional quality metric (if available from CodexMetrics / SQI)
    """

    motif_id: str
    label: str
    steps: List[str]
    support: int
    strength: float
    sqi: float
    tags: List[str]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_symbol(event: Dict[str, Any]) -> str:
    """
    Try to collapse a glyph event to a canonical symbol / op name.
    Adjust this if your glyph trace uses different keys.
    """
    return (
        str(event.get("op"))
        or str(event.get("kind"))
        or str(event.get("type"))
        or "?"
    )


def _ngrams(seq: Sequence[str], n: int) -> List[Tuple[str, ...]]:
    return [
        tuple(seq[i : i + n])
        for i in range(0, max(0, len(seq) - n + 1))
    ]


def extract_motifs_from_glyph_trace(
    glyph_trace: List[Dict[str, Any]],
    codex_metrics: Dict[str, Dict[str, float]] | None = None,
    max_length: int = 5,
    min_support: int = 3,
    max_motifs: int = 32,
) -> List[Motif]:
    """
    Very simple motif extractor based on n-gram frequency over glyph_trace.

    Inputs:
      - glyph_trace: list of glyph events (dicts) from QFC / DevTools
      - codex_metrics: optional per-op metrics (e.g. time, error rate, SQI)
      - max_length: longest pattern length (in steps)
      - min_support: minimum number of occurrences to count as a motif
      - max_motifs: cap on number of motifs returned

    Output:
      - list[Motif] sorted by strength descending
    """

    if not glyph_trace:
        return []

    codex_metrics = codex_metrics or {}
    symbols = [_extract_symbol(ev) for ev in glyph_trace]

    # Count n-grams for n = 2..max_length
    counts: Dict[Tuple[str, ...], int] = {}
    total_events = len(symbols)

    for n in range(2, max_length + 1):
        for gram in _ngrams(symbols, n):
            counts[gram] = counts.get(gram, 0) + 1

    # Filter by support
    frequent: List[Tuple[Tuple[str, ...], int]] = [
        (gram, c) for gram, c in counts.items() if c >= min_support
    ]
    if not frequent:
        return []

    # Sort by support then length (longer patterns first for same support)
    frequent.sort(key=lambda x: (x[1], len(x[0])), reverse=True)

    # Turn into Motif objects
    motifs: List[Motif] = []
    max_support_seen = max(c for _, c in frequent) or 1

    for idx, (gram, support) in enumerate(frequent[:max_motifs]):
        steps = list(gram)
        strength = support / max_support_seen

        # crude SQI: average of any SQI-like metric we can find for the ops
        sqis: List[float] = []
        for s in steps:
            m = codex_metrics.get(s) or {}
            # prefer "SQI" but fall back to any "sqi" key
            if isinstance(m.get("SQI"), (int, float)):
                sqis.append(float(m["SQI"]))
            elif isinstance(m.get("sqi"), (int, float)):
                sqis.append(float(m["sqi"]))
        avg_sqi = sum(sqis) / len(sqis) if sqis else 0.5

        motif_id = f"motif:{idx:04d}"
        label = " → ".join(steps)

        tags = ["crystal-motif"]
        if len(steps) >= 3:
            tags.append("long-form")
        if support >= 5:
            tags.append("high-support")

        metrics: Dict[str, Any] = {
            "support": support,
            "strength": strength,
            "step_count": len(steps),
            "avg_sqi": avg_sqi,
        }

        motifs.append(
            Motif(
                motif_id=motif_id,
                label=label,
                steps=steps,
                support=support,
                strength=strength,
                sqi=avg_sqi,
                tags=tags,
                metrics=metrics,
            )
        )

    return motifs