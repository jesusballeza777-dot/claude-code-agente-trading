"""Límites del motor de riesgo y techos del plan maestro.

Los valores operativos viven en un fichero TOML versionado (`limits_f7_f8.toml`). Los techos
del plan están en código: un fichero de configuración no puede superarlos. Superar un techo
requiere cambiar este módulo con un ADR aprobado por el propietario (plan §3; CLAUDE.md regla 4).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from importlib import resources
from pathlib import Path
from typing import Any, Final

# Techos del plan §3 (el valor más permisivo de cualquier fase, F9 incluida).
CEILING_RISK_PER_TRADE: Final = Decimal("0.01")
CEILING_EFFECTIVE_LEVERAGE: Final = Decimal("3")
FLOOR_LIQUIDATION_TO_STOP_RATIO: Final = Decimal("3")
CEILING_DAILY_LOSS: Final = Decimal("0.02")
CEILING_WEEKLY_LOSS: Final = Decimal("0.05")
CEILING_DRAWDOWN: Final = Decimal("0.20")

PLAN_F7_F8_RESOURCE: Final = "limits_f7_f8.toml"


class InvalidRiskLimitsError(ValueError):
    """La configuración de límites es inválida o supera un techo del plan."""


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Límites del motor de riesgo. Las fracciones son sobre el capital (0.005 = 0.5%)."""

    risk_per_trade: Decimal
    max_effective_leverage: Decimal
    min_liquidation_to_stop_ratio: Decimal
    max_daily_loss: Decimal
    max_weekly_loss: Decimal
    drawdown_halt: Decimal
    drawdown_hard_stop: Decimal
    correlated_groups: tuple[frozenset[str], ...]
    short_enabled_strategies: frozenset[str]
    max_price_age: timedelta
    max_bar_lag: timedelta
    max_clock_skew: timedelta

    def __post_init__(self) -> None:
        _positive_at_most("risk_per_trade", self.risk_per_trade, CEILING_RISK_PER_TRADE)
        _positive_at_most(
            "max_effective_leverage", self.max_effective_leverage, CEILING_EFFECTIVE_LEVERAGE
        )
        ratio = _decimal("min_liquidation_to_stop_ratio", self.min_liquidation_to_stop_ratio)
        if ratio < FLOOR_LIQUIDATION_TO_STOP_RATIO:
            raise InvalidRiskLimitsError(
                f"min_liquidation_to_stop_ratio={ratio} es menor que el mínimo del plan "
                f"({FLOOR_LIQUIDATION_TO_STOP_RATIO})"
            )
        _positive_at_most("max_daily_loss", self.max_daily_loss, CEILING_DAILY_LOSS)
        _positive_at_most("max_weekly_loss", self.max_weekly_loss, CEILING_WEEKLY_LOSS)
        _positive_at_most("drawdown_halt", self.drawdown_halt, CEILING_DRAWDOWN)
        _positive_at_most("drawdown_hard_stop", self.drawdown_hard_stop, CEILING_DRAWDOWN)
        if self.max_weekly_loss < self.max_daily_loss:
            raise InvalidRiskLimitsError("max_weekly_loss no puede ser menor que max_daily_loss")
        if self.drawdown_halt > self.drawdown_hard_stop:
            raise InvalidRiskLimitsError("drawdown_halt no puede superar drawdown_hard_stop")
        if self.risk_per_trade > self.max_daily_loss:
            raise InvalidRiskLimitsError("risk_per_trade no puede superar max_daily_loss")
        _validate_groups(self.correlated_groups)
        _validate_names("short_enabled_strategies", self.short_enabled_strategies)
        for name in ("max_price_age", "max_bar_lag"):
            if getattr(self, name) <= timedelta(0):
                raise InvalidRiskLimitsError(f"{name} debe ser positivo")
        if self.max_clock_skew < timedelta(0):
            raise InvalidRiskLimitsError("max_clock_skew no puede ser negativo")

    def group_of(self, base_asset: str) -> frozenset[str] | None:
        """Grupo de correlación al que pertenece el activo, si pertenece a alguno."""
        for group in self.correlated_groups:
            if base_asset in group:
                return group
        return None


def load_plan_limits_f7_f8() -> RiskLimits:
    """Límites de las fases F7-F8 tal como están versionados en el paquete."""
    text = resources.files("trading.risk").joinpath(PLAN_F7_F8_RESOURCE).read_text("utf-8")
    return limits_from_toml(text)


def load_limits(path: Path) -> RiskLimits:
    """Carga y valida límites desde un fichero TOML."""
    return limits_from_toml(path.read_text(encoding="utf-8"))


_SCHEMA: Final[dict[str, frozenset[str]]] = {
    "risk": frozenset(
        {
            "risk_per_trade",
            "max_effective_leverage",
            "min_liquidation_to_stop_ratio",
            "max_daily_loss",
            "max_weekly_loss",
            "drawdown_halt",
            "drawdown_hard_stop",
        }
    ),
    "exposure": frozenset({"correlated_groups", "short_enabled_strategies"}),
    "data_freshness": frozenset(
        {"max_price_age_seconds", "max_bar_lag_seconds", "max_clock_skew_seconds"}
    ),
}


def limits_from_toml(text: str) -> RiskLimits:
    """Construye RiskLimits desde TOML. Claves desconocidas o ausentes son un error."""
    try:
        raw = tomllib.loads(text, parse_float=Decimal)
    except tomllib.TOMLDecodeError as exc:
        raise InvalidRiskLimitsError(f"TOML inválido: {exc}") from exc
    _check_keys("raíz", raw, frozenset(_SCHEMA))
    for section, keys in _SCHEMA.items():
        if not isinstance(raw[section], dict):
            raise InvalidRiskLimitsError(f"[{section}] debe ser una tabla")
        _check_keys(f"[{section}]", raw[section], keys)
    risk, exposure, freshness = raw["risk"], raw["exposure"], raw["data_freshness"]
    return RiskLimits(
        risk_per_trade=_number(risk, "risk_per_trade"),
        max_effective_leverage=_number(risk, "max_effective_leverage"),
        min_liquidation_to_stop_ratio=_number(risk, "min_liquidation_to_stop_ratio"),
        max_daily_loss=_number(risk, "max_daily_loss"),
        max_weekly_loss=_number(risk, "max_weekly_loss"),
        drawdown_halt=_number(risk, "drawdown_halt"),
        drawdown_hard_stop=_number(risk, "drawdown_hard_stop"),
        correlated_groups=tuple(
            frozenset(_string_list(group, "correlated_groups[]"))
            for group in _list(exposure, "correlated_groups")
        ),
        short_enabled_strategies=frozenset(
            _string_list(_list(exposure, "short_enabled_strategies"), "short_enabled_strategies")
        ),
        max_price_age=timedelta(seconds=_integer(freshness, "max_price_age_seconds")),
        max_bar_lag=timedelta(seconds=_integer(freshness, "max_bar_lag_seconds")),
        max_clock_skew=timedelta(seconds=_integer(freshness, "max_clock_skew_seconds")),
    )


# --- validación ----------------------------------------------------------------------------


def _decimal(name: str, value: object) -> Decimal:
    if not isinstance(value, Decimal):
        raise InvalidRiskLimitsError(f"{name} debe ser Decimal, no {type(value).__name__}")
    if not value.is_finite():
        raise InvalidRiskLimitsError(f"{name} debe ser finito")
    return value


def _positive_at_most(name: str, value: object, ceiling: Decimal) -> None:
    number = _decimal(name, value)
    if number <= 0:
        raise InvalidRiskLimitsError(f"{name} debe ser positivo")
    if number > ceiling:
        raise InvalidRiskLimitsError(f"{name}={number} supera el techo del plan ({ceiling})")


def _validate_names(name: str, values: frozenset[str]) -> None:
    for value in values:
        if not value or value != value.strip():
            raise InvalidRiskLimitsError(f"{name} contiene un nombre vacío o con espacios")


def _validate_groups(groups: tuple[frozenset[str], ...]) -> None:
    seen: set[str] = set()
    for group in groups:
        if len(group) < 2:
            raise InvalidRiskLimitsError("cada grupo de correlación necesita al menos 2 activos")
        _validate_names("correlated_groups", group)
        if seen & group:
            raise InvalidRiskLimitsError("un activo no puede estar en dos grupos de correlación")
        seen |= group


# --- lectura de TOML -------------------------------------------------------------------------


def _check_keys(where: str, table: dict[str, Any], expected: frozenset[str]) -> None:
    missing = expected - table.keys()
    unknown = table.keys() - expected
    if missing:
        raise InvalidRiskLimitsError(f"{where}: faltan claves {sorted(missing)}")
    if unknown:
        raise InvalidRiskLimitsError(f"{where}: claves desconocidas {sorted(unknown)}")


def _number(table: dict[str, Any], key: str) -> Decimal:
    value = table[key]
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise InvalidRiskLimitsError(f"{key} debe ser un número")
    return Decimal(value)


def _integer(table: dict[str, Any], key: str) -> int:
    value = table[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRiskLimitsError(f"{key} debe ser un entero")
    return value


def _list(table: dict[str, Any], key: str) -> list[Any]:
    value = table[key]
    if not isinstance(value, list):
        raise InvalidRiskLimitsError(f"{key} debe ser una lista")
    return value


def _string_list(value: object, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise InvalidRiskLimitsError(f"{key} debe ser una lista de textos")
    return [item for item in value if isinstance(item, str)]
