from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def source() -> str:
    return APP.read_text()

def test_boardroom_currency_and_percent_formatters_exist() -> None:
    text = source()
    assert "function formatBoardroomEuro(value)" in text
    assert "function formatBoardroomPercent(value)" in text
    assert "€${number.toLocaleString" in text
    assert "minimumFractionDigits: 2" in text
    assert "formatBoardroomPercent(finance.grossMarginPct" in text

def test_boardroom_cash_and_revenue_use_euros() -> None:
    text = source()
    assert "formatBoardroomEuro(cash.onHand" in text
    assert "formatBoardroomEuro(sales.revenue" in text

def test_boardroom_metric_cards_are_compact() -> None:
    text = source()
    assert "aion-boardroom-compact-metric-card" in text
    assert "aion-boardroom-compact-metric-line" in text
    assert "installAionBoardroomCompactMetricStyles" in text
    assert "AION BOARDROOM COMPACT METRICS LOCK" in text


def test_boardroom_metric_cards_use_tight_dashboard_sizing() -> None:
    text = source()
    assert "min-height: 52px" in text
    assert "font-size: 21px" in text
    assert "gap: 8px" in text
    assert "min-height: 48px" in text


def test_operator_presence_outer_panel_is_not_oversized() -> None:
    text = source()
    assert "min-height: unset" in text
    assert "height: auto" in text
    assert "padding-bottom: 12px" in text
    assert "card-grid + *" in text
