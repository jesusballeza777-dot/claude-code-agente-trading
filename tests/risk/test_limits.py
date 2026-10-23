"""Límites del plan §3 como configuración y techos que la configuración no puede superar."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from trading.risk import (
    InvalidRiskLimitsError,
    RiskLimits,
    limits_from_toml,
    load_limits,
    load_plan_limits_f7_f8,
)

SHIPPED = Path(__file__).resolve().parents[2] / "src" / "trading" / "risk" / "limits_f7_f8.toml"


def test_shipped_limits_match_plan_section_3(limits: RiskLimits) -> None:
    assert limits.risk_per_trade == Decimal("0.005")
    assert limits.max_effective_leverage == Decimal(2)
    assert limits.min_liquidation_to_stop_ratio == Decimal(3)
    assert limits.max_daily_loss == Decimal("0.02")
    assert limits.max_weekly_loss == Decimal("0.04")
    assert limits.drawdown_halt == Decimal("0.15")
    assert limits.drawdown_hard_stop == Decimal("0.20")
    assert limits.correlated_groups == (frozenset({"BTC", "ETH"}),)
    assert limits.short_enabled_strategies == frozenset()


def test_plan_amounts_in_usd_for_1500(limits: RiskLimits) -> None:
    capital = Decimal(1500)
    assert capital * limits.risk_per_trade == Decimal("7.5")
    assert capital * limits.drawdown_halt == Decimal(225)
    assert capital * limits.drawdown_hard_stop == Decimal(300)


def test_proposed_freshness_values(limits: RiskLimits) -> None:
    assert limits.max_price_age == timedelta(seconds=60)
    assert limits.max_bar_lag == timedelta(seconds=300)
    assert limits.max_clock_skew == timedelta(seconds=5)


def test_load_limits_from_path_equals_packaged(limits: RiskLimits) -> None:
    assert load_limits(SHIPPED) == limits == load_plan_limits_f7_f8()


def test_ceiling_values_themselves_are_accepted(limits: RiskLimits) -> None:
    at_ceiling = replace(
        limits,
        risk_per_trade=Decimal("0.01"),
        max_effective_leverage=Decimal(3),
        max_weekly_loss=Decimal("0.05"),
        drawdown_halt=Decimal("0.20"),
        drawdown_hard_stop=Decimal("0.20"),
    )
    assert at_ceiling.max_effective_leverage == Decimal(3)


@pytest.mark.parametrize(
    "changes",
    [
        {"max_effective_leverage": Decimal("3.0001")},
        {"max_effective_leverage": Decimal(0)},
        {"max_effective_leverage": Decimal(-1)},
        {"risk_per_trade": Decimal("0.0101")},
        {"risk_per_trade": Decimal(0)},
        {"min_liquidation_to_stop_ratio": Decimal("2.99")},
        {"max_daily_loss": Decimal("0.0201")},
        {"max_weekly_loss": Decimal("0.0501")},
        {"max_weekly_loss": Decimal("0.01")},
        {"drawdown_halt": Decimal("0.16"), "drawdown_hard_stop": Decimal("0.15")},
        {"drawdown_hard_stop": Decimal("0.2001")},
        {"risk_per_trade": Decimal("0.01"), "max_daily_loss": Decimal("0.009")},
        {"risk_per_trade": Decimal("NaN")},
        {"max_effective_leverage": Decimal("Infinity")},
        {"risk_per_trade": 0.005},
        {"correlated_groups": (frozenset({"BTC"}),)},
        {"correlated_groups": (frozenset({"BTC", "ETH"}), frozenset({"ETH", "SOL"}))},
        {"correlated_groups": (frozenset({"BTC", ""}),)},
        {"short_enabled_strategies": frozenset({" H1"})},
        {"max_price_age": timedelta(0)},
        {"max_bar_lag": timedelta(seconds=-1)},
        {"max_clock_skew": timedelta(seconds=-1)},
    ],
)
def test_invalid_or_above_ceiling_limits_are_rejected(
    limits: RiskLimits, changes: dict[str, Any]
) -> None:
    with pytest.raises(InvalidRiskLimitsError):
        replace(limits, **changes)


def test_group_of(limits: RiskLimits) -> None:
    assert limits.group_of("ETH") == frozenset({"BTC", "ETH"})
    assert limits.group_of("SOL") is None


# --- TOML ------------------------------------------------------------------------------------


def _shipped_text() -> str:
    return SHIPPED.read_text(encoding="utf-8")


def test_toml_accepts_validated_short_strategies() -> None:
    text = _shipped_text().replace(
        "short_enabled_strategies = []", 'short_enabled_strategies = ["H1"]'
    )
    assert limits_from_toml(text).short_enabled_strategies == frozenset({"H1"})


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("max_daily_loss = 0.02", "max_daily_loss = 0.02\nmax_hourly_loss = 0.01", "desconocidas"),
        ("max_daily_loss = 0.02", "", "faltan"),
        ("[data_freshness]", "[datos]", "faltan"),
        ("max_effective_leverage = 2", "max_effective_leverage = true", "número"),
        ("max_effective_leverage = 2", 'max_effective_leverage = "2"', "número"),
        ("max_effective_leverage = 2", "max_effective_leverage = 4", "techo"),
        ("max_price_age_seconds = 60", "max_price_age_seconds = 60.5", "entero"),
        ("max_price_age_seconds = 60", "max_price_age_seconds = false", "entero"),
        ('correlated_groups = [["BTC", "ETH"]]', 'correlated_groups = "BTC,ETH"', "lista"),
        ('correlated_groups = [["BTC", "ETH"]]', 'correlated_groups = [["BTC", 1]]', "textos"),
        ("short_enabled_strategies = []", "short_enabled_strategies = [1]", "textos"),
        ("max_daily_loss = 0.02", "max_daily_loss = = 0.02", "TOML"),
    ],
)
def test_toml_rejects_malformed_config(old: str, new: str, message: str) -> None:
    text = _shipped_text()
    assert old in text
    with pytest.raises(InvalidRiskLimitsError, match=message):
        limits_from_toml(text.replace(old, new, 1))


def test_toml_rejects_section_that_is_not_a_table() -> None:
    text = _shipped_text()
    start = text.index("[exposure]")
    end = text.index("# PROPUESTO")
    broken = text[:start] + text[end:]
    broken = broken.replace("[risk]", 'exposure = "x"\n\n[risk]', 1)
    with pytest.raises(InvalidRiskLimitsError, match="tabla"):
        limits_from_toml(broken)
