"""Motor de riesgo: código puro, sin red, con veto absoluto (CLAUDE.md, regla 4).

Los límites vienen de `limits_f7_f8.toml` (plan maestro v2 §3) y no pueden superar los
techos del plan definidos en `limits.py`. Decisiones de diseño: ADR-007.
Reglas ampliadas (más restrictivas, ADR-013 Propuesto): `extended.py` y
`limits_v1_propuesto.toml`. Explicación de vetos en español: `explain.py`.
"""

from trading.risk.engine import (
    AccountStatus,
    RiskDecision,
    Veto,
    VetoReason,
    assess_account,
    evaluate_entry,
)
from trading.risk.explain import VetoExplanation, explain, explain_decision
from trading.risk.extended import (
    ConditionsStatus,
    ExtendedLimits,
    MacroEvent,
    MacroEventKind,
    MarketConditions,
    SymbolConditions,
    assess_conditions,
    evaluate_entry_v1,
    exposure_vetoes,
    extended_limits_from_toml,
    funding_vetoes,
    load_extended_limits,
    load_extended_limits_v1_propuesto,
    symbol_vetoes,
)
from trading.risk.limits import (
    InvalidRiskLimitsError,
    RiskLimits,
    limits_from_toml,
    load_limits,
    load_plan_limits_f7_f8,
)
from trading.risk.liquidation import adverse_distance, isolated_liquidation_price
from trading.risk.models import (
    AccountState,
    CostModel,
    EntryProposal,
    LiquidationModel,
    MarginMode,
    MarketSnapshot,
    MarketType,
    OpenPosition,
    PerpetualTerms,
    Side,
)
from trading.risk.periods import day_start, week_start
from trading.risk.sizing import effective_leverage, size_by_risk, trade_risk, unit_risk

__all__ = [
    "AccountState",
    "AccountStatus",
    "ConditionsStatus",
    "CostModel",
    "EntryProposal",
    "ExtendedLimits",
    "InvalidRiskLimitsError",
    "LiquidationModel",
    "MacroEvent",
    "MacroEventKind",
    "MarginMode",
    "MarketConditions",
    "MarketSnapshot",
    "MarketType",
    "OpenPosition",
    "PerpetualTerms",
    "RiskDecision",
    "RiskLimits",
    "Side",
    "SymbolConditions",
    "Veto",
    "VetoExplanation",
    "VetoReason",
    "adverse_distance",
    "assess_account",
    "assess_conditions",
    "day_start",
    "effective_leverage",
    "evaluate_entry",
    "evaluate_entry_v1",
    "explain",
    "explain_decision",
    "exposure_vetoes",
    "extended_limits_from_toml",
    "funding_vetoes",
    "isolated_liquidation_price",
    "limits_from_toml",
    "load_extended_limits",
    "load_extended_limits_v1_propuesto",
    "load_limits",
    "load_plan_limits_f7_f8",
    "size_by_risk",
    "symbol_vetoes",
    "trade_risk",
    "unit_risk",
    "week_start",
]
