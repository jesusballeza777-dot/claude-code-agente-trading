"""Tipos del backtester: datos de mercado, órdenes, operaciones y resultados."""

from __future__ import annotations

import bisect
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from trading.risk import Side, VetoReason


class ExitReason(StrEnum):
    SIGNAL = "SEÑAL"
    STOP = "STOP"
    DELISTED = "DESLISTADO"
    END_OF_PERIOD = "FIN_DE_PERIODO"
    HARD_STOP = "CORTE_DURO"


class SignalOutcome(StrEnum):
    EXECUTED = "EJECUTADA"
    VETOED = "VETADA"
    NOT_EXECUTABLE = "NO_EJECUTABLE"  # tamaño 0 o por debajo del nocional mínimo (C-19)
    FILTERED = "FILTRADA"  # filtro H4
    NO_BAR = "SIN_VELA"  # no hubo vela para ejecutar


@dataclass(frozen=True, slots=True)
class Series:
    """Velas de un símbolo en un intervalo, ordenadas por hora de apertura."""

    symbol: str
    base_asset: str
    interval: timedelta
    times: tuple[datetime, ...]
    open: tuple[float, ...]
    high: tuple[float, ...]
    low: tuple[float, ...]
    close: tuple[float, ...]
    index: Mapping[datetime, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        sizes = {len(self.times), len(self.open), len(self.high), len(self.low), len(self.close)}
        if len(sizes) != 1:
            raise ValueError(f"{self.symbol}: columnas de distinta longitud")
        if any(b <= a for a, b in zip(self.times, self.times[1:], strict=False)):
            raise ValueError(f"{self.symbol}: velas desordenadas o duplicadas")
        if not self.index:
            object.__setattr__(self, "index", {t: i for i, t in enumerate(self.times)})

    def bar_closing_at(self, close_time: datetime) -> int | None:
        return self.index.get(close_time - self.interval)

    @property
    def last_close_time(self) -> datetime:
        return self.times[-1] + self.interval


@dataclass(frozen=True, slots=True)
class FundingEvent:
    time: datetime
    rate: float  # tasa de la liquidación (no normalizada)
    interval_hours: int

    @property
    def rate_8h(self) -> float:
        return self.rate * 8 / self.interval_hours


@dataclass(frozen=True, slots=True)
class Valuation:
    """Cierres de 4h para valorar el nocional en cada liquidación de funding (§4.3)."""

    close_times: tuple[datetime, ...]
    closes: tuple[float, ...]

    def at(self, moment: datetime) -> float | None:
        position = bisect.bisect_right(self.close_times, moment) - 1
        return self.closes[position] if position >= 0 else None


@dataclass(frozen=True, slots=True)
class MarketData:
    interval: timedelta
    series: Mapping[str, Series]
    funding: Mapping[str, tuple[FundingEvent, ...]]
    valuation: Mapping[str, Valuation]
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class EntryIntent:
    symbol: str
    side: Side
    stop_distance: float  # k × ATR en la vela de señal
    priority: int  # menor = primero


@dataclass(frozen=True, slots=True)
class Decisions:
    exits: tuple[str, ...] = ()
    entries: tuple[EntryIntent, ...] = ()


class Book(Protocol):
    """Lo que una estrategia puede ver de la cartera al cierre de una vela."""

    @property
    def positions(self) -> Mapping[str, Side]: ...


class Strategy(Protocol):
    strategy_id: str

    def on_close(self, close_time: datetime, book: Book) -> Decisions: ...

    def on_exit(self, symbol: str, side: Side, reason: ExitReason) -> None: ...


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    side: Side
    signal_time: datetime
    entry_time: datetime
    entry_price: Decimal
    stop_price: Decimal
    quantity: Decimal
    planned_risk: Decimal
    exit_time: datetime
    exit_price: Decimal
    exit_reason: ExitReason
    fees: Decimal
    funding: Decimal  # positivo = pagado
    pnl: Decimal  # neto de comisiones y funding

    @property
    def r_multiple(self) -> Decimal:
        return self.pnl / self.planned_risk


@dataclass(frozen=True, slots=True)
class SignalRecord:
    time: datetime
    symbol: str
    side: Side
    outcome: SignalOutcome
    reasons: tuple[VetoReason, ...] = ()
    note: str = ""


@dataclass(frozen=True, slots=True)
class BacktestResult:
    strategy_id: str
    trades: tuple[Trade, ...]
    signals: tuple[SignalRecord, ...]
    equity_curve: tuple[tuple[datetime, Decimal], ...]
    initial_capital: Decimal
    final_equity: Decimal
    halted_at: datetime | None
