"""Reporte fiscal: solo operaciones reales, fecha de CDMX, tipo de cambio y CSV."""

import csv
import io
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from factories import make_trade
from trading.audit import TradingMode
from trading.reporting import (
    MissingFxRateError,
    fiscal_date,
    fx_rate_for,
    tax_rows,
    tax_totals,
    to_csv,
)
from trading.reporting.tax import CSV_HEADER

RATES = {date(2026, 1, 2): Decimal("18.70"), date(2026, 1, 5): Decimal("18.65")}


def test_fiscal_date_uses_mexico_city_time() -> None:
    late_utc = datetime(2026, 1, 1, 3, 0, tzinfo=UTC)  # 31-dic-2025 21:00 en CDMX
    assert fiscal_date(late_utc) == date(2025, 12, 31)
    trade = make_trade(opened_at=late_utc - timedelta(hours=1), closed_at=late_utc)
    rates = {date(2025, 12, 31): Decimal("18.00")}
    assert len(tax_rows([trade], rates, 2025)) == 1
    assert tax_rows([trade], rates, 2026) == []


def test_fx_uses_last_published_rate() -> None:
    sunday = date(2026, 1, 4)
    assert fx_rate_for(sunday, RATES) == (date(2026, 1, 2), Decimal("18.70"))
    assert fx_rate_for(date(2026, 1, 5), RATES) == (date(2026, 1, 5), Decimal("18.65"))
    with pytest.raises(MissingFxRateError):
        fx_rate_for(date(2026, 1, 20), RATES)
    with pytest.raises(MissingFxRateError):
        fx_rate_for(sunday, RATES, max_lookback_days=1)
    with pytest.raises(ValueError, match="no positivo"):
        fx_rate_for(date(2026, 1, 2), {date(2026, 1, 2): Decimal(0)})


def test_only_live_trades_are_reported() -> None:
    trades = [
        make_trade(trade_id="live"),
        make_trade(trade_id="sombra", mode=TradingMode.SHADOW),
        make_trade(trade_id="bt", mode=TradingMode.BACKTEST),
    ]
    rows = tax_rows(trades, RATES, 2026)
    assert [r.trade_id for r in rows] == ["live"]


def test_row_amounts_and_rounding() -> None:
    trade = make_trade(fees=Decimal("0.605"), funding=Decimal("0.2"))  # 0.605 -> 0.60 (par)
    [row] = tax_rows([trade], RATES, 2026)
    assert row.fiscal_date == date(2026, 1, 5)
    assert (row.gross_pnl_usd, row.fees_usd, row.funding_usd) == (
        Decimal("12.00"),
        Decimal("0.60"),
        Decimal("0.20"),
    )
    assert row.net_pnl_usd == Decimal("11.20")
    assert row.fx_rate == Decimal("18.65")
    assert row.net_pnl_mxn == Decimal("208.88")  # 11.20 x 18.65 = 208.88


def test_totals_and_csv() -> None:
    loser = make_trade(
        trade_id="t2",
        exit_price=Decimal(59400),
        expected_exit_price=Decimal(59400),
        closed_at=make_trade().closed_at + timedelta(hours=1),
    )
    rows = tax_rows([loser, make_trade()], RATES, 2026)
    totals = tax_totals(rows)
    assert totals.trades == 2
    assert totals.gains_usd == Decimal("11.20")
    assert totals.losses_usd == Decimal("-6.80")
    assert totals.net_usd == Decimal("4.40")
    assert totals.net_mxn == totals.gains_mxn + totals.losses_mxn
    assert totals.fees_usd == Decimal("1.20")

    parsed = list(csv.reader(io.StringIO(to_csv(rows))))
    assert tuple(parsed[0]) == CSV_HEADER
    assert [line[0] for line in parsed[1:]] == ["t1", "t2"]
    assert parsed[1][CSV_HEADER.index("pnl_neto_mxn")] == "208.88"
    assert parsed[1][CSV_HEADER.index("cierre_utc")] == "2026-01-05T20:00:00+00:00"


@given(
    st.lists(
        st.tuples(
            st.decimals(min_value=Decimal(50000), max_value=Decimal(70000), places=2),
            st.decimals(min_value=Decimal(0), max_value=Decimal(5), places=4),
        ),
        max_size=20,
    )
)
def test_totals_always_match_rows(cases: list[tuple[Decimal, Decimal]]) -> None:
    trades = [
        make_trade(
            trade_id=f"t{i}",
            exit_price=exit_price,
            expected_exit_price=exit_price,
            fees=fees,
            closed_at=make_trade().closed_at + timedelta(minutes=i),
        )
        for i, (exit_price, fees) in enumerate(cases)
    ]
    rows = tax_rows(trades, RATES, 2026)
    totals = tax_totals(rows)
    assert totals.net_usd == sum((r.net_pnl_usd for r in rows), Decimal(0))
    assert totals.net_mxn == sum((r.net_pnl_mxn for r in rows), Decimal(0))
    assert all(r.net_pnl_mxn == r.net_pnl_mxn.quantize(Decimal("0.01")) for r in rows)
