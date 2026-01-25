from __future__ import annotations

def denial_explanation_line(*, goal: str, deny_reason: str | None) -> str:
    """
    Fact-only, single-line denial explanation.
    No prose. No punctuation sentences. Stable key=value tokens only.
    """
    g = (goal or "maintain_coherence").strip()
    r = (deny_reason or "unknown").strip()
    # Keep it single-line no matter what
    g = g.replace("\n", " ").replace("\r", " ")
    r = r.replace("\n", " ").replace("\r", " ")
    return f"deny_learn=1 goal={g} deny_reason={r}"