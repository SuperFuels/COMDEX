from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _norm_prompt(s: str) -> str:
    return (s or "").strip().lower()


def _load_json(path: Path) -> Any:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue
    except Exception:
        return


def _extract_lex_events(lex: Any, prompt: str) -> List[Dict[str, Any]]:
    """
    Best-effort:
      - If LexMemory schema has per-prompt 'history' / 'events', use it.
      - Else, look for meta.auto_correct/cause markers on any sub-entries.
    Returns newest-first events with shape:
      {t, prompt, from_answer, to_answer, cause, session}
    """
    p = _norm_prompt(prompt)
    out: List[Dict[str, Any]] = []
    if not isinstance(lex, dict) or not p:
        return out

    candidates: List[Tuple[str, Any]] = []

    if "entries" in lex and isinstance(lex["entries"], dict):
        for k, v in lex["entries"].items():
            if _norm_prompt(k) == p:
                candidates.append((k, v))
    for k, v in lex.items():
        if isinstance(k, str) and _norm_prompt(k) == p and k != "entries":
            candidates.append((k, v))

    for _key, rec in candidates:
        if not isinstance(rec, dict):
            continue

        for hist_key in ("history", "events", "corrections"):
            hist = rec.get(hist_key)
            if isinstance(hist, list):
                for ev in hist:
                    if not isinstance(ev, dict):
                        continue
                    out.append(
                        {
                            "t": ev.get("t") or ev.get("ts") or ev.get("timestamp"),
                            "prompt": prompt,
                            "from_answer": ev.get("from_answer") or ev.get("from"),
                            "to_answer": ev.get("to_answer") or ev.get("to"),
                            "cause": ev.get("cause") or ev.get("reason") or "lex_history",
                            "session": ev.get("session"),
                            "source": f"lex:{hist_key}",
                        }
                    )

        meta = rec.get("meta") if isinstance(rec.get("meta"), dict) else {}
        if meta.get("auto_correct") is True:
            out.append(
                {
                    "t": meta.get("t") or meta.get("ts") or None,
                    "prompt": prompt,
                    "from_answer": meta.get("from_answer"),
                    "to_answer": rec.get("answer") or meta.get("to_answer"),
                    "cause": "auto_correct",
                    "session": meta.get("session"),
                    "source": "lex:meta",
                }
            )

    out.sort(key=lambda e: (e.get("t") is not None, e.get("t") or 0), reverse=True)
    return out


def _extract_turnlog_inferred_fix_events(prompt: str, limit: int) -> List[Dict[str, Any]]:
    """
    Legacy behavior: infer a "fix" event when a wrong recall is later followed by a correct recall.
    """
    p = _norm_prompt(prompt)
    if not p:
        return []

    turn_log = _data_root() / "telemetry" / "turn_log.jsonl"
    last_wrong: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = []

    for r in _iter_jsonl(turn_log):
        if _norm_prompt(str(r.get("prompt") or "")) != p:
            continue

        correct = r.get("correct")

        if correct is False:
            last_wrong = {
                "ts": r.get("ts"),
                "session": r.get("session"),
                "guess": r.get("guess"),
                "answer": r.get("answer"),
            }

        elif correct is True and last_wrong:
            events.append(
                {
                    "t": r.get("ts"),
                    "prompt": prompt,
                    "from_answer": last_wrong.get("guess"),
                    "to_answer": r.get("answer") or r.get("guess"),
                    "cause": "turnlog_inferred_fix",
                    "session": r.get("session"),
                    "source": "turn_log",
                }
            )
            last_wrong = None

    events.reverse()  # newest-first
    return events[:limit]


def _extract_turnlog_mismatch_events(prompt: str, limit: int) -> List[Dict[str, Any]]:
    """
    New behavior: include EVERY mismatch (wrong turn) even if it doesn't represent a new memory transition.
    This is what you want for “show me the latest run anyway”.
    """
    p = _norm_prompt(prompt)
    if not p:
        return []

    turn_log = _data_root() / "telemetry" / "turn_log.jsonl"
    out: List[Dict[str, Any]] = []

    for r in _iter_jsonl(turn_log):
        if _norm_prompt(str(r.get("prompt") or "")) != p:
            continue
        if r.get("correct") is not False:
            continue

        guess = r.get("guess")
        ans = r.get("answer")
        if guess is None and ans is None:
            continue  # non-informative / partial row

        out.append(
            {
                "t": r.get("ts"),
                "prompt": prompt,
                "from_answer": guess,
                "to_answer": ans,
                "cause": "turnlog_mismatch",
                "session": r.get("session"),
                "source": "turn_log",
            }
        )

    out.reverse()  # newest-first
    return out[:limit]

def _as_float_ts(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _within_window(t: Optional[float], since_ts: Optional[float], until_ts: Optional[float]) -> bool:
    if t is None:
        # If caller asked for a window, unknown timestamps can't be trusted → drop them.
        if since_ts is not None or until_ts is not None:
            return False
        return True
    if since_ts is not None and t < since_ts:
        return False
    if until_ts is not None and t > until_ts:
        return False
    return True


def _sort_newest_first(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # newest-first; unknown timestamps last
    return sorted(
        events,
        key=lambda e: (_as_float_ts(e.get("t")) is not None, _as_float_ts(e.get("t")) or 0.0),
        reverse=True,
    )


def _dedupe_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Stable dedupe for "same incident" across sources.
    # Key: (source, session, t, from, to, cause)
    seen = set()
    out: List[Dict[str, Any]] = []
    for e in events:
        key = (
            e.get("source"),
            e.get("session"),
            e.get("t"),
            e.get("from_answer"),
            e.get("to_answer"),
            e.get("cause"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def get_correction_history(
    prompt: str,
    limit: int = 20,
    since_ts: Optional[float] = None,
    until_ts: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Preferred source: LexMemory (if it contains correction events).
    Fallback: TurnLog mismatch extraction (every correct=false row).
    Supports time-window filtering.
    """
    limit = max(1, min(int(limit or 20), 200))
    since_ts_f = _as_float_ts(since_ts)
    until_ts_f = _as_float_ts(until_ts)

    lex_path = _data_root() / "memory" / "lex_memory.json"
    lex = _load_json(lex_path)

    events: List[Dict[str, Any]] = []

    # Primary: Lex events (if present)
    lex_events = _extract_lex_events(lex, prompt)
    if lex_events:
        events.extend(lex_events)
    else:
        # Fallback: TurnLog mismatches
        events.extend(_extract_turnlog_mismatch_events(prompt, limit=limit * 5))

    # Filter by time window
    filtered: List[Dict[str, Any]] = []
    for e in events:
        t = _as_float_ts(e.get("t"))
        if _within_window(t, since_ts_f, until_ts_f):
            filtered.append(e)

    # Dedupe + newest-first + limit
    filtered = _dedupe_events(filtered)
    filtered = _sort_newest_first(filtered)
    return filtered[:limit]