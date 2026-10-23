"""Backtester por eventos: ejecución, costes, funding, paradas y registro de señales."""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from synthetic import DAY, FOUR_HOURS, START, Scripted, flat_bars, market, series_from
from trading.backtest.engine import BacktestConfig, CostConfig, run_backtest
from trading.backtest.model import EntryIntent, ExitReason, FundingEvent, SignalOutcome
from trading.risk import (
    CostModel,
    RiskLimits,
    Side,
    VetoReason,
    load_extended_limits_v1_propuesto,
    load_plan_limits_f7_f8,
    size_by_risk,
    trade_risk,
)
from trading.risk.models import RISK_DECIMAL_CONTEXT

LIMITS = load_plan_limits_f7_f8()
FEE = Decimal("0.0005")
SLIP = Decimal("0.0005")


def _limits(*strategies: str) -> RiskLimits:
    return replace(LIMITS, short_enabled_strategies=frozenset(strategies))


def _config(data, **changes) -> BacktestConfig:
    return replace(BacktestConfig(limits=LIMITS, start=data.start, end=data.end), **changes)


def _day(n: int) -> datetime:
    return START + n * DAY


def _long(distance: float = 5.0, symbol: str = "BTCUSDT") -> EntryIntent:
    return EntryIntent(symbol, Side.LONG, distance, priority=0)


def _bars(*custom: tuple[int, tuple[float, float, float, float]], count: int = 8):
    bars = flat_bars(100.0, count)
    for index, bar in custom:
        bars[index] = bar
    return bars


def _expected_quantity(price: Decimal, stop: Decimal, equity: Decimal = Decimal(1500)) -> Decimal:
    return size_by_risk(
        equity=equity,
        entry_price=price,
        stop_price=stop,
        risk_fraction=Decimal("0.005"),
        costs=CostModel(FEE, SLIP),
        max_notional=2 * equity,
    )


def test_long_entry_and_stop_with_costs() -> None:
    data = market(series_from("BTCUSDT", _bars((2, (100.0, 100.0, 90.0, 92.0)))))
    strategy = Scripted(entries={_day(1): [_long()]})
    result = run_backtest(strategy, data, _config(data))

    (trade,) = result.trades
    with localcontext(RISK_DECIMAL_CONTEXT):
        price = Decimal("100") * (1 + SLIP)
        stop = price - 5
        quantity = _expected_quantity(price, stop)
        fill = stop * (1 - 2 * SLIP)
        fees = quantity * price * FEE + quantity * fill * FEE
        pnl = quantity * (fill - price) - fees
    assert (trade.entry_price, trade.stop_price, trade.quantity) == (price, stop, quantity)
    assert trade.exit_reason is ExitReason.STOP
    assert trade.exit_price == fill
    assert trade.exit_time == _day(3)
    assert trade.fees == fees
    assert trade.pnl == pnl
    assert trade.planned_risk == trade_risk(quantity, price, stop, CostModel(FEE, SLIP))
    assert Decimal("-1.0") < trade.r_multiple < Decimal("-0.99")
    with localcontext(RISK_DECIMAL_CONTEXT):
        assert result.final_equity == Decimal(1500) + trade.pnl
    assert strategy.seen_exits == [("BTCUSDT", Side.LONG, ExitReason.STOP)]
    assert [s.outcome for s in result.signals] == [SignalOutcome.EXECUTED]


def test_gap_through_the_stop_fills_at_the_open() -> None:
    data = market(series_from("BTCUSDT", _bars((2, (90.0, 91.0, 85.0, 88.0)))))
    result = run_backtest(Scripted(entries={_day(1): [_long()]}), data, _config(data))
    assert result.trades[0].exit_price == Decimal(90) * (1 - 2 * SLIP)


def test_short_stop_and_rule_exit() -> None:
    bars = _bars((2, (100.0, 106.0, 99.0, 104.0)), (4, (100.0, 105.0, 99.0, 100.0)))
    data = market(series_from("BTCUSDT", bars))
    strategy = Scripted(
        entries={
            _day(1): [EntryIntent("BTCUSDT", Side.SHORT, 5.0, 0)],
            _day(3): [EntryIntent("BTCUSDT", Side.SHORT, 6.0, 0)],
        },
        exits={_day(5): ["BTCUSDT"]},
    )
    result = run_backtest(strategy, data, _config(data, limits=_limits("TEST")))
    first, second = result.trades
    assert first.exit_reason is ExitReason.STOP
    assert first.exit_price == (Decimal(100) * (1 - SLIP) + 5) * (1 + 2 * SLIP)
    assert second.exit_reason is ExitReason.SIGNAL
    assert second.exit_time == _day(5)
    assert second.exit_price == Decimal(100) * (1 + SLIP)


def test_funding_is_paid_only_while_holding() -> None:
    data = market(
        series_from("BTCUSDT", _bars()),
        funding={
            "BTCUSDT": tuple(
                FundingEvent(_day(1) + timedelta(hours=h), 0.001, 8) for h in (0, 8, 16, 24, 32)
            )
        },
    )
    strategy = Scripted(entries={_day(1): [_long()]}, exits={_day(2): ["BTCUSDT"]})
    (trade,) = run_backtest(strategy, data, _config(data)).trades
    # Se entra a las 00:00 del día 1 y se sale a las 00:00 del día 2: pagan 08:00, 16:00 y
    # la de la salida (00:00 del día 2); no la de la entrada ni la de las 08:00 del día 2.
    with localcontext(RISK_DECIMAL_CONTEXT):
        assert trade.funding == 3 * trade.quantity * Decimal(100) * Decimal("0.001")


def test_funding_stress_multiplies_only_payments() -> None:
    events = {
        "BTCUSDT": (
            FundingEvent(_day(1) + timedelta(hours=8), 0.001, 8),
            FundingEvent(_day(1) + timedelta(hours=16), -0.001, 8),
        )
    }
    data = market(series_from("BTCUSDT", _bars()), funding=events)
    strategy = Scripted(entries={_day(1): [_long()]}, exits={_day(2): ["BTCUSDT"]})
    stressed = CostConfig(scale=Decimal("1.5"))
    (trade,) = run_backtest(strategy, data, _config(data, costs=stressed)).trades
    with localcontext(RISK_DECIMAL_CONTEXT):
        paid = trade.quantity * Decimal(100) * Decimal("0.001")
        assert trade.funding == paid * Decimal("1.5") - paid


def test_delisted_symbol_is_closed_at_its_last_close() -> None:
    btc = series_from("BTCUSDT", flat_bars(100.0, 10))
    alt = series_from("ALTUSDT", flat_bars(10.0, 4, spread=0.1))
    data = market(btc, alt)
    strategy = Scripted(entries={_day(1): [_long(0.5, "ALTUSDT")]})
    (trade,) = run_backtest(strategy, data, _config(data)).trades
    assert trade.exit_reason is ExitReason.DELISTED
    assert trade.exit_time == _day(4)
    assert trade.exit_price == Decimal(10) * (1 - Decimal("0.0010"))


def test_open_positions_close_at_the_end_of_the_period() -> None:
    data = market(series_from("BTCUSDT", _bars()))
    (trade,) = run_backtest(Scripted(entries={_day(1): [_long()]}), data, _config(data)).trades
    assert trade.exit_reason is ExitReason.END_OF_PERIOD
    assert trade.exit_time == data.end


def test_hard_stop_flattens_and_halts() -> None:
    bars = flat_bars(100.0, 10, spread=0.1)
    bars[2] = (50.0, 51.0, 49.0, 50.0)
    data = market(series_from("BTCUSDT", bars))
    strategy = Scripted(entries={_day(1): [_long(0.5)], _day(5): [_long(0.5)]})
    result = run_backtest(strategy, data, _config(data))
    assert len(result.trades) == 1
    assert result.halted_at == _day(3)
    assert _day(5) not in strategy.closes  # tras el corte duro no se generan señales
    assert result.final_equity < Decimal(1200)


def test_vetoes_and_non_executable_signals_are_recorded() -> None:
    data = market(series_from("BTCUSDT", _bars()))
    strategy = Scripted(
        entries={
            _day(1): [EntryIntent("BTCUSDT", Side.SHORT, 5.0, 0)],
            _day(2): [_long(10.0)],  # orden de ≈USD 73: por debajo del mínimo de 100
            _day(3): [_long(200.0)],  # stop negativo
        }
    )
    signals = run_backtest(strategy, data, _config(data)).signals
    assert [(s.outcome, s.reasons) for s in signals] == [
        (SignalOutcome.VETOED, (VetoReason.SHORT_NOT_VALIDATED,)),
        (SignalOutcome.NOT_EXECUTABLE, (VetoReason.BELOW_MIN_NOTIONAL,)),
        (SignalOutcome.VETOED, (VetoReason.INVALID_STOP,)),
    ]


def test_delay_bars_execute_later() -> None:
    data = market(series_from("BTCUSDT", _bars()))
    strategy = Scripted(entries={_day(1): [_long()]})
    (trade,) = run_backtest(strategy, data, _config(data, delay_bars=1)).trades
    assert trade.entry_time == _day(2)
    with pytest.raises(ValueError, match="delay_bars"):
        run_backtest(strategy, data, _config(data, delay_bars=-1))


def test_deferred_entry_hours_for_c18() -> None:
    series = series_from("BTCUSDT", flat_bars(100.0, 12), step=FOUR_HOURS)
    data = market(series)
    eight = START + timedelta(hours=8)
    strategy = Scripted(entries={eight: [_long()]})
    config = _config(data, deferred_entry_hours={8: 16, 12: 16})
    (trade,) = run_backtest(strategy, data, config).trades
    assert trade.entry_time == START + timedelta(hours=16)


def test_missing_bar_at_execution_is_recorded() -> None:
    btc = series_from("BTCUSDT", flat_bars(100.0, 8))
    alt = series_from("ALTUSDT", flat_bars(10.0, 2, spread=0.1))
    data = market(btc, alt)
    strategy = Scripted(entries={_day(2): [_long(0.5, "ALTUSDT")]})
    (signal,) = run_backtest(strategy, data, _config(data)).signals
    assert signal.outcome is SignalOutcome.NO_BAR


def test_extended_rules_clip_alt_size_to_ten_percent() -> None:
    btc = series_from("BTCUSDT", flat_bars(100.0, 8))
    alt = series_from("ALTUSDT", flat_bars(10.0, 8, spread=0.1))
    data = market(btc, alt, funding={"ALTUSDT": (FundingEvent(START, 0.0001, 8),)})
    strategy = Scripted(entries={_day(1): [_long(0.2, "ALTUSDT")]})
    plain = run_backtest(strategy, data, _config(data)).trades[0]
    strategy = Scripted(entries={_day(1): [_long(0.2, "ALTUSDT")]})
    config = _config(
        data,
        extended=load_extended_limits_v1_propuesto(),
        betas_at=lambda _t: {"BTC": Decimal(1), "ALT": Decimal("1.5")},
    )
    clipped = run_backtest(strategy, data, config).trades[0]
    assert plain.quantity * plain.entry_price > Decimal(150)
    assert clipped.quantity * clipped.entry_price <= Decimal(150)


def test_extended_rules_veto_adverse_funding() -> None:
    events = {"BTCUSDT": (FundingEvent(START + timedelta(hours=16), 0.002, 8),)}
    data = market(series_from("BTCUSDT", _bars()), funding=events)
    config = _config(
        data,
        extended=load_extended_limits_v1_propuesto(),
        betas_at=lambda _t: {"BTC": Decimal(1)},
    )
    (signal,) = run_backtest(Scripted(entries={_day(1): [_long()]}), data, config).signals
    assert signal.reasons == (VetoReason.ADVERSE_FUNDING,)
