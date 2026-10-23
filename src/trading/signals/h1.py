"""H1-v1: momentum de series temporales diario en BTC (pre-registro H1 §4; ACLARACIONES §3.2).

señal_t = signo(C_t / C_{t−L} − 1); si es exactamente 0, la señal anterior.
- Con posición contraria a la señal: salida en la apertura siguiente y entrada en la nueva
  dirección (se invierte).
- Sin posición: entrada en la dirección de la señal, salvo tras un stop: entonces solo cuando
  la señal cambia de signo respecto a la posición detenida.
- Stop fijo a k × ATR(n) desde la entrada. Sin salida por tiempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading.backtest.model import Book, Decisions, EntryIntent, ExitReason, Series
from trading.features.indicators import lag_return, wilder_atr
from trading.risk import Side


@dataclass(frozen=True, slots=True)
class H1Params:
    lookback: int = 7  # L
    atr_period: int = 14  # n
    atr_multiple: float = 2.0  # k


class H1Strategy:
    def __init__(self, series: Series, params: H1Params, strategy_id: str = "H1") -> None:
        self.strategy_id = strategy_id
        self.series = series
        self.params = params
        self.returns = lag_return(series.close, params.lookback)
        self.atr = wilder_atr(series.high, series.low, series.close, params.atr_period)
        self.last_signal = 0
        self.stopped_side: Side | None = None

    def on_close(self, close_time: datetime, book: Book) -> Decisions:
        symbol = self.series.symbol
        index = self.series.bar_closing_at(close_time)
        if index is None:
            return Decisions()
        change, atr = self.returns[index], self.atr[index]
        if change is None or atr is None:
            return Decisions()
        if change > 0:
            self.last_signal = 1
        elif change < 0:
            self.last_signal = -1
        if self.last_signal == 0:
            return Decisions()
        side = Side.LONG if self.last_signal > 0 else Side.SHORT
        held = book.positions.get(symbol)
        entry = EntryIntent(symbol, side, self.params.atr_multiple * atr, priority=0)
        if held is side:
            return Decisions()
        if held is not None:
            return Decisions(exits=(symbol,), entries=(entry,))
        if self.stopped_side is side:
            return Decisions()
        self.stopped_side = None
        return Decisions(entries=(entry,))

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None:
        if reason is ExitReason.STOP:
            self.stopped_side = side
