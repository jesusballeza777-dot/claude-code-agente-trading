"""Motor de riesgo: aprueba o veta una propuesta de entrada.

Código puro y determinista: sin red, sin reloj (la hora llega como argumento) y sin estado.
Evalúa todas las reglas y devuelve todos los vetos que apliquen, no solo el primero, para
que la auditoría vea el cuadro completo. Una propuesta se aprueba solo si no hay ningún veto.

Convención de límites exactos (ADR-007):
- Presupuestos (riesgo por operación, apalancamiento, pérdida diaria/semanal, exposición
  correlacionada): alcanzar exactamente el límite está permitido; superarlo se veta.
- Distancia a liquidación: exactamente `ratio x distancia al stop` está permitido.
- Drawdown: alcanzar exactamente el umbral activa la parada.
- Datos: una edad exactamente igual al máximo está permitida.
- Nocional mínimo: exactamente el mínimo está permitido.

Cada veto lleva un código estable (`VetoReason`), un detalle técnico y, cuando aplica, la cifra
observada y el límite, que `trading.risk.explain` convierte en un mensaje en español.
Las reglas ampliadas de ADR-013 (Propuesto) están en `trading.risk.extended`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from trading.risk.limits import RiskLimits
from trading.risk.liquidation import adverse_distance, isolated_liquidation_price
from trading.risk.models import (
    AccountState,
    CostModel,
    EntryProposal,
    LiquidationModel,
    MarginMode,
    MarketSnapshot,
    MarketType,
    Side,
    in_risk_context,
    require_aware,
)
from trading.risk.sizing import trade_risk


class VetoReason(StrEnum):
    TRADING_HALTED = "TRADING_HALTED"
    NON_POSITIVE_EQUITY = "NON_POSITIVE_EQUITY"
    DRAWDOWN_HALT = "DRAWDOWN_HALT"
    DRAWDOWN_HARD_STOP = "DRAWDOWN_HARD_STOP"
    MARKET_DATA_MISMATCH = "MARKET_DATA_MISMATCH"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    STALE_PRICE = "STALE_PRICE"
    STALE_BARS = "STALE_BARS"
    NON_POSITIVE_QUANTITY = "NON_POSITIVE_QUANTITY"
    INVALID_STOP = "INVALID_STOP"
    SHORT_ON_SPOT = "SHORT_ON_SPOT"
    SHORT_NOT_VALIDATED = "SHORT_NOT_VALIDATED"
    CROSS_MARGIN = "CROSS_MARGIN"
    RISK_PER_TRADE = "RISK_PER_TRADE"
    EFFECTIVE_LEVERAGE = "EFFECTIVE_LEVERAGE"
    LIQUIDATION_TOO_CLOSE = "LIQUIDATION_TOO_CLOSE"
    DAILY_LOSS = "DAILY_LOSS"
    WEEKLY_LOSS = "WEEKLY_LOSS"
    CORRELATED_EXPOSURE = "CORRELATED_EXPOSURE"
    BELOW_MIN_NOTIONAL = "BELOW_MIN_NOTIONAL"
    LIQUIDATION_MODEL_UNAVAILABLE = "LIQUIDATION_MODEL_UNAVAILABLE"
    # Reglas ampliadas (ADR-013, Propuesto): trading.risk.extended
    BETA_EXPOSURE = "BETA_EXPOSURE"
    ALT_NOTIONAL = "ALT_NOTIONAL"
    ALTS_TOTAL_NOTIONAL = "ALTS_TOTAL_NOTIONAL"
    MAX_OPEN_POSITIONS = "MAX_OPEN_POSITIONS"
    STABLECOIN_DEPEG = "STABLECOIN_DEPEG"
    MACRO_EVENT_WINDOW = "MACRO_EVENT_WINDOW"
    VOLATILITY_CIRCUIT = "VOLATILITY_CIRCUIT"
    API_ERROR_CIRCUIT = "API_ERROR_CIRCUIT"
    SPREAD_TOO_WIDE = "SPREAD_TOO_WIDE"
    BOOK_TOO_THIN = "BOOK_TOO_THIN"
    ADVERSE_FUNDING = "ADVERSE_FUNDING"
    MISSING_CONDITION = "MISSING_CONDITION"


@dataclass(frozen=True, slots=True)
class Veto:
    """Un motivo de veto.

    `reason` es el código estable que usan la auditoría y la app; `detail` es el texto técnico.
    `observed` y `limit` son la cifra que incumple y su límite, en la unidad propia del motivo
    (USD, fracción, múltiplo, segundos o conteo; ver `trading.risk.explain`). `subject` nombra
    el activo, la estrategia o el dato afectado, si aplica.
    """

    reason: VetoReason
    detail: str
    observed: Decimal | None = None
    limit: Decimal | None = None
    subject: str = ""


@dataclass(frozen=True, slots=True)
class AccountStatus:
    """Estado de la cuenta frente a las paradas del sistema."""

    drawdown: Decimal | None
    vetoes: tuple[Veto, ...]
    flatten_positions: bool

    @property
    def halt_new_entries(self) -> bool:
        return bool(self.vetoes)


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """Resultado de evaluar una propuesta. Las métricas son None si no se pudieron calcular."""

    vetoes: tuple[Veto, ...]
    flatten_positions: bool
    trade_risk: Decimal | None
    effective_leverage_after: Decimal | None
    liquidation_price: Decimal | None
    close_orderly: bool = False

    @property
    def approved(self) -> bool:
        return not self.vetoes

    @property
    def reasons(self) -> frozenset[VetoReason]:
        return frozenset(v.reason for v in self.vetoes)


@in_risk_context
def assess_account(account: AccountState, limits: RiskLimits) -> AccountStatus:
    """Paradas del sistema: parada manual, capital no positivo y drawdown (plan §3)."""
    vetoes: list[Veto] = []
    if account.trading_halted:
        vetoes.append(Veto(VetoReason.TRADING_HALTED, "sistema detenido (parada manual o latch)"))
    if account.equity <= 0:
        vetoes.append(
            Veto(VetoReason.NON_POSITIVE_EQUITY, f"capital={account.equity}", account.equity)
        )
        return AccountStatus(drawdown=None, vetoes=tuple(vetoes), flatten_positions=True)

    # Drawdown desde el máximo histórico del capital (ADR-007); el máximo incluye el capital actual.
    peak = max(account.peak_equity, account.equity)
    loss_from_peak = peak - account.equity
    drawdown = loss_from_peak / peak
    flatten = False
    if loss_from_peak >= limits.drawdown_hard_stop * peak:
        flatten = True
        vetoes.append(
            Veto(
                VetoReason.DRAWDOWN_HARD_STOP,
                f"drawdown={drawdown:.4%} >= corte duro {limits.drawdown_hard_stop:.2%}",
                drawdown,
                limits.drawdown_hard_stop,
            )
        )
    elif loss_from_peak >= limits.drawdown_halt * peak:
        vetoes.append(
            Veto(
                VetoReason.DRAWDOWN_HALT,
                f"drawdown={drawdown:.4%} >= parada {limits.drawdown_halt:.2%}",
                drawdown,
                limits.drawdown_halt,
            )
        )
    return AccountStatus(drawdown=drawdown, vetoes=tuple(vetoes), flatten_positions=flatten)


@in_risk_context
def evaluate_entry(
    proposal: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    costs: CostModel,
    now: datetime,
) -> RiskDecision:
    """Evalúa una propuesta de entrada contra todos los límites. Veto absoluto."""
    require_aware("now", now)
    status = assess_account(account, limits)
    vetoes = list(status.vetoes)
    vetoes += _freshness_vetoes(proposal, market, limits, now)
    vetoes += _structure_vetoes(proposal, limits)

    stop_ok = _stop_on_correct_side(proposal)
    if not stop_ok:
        vetoes.append(
            Veto(
                VetoReason.INVALID_STOP,
                f"stop {proposal.stop_price} en el lado equivocado de la entrada "
                f"{proposal.entry_price} para {proposal.side}",
            )
        )

    risk: Decimal | None = None
    leverage_after: Decimal | None = None
    liquidation_price: Decimal | None = None
    if stop_ok and proposal.quantity > 0 and account.equity > 0:
        risk = trade_risk(proposal.quantity, proposal.entry_price, proposal.stop_price, costs)
        total_notional = account.open_notional + proposal.notional
        leverage_after = total_notional / account.equity
        vetoes += _budget_vetoes(proposal, account, limits, risk, total_notional, leverage_after)
        liquidation_vetoes, liquidation_price = _liquidation_vetoes(proposal, limits)
        vetoes += liquidation_vetoes

    return RiskDecision(
        vetoes=tuple(vetoes),
        flatten_positions=status.flatten_positions,
        trade_risk=risk,
        effective_leverage_after=leverage_after,
        liquidation_price=liquidation_price,
    )


# --- reglas ----------------------------------------------------------------------------------


def _freshness_vetoes(
    proposal: EntryProposal, market: MarketSnapshot, limits: RiskLimits, now: datetime
) -> list[Veto]:
    vetoes: list[Veto] = []
    if market.symbol != proposal.symbol:
        vetoes.append(
            Veto(
                VetoReason.MARKET_DATA_MISMATCH,
                f"datos de {market.symbol} para una propuesta de {proposal.symbol}",
                subject=proposal.symbol,
            )
        )
    ahead = max(market.price_time, market.last_bar_close_time) - now
    if ahead > limits.max_clock_skew:
        vetoes.append(
            Veto(
                VetoReason.FUTURE_TIMESTAMP,
                f"marca de tiempo de datos {ahead} en el futuro > {limits.max_clock_skew}",
                seconds(ahead),
                seconds(limits.max_clock_skew),
            )
        )
    price_age = now - market.price_time
    if price_age > limits.max_price_age:
        vetoes.append(
            Veto(
                VetoReason.STALE_PRICE,
                f"precio con {price_age} > {limits.max_price_age}",
                seconds(price_age),
                seconds(limits.max_price_age),
                subject=market.symbol,
            )
        )
    bar_age = now - market.last_bar_close_time
    max_bar_age = market.bar_interval + limits.max_bar_lag
    if bar_age > max_bar_age:
        vetoes.append(
            Veto(
                VetoReason.STALE_BARS,
                f"última vela cerrada hace {bar_age} > {market.bar_interval} + "
                f"{limits.max_bar_lag}",
                seconds(bar_age),
                seconds(max_bar_age),
            )
        )
    return vetoes


def seconds(duration: timedelta) -> Decimal:
    """Duración en segundos como Decimal exacto (sin pasar por float)."""
    return Decimal(duration // timedelta(microseconds=1)).scaleb(-6)


def _structure_vetoes(proposal: EntryProposal, limits: RiskLimits) -> list[Veto]:
    vetoes: list[Veto] = []
    if proposal.quantity <= 0:
        vetoes.append(Veto(VetoReason.NON_POSITIVE_QUANTITY, f"cantidad={proposal.quantity}"))
    elif proposal.notional < proposal.min_notional:
        vetoes.append(
            Veto(
                VetoReason.BELOW_MIN_NOTIONAL,
                f"nocional {proposal.notional} < mínimo del contrato {proposal.min_notional} "
                "(protocolo C-19: nunca se aumenta el tamaño)",
                proposal.notional,
                proposal.min_notional,
                subject=proposal.symbol,
            )
        )
    if proposal.side is Side.SHORT:
        if proposal.market is MarketType.SPOT:
            vetoes.append(Veto(VetoReason.SHORT_ON_SPOT, "no hay cortos en spot (ADR-001)"))
        if proposal.strategy_id not in limits.short_enabled_strategies:
            vetoes.append(
                Veto(
                    VetoReason.SHORT_NOT_VALIDATED,
                    f"estrategia {proposal.strategy_id!r} sin cortos validados (plan §3)",
                    subject=proposal.strategy_id,
                )
            )
    if proposal.perpetual is not None and proposal.perpetual.margin_mode is MarginMode.CROSS:
        vetoes.append(Veto(VetoReason.CROSS_MARGIN, "margen cruzado prohibido (plan §3)"))
    return vetoes


def _stop_on_correct_side(proposal: EntryProposal) -> bool:
    if proposal.side is Side.LONG:
        return proposal.stop_price < proposal.entry_price
    return proposal.stop_price > proposal.entry_price


def _budget_vetoes(
    proposal: EntryProposal,
    account: AccountState,
    limits: RiskLimits,
    risk: Decimal,
    total_notional: Decimal,
    leverage_after: Decimal,
) -> list[Veto]:
    vetoes: list[Veto] = []
    budget = account.equity * limits.risk_per_trade
    if risk > budget:
        vetoes.append(
            Veto(
                VetoReason.RISK_PER_TRADE,
                f"riesgo {risk} > presupuesto por operación {budget}",
                risk,
                budget,
            )
        )

    if total_notional > limits.max_effective_leverage * account.equity:
        vetoes.append(
            Veto(
                VetoReason.EFFECTIVE_LEVERAGE,
                f"apalancamiento efectivo {leverage_after:.4f}x > {limits.max_effective_leverage}x",
                leverage_after,
                limits.max_effective_leverage,
            )
        )

    # Pérdida diaria/semanal prospectiva: pérdida ya incurrida en el periodo + riesgo hasta el
    # stop de las posiciones abiertas + riesgo de la nueva operación (ADR-007).
    worst_case_equity = account.equity - account.open_risk - risk
    for reason, start, limit in (
        (VetoReason.DAILY_LOSS, account.day_start_equity, limits.max_daily_loss),
        (VetoReason.WEEKLY_LOSS, account.week_start_equity, limits.max_weekly_loss),
    ):
        worst_case_loss = start - worst_case_equity
        allowed_loss = limit * start
        if worst_case_loss > allowed_loss:
            vetoes.append(
                Veto(
                    reason,
                    f"pérdida posible del periodo {worst_case_loss} > {limit:.2%} de {start}",
                    worst_case_loss,
                    allowed_loss,
                )
            )

    group = limits.group_of(proposal.base_asset)
    if group is not None:
        group_risk = risk + sum(
            (p.risk_to_stop for p in account.open_positions if p.base_asset in group),
            Decimal(0),
        )
        if group_risk > budget:
            vetoes.append(
                Veto(
                    VetoReason.CORRELATED_EXPOSURE,
                    f"riesgo conjunto de {sorted(group)} {group_risk} > presupuesto {budget}",
                    group_risk,
                    budget,
                    subject=" y ".join(sorted(group)),
                )
            )
    return vetoes


def _liquidation_vetoes(
    proposal: EntryProposal, limits: RiskLimits
) -> tuple[list[Veto], Decimal | None]:
    terms = proposal.perpetual
    if terms is None:
        return [], None
    if terms.liquidation_model is not LiquidationModel.BINANCE_USDM_ISOLATED:
        return [
            Veto(
                VetoReason.LIQUIDATION_MODEL_UNAVAILABLE,
                f"sin fórmula de liquidación implementada para {terms.liquidation_model}",
                subject=terms.liquidation_model.value,
            )
        ], None
    isolated_margin = proposal.notional / terms.exchange_leverage
    price = isolated_liquidation_price(
        side=proposal.side,
        quantity=proposal.quantity,
        entry_price=proposal.entry_price,
        isolated_margin=isolated_margin,
        maintenance_margin_rate=terms.maintenance_margin_rate,
        maintenance_amount=terms.maintenance_amount,
    )
    if price is None:
        return [], None
    # Comparación sin dividir: |entrada - liquidación| >= ratio x |entrada - stop|.
    buffer_in_price = adverse_distance(proposal.side, proposal.entry_price, price)
    stop_distance = abs(proposal.entry_price - proposal.stop_price)
    required = limits.min_liquidation_to_stop_ratio * stop_distance
    if buffer_in_price < required:
        return [
            Veto(
                VetoReason.LIQUIDATION_TOO_CLOSE,
                f"liquidación estimada en {price}: colchón {buffer_in_price} < "
                f"{limits.min_liquidation_to_stop_ratio} x distancia al stop",
                buffer_in_price / stop_distance,
                limits.min_liquidation_to_stop_ratio,
            )
        ], price
    return [], price
