"""Reglas H1, H2 y H4 sobre series construidas a mano, y prueba anti look-ahead."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal

from synthetic import DAY, FOUR_HOURS, START, flat_bars, market, random_walk, series_from
from trading.backtest.engine import BacktestConfig, run_backtest
from trading.backtest.metrics import expectancy
from trading.backtest.model import (
    Book,
    Decisions,
    EntryIntent,
    ExitReason,
    FundingEvent,
    SignalOutcome,
)
from trading.data.universe import Ranked, UniverseSnapshot
from trading.risk import Side, load_plan_limits_f7_f8
from trading.signals.h1 import H1Params, H1Strategy
from trading.signals.h2 import H2Params, H2Strategy, IndicatorCache
from trading.signals.h4 import FundingFilter, H4Params, blocks, mean_funding_before

LIMITS = replace(load_plan_limits_f7_f8(), short_enabled_strategies=frozenset({"H1", "H2"}))


@dataclass
class FakeBook:
    positions: Mapping[str, Side] = field(default_factory=dict)


# --- H1 -----------------------------------------------------------------------------------------


def _h1(closes: list[float]) -> H1Strategy:
    bars = [(c, c + 1, c - 1, c) for c in closes]
    return H1Strategy(series_from("BTCUSDT", bars), H1Params(lookback=2, atr_period=2))


def test_h1_waits_for_warmup_then_follows_the_sign() -> None:
    strategy = _h1([100, 101, 102, 103, 102, 101, 100])
    close = lambda i: START + (i + 1) * DAY  # noqa: E731 - cierre de la vela i
    assert strategy.on_close(close(1), FakeBook()) == Decisions()  # sin ATR(2) ni retorno
    decision = strategy.on_close(close(2), FakeBook())
    assert decision.entries[0].side is Side.LONG
    assert decision.entries[0].stop_distance == 2.0 * strategy.atr[2]  # type: ignore[operator]
    held = FakeBook({"BTCUSDT": Side.LONG})
    assert strategy.on_close(close(3), held) == Decisions()
    # Rentabilidad de 2 días negativa en la vela 5: sale e invierte en la misma apertura.
    flip = strategy.on_close(close(5), held)
    assert flip.exits == ("BTCUSDT",)
    assert flip.entries[0].side is Side.SHORT


def test_h1_zero_return_keeps_the_previous_signal() -> None:
    strategy = _h1([100, 101, 102, 101, 102])
    close = lambda i: START + (i + 1) * DAY  # noqa: E731
    strategy.on_close(close(2), FakeBook())
    assert strategy.last_signal == 1
    decision = strategy.on_close(close(4), FakeBook({"BTCUSDT": Side.LONG}))  # 102/102 - 1 = 0
    assert strategy.last_signal == 1
    assert decision == Decisions()
    assert strategy.on_close(START + 30 * DAY, FakeBook()) == Decisions()  # sin vela


def test_h1_after_a_stop_waits_for_the_sign_to_change() -> None:
    strategy = _h1([100, 101, 102, 103, 104, 103, 102])
    close = lambda i: START + (i + 1) * DAY  # noqa: E731
    strategy.on_exit("BTCUSDT", Side.LONG, ExitReason.STOP)
    assert strategy.on_close(close(3), FakeBook()) == Decisions()  # sigue largo: bloqueado
    decision = strategy.on_close(close(6), FakeBook())  # ya es corto
    assert decision.entries[0].side is Side.SHORT
    assert strategy.stopped_side is None
    strategy.on_exit("BTCUSDT", Side.SHORT, ExitReason.SIGNAL)
    assert strategy.stopped_side is None


# --- H2 -----------------------------------------------------------------------------------------


def _universe(*symbols: str, date: datetime = START) -> list[UniverseSnapshot]:
    ranked = tuple(Ranked(s, 1e9 - i, START) for i, s in enumerate(symbols))
    return [UniverseSnapshot(date=date, members=symbols, ranking=ranked)]


def _breakout_series(direction: int = 1) -> list[tuple[float, float, float, float]]:
    """Calma, luego volatilidad creciente y una ruptura en la vela 30."""
    bars = [(100.0, 100.5, 99.5, 100.0)] * 25
    bars += [(100.0, 101.5, 98.5, 100.0)] * 5
    breakout = 103.0 if direction > 0 else 97.0
    bars.append((100.0, max(breakout, 101.0), min(breakout, 99.0), breakout))
    bars += [(breakout, breakout + 0.5, breakout - 0.5, breakout)] * 5
    return bars


PARAMS = H2Params(channel=10, exit_channel=5, atr_short=3, atr_long=20, atr_multiple=2.0)


def test_h2_detects_a_new_breakout_with_expanding_volatility() -> None:
    for direction, side in ((1, Side.LONG), (-1, Side.SHORT)):
        series = series_from("SOLUSDT", _breakout_series(direction), step=FOUR_HOURS)
        strategy = H2Strategy({"SOLUSDT": series}, _universe("SOLUSDT"), PARAMS)
        at = lambda i: START + (i + 1) * FOUR_HOURS  # noqa: E731
        assert strategy.on_close(at(29), FakeBook()) == Decisions()
        decision = strategy.on_close(at(30), FakeBook())
        assert [(e.symbol, e.side) for e in decision.entries] == [("SOLUSDT", side)]
        # La vela siguiente sigue fuera del canal, pero ya no es una ruptura nueva.
        assert strategy.on_close(at(31), FakeBook()).entries == ()


def test_h2_requires_the_volatility_filter_and_the_universe() -> None:
    calm = [(100.0, 100.5, 99.5, 100.0)] * 30 + [(100.0, 100.6, 99.9, 100.55)]
    series = series_from("SOLUSDT", calm, step=FOUR_HOURS)
    strategy = H2Strategy({"SOLUSDT": series}, _universe("SOLUSDT"), PARAMS)
    assert strategy.on_close(START + 31 * FOUR_HOURS, FakeBook()).entries == ()
    breakout = series_from("SOLUSDT", _breakout_series(), step=FOUR_HOURS)
    outside = H2Strategy({"SOLUSDT": breakout}, _universe("BTCUSDT"), PARAMS)
    assert outside.on_close(START + 31 * FOUR_HOURS, FakeBook()).entries == ()
    late = _universe("SOLUSDT", date=START + 100 * FOUR_HOURS)
    assert H2Strategy({"SOLUSDT": breakout}, late, PARAMS).snapshot_at(START) is None


def test_h2_exits_on_the_opposite_channel() -> None:
    bars = [*_breakout_series(), (103.0, 103.0, 95.0, 96.0)]
    series = series_from("SOLUSDT", bars, step=FOUR_HOURS)
    strategy = H2Strategy({"SOLUSDT": series}, _universe("SOLUSDT"), PARAMS, IndicatorCache())
    exit_close = START + len(bars) * FOUR_HOURS
    assert strategy.on_close(exit_close, FakeBook({"SOLUSDT": Side.LONG})).exits == ("SOLUSDT",)
    assert strategy.on_close(exit_close, FakeBook({"SOLUSDT": Side.SHORT})).exits == ()
    up = [(103.0, 110.0, 103.0, 109.0)]
    short_series = series_from("SOLUSDT", _breakout_series(-1)[:-1] + up, step=FOUR_HOURS)
    short = H2Strategy({"SOLUSDT": short_series}, _universe("SOLUSDT"), PARAMS)
    closing = START + 36 * FOUR_HOURS
    assert short.on_close(closing, FakeBook({"SOLUSDT": Side.SHORT})).exits == ("SOLUSDT",)
    strategy.on_exit("SOLUSDT", Side.LONG, ExitReason.STOP)


def test_indicator_cache_rejects_unknown_kinds() -> None:
    import pytest

    series = series_from("SOLUSDT", flat_bars(10.0, 5))
    with pytest.raises(ValueError, match="desconocido"):
        IndicatorCache().get(series, "rsi", 14)


# --- H4 -----------------------------------------------------------------------------------------


def _events(rates: list[float], hours: int = 8) -> tuple[FundingEvent, ...]:
    return tuple(
        FundingEvent(START + i * timedelta(hours=hours), r, hours) for i, r in enumerate(rates)
    )


def test_h4_mean_uses_only_settled_funding_before_t() -> None:
    events = _events([0.0001, 0.0004, 0.0007, 0.0100])
    at_16h = START + timedelta(hours=16)
    assert mean_funding_before(events, at_16h, 2) == (0.0001 + 0.0004) / 2  # 16:00 excluida
    assert mean_funding_before(events, at_16h, 3) is None
    hourly = _events([0.0001] * 4, hours=1)
    assert mean_funding_before(hourly, START + timedelta(hours=4), 3) == 0.0008  # x 8 / 1


def test_h4_blocks_by_direction_and_threshold() -> None:
    params = H4Params()
    assert blocks(Side.LONG, 0.0005, params)
    assert not blocks(Side.LONG, 0.00049, params)
    assert blocks(Side.SHORT, -0.0005, params)
    assert not blocks(Side.SHORT, 0.0010, params)
    assert not blocks(Side.LONG, None, params)


@dataclass
class _Always:
    side: Side
    strategy_id: str = "BASE"
    exits: list[ExitReason] = field(default_factory=list)

    def on_close(self, close_time: datetime, book: Book) -> Decisions:
        return Decisions(exits=("X",), entries=(EntryIntent("BTCUSDT", self.side, 1.0, 0),))

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None:
        self.exits.append(reason)


def test_h4_filter_drops_crowded_entries_and_keeps_exits() -> None:
    funding = {"BTCUSDT": _events([0.0006, 0.0006, 0.0006])}
    after = START + timedelta(days=1)
    base = _Always(Side.LONG)
    long_filter = FundingFilter(base, funding)
    assert long_filter.strategy_id == "H4-BASE"
    decision = long_filter.on_close(after, FakeBook())
    assert decision.entries == ()
    assert decision.exits == ("X",)
    assert long_filter.filtered[0].funding_8h == 0.0006
    short_filter = FundingFilter(_Always(Side.SHORT), funding, strategy_id="H4-test")
    assert len(short_filter.on_close(after, FakeBook()).entries) == 1
    long_filter.on_exit("BTCUSDT", Side.LONG, ExitReason.STOP)
    assert base.exits == [ExitReason.STOP]


# --- anti look-ahead ------------------------------------------------------------------------------


def _h2_run(bars_by_symbol: dict[str, list[tuple[float, float, float, float]]]):
    series = {s: series_from(s, b, step=FOUR_HOURS) for s, b in bars_by_symbol.items()}
    data = market(*series.values())
    strategy = H2Strategy(series, _universe(*series), H2Params(20, 8, 5, 30, 2.0))
    config = BacktestConfig(limits=LIMITS, start=data.start, end=data.end)
    return run_backtest(strategy, data, config)


def test_changing_the_future_never_changes_past_decisions() -> None:
    bars = {f"A{i}USDT": random_walk(600, seed=i, start_price=50 + i) for i in range(4)}
    original = _h2_run(bars)
    cut = 400
    altered = {
        s: b[:cut] + [(o * 1.7, h * 1.9, lo * 1.5, c * 1.8) for o, h, lo, c in b[cut:]]
        for s, b in bars.items()
    }
    changed = _h2_run(altered)
    limit = START + cut * FOUR_HOURS
    before = [s for s in original.signals if s.time < limit]
    assert before
    assert before == [s for s in changed.signals if s.time < limit]
    closed = [t for t in original.trades if t.exit_time <= limit]
    assert closed == [t for t in changed.trades if t.exit_time <= limit]


@dataclass
class _NextBar:
    """Juguete: entra en la dirección de la última vela y sale a la apertura siguiente."""

    series_symbol: str
    closes: tuple[float, ...]
    opens: tuple[float, ...]
    strategy_id: str = "H2"

    def on_close(self, close_time: datetime, book: Book) -> Decisions:
        index = int((close_time - START) / DAY) - 1
        if self.series_symbol in book.positions:
            return Decisions(exits=(self.series_symbol,))
        move = self.closes[index] - self.opens[index]
        side = Side.LONG if move > 0 else Side.SHORT
        return Decisions(entries=(EntryIntent(self.series_symbol, side, 6.0, 0),))

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None:
        return None


def test_one_bar_delay_degrades_a_short_lived_edge() -> None:
    import random

    rng = random.Random(7)
    bars, price, move = [], 100.0, 0.0
    for _ in range(400):
        # Cada vela repite el signo de la anterior y luego revierte: ventaja de una sola vela.
        step = (1.5 if move >= 0 else -1.5) if rng.random() < 0.8 else rng.choice([-1.5, 1.5])
        opened, closed = price, price + step
        bars.append((opened, max(opened, closed) + 0.2, min(opened, closed) - 0.2, closed))
        move, price = step, closed if abs(closed - 100) < 20 else 100.0
    series = series_from("BTCUSDT", bars)
    data = market(series)
    toy = lambda: _NextBar("BTCUSDT", series.close, series.open)  # noqa: E731
    config = BacktestConfig(limits=LIMITS, start=data.start, end=data.end)
    normal = run_backtest(toy(), data, config)
    delayed = run_backtest(toy(), data, replace(config, delay_bars=1))
    r_normal = [float(t.r_multiple) for t in normal.trades]
    r_delayed = [float(t.r_multiple) for t in delayed.trades]
    assert expectancy(r_normal) > 0
    assert expectancy(r_delayed) < expectancy(r_normal)
    assert all(s.outcome is not SignalOutcome.FILTERED for s in normal.signals)
    assert Decimal(0) < normal.final_equity
