"""Reglas ampliadas del motor de riesgo (ADR-013, estado Propuesto; auditoría A-05, A-07, A-10).

Todas son más restrictivas que el motor v0 y se suman a `evaluate_entry`; ninguna relaja un
límite. Los datos que necesitan (betas, precios de stablecoins, calendario macro, volatilidad,
libro de órdenes, funding, errores de la API) los calcula código determinista fuera del motor
y llegan como argumentos. Si falta uno, el motor veta (fallo cerrado).

Se agrupan en tres bloques para que el backtester pueda aplicar los que tienen datos
históricos públicos (exposición y funding) y declarar los que no:

- `exposure_vetoes` y `funding_vetoes`: exposición beta-ajustada, alts, posiciones y funding.
- `assess_conditions`: estado de la cuenta frente al entorno (depeg, eventos macro, errores de
  la API). El depeg pide además un cierre ordenado de las posiciones.
- `symbol_vetoes`: volatilidad, spread, profundidad y funding del activo de la propuesta.

`evaluate_entry_v1` aplica el motor v0 y los tres bloques: es la evaluación de la sombra (F7)
y de la operación real.

Convención de límites exactos: igual que el motor v0, alcanzar exactamente un presupuesto
(exposición, nocional, spread, profundidad, funding, desviación del depeg) está permitido.
Las paradas saltan al alcanzar su umbral: la ventana macro incluye sus bordes (±2 h exactas)
y el disyuntor de errores salta con exactamente 3 errores. La volatilidad veta solo por
encima del p99.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from importlib import resources
from pathlib import Path
from typing import Final

from trading.risk.engine import RiskDecision, Veto, VetoReason, evaluate_entry, seconds
from trading.risk.limits import (
    CEILING_EFFECTIVE_LEVERAGE,
    InvalidRiskLimitsError,
    RiskLimits,
    _check_keys,
    _integer,
    _number,
    _string_list,
)
from trading.risk.models import (
    AccountState,
    CostModel,
    EntryProposal,
    MarketSnapshot,
    MarketType,
    Side,
    in_risk_context,
    require_aware,
    require_decimal,
    require_name,
    require_non_negative,
    require_positive,
)

PROPOSED_V1_RESOURCE: Final = "limits_v1_propuesto.toml"
BPS: Final = Decimal(10_000)


@dataclass(frozen=True, slots=True)
class ExtendedLimits:
    """Valores de las reglas ampliadas. Fracciones sobre el capital a mercado."""

    max_beta_adjusted_exposure: Decimal
    max_notional_per_alt: Decimal
    max_notional_all_alts: Decimal
    max_open_positions: int
    core_assets: frozenset[str]
    monitored_stablecoins: frozenset[str]
    max_stablecoin_deviation: Decimal
    macro_blackout: timedelta
    max_api_errors: int
    api_error_window: timedelta
    max_spread_bps_core: Decimal
    max_spread_bps_alt: Decimal
    depth_band_bps_core: Decimal
    depth_band_bps_alt: Decimal
    min_depth_multiple: Decimal
    max_adverse_funding_8h: Decimal

    def __post_init__(self) -> None:
        exposure = _limit_decimal("max_beta_adjusted_exposure", self.max_beta_adjusted_exposure)
        if exposure > CEILING_EFFECTIVE_LEVERAGE:
            raise InvalidRiskLimitsError(
                "max_beta_adjusted_exposure supera el techo de apalancamiento del plan"
            )
        per_alt = _limit_fraction("max_notional_per_alt", self.max_notional_per_alt)
        all_alts = _limit_fraction("max_notional_all_alts", self.max_notional_all_alts)
        if per_alt > all_alts:
            raise InvalidRiskLimitsError("max_notional_per_alt no puede superar el total en alts")
        _limit_fraction("max_stablecoin_deviation", self.max_stablecoin_deviation)
        _limit_fraction("max_adverse_funding_8h", self.max_adverse_funding_8h)
        for name in (
            "max_spread_bps_core",
            "max_spread_bps_alt",
            "depth_band_bps_core",
            "depth_band_bps_alt",
        ):
            _limit_decimal(name, getattr(self, name))
        if _limit_decimal("min_depth_multiple", self.min_depth_multiple) < 1:
            raise InvalidRiskLimitsError("min_depth_multiple debe ser >= 1")
        for name in ("max_open_positions", "max_api_errors"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise InvalidRiskLimitsError(f"{name} debe ser un entero >= 1")
        for name in ("macro_blackout", "api_error_window"):
            if getattr(self, name) <= timedelta(0):
                raise InvalidRiskLimitsError(f"{name} debe ser positivo")
        for name in ("core_assets", "monitored_stablecoins"):
            values = getattr(self, name)
            if not values or any(not v or v != v.strip() for v in values):
                raise InvalidRiskLimitsError(f"{name} necesita nombres no vacíos")

    def is_alt(self, base_asset: str) -> bool:
        return base_asset not in self.core_assets

    def max_spread_bps(self, base_asset: str) -> Decimal:
        return self.max_spread_bps_alt if self.is_alt(base_asset) else self.max_spread_bps_core

    def depth_band_bps(self, base_asset: str) -> Decimal:
        """Banda alrededor del precio medio en la que el recolector mide la profundidad."""
        return self.depth_band_bps_alt if self.is_alt(base_asset) else self.depth_band_bps_core


class MacroEventKind(StrEnum):
    FOMC = "FOMC"
    CPI = "CPI"
    NFP = "NFP"


@dataclass(frozen=True, slots=True)
class MacroEvent:
    kind: MacroEventKind
    time: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MacroEventKind):
            raise TypeError("kind debe ser un MacroEventKind")
        require_aware("time", self.time)


@dataclass(frozen=True, slots=True)
class MarketConditions:
    """Entorno de la cuenta en el momento de evaluar.

    - `stablecoin_prices`: precio en USD de cada stablecoin vigilada (fuente: F6, por verificar).
    - `macro_events` y `macro_calendar_through`: el calendario es completo hasta esa hora.
    - `api_error_times`: errores de la API del exchange registrados por la ejecución (F6).
    - `betas`: beta frente a BTC de cada activo (BTC = 1), calculada por `features`.
    """

    stablecoin_prices: Mapping[str, Decimal]
    macro_events: tuple[MacroEvent, ...]
    macro_calendar_through: datetime
    api_error_times: tuple[datetime, ...]
    betas: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        for coin, price in self.stablecoin_prices.items():
            require_name("stablecoin", coin)
            require_positive(f"precio de {coin}", price)
        for asset, beta in self.betas.items():
            require_name("activo", asset)
            require_decimal(f"beta de {asset}", beta)
        require_aware("macro_calendar_through", self.macro_calendar_through)
        for moment in self.api_error_times:
            require_aware("api_error_times[]", moment)


@dataclass(frozen=True, slots=True)
class SymbolConditions:
    """Volatilidad, libro y funding del contrato de la propuesta.

    - `realized_vol_1h` y `vol_1h_p99`: volatilidad realizada de la última hora y su percentil
      99 histórico, ambos como fracción, calculados por `features` con la misma definición.
    - `best_bid`, `best_ask` y `depth_notional`: mejor precio de compra y de venta, y nocional
      en USD disponible del lado que consume la orden dentro de `depth_band_bps` del medio.
    - `quote_time`: hora de esa lectura del libro.
    - `funding_rate_8h`: funding vigente expresado por 8 h (Hyperliquid liquida cada hora:
      multiplicar por 8); positivo = pagan los largos. None en spot.
    """

    symbol: str
    realized_vol_1h: Decimal
    vol_1h_p99: Decimal
    best_bid: Decimal
    best_ask: Decimal
    depth_notional: Decimal
    quote_time: datetime
    funding_rate_8h: Decimal | None

    def __post_init__(self) -> None:
        require_name("symbol", self.symbol)
        require_non_negative("realized_vol_1h", self.realized_vol_1h)
        require_positive("vol_1h_p99", self.vol_1h_p99)
        bid = require_positive("best_bid", self.best_bid)
        if require_positive("best_ask", self.best_ask) < bid:
            raise ValueError("libro cruzado: best_ask < best_bid")
        require_non_negative("depth_notional", self.depth_notional)
        require_aware("quote_time", self.quote_time)
        if self.funding_rate_8h is not None:
            require_decimal("funding_rate_8h", self.funding_rate_8h)

    @property
    def spread_bps(self) -> Decimal:
        mid = (self.best_bid + self.best_ask) / 2
        return (self.best_ask - self.best_bid) / mid * BPS


@dataclass(frozen=True, slots=True)
class ConditionsStatus:
    vetoes: tuple[Veto, ...]
    close_orderly: bool


# --- reglas ----------------------------------------------------------------------------------


@in_risk_context
def exposure_vetoes(
    proposal: EntryProposal,
    account: AccountState,
    betas: Mapping[str, Decimal],
    limits: ExtendedLimits,
) -> list[Veto]:
    """Exposición beta-ajustada, nocional por alt y en todas las alts, y número de posiciones.

    Con capital no positivo devuelve []: `assess_account` ya veta y pide cerrar.
    """
    vetoes: list[Veto] = []
    positions_after = len(account.open_positions) + 1
    if positions_after > limits.max_open_positions:
        vetoes.append(
            Veto(
                VetoReason.MAX_OPEN_POSITIONS,
                f"{positions_after} posiciones abiertas > máximo {limits.max_open_positions}",
                Decimal(positions_after),
                Decimal(limits.max_open_positions),
            )
        )
    equity = account.equity
    if equity <= 0 or proposal.quantity <= 0:
        return vetoes

    exposures = [(p.base_asset, p.notional) for p in account.open_positions]
    exposures.append((proposal.base_asset, proposal.notional))

    missing = sorted({asset for asset, _ in exposures if asset not in betas})
    if missing:
        vetoes.append(
            Veto(
                VetoReason.MISSING_CONDITION,
                f"sin beta frente a BTC para {missing}",
                subject="beta frente a BTC de " + ", ".join(missing),
            )
        )
    else:
        beta_exposure = sum(
            (notional * abs(betas[asset]) for asset, notional in exposures), Decimal(0)
        )
        allowed = limits.max_beta_adjusted_exposure * equity
        if beta_exposure > allowed:
            vetoes.append(
                Veto(
                    VetoReason.BETA_EXPOSURE,
                    f"exposición beta-ajustada {beta_exposure} > {allowed}",
                    beta_exposure,
                    allowed,
                )
            )

    if limits.is_alt(proposal.base_asset):
        same_alt = sum(
            (notional for asset, notional in exposures if asset == proposal.base_asset),
            Decimal(0),
        )
        allowed_alt = limits.max_notional_per_alt * equity
        if same_alt > allowed_alt:
            vetoes.append(
                Veto(
                    VetoReason.ALT_NOTIONAL,
                    f"nocional en {proposal.base_asset} {same_alt} > {allowed_alt}",
                    same_alt,
                    allowed_alt,
                    subject=proposal.base_asset,
                )
            )
        all_alts = sum(
            (notional for asset, notional in exposures if limits.is_alt(asset)), Decimal(0)
        )
        allowed_alts = limits.max_notional_all_alts * equity
        if all_alts > allowed_alts:
            vetoes.append(
                Veto(
                    VetoReason.ALTS_TOTAL_NOTIONAL,
                    f"nocional en alts {all_alts} > {allowed_alts}",
                    all_alts,
                    allowed_alts,
                )
            )
    return vetoes


@in_risk_context
def funding_vetoes(
    proposal: EntryProposal, funding_rate_8h: Decimal | None, limits: ExtendedLimits
) -> list[Veto]:
    """Funding en contra por encima del umbral (ADR-001 punto 6). Solo en perpetuos."""
    if proposal.market is not MarketType.PERPETUAL:
        return []
    if funding_rate_8h is None:
        return [
            Veto(
                VetoReason.MISSING_CONDITION,
                f"sin funding para {proposal.symbol}",
                subject=f"funding de {proposal.symbol}",
            )
        ]
    rate = require_decimal("funding_rate_8h", funding_rate_8h)
    adverse = rate if proposal.side is Side.LONG else -rate
    if adverse > limits.max_adverse_funding_8h:
        return [
            Veto(
                VetoReason.ADVERSE_FUNDING,
                f"funding en contra {adverse} por 8 h > {limits.max_adverse_funding_8h}",
                adverse,
                limits.max_adverse_funding_8h,
                subject=proposal.symbol,
            )
        ]
    return []


@in_risk_context
def assess_conditions(
    conditions: MarketConditions, limits: ExtendedLimits, now: datetime
) -> ConditionsStatus:
    """Depeg de stablecoins, ventana de eventos macro y disyuntor de errores de la API."""
    require_aware("now", now)
    vetoes: list[Veto] = []
    close_orderly = False

    for coin in sorted(limits.monitored_stablecoins):
        price = conditions.stablecoin_prices.get(coin)
        if price is None:
            vetoes.append(
                Veto(
                    VetoReason.MISSING_CONDITION,
                    f"sin precio de {coin}",
                    subject=f"precio de {coin}",
                )
            )
            continue
        deviation = abs(price - 1)
        if deviation > limits.max_stablecoin_deviation:
            close_orderly = True
            vetoes.append(
                Veto(
                    VetoReason.STABLECOIN_DEPEG,
                    f"{coin} a {price} USD: desviación {deviation} > "
                    f"{limits.max_stablecoin_deviation}",
                    deviation,
                    limits.max_stablecoin_deviation,
                    subject=coin,
                )
            )

    if conditions.macro_calendar_through < now + limits.macro_blackout:
        vetoes.append(
            Veto(
                VetoReason.MISSING_CONDITION,
                f"calendario macro completo solo hasta {conditions.macro_calendar_through}",
                subject="calendario macro",
            )
        )
    for event in sorted(conditions.macro_events, key=lambda e: e.time):
        distance = abs(event.time - now)
        if distance <= limits.macro_blackout:
            vetoes.append(
                Veto(
                    VetoReason.MACRO_EVENT_WINDOW,
                    f"{event.kind} a las {event.time.isoformat()}: a {distance} <= "
                    f"{limits.macro_blackout}",
                    seconds(distance),
                    seconds(limits.macro_blackout),
                    subject=f"{event.kind} {event.time:%Y-%m-%d %H:%M} UTC",
                )
            )

    window_start = now - limits.api_error_window
    errors = sum(1 for moment in conditions.api_error_times if moment > window_start)
    if errors >= limits.max_api_errors:
        vetoes.append(
            Veto(
                VetoReason.API_ERROR_CIRCUIT,
                f"{errors} errores de la API en {limits.api_error_window} >= "
                f"{limits.max_api_errors}",
                Decimal(errors),
                Decimal(limits.max_api_errors),
            )
        )
    return ConditionsStatus(vetoes=tuple(vetoes), close_orderly=close_orderly)


@in_risk_context
def symbol_vetoes(
    proposal: EntryProposal,
    symbol: SymbolConditions,
    risk_limits: RiskLimits,
    limits: ExtendedLimits,
    now: datetime,
) -> list[Veto]:
    """Volatilidad, spread, profundidad y funding del contrato de la propuesta."""
    require_aware("now", now)
    if symbol.symbol != proposal.symbol:
        return [
            Veto(
                VetoReason.MARKET_DATA_MISMATCH,
                f"condiciones de {symbol.symbol} para una propuesta de {proposal.symbol}",
                subject=proposal.symbol,
            )
        ]
    vetoes: list[Veto] = []
    quote_age = now - symbol.quote_time
    if quote_age > risk_limits.max_price_age:
        vetoes.append(
            Veto(
                VetoReason.STALE_PRICE,
                f"libro con {quote_age} > {risk_limits.max_price_age}",
                seconds(quote_age),
                seconds(risk_limits.max_price_age),
                subject=f"libro de {symbol.symbol}",
            )
        )
    if symbol.realized_vol_1h > symbol.vol_1h_p99:
        vetoes.append(
            Veto(
                VetoReason.VOLATILITY_CIRCUIT,
                f"volatilidad 1h {symbol.realized_vol_1h} > p99 {symbol.vol_1h_p99}",
                symbol.realized_vol_1h,
                symbol.vol_1h_p99,
                subject=symbol.symbol,
            )
        )
    # Sin dividir: (ask - bid) x 10,000 > máximo x medio, con medio = (ask + bid) / 2.
    max_bps = limits.max_spread_bps(proposal.base_asset)
    if (symbol.best_ask - symbol.best_bid) * BPS * 2 > max_bps * (
        symbol.best_ask + symbol.best_bid
    ):
        vetoes.append(
            Veto(
                VetoReason.SPREAD_TOO_WIDE,
                f"spread {symbol.spread_bps} pb > {max_bps} pb",
                symbol.spread_bps,
                max_bps,
                subject=symbol.symbol,
            )
        )
    if proposal.quantity > 0:
        required_depth = limits.min_depth_multiple * proposal.notional
        if symbol.depth_notional < required_depth:
            vetoes.append(
                Veto(
                    VetoReason.BOOK_TOO_THIN,
                    f"profundidad {symbol.depth_notional} < {limits.min_depth_multiple} x "
                    f"nocional {proposal.notional}",
                    symbol.depth_notional,
                    required_depth,
                    subject=symbol.symbol,
                )
            )
    vetoes += funding_vetoes(proposal, symbol.funding_rate_8h, limits)
    return vetoes


@in_risk_context
def evaluate_entry_v1(
    proposal: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    conditions: MarketConditions,
    symbol: SymbolConditions,
    risk_limits: RiskLimits,
    limits: ExtendedLimits,
    costs: CostModel,
    now: datetime,
) -> RiskDecision:
    """Motor v0 más todas las reglas ampliadas. Veto absoluto; todos los vetos juntos."""
    base = evaluate_entry(proposal, account, market, risk_limits, costs, now)
    status = assess_conditions(conditions, limits, now)
    vetoes = list(base.vetoes)
    vetoes += status.vetoes
    vetoes += exposure_vetoes(proposal, account, conditions.betas, limits)
    vetoes += symbol_vetoes(proposal, symbol, risk_limits, limits, now)
    return RiskDecision(
        vetoes=tuple(vetoes),
        flatten_positions=base.flatten_positions,
        trade_risk=base.trade_risk,
        effective_leverage_after=base.effective_leverage_after,
        liquidation_price=base.liquidation_price,
        close_orderly=status.close_orderly,
    )


# --- carga -----------------------------------------------------------------------------------

_SCHEMA: Final[dict[str, frozenset[str]]] = {
    "exposure": frozenset(
        {
            "max_beta_adjusted_exposure",
            "max_notional_per_alt",
            "max_notional_all_alts",
            "max_open_positions",
            "core_assets",
        }
    ),
    "stablecoins": frozenset({"monitored", "max_deviation"}),
    "macro": frozenset({"blackout_minutes"}),
    "circuit_breakers": frozenset({"max_api_errors", "api_error_window_minutes"}),
    "liquidity": frozenset(
        {
            "max_spread_bps_core",
            "max_spread_bps_alt",
            "depth_band_bps_core",
            "depth_band_bps_alt",
            "min_depth_multiple",
        }
    ),
    "funding": frozenset({"max_adverse_funding_8h"}),
}


def load_extended_limits_v1_propuesto() -> ExtendedLimits:
    """Valores propuestos en el ADR-013, tal como están versionados en el paquete."""
    text = resources.files("trading.risk").joinpath(PROPOSED_V1_RESOURCE).read_text("utf-8")
    return extended_limits_from_toml(text)


def load_extended_limits(path: Path) -> ExtendedLimits:
    return extended_limits_from_toml(path.read_text(encoding="utf-8"))


def extended_limits_from_toml(text: str) -> ExtendedLimits:
    """Construye ExtendedLimits desde TOML. Claves desconocidas o ausentes son un error."""
    try:
        raw = tomllib.loads(text, parse_float=Decimal)
    except tomllib.TOMLDecodeError as exc:
        raise InvalidRiskLimitsError(f"TOML inválido: {exc}") from exc
    _check_keys("raíz", raw, frozenset(_SCHEMA))
    for section, keys in _SCHEMA.items():
        if not isinstance(raw[section], dict):
            raise InvalidRiskLimitsError(f"[{section}] debe ser una tabla")
        _check_keys(f"[{section}]", raw[section], keys)
    exposure, stable, macro = raw["exposure"], raw["stablecoins"], raw["macro"]
    breakers, liquidity, funding = raw["circuit_breakers"], raw["liquidity"], raw["funding"]
    return ExtendedLimits(
        max_beta_adjusted_exposure=_number(exposure, "max_beta_adjusted_exposure"),
        max_notional_per_alt=_number(exposure, "max_notional_per_alt"),
        max_notional_all_alts=_number(exposure, "max_notional_all_alts"),
        max_open_positions=_integer(exposure, "max_open_positions"),
        core_assets=frozenset(_string_list(exposure["core_assets"], "core_assets")),
        monitored_stablecoins=frozenset(_string_list(stable["monitored"], "monitored")),
        max_stablecoin_deviation=_number(stable, "max_deviation"),
        macro_blackout=timedelta(minutes=_integer(macro, "blackout_minutes")),
        max_api_errors=_integer(breakers, "max_api_errors"),
        api_error_window=timedelta(minutes=_integer(breakers, "api_error_window_minutes")),
        max_spread_bps_core=_number(liquidity, "max_spread_bps_core"),
        max_spread_bps_alt=_number(liquidity, "max_spread_bps_alt"),
        depth_band_bps_core=_number(liquidity, "depth_band_bps_core"),
        depth_band_bps_alt=_number(liquidity, "depth_band_bps_alt"),
        min_depth_multiple=_number(liquidity, "min_depth_multiple"),
        max_adverse_funding_8h=_number(funding, "max_adverse_funding_8h"),
    )


def _limit_decimal(name: str, value: object) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise InvalidRiskLimitsError(f"{name} debe ser un Decimal finito")
    if value <= 0:
        raise InvalidRiskLimitsError(f"{name} debe ser positivo")
    return value


def _limit_fraction(name: str, value: object) -> Decimal:
    number = _limit_decimal(name, value)
    if number > 1:
        raise InvalidRiskLimitsError(f"{name} es una fracción y no puede superar 1")
    return number
