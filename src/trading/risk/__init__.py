"""Motor de riesgo: código puro, sin red, con veto absoluto (CLAUDE.md, regla 4).

Los límites vienen de `limits_f7_f8.toml` (plan maestro v2 §3) y no pueden superar los
techos del plan definidos en `limits.py`. Decisiones de diseño: ADR-007.
"""

from trading.risk.engine import (
    AccountStatus,
    RiskDecision,
    Veto,
    VetoReason,
    assess_account,
    evaluate_entry,
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
    MarginMode,
    MarketSnapshot,
    MarketType,
    OpenPosition,
    PerpetualTerms,
    Side,
)
from trading.risk.sizing import effective_leverage, size_by_risk, trade_risk, unit_risk

__all__ = [
    "AccountState",
    "AccountStatus",
    "CostModel",
    "EntryProposal",
    "InvalidRiskLimitsError",
    "MarginMode",
    "MarketSnapshot",
    "MarketType",
    "OpenPosition",
    "PerpetualTerms",
    "RiskDecision",
    "RiskLimits",
    "Side",
    "Veto",
    "VetoReason",
    "adverse_distance",
    "assess_account",
    "effective_leverage",
    "evaluate_entry",
    "isolated_liquidation_price",
    "limits_from_toml",
    "load_limits",
    "load_plan_limits_f7_f8",
    "size_by_risk",
    "trade_risk",
    "unit_risk",
]
