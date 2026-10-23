"""Mercados sintéticos para probar el backtester sin datos reales."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from trading.backtest.model import (
    Book,
    Decisions,
    EntryIntent,
    ExitReason,
    FundingEvent,
    MarketData,
    Series,
    Valuation,
)
from trading.risk import Side

START = datetime(2020, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)
FOUR_HOURS = timedelta(hours=4)


def series_from(
    symbol: str,
    bars: Sequence[tuple[float, float, float, float]],
    *,
    start: datetime = START,
    step: timedelta = DAY,
) -> Series:
    """Serie a partir de tuplas (open, high, low, close)."""
    return Series(
        symbol=symbol,
        base_asset=symbol.removesuffix("USDT"),
        interval=step,
        times=tuple(start + i * step for i in range(len(bars))),
        open=tuple(b[0] for b in bars),
        high=tuple(b[1] for b in bars),
        low=tuple(b[2] for b in bars),
        close=tuple(b[3] for b in bars),
    )


def flat_bars(
    price: float, count: int, spread: float = 1.0
) -> list[tuple[float, float, float, float]]:
    return [(price, price + spread, price - spread, price)] * count


def random_walk(
    count: int, *, seed: int, start_price: float = 100.0, vol: float = 0.02
) -> list[tuple[float, float, float, float]]:
    rng = random.Random(seed)
    bars, price = [], start_price
    for _ in range(count):
        opened = price
        closed = max(opened * (1 + rng.gauss(0, vol)), 0.01)
        high = max(opened, closed) * (1 + abs(rng.gauss(0, vol / 2)))
        low = min(opened, closed) * (1 - abs(rng.gauss(0, vol / 2)))
        bars.append((round(opened, 4), round(high, 4), round(low, 4), round(closed, 4)))
        price = closed
    return bars


def market(
    *series: Series,
    funding: Mapping[str, tuple[FundingEvent, ...]] | None = None,
    end: datetime | None = None,
) -> MarketData:
    step = series[0].interval
    last = max(s.times[-1] for s in series) + step
    return MarketData(
        interval=step,
        series={s.symbol: s for s in series},
        funding=funding or {},
        valuation={s.symbol: Valuation(tuple(t + step for t in s.times), s.close) for s in series},
        start=min(s.times[0] for s in series),
        end=end or last,
    )


@dataclass
class Scripted:
    """Estrategia de prueba: órdenes fijadas por hora de cierre."""

    entries: dict[datetime, list[EntryIntent]] = field(default_factory=dict)
    exits: dict[datetime, list[str]] = field(default_factory=dict)
    strategy_id: str = "TEST"
    seen_exits: list[tuple[str, Side, ExitReason]] = field(default_factory=list)
    closes: list[datetime] = field(default_factory=list)

    def on_close(self, close_time: datetime, book: Book) -> Decisions:
        self.closes.append(close_time)
        return Decisions(
            exits=tuple(self.exits.get(close_time, [])),
            entries=tuple(self.entries.get(close_time, [])),
        )

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None:
        self.seen_exits.append((symbol, side, reason))
