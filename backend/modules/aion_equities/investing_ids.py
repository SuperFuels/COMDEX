# backend/modules/aion_equities/investing_ids.py
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

__all__ = [
    # errors
    "InvestingIDsError",
    # core helpers
    "normalize_ticker",
    "slugify_segment",
    "validate_canonical_id",
    "parse_quarter_label",
    # canonical constructors (preferred / explicit)
    "make_company_id",
    "make_sector_id",
    "make_macro_id",
    "make_ai_adoption_id",
    "make_pattern_id",
    "make_risk_id",
    "make_quarter_event_id",
    "make_earnings_event_id",
    "make_filing_event_id",
    "make_news_event_id",
    "make_catalyst_event_id",
    "make_thesis_id",
    # compatibility aliases (short names used in earlier scaffolding)
    "sanitize_slug",
    "sanitize_ticker",
    "company_id",
    "sector_id",
    "macro_id",
    "ai_adoption_id",
    "pattern_id",
    "risk_id",
    "company_quarter_id",
    "company_earnings_id",
    "company_filing_id",
    "company_news_id",
    "company_catalyst_id",
    "thesis_id",
    # inspectors
    "is_company_id",
    "is_thesis_id",
    "is_company_event_id",
    # convenience bundle
    "IDBundle",
]

# ---------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------


class InvestingIDsError(ValueError):
    """Raised when canonical investing ID generation/validation fails."""


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

_ALLOWED_THESIS_MODES = {
    "long",
    "short",
    "swing_short",
    "catalyst_long",
    "neutral_watch",
}

# Broad syntax-level canonical ID check.
# Requires root segment to start lowercase alpha and at least one slash segment after.
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
    - converts spaces/slashes/backslashes to underscores
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
        raise InvestingIDsError("Segment is empty after normalization")
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
        raise InvestingIDsError("ticker is required")

    t = str(ticker).strip().upper()
    t = re.sub(r"\s+", "", t)

    if not t:
        raise InvestingIDsError("ticker is empty")

    if not _TICKER_RE.match(t):
        raise InvestingIDsError(f"Invalid ticker format: {ticker!r}")
    return t


def validate_canonical_id(canonical_id: str) -> str:
    """
    Broad validation for canonical IDs (syntax-level).
    Constructors provide stronger semantic validation.
    """
    if not isinstance(canonical_id, str) or not canonical_id.strip():
        raise InvestingIDsError("canonical_id must be a non-empty string")

    cid = canonical_id.strip()
    if not _CANONICAL_ID_RE.match(cid):
        raise InvestingIDsError(f"Invalid canonical ID syntax: {cid!r}")
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
        raise InvestingIDsError(f"Invalid date format (expected YYYY-MM-DD): {value!r}")
    return s


def parse_quarter_label(label: Any) -> tuple[int, int]:
    """
    Parse 'YYYY-Q#' (e.g. '2026-Q1') -> (2026, 1)
    """
    s = str(label).strip().upper()
    m = _QUARTER_LABEL_RE.match(s)
    if not m:
        raise InvestingIDsError(f"Invalid quarter label (expected YYYY-Q#): {label!r}")
    return int(m.group("year")), int(m.group("q"))


def _quarter_label(year: int, quarter: int) -> str:
    y = int(year)
    q = int(quarter)
    if y < 1900 or y > 3000:
        raise InvestingIDsError(f"Invalid year for quarter label: {year!r}")
    if q not in (1, 2, 3, 4):
        raise InvestingIDsError(f"Quarter must be 1..4, got {quarter!r}")
    return f"{y}-Q{q}"


# ---------------------------------------------------------------------
# Canonical constructors (preferred names)
# ---------------------------------------------------------------------
def make_company_id(ticker: Any) -> str:
    """company/<ticker>  e.g. company/AHT.L"""
    t = normalize_ticker(ticker)
    return validate_canonical_id(f"company/{t}")


def make_sector_id(sector_name: Any) -> str:
    """sector/<sector_name>  e.g. sector/industrial_equipment_rental"""
    seg = slugify_segment(sector_name)
    return validate_canonical_id(f"sector/{seg}")


def make_macro_id(regime: Any) -> str:
    """macro/<regime>  e.g. macro/uk_rates_high_real"""
    seg = slugify_segment(regime)
    return validate_canonical_id(f"macro/{seg}")


def make_ai_adoption_id(theme_or_sector: Any) -> str:
    """ai_adoption/<theme_or_sector>  e.g. ai_adoption/back_office_automation"""
    seg = slugify_segment(theme_or_sector)
    return validate_canonical_id(f"ai_adoption/{seg}")


def make_pattern_id(pattern_name: Any) -> str:
    """pattern/<pattern_name>  e.g. pattern/debt_wall_stress"""
    seg = slugify_segment(pattern_name)
    return validate_canonical_id(f"pattern/{seg}")


def make_risk_id(portfolio_or_policy_state: Any) -> str:
    """risk/<portfolio_or_policy_state>  e.g. risk/core_equities_policy_v1"""
    seg = slugify_segment(portfolio_or_policy_state)
    return validate_canonical_id(f"risk/{seg}")


def make_quarter_event_id(
    ticker: Any,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    *,
    quarter_label: Optional[str] = None,
) -> str:
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
            raise InvestingIDsError("Provide (year and quarter) or quarter_label")
        qlabel = _quarter_label(int(year), int(quarter))

    return validate_canonical_id(f"company/{t}/quarter/{qlabel}")


def make_earnings_event_id(ticker: Any, date_str: Any) -> str:
    """company/<ticker>/earnings/<YYYY-MM-DD>"""
    t = normalize_ticker(ticker)
    d = _normalize_date_str(date_str)
    return validate_canonical_id(f"company/{t}/earnings/{d}")


def make_filing_event_id(ticker: Any, date_str: Any, kind: Any) -> str:
    """
    company/<ticker>/filing/<YYYY-MM-DD>/<kind>

    kind examples:
      annual_report, half_year_results, trading_update, proxy, 10q, 10k
    """
    t = normalize_ticker(ticker)
    d = _normalize_date_str(date_str)
    k = slugify_segment(kind)
    return validate_canonical_id(f"company/{t}/filing/{d}/{k}")


def make_news_event_id(ticker: Any, event_id: Any) -> str:
    """company/<ticker>/news/<event_id>"""
    t = normalize_ticker(ticker)
    e = slugify_segment(event_id)
    return validate_canonical_id(f"company/{t}/news/{e}")


def make_catalyst_event_id(ticker: Any, event_id: Any) -> str:
    """company/<ticker>/catalyst/<event_id>"""
    t = normalize_ticker(ticker)
    e = slugify_segment(event_id)
    return validate_canonical_id(f"company/{t}/catalyst/{e}")


def make_thesis_id(ticker: Any, mode: Any, window: Any, *, strict_mode: bool = True) -> str:
    """
    thesis/<ticker>/<mode>/<window>

    Examples:
      thesis/AHT.L/long/2026q2_pre_earnings
      thesis/BARC.L/swing_short/2026q3_post_results
    """
    t = normalize_ticker(ticker)
    m = slugify_segment(mode)
    w = slugify_segment(window)

    if strict_mode and m not in _ALLOWED_THESIS_MODES:
        raise InvestingIDsError(
            f"Invalid thesis mode: {mode!r}. Allowed: {sorted(_ALLOWED_THESIS_MODES)}"
        )

    return validate_canonical_id(f"thesis/{t}/{m}/{w}")


# ---------------------------------------------------------------------
# Compatibility aliases (keep old scaffolding working)
# ---------------------------------------------------------------------
def sanitize_slug(value: Any) -> str:
    """Back-compat alias for older scaffolding."""
    return slugify_segment(value)


def sanitize_ticker(ticker: Any) -> str:
    """Back-compat alias for older scaffolding."""
    return normalize_ticker(ticker)


def company_id(ticker: Any) -> str:
    return make_company_id(ticker)


def sector_id(sector_name: Any) -> str:
    return make_sector_id(sector_name)


def macro_id(regime: Any) -> str:
    return make_macro_id(regime)


def ai_adoption_id(theme_or_sector: Any) -> str:
    return make_ai_adoption_id(theme_or_sector)


def pattern_id(pattern_name: Any) -> str:
    return make_pattern_id(pattern_name)


def risk_id(portfolio_or_policy_state: Any) -> str:
    return make_risk_id(portfolio_or_policy_state)


def company_quarter_id(ticker: Any, year: int, quarter: int) -> str:
    return make_quarter_event_id(ticker, year=year, quarter=quarter)


def company_earnings_id(ticker: Any, ymd: Any) -> str:
    return make_earnings_event_id(ticker, ymd)


def company_filing_id(ticker: Any, ymd: Any, kind: Any) -> str:
    return make_filing_event_id(ticker, ymd, kind)


def company_news_id(ticker: Any, event_id: Any) -> str:
    return make_news_event_id(ticker, event_id)


def company_catalyst_id(ticker: Any, event_id: Any) -> str:
    return make_catalyst_event_id(ticker, event_id)


def thesis_id(ticker: Any, mode: Any, window: Any) -> str:
    return make_thesis_id(ticker, mode, window, strict_mode=False)


# ---------------------------------------------------------------------
# Inspectors
# ---------------------------------------------------------------------
def is_company_id(canonical_id: str) -> bool:
    try:
        cid = validate_canonical_id(canonical_id)
    except InvestingIDsError:
        return False
    parts = cid.split("/")
    return len(parts) == 2 and parts[0] == "company"


def is_thesis_id(canonical_id: str) -> bool:
    try:
        cid = validate_canonical_id(canonical_id)
    except InvestingIDsError:
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
    except InvestingIDsError:
        return False
    parts = cid.split("/")
    return (
        len(parts) >= 4
        and parts[0] == "company"
        and parts[2] in {"quarter", "earnings", "filing", "news", "catalyst"}
    )


# ---------------------------------------------------------------------
# Convenience bundle
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class IDBundle:
    ticker: str

    def company(self) -> str:
        return make_company_id(self.ticker)

    def quarter(self, year: int, quarter: int) -> str:
        return make_quarter_event_id(self.ticker, year=year, quarter=quarter)

    def quarter_from_label(self, quarter_label: str) -> str:
        return make_quarter_event_id(self.ticker, quarter_label=quarter_label)

    def earnings(self, ymd: Any) -> str:
        return make_earnings_event_id(self.ticker, ymd)

    def filing(self, ymd: Any, kind: Any) -> str:
        return make_filing_event_id(self.ticker, ymd, kind)

    def news(self, event_id: Any) -> str:
        return make_news_event_id(self.ticker, event_id)

    def catalyst(self, event_id: Any) -> str:
        return make_catalyst_event_id(self.ticker, event_id)

    def thesis(self, mode: Any, window: Any, *, strict_mode: bool = False) -> str:
        return make_thesis_id(self.ticker, mode, window, strict_mode=strict_mode)