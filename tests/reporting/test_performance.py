"""Rendimiento: métricas en R, drawdown, rachas y agrupaciones."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from factories import r_trade
from trading.reporting import rolling_expectancy, summarize, summarize_by


def test_empty_summary() -> None:
    summary = summarize([])
    assert summary.trades == 0
    assert summary.win_rate is None
    assert summary.expectancy_r is None
    assert summary.profit_factor is None
    assert summary.max_drawdown_r == 0
    assert summary.net_pnl == 0


def test_known_sequence() -> None:
    trades = [
        r_trade("a", 2, 1),
        r_trade("b", -1, 2),
        r_trade("c", -1, 3),
        r_trade("d", 1, 4),
        r_trade("e", 0, 5),
    ]
    s = summarize(reversed(trades))  # el orden de entrada no importa: se ordena por cierre
    assert s.trades == 5
    assert (s.wins, s.losses) == (2, 2)
    assert s.win_rate == Decimal("0.4")
    assert s.expectancy_r == Decimal("0.2")
    assert s.profit_factor == Decimal("1.5")
    assert s.avg_win_r == Decimal("1.5")
    assert s.avg_loss_r == Decimal(-1)
    assert s.max_drawdown_r == Decimal(2)
    assert s.max_losing_streak == 2
    assert s.net_pnl == Decimal(10)


def test_profit_factor_undefined_without_losses() -> None:
    assert summarize([r_trade("a", 1, 1), r_trade("b", 2, 2)]).profit_factor is None


def test_summarize_by_strategy() -> None:
    trades = [r_trade("a", 1, 1, strategy_id="H1"), r_trade("b", -1, 2, strategy_id="H2")]
    groups = summarize_by(trades, key=lambda t: t.strategy_id)
    assert list(groups) == ["H1", "H2"]
    assert groups["H1"].expectancy_r == 1
    assert groups["H2"].expectancy_r == -1


def test_rolling_expectancy() -> None:
    trades = [r_trade("a", 2, 1), r_trade("b", -1, 2), r_trade("c", 1, 3)]
    points = rolling_expectancy(trades, window=2)
    assert [p[1] for p in points] == [Decimal("0.5"), Decimal(0)]
    assert points[-1][0] == trades[-1].closed_at
    with pytest.raises(ValueError, match="window"):
        rolling_expectancy(trades, window=0)


@given(
    st.lists(
        st.decimals(min_value=Decimal(-3), max_value=Decimal(5), places=2), min_size=1, max_size=40
    )
)
def test_summary_invariants(r_values: list[Decimal]) -> None:
    trades = [r_trade(f"t{i}", r, i) for i, r in enumerate(r_values)]
    s = summarize(trades)
    assert s.trades == len(r_values)
    assert s.wins + s.losses <= s.trades
    assert s.net_pnl == sum((t.net_pnl for t in trades), Decimal(0))
    assert s.expectancy_r == sum(r_values, Decimal(0)) / len(r_values)
    assert s.max_drawdown_r >= 0
    assert s.max_losing_streak <= s.losses
