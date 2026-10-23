"""H2-v1: ruptura de canal de 4h con filtro de expansión de volatilidad (pre-registro H2 §4).

canal_alto_t = max(H_{t−N} … H_{t−1}); canal_bajo_t = min(L_{t−N} … L_{t−1})
salida_alta_t = max(H_{t−M} … H_{t−1}); salida_baja_t = min(L_{t−M} … L_{t−1})
filtro_t = ATR(corto)_t > ATR(largo)_t
Largo: C_t > canal_alto_t y C_{t−1} <= canal_alto_{t−1} y filtro; corto simétrico.
Salida del largo: C_t < salida_baja_t (del corto: C_t > salida_alta_t), o el stop.
Solo activos del universo vigente y sin posición; máximo una posición por activo.
"""

from __future__ import annotations

import bisect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from trading.backtest.model import Book, Decisions, EntryIntent, ExitReason, Series
from trading.data.universe import UniverseSnapshot
from trading.features.indicators import prior_max, prior_min, wilder_atr
from trading.risk import Side


@dataclass(frozen=True, slots=True)
class H2Params:
    channel: int = 60  # N
    exit_channel: int = 20  # M
    atr_short: int = 14
    atr_long: int = 100
    atr_multiple: float = 2.0  # k


@dataclass(frozen=True, slots=True)
class _Arrays:
    close: Sequence[float]
    channel_high: Sequence[float | None]
    channel_low: Sequence[float | None]
    exit_high: Sequence[float | None]
    exit_low: Sequence[float | None]
    atr_short: Sequence[float | None]
    atr_long: Sequence[float | None]


class IndicatorCache:
    """Indicadores por símbolo y parámetro, compartidos entre variantes de la rejilla."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str, int], list[float | None]] = {}

    def get(self, series: Series, kind: str, n: int) -> list[float | None]:
        key = (series.symbol, kind, n)
        if key not in self._data:
            match kind:
                case "max_high":
                    self._data[key] = prior_max(series.high, n)
                case "min_low":
                    self._data[key] = prior_min(series.low, n)
                case "atr":
                    self._data[key] = wilder_atr(series.high, series.low, series.close, n)
                case _:
                    raise ValueError(f"indicador desconocido: {kind}")
        return self._data[key]


class H2Strategy:
    def __init__(
        self,
        series: Mapping[str, Series],
        universe: Sequence[UniverseSnapshot],
        params: H2Params,
        cache: IndicatorCache | None = None,
        strategy_id: str = "H2",
    ) -> None:
        self.strategy_id = strategy_id
        self.series = series
        self.params = params
        self.universe = sorted(universe, key=lambda u: u.date)
        self._dates = [u.date for u in self.universe]
        cache = cache or IndicatorCache()
        self.arrays = {
            symbol: _Arrays(
                close=s.close,
                channel_high=cache.get(s, "max_high", params.channel),
                channel_low=cache.get(s, "min_low", params.channel),
                exit_high=cache.get(s, "max_high", params.exit_channel),
                exit_low=cache.get(s, "min_low", params.exit_channel),
                atr_short=cache.get(s, "atr", params.atr_short),
                atr_long=cache.get(s, "atr", params.atr_long),
            )
            for symbol, s in series.items()
        }

    def snapshot_at(self, moment: datetime) -> UniverseSnapshot | None:
        position = bisect.bisect_right(self._dates, moment) - 1
        return self.universe[position] if position >= 0 else None

    def on_close(self, close_time: datetime, book: Book) -> Decisions:
        exits = []
        for symbol, side in book.positions.items():
            index = self._index(symbol, close_time)
            if index is None:
                continue
            a = self.arrays[symbol]
            low, high = a.exit_low[index], a.exit_high[index]
            if (side is Side.LONG and low is not None and a.close[index] < low) or (
                side is Side.SHORT and high is not None and a.close[index] > high
            ):
                exits.append(symbol)

        entries = []
        snapshot = self.snapshot_at(close_time)
        if snapshot is not None:
            members = set(snapshot.members)
            ranked = [r.symbol for r in snapshot.ranking if r.symbol in members]
            for priority, symbol in enumerate(ranked):
                if symbol in book.positions:
                    continue
                intent = self._breakout(symbol, close_time, priority)
                if intent is not None:
                    entries.append(intent)
        return Decisions(exits=tuple(exits), entries=tuple(entries))

    def _breakout(self, symbol: str, close_time: datetime, priority: int) -> EntryIntent | None:
        index = self._index(symbol, close_time)
        if index is None or index < 1:
            return None
        a = self.arrays[symbol]
        hi, hi_prev = a.channel_high[index], a.channel_high[index - 1]
        lo, lo_prev = a.channel_low[index], a.channel_low[index - 1]
        short_atr, long_atr = a.atr_short[index], a.atr_long[index]
        if (
            hi is None
            or hi_prev is None
            or lo is None
            or lo_prev is None
            or short_atr is None
            or long_atr is None
            or short_atr <= long_atr
        ):
            return None
        close, previous = a.close[index], a.close[index - 1]
        distance = self.params.atr_multiple * short_atr
        if close > hi and previous <= hi_prev:
            return EntryIntent(symbol, Side.LONG, distance, priority)
        if close < lo and previous >= lo_prev:
            return EntryIntent(symbol, Side.SHORT, distance, priority)
        return None

    def _index(self, symbol: str, close_time: datetime) -> int | None:
        series = self.series.get(symbol)
        return None if series is None else series.bar_closing_at(close_time)

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None:
        """H2 no guarda estado: la condición de "nueva ruptura" ya impide reentrar."""
