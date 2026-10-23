"""H4-v1: filtro de funding sobre una estrategia base (pre-registro H4 §4).

Para cada entrada que la base generaría al cierre t con dirección D:
f = media de las `count` últimas tasas liquidadas con calc_time < t, normalizadas a 8 h.
Largo con f >= +umbral o corto con f <= −umbral: la entrada se descarta ("filtrada").
Con menos de `count` liquidaciones previas no se filtra (ACLARACIONES §7).
"""

from __future__ import annotations

import bisect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from trading.backtest.model import (
    Book,
    Decisions,
    EntryIntent,
    ExitReason,
    FundingEvent,
    Strategy,
)
from trading.risk import Side


@dataclass(frozen=True, slots=True)
class H4Params:
    threshold_8h: float = 0.0005  # 0.05% por 8 h
    count: int = 3


@dataclass(frozen=True, slots=True)
class FilteredEntry:
    time: datetime
    symbol: str
    side: Side
    funding_8h: float


def mean_funding_before(
    events: Sequence[FundingEvent], moment: datetime, count: int
) -> float | None:
    """Media de las `count` últimas tasas normalizadas a 8 h con calc_time < moment."""
    times = [e.time for e in events]
    position = bisect.bisect_left(times, moment)
    if position < count:
        return None
    window = events[position - count : position]
    return sum(e.rate_8h for e in window) / count


def blocks(side: Side, funding_8h: float | None, params: H4Params) -> bool:
    if funding_8h is None:
        return False
    if side is Side.LONG:
        return funding_8h >= params.threshold_8h
    return funding_8h <= -params.threshold_8h


@dataclass
class FundingFilter:
    base: Strategy
    funding: Mapping[str, Sequence[FundingEvent]]
    params: H4Params = field(default_factory=H4Params)
    strategy_id: str = ""
    filtered: list[FilteredEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.strategy_id:
            self.strategy_id = f"H4-{self.base.strategy_id}"

    def on_close(self, close_time: datetime, book: Book) -> Decisions:
        decisions = self.base.on_close(close_time, book)
        kept: list[EntryIntent] = []
        for intent in decisions.entries:
            value = mean_funding_before(
                self.funding.get(intent.symbol, ()), close_time, self.params.count
            )
            if value is not None and blocks(intent.side, value, self.params):
                self.filtered.append(FilteredEntry(close_time, intent.symbol, intent.side, value))
            else:
                kept.append(intent)
        return Decisions(exits=decisions.exits, entries=tuple(kept))

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None:
        self.base.on_exit(symbol, side, reason)
