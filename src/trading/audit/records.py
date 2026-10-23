"""Registros de auditoría: cada decisión y cada operación, tal como ocurrieron.

Son la fuente de todo lo que muestra la app (ADR-010): embudo de decisiones, rendimiento,
fichas de aprendizaje y reportes fiscales. Los registros son inmutables y se validan al
construirse; un registro incoherente (por ejemplo, una operación ejecutada que el motor
de riesgo había vetado) lanza ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from trading.risk.models import (
    Side,
    require_aware,
    require_decimal,
    require_name,
    require_non_negative,
    require_positive,
)


class Venue(StrEnum):
    BINANCE = "BINANCE"
    HYPERLIQUID = "HYPERLIQUID"
    KRAKEN = "KRAKEN"


class TradingMode(StrEnum):
    """Dónde ocurrió la operación. Solo LIVE entra en los reportes fiscales."""

    BACKTEST = "BACKTEST"
    SHADOW = "SHADOW"
    LIVE = "LIVE"


class DecisionAction(StrEnum):
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"
    HOLD = "HOLD"
    ABSTAIN = "ABSTAIN"


class ApprovalLevel(StrEnum):
    A = "A"
    B = "B"


class OwnerResponse(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"  # sin entrada que aprobar, vetada por el motor, o en sombra
    APPROVED = "APPROVED"  # nivel B aprobada
    REJECTED = "REJECTED"  # nivel B rechazada
    EXPIRED = "EXPIRED"  # nivel B caducada sin respuesta
    AUTO_EXECUTED = "AUTO_EXECUTED"  # nivel A sin veto en la ventana
    VETOED = "VETOED"  # nivel A vetada por el propietario


BLOCKING_RESPONSES = frozenset(
    {OwnerResponse.REJECTED, OwnerResponse.EXPIRED, OwnerResponse.VETOED}
)


class ExitReason(StrEnum):
    STOP = "STOP"
    SIGNAL = "SIGNAL"
    MANUAL = "MANUAL"
    KILL_SWITCH = "KILL_SWITCH"
    LIQUIDATION = "LIQUIDATION"


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Una decisión de Claude sobre una señal, con lo que pasó después.

    `counterfactual_r` es el resultado en R que habría tenido la señal si se hubiera
    ejecutado, medido en sombra. Solo existe para decisiones que no se ejecutaron.
    """

    decision_id: str
    decided_at: datetime
    strategy_id: str
    symbol: str
    action: DecisionAction
    rationale: str
    risk_vetoes: tuple[str, ...] = ()
    level: ApprovalLevel | None = None
    owner_response: OwnerResponse = OwnerResponse.NOT_REQUIRED
    trade_id: str | None = None
    counterfactual_r: Decimal | None = None

    def __post_init__(self) -> None:
        for name in ("decision_id", "strategy_id", "symbol"):
            require_name(name, getattr(self, name))
        require_aware("decided_at", self.decided_at)
        if self.counterfactual_r is not None:
            require_decimal("counterfactual_r", self.counterfactual_r)
        if self.trade_id is None:
            return
        require_name("trade_id", self.trade_id)
        if not self.is_entry:
            raise ValueError("solo una decisión de entrada abre una operación")
        if self.risk_vetoes:
            raise ValueError("una decisión vetada por el motor de riesgo no puede ejecutarse")
        if self.owner_response in BLOCKING_RESPONSES:
            raise ValueError(f"una decisión {self.owner_response} no puede ejecutarse")
        if self.counterfactual_r is not None:
            raise ValueError("una decisión ejecutada no tiene resultado contrafactual")

    @property
    def is_entry(self) -> bool:
        return self.action in (DecisionAction.ENTER_LONG, DecisionAction.ENTER_SHORT)

    @property
    def executed(self) -> bool:
        return self.trade_id is not None


@dataclass(frozen=True, slots=True)
class TradeRecord:
    """Una operación cerrada. Importes en USD (USDT/USDC se tratan 1:1, por validar).

    `planned_risk` es 1 R: la pérdida planificada hasta el stop, con costes, tal como la
    calculó el motor de riesgo al entrar. `funding` es positivo si la posición lo pagó y
    negativo si lo cobró.
    """

    trade_id: str
    venue: Venue
    mode: TradingMode
    strategy_id: str
    symbol: str
    base_asset: str
    side: Side
    opened_at: datetime
    closed_at: datetime
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    expected_entry_price: Decimal
    expected_exit_price: Decimal
    stop_price: Decimal
    planned_risk: Decimal
    fees: Decimal
    funding: Decimal
    exit_reason: ExitReason
    max_adverse_price: Decimal | None = None
    max_favorable_price: Decimal | None = None

    def __post_init__(self) -> None:
        for name in ("trade_id", "strategy_id", "symbol", "base_asset"):
            require_name(name, getattr(self, name))
        require_aware("opened_at", self.opened_at)
        require_aware("closed_at", self.closed_at)
        if self.closed_at < self.opened_at:
            raise ValueError("closed_at no puede ser anterior a opened_at")
        for name in (
            "quantity",
            "entry_price",
            "exit_price",
            "expected_entry_price",
            "expected_exit_price",
            "stop_price",
            "planned_risk",
        ):
            require_positive(name, getattr(self, name))
        require_non_negative("fees", self.fees)
        require_decimal("funding", self.funding)
        stop_below = self.stop_price < self.expected_entry_price
        if stop_below != (self.side is Side.LONG):
            raise ValueError("el stop está en el lado equivocado de la entrada")
        for name in ("max_adverse_price", "max_favorable_price"):
            value = getattr(self, name)
            if value is not None:
                require_positive(name, value)

    @property
    def direction(self) -> Decimal:
        return Decimal(1) if self.side is Side.LONG else Decimal(-1)

    @property
    def gross_pnl(self) -> Decimal:
        return self.direction * self.quantity * (self.exit_price - self.entry_price)

    @property
    def net_pnl(self) -> Decimal:
        return self.gross_pnl - self.fees - self.funding

    @property
    def r_multiple(self) -> Decimal:
        return self.net_pnl / self.planned_risk

    @property
    def entry_slippage_bps(self) -> Decimal:
        """Deslizamiento de entrada en puntos básicos; positivo = peor de lo esperado."""
        expected = self.expected_entry_price
        return self.direction * (self.entry_price - expected) / expected * 10_000

    @property
    def exit_slippage_bps(self) -> Decimal:
        """Deslizamiento de salida en puntos básicos; positivo = peor de lo esperado."""
        expected = self.expected_exit_price
        return self.direction * (expected - self.exit_price) / expected * 10_000

    @property
    def mae_r(self) -> Decimal | None:
        """Máxima excursión adversa en R (≤ 0)."""
        if self.max_adverse_price is None:
            return None
        move = self.direction * (self.max_adverse_price - self.entry_price)
        return min(move, Decimal(0)) * self.quantity / self.planned_risk

    @property
    def mfe_r(self) -> Decimal | None:
        """Máxima excursión favorable en R (≥ 0)."""
        if self.max_favorable_price is None:
            return None
        move = self.direction * (self.max_favorable_price - self.entry_price)
        return max(move, Decimal(0)) * self.quantity / self.planned_risk
