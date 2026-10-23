"""Tipos de entrada del motor de riesgo.

Todo importe es Decimal y toda hora es consciente de zona horaria. Una entrada mal formada
(precio no positivo, hora sin zona, perpetuo sin términos de margen) lanza ValueError al
construirse: el flujo que la recibe no opera (fallo cerrado).
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from enum import StrEnum

# Contexto decimal fijo del motor: el resultado no depende de getcontext() del proceso.
RISK_DECIMAL_CONTEXT = Context(
    prec=34, rounding=ROUND_HALF_EVEN, traps=[InvalidOperation, DivisionByZero, Overflow]
)


def in_risk_context[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Ejecuta la función con el contexto decimal del motor."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with localcontext(RISK_DECIMAL_CONTEXT):
            return func(*args, **kwargs)

    return wrapper


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class MarketType(StrEnum):
    SPOT = "SPOT"
    PERPETUAL = "PERPETUAL"


class MarginMode(StrEnum):
    ISOLATED = "ISOLATED"
    CROSS = "CROSS"


@dataclass(frozen=True, slots=True)
class CostModel:
    """Costes estimados por lado, como fracción.

    `fee_rate` se aplica sobre el nocional y `slippage_rate` sobre el precio, en la entrada y
    en la salida por stop.
    """

    fee_rate: Decimal
    slippage_rate: Decimal

    def __post_init__(self) -> None:
        for name in ("fee_rate", "slippage_rate"):
            value = require_decimal(name, getattr(self, name))
            if not Decimal(0) <= value < Decimal(1):
                raise ValueError(f"{name} debe estar en [0, 1)")


@dataclass(frozen=True, slots=True)
class PerpetualTerms:
    """Condiciones de margen de una posición en perpetuo.

    `exchange_leverage` es el apalancamiento configurado en el exchange: fija el margen aislado
    (nocional / apalancamiento) y por tanto el precio de liquidación. No es el apalancamiento
    efectivo de la cuenta, que limita el motor. `maintenance_margin_rate` y `maintenance_amount`
    son los del tramo de margen del contrato para el nocional de la posición.
    """

    margin_mode: MarginMode
    exchange_leverage: Decimal
    maintenance_margin_rate: Decimal
    maintenance_amount: Decimal

    def __post_init__(self) -> None:
        if require_decimal("exchange_leverage", self.exchange_leverage) < 1:
            raise ValueError("exchange_leverage debe ser >= 1")
        mmr = require_decimal("maintenance_margin_rate", self.maintenance_margin_rate)
        if not Decimal(0) <= mmr < Decimal(1):
            raise ValueError("maintenance_margin_rate debe estar en [0, 1)")
        if require_decimal("maintenance_amount", self.maintenance_amount) < 0:
            raise ValueError("maintenance_amount no puede ser negativo")


@dataclass(frozen=True, slots=True)
class EntryProposal:
    """Propuesta de entrada que el motor aprueba o veta."""

    strategy_id: str
    symbol: str
    base_asset: str
    market: MarketType
    side: Side
    entry_price: Decimal
    stop_price: Decimal
    quantity: Decimal
    perpetual: PerpetualTerms | None = None

    def __post_init__(self) -> None:
        for name in ("strategy_id", "symbol", "base_asset"):
            require_name(name, getattr(self, name))
        require_positive("entry_price", self.entry_price)
        require_positive("stop_price", self.stop_price)
        require_decimal("quantity", self.quantity)
        if self.market is MarketType.PERPETUAL and self.perpetual is None:
            raise ValueError("una entrada en perpetuo necesita PerpetualTerms")
        if self.market is MarketType.SPOT and self.perpetual is not None:
            raise ValueError("una entrada en spot no lleva PerpetualTerms")

    @property
    def notional(self) -> Decimal:
        return abs(self.quantity) * self.entry_price


@dataclass(frozen=True, slots=True)
class OpenPosition:
    """Posición abierta, valorada a precio de marca.

    `risk_to_stop` es la pérdida adicional, con costes, si salta el stop desde el precio actual
    (0 si el stop ya protege beneficio).
    """

    symbol: str
    base_asset: str
    side: Side
    notional: Decimal
    risk_to_stop: Decimal

    def __post_init__(self) -> None:
        require_name("symbol", self.symbol)
        require_name("base_asset", self.base_asset)
        require_non_negative("notional", self.notional)
        require_non_negative("risk_to_stop", self.risk_to_stop)


@dataclass(frozen=True, slots=True)
class AccountState:
    """Estado de la cuenta. `equity` incluye el PnL no realizado y puede ser <= 0."""

    equity: Decimal
    peak_equity: Decimal
    day_start_equity: Decimal
    week_start_equity: Decimal
    open_positions: tuple[OpenPosition, ...] = ()
    trading_halted: bool = False

    def __post_init__(self) -> None:
        require_decimal("equity", self.equity)
        require_positive("peak_equity", self.peak_equity)
        require_positive("day_start_equity", self.day_start_equity)
        require_positive("week_start_equity", self.week_start_equity)

    @property
    def open_notional(self) -> Decimal:
        return sum((p.notional for p in self.open_positions), Decimal(0))

    @property
    def open_risk(self) -> Decimal:
        return sum((p.risk_to_stop for p in self.open_positions), Decimal(0))


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Marcas de tiempo de los datos en los que se apoya la propuesta."""

    symbol: str
    price_time: datetime
    last_bar_close_time: datetime
    bar_interval: timedelta

    def __post_init__(self) -> None:
        require_name("symbol", self.symbol)
        require_aware("price_time", self.price_time)
        require_aware("last_bar_close_time", self.last_bar_close_time)
        if self.bar_interval <= timedelta(0):
            raise ValueError("bar_interval debe ser positivo")


# --- validadores compartidos -----------------------------------------------------------------


def require_decimal(name: str, value: object) -> Decimal:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} debe ser Decimal, no {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"{name} debe ser finito")
    return value


def require_positive(name: str, value: object) -> Decimal:
    number = require_decimal(name, value)
    if number <= 0:
        raise ValueError(f"{name} debe ser positivo")
    return number


def require_non_negative(name: str, value: object) -> Decimal:
    number = require_decimal(name, value)
    if number < 0:
        raise ValueError(f"{name} no puede ser negativo")
    return number


def require_name(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} debe ser un texto no vacío y sin espacios en los extremos")
    return value


def require_aware(name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} debe ser datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} debe llevar zona horaria")
    return value
