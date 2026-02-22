# backend/modules/aion_equities/investing_ids.py
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

__all__ = [
    "normalize_ticker",
    "slugify_segment",
    "validate_canonical_id",
    "make_company_id",
    "make_sector_id",
    "make_macro_id",
    "make_ai_adoption_id",
    "make_quarter_event_id",
    "make_earnings_event_id",
    "make_filing_event_id",
    "make_news_event_id",
    "make_catalyst_event_id",
    "make_thesis_id",
    "make_pattern_id",
    "make_risk_id",
    "parse_quarter_label",
]

# ---------------------------------------------------------------------
# Canonical ID grammar (v1)
# ---------------------------------------------------------------------
#
# company/<ticker>
# sector/<sector_name>
# macro/<regime>
# ai_adoption/<theme_or_sector>
#
# company/<ticker>/quarter/<YYYY-Q#>
# company/<ticker>/earnings/<YYYY-MM-DD>
# company/<ticker>/filing/<YYYY-MM-DD>/<kind>
# company/<ticker>/news/<event_id>
# company/<ticker>/catalyst/<event_id>
#
# thesis/<ticker>/<mode>/<window>
# pattern/<pattern_name>
# risk/<portfolio_or_policy_state>
#
# Notes:
# - Tickers are normalized to uppercase, preserving ".", "-", "_" (e.g. AHT.L)
# - Non-ticker segments are slugified to lowercase snake_case-ish with [a-z0-9_-.]
# - IDs are plain strings used consistently across containers, KG nodes, and events
# ---------------------------------------------------------------------


# Allowed thesis modes for v1 (can be extended later)
_ALLOWED_THESIS_MODES = {
    "long",
    "short",
    "swing_short",
    "catalyst_long",
    "neutral_watch",
}

# Generic ID regex (broad safety check; specific constructors are stricter)
_CANONICAL_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(?:/[A-Za-z0-9._-]+)+$")

# Ticker regex: uppercase letters/numbers with optional .-_ separators
# Examples: AHT.L, BRBY.L, MSFT, RIO.L, 3IN.L
_TICKER_RE = re.compile(r"^[A-Z0-9]+(?:[._-][A-Z0-9]+)*$")

# Quarter label regex: 2026-Q1..Q4
_QUARTER_LABEL_RE = re.compile(r"^(?P<year>\d{4})-Q(?P<q>[1-4])$")

# Date regex: YYYY-MM-DD
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------
def slugify_segment(value: Any, *, allow_empty: bool = False) -> str:
    """
    Normalize an arbitrary value into a safe canonical ID segment.

    Rules:
    - lowercases
    - trims whitespace
    - converts spaces/slashes to underscores
    - strips unsupported chars (keeps a-z0-9 _ - .)
    - collapses repeated separators
    """
    s = "" if value is None else str(value)
    s = s.strip().lower()

    # Common separators -> underscore
    s = s.replace("/", "_").replace("\\", "_").replace(" ", "_")

    # Remove anything not safe for segment
    s = re.sub(r"[^a-z0-9._-]+", "", s)

    # Collapse repeated separators
    s = re.sub(r"_+", "_", s)
    s = re.sub(r"-+", "-", s)
    s = re.sub(r"\.+", ".", s)

    # Trim separators at ends
    s = s.strip("._-")

    if not s and not allow_empty:
        raise ValueError("Segment is empty after normalization")
    return s


def normalize_ticker(ticker: Any) -> str:
    """
    Normalize ticker for canonical IDs.

    Preserves '.', '-', '_' and uppercases letters.
    Examples:
      'aht.l' -> 'AHT.L'
      ' msft ' -> 'MSFT'
    """
    if ticker is None:
        raise ValueError("ticker is required")

    t = str(ticker).strip().upper()
    t = re.sub(r"\s+", "", t)

    if not t:
        raise ValueError("ticker is empty")

    if not _TICKER_RE.match(t):
        raise ValueError(f"Invalid ticker format: {ticker!r}")
    return t


def validate_canonical_id(canonical_id: str) -> str:
    """
    Broad validation for canonical IDs (syntax-level).
    Constructors provide stronger semantic validation.
    """
    if not isinstance(canonical_id, str) or not canonical_id.strip():
        raise ValueError("canonical_id must be a non-empty string")

    cid = canonical_id.strip()
    if not _CANONICAL_ID_RE.match(cid):
        raise ValueError(f"Invalid canonical ID syntax: {cid!r}")
    return cid


def _normalize_date_str(value: Any) -> str:
    """
    Accepts:
      - 'YYYY-MM-DD'
      - datetime.date
      - datetime.datetime
    Returns:
      - 'YYYY-MM-DD'
    """
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    s = str(value).strip()
    if not _DATE_RE.match(s):
        raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {value!r}")
    return s


def parse_quarter_label(label: Any) -> tuple[int, int]:
    """
    Parse 'YYYY-Q#' (e.g. '2026-Q1') -> (2026, 1)
    """
    s = str(label).strip().upper()
    m = _QUARTER_LABEL_RE.match(s)
    if not m:
        raise ValueError(f"Invalid quarter label (expected YYYY-Q#): {label!r}")
    return int(m.group("year")), int(m.group("q"))


def _quarter_label(year: int, quarter: int) -> str:
    y = int(year)
    q = int(quarter)
    if y < 1900 or y > 3000:
        raise ValueError(f"Invalid year for quarter label: {year!r}")
    if q not in (1, 2, 3, 4):
        raise ValueError(f"Quarter must be 1..4, got {quarter!r}")
    return f"{y}-Q{q}"


# ---------------------------------------------------------------------
# Root entity IDs
# ---------------------------------------------------------------------
def make_company_id(ticker: Any) -> str:
    """
    company/<ticker>
    Example: company/AHT.L
    """
    t = normalize_ticker(ticker)
    cid = f"company/{t}"
    return validate_canonical_id(cid)


def make_sector_id(sector_name: Any) -> str:
    """
    sector/<sector_name>
    Example: sector/industrial_equipment_rental
    """
    seg = slugify_segment(sector_name)
    cid = f"sector/{seg}"
    return validate_canonical_id(cid)


def make_macro_id(regime: Any) -> str:
    """
    macro/<regime>
    Example: macro/uk_rates_high_real
    """
    seg = slugify_segment(regime)
    cid = f"macro/{seg}"
    return validate_canonical_id(cid)


def make_ai_adoption_id(theme_or_sector: Any) -> str:
    """
    ai_adoption/<theme_or_sector>
    Example: ai_adoption/back_office_automation
    """
    seg = slugify_segment(theme_or_sector)
    cid = f"ai_adoption/{seg}"
    return validate_canonical_id(cid)


def make_pattern_id(pattern_name: Any) -> str:
    """
    pattern/<pattern_name>
    Example: pattern/debt_wall_stress
    """
    seg = slugify_segment(pattern_name)
    cid = f"pattern/{seg}"
    return validate_canonical_id(cid)


def make_risk_id(portfolio_or_policy_state: Any) -> str:
    """
    risk/<portfolio_or_policy_state>
    Example: risk/core_equities_policy_v1
    """
    seg = slugify_segment(portfolio_or_policy_state)
    cid = f"risk/{seg}"
    return validate_canonical_id(cid)


# ---------------------------------------------------------------------
# Time-sliced / event IDs under company
# ---------------------------------------------------------------------
def make_quarter_event_id(ticker: Any, year: Optional[int] = None, quarter: Optional[int] = None, *, quarter_label: Optional[str] = None) -> str:
    """
    company/<ticker>/quarter/<YYYY-Q#>

    Usage:
      make_quarter_event_id("AHT.L", 2026, 1)
      make_quarter_event_id("AHT.L", quarter_label="2026-Q1")
    """
    t = normalize_ticker(ticker)

    if quarter_label is not None:
        y, q = parse_quarter_label(quarter_label)
        qlabel = _quarter_label(y, q)
    else:
        if year is None or quarter is None:
            raise ValueError("Provide (year and quarter) or quarter_label")
        qlabel = _quarter_label(int(year), int(quarter))

    cid = f"company/{t}/quarter/{qlabel}"
    return validate_canonical_id(cid)


def make_earnings_event_id(ticker: Any, date_str: Any) -> str:
    """
    company/<ticker>/earnings/<YYYY-MM-DD>
    """
    t = normalize_ticker(ticker)
    d = _normalize_date_str(date_str)
    cid = f"company/{t}/earnings/{d}"
    return validate_canonical_id(cid)


def make_filing_event_id(ticker: Any, date_str: Any, kind: Any) -> str:
    """
    company/<ticker>/filing/<YYYY-MM-DD>/<kind>

    kind examples:
      annual_report
      half_year_results
      trading_update
      proxy
      10q
      10k
    """
    t = normalize_ticker(ticker)
    d = _normalize_date_str(date_str)
    k = slugify_segment(kind)
    cid = f"company/{t}/filing/{d}/{k}"
    return validate_canonical_id(cid)


def make_news_event_id(ticker: Any, event_id: Any) -> str:
    """
    company/<ticker>/news/<event_id>

    event_id should be a stable source ID / hash / slug.
    """
    t = normalize_ticker(ticker)
    e = slugify_segment(event_id)
    cid = f"company/{t}/news/{e}"
    return validate_canonical_id(cid)


def make_catalyst_event_id(ticker: Any, event_id: Any) -> str:
    """
    company/<ticker>/catalyst/<event_id>

    event_id examples:
      earnings_2026-06-18
      debt_refi_q3_2026
      cma_decision_2026-09
    """
    t = normalize_ticker(ticker)
    e = slugify_segment(event_id)
    cid = f"company/{t}/catalyst/{e}"
    return validate_canonical_id(cid)


# ---------------------------------------------------------------------
# Thesis IDs
# ---------------------------------------------------------------------
def make_thesis_id(ticker: Any, mode: Any, window: Any, *, strict_mode: bool = True) -> str:
    """
    thesis/<ticker>/<mode>/<window>

    Example:
      thesis/AHT.L/long/2026Q2_pre_earnings
      thesis/BARC.L/swing_short/2026Q3_post_results

    strict_mode=True enforces v1 allowed modes.
    """
    t = normalize_ticker(ticker)
    m = slugify_segment(mode)
    w = slugify_segment(window)

    if strict_mode and m not in _ALLOWED_THESIS_MODES:
        raise ValueError(
            f"Invalid thesis mode: {mode!r}. Allowed: {sorted(_ALLOWED_THESIS_MODES)}"
        )

    cid = f"thesis/{t}/{m}/{w}"
    return validate_canonical_id(cid)


# ---------------------------------------------------------------------
# Optional convenience parsers / inspectors
# ---------------------------------------------------------------------
def is_company_id(canonical_id: str) -> bool:
    try:
        cid = validate_canonical_id(canonical_id)
    except ValueError:
        return False
    parts = cid.split("/")
    return len(parts) == 2 and parts[0] == "company"


def is_thesis_id(canonical_id: str) -> bool:
    try:
        cid = validate_canonical_id(canonical_id)
    except ValueError:
        return False
    parts = cid.split("/")
    return len(parts) == 4 and parts[0] == "thesis"


def is_company_event_id(canonical_id: str) -> bool:
    """
    Returns True for:
      company/<ticker>/(quarter|earnings|filing|news|catalyst)/...
    """
    try:
        cid = validate_canonical_id(canonical_id)
    except ValueError:
        return False
    parts = cid.split("/")
    return (
        len(parts) >= 4
        and parts[0] == "company"
        and parts[2] in {"quarter", "earnings", "filing", "news", "catalyst"}
    )


# Keep these helpers internal by default (not exported), but handy if you want them.
# If you want them public later, add them to __all__.