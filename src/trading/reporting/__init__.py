"""Cálculos que alimentan la app (ADR-010): rendimiento, embudo de decisiones, fichas de
aprendizaje y reporte fiscal. Código determinista; la app solo muestra estos resultados."""

from trading.reporting.decisions import (
    DecisionFunnel,
    FilterValue,
    ValueAdded,
    decision_funnel,
    value_added,
)
from trading.reporting.performance import (
    PerformanceSummary,
    rolling_expectancy,
    summarize,
    summarize_by,
)
from trading.reporting.review import ReviewTag, TagImpact, TradeReview, review_trade, tag_impact
from trading.reporting.tax import (
    MissingFxRateError,
    TaxRow,
    TaxTotals,
    fiscal_date,
    fx_rate_for,
    tax_rows,
    tax_totals,
    to_csv,
)

__all__ = [
    "DecisionFunnel",
    "FilterValue",
    "MissingFxRateError",
    "PerformanceSummary",
    "ReviewTag",
    "TagImpact",
    "TaxRow",
    "TaxTotals",
    "TradeReview",
    "ValueAdded",
    "decision_funnel",
    "fiscal_date",
    "fx_rate_for",
    "review_trade",
    "rolling_expectancy",
    "summarize",
    "summarize_by",
    "tag_impact",
    "tax_rows",
    "tax_totals",
    "to_csv",
    "value_added",
]
