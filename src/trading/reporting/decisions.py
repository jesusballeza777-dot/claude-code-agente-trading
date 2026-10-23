"""Embudo de decisiones y valor añadido de cada filtro (pantalla "Decisiones" de la app).

El valor añadido compara lo que se ejecutó con el resultado contrafactual, medido en sombra,
de lo que se descartó: si lo descartado rinde igual que lo ejecutado, ese filtro no aporta.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from trading.audit.records import (
    BLOCKING_RESPONSES,
    DecisionAction,
    DecisionRecord,
    OwnerResponse,
    TradeRecord,
)


@dataclass(frozen=True, slots=True)
class DecisionFunnel:
    total: int
    by_action: dict[DecisionAction, int]
    entries_proposed: int
    risk_vetoed: int
    risk_veto_reasons: dict[str, int]
    owner_responses: dict[OwnerResponse, int]
    executed: int


@dataclass(frozen=True, slots=True)
class FilterValue:
    """Resultado medio en R de lo descartado por un filtro, y cuántos casos tienen medida."""

    measured: int
    mean_r: Decimal | None


@dataclass(frozen=True, slots=True)
class ValueAdded:
    executed: FilterValue
    skipped_by_claude: FilterValue
    vetoed_by_risk: FilterValue
    blocked_by_owner: FilterValue


def decision_funnel(decisions: Iterable[DecisionRecord]) -> DecisionFunnel:
    items = list(decisions)
    entries = [d for d in items if d.is_entry]
    vetoed = [d for d in entries if d.risk_vetoes]
    reasons: Counter[str] = Counter(reason for d in vetoed for reason in d.risk_vetoes)
    return DecisionFunnel(
        total=len(items),
        by_action={action: sum(d.action is action for d in items) for action in DecisionAction},
        entries_proposed=len(entries),
        risk_vetoed=len(vetoed),
        risk_veto_reasons=dict(sorted(reasons.items())),
        owner_responses={r: sum(d.owner_response is r for d in entries) for r in OwnerResponse},
        executed=sum(d.executed for d in items),
    )


def _filter_value(values: Sequence[Decimal]) -> FilterValue:
    mean = sum(values, Decimal(0)) / len(values) if values else None
    return FilterValue(measured=len(values), mean_r=mean)


def value_added(decisions: Iterable[DecisionRecord], trades: Iterable[TradeRecord]) -> ValueAdded:
    items = list(decisions)
    r_by_trade = {t.trade_id: t.r_multiple for t in trades}
    executed = [r_by_trade[d.trade_id] for d in items if d.trade_id in r_by_trade]

    def counterfactuals(selected: Iterable[DecisionRecord]) -> list[Decimal]:
        return [d.counterfactual_r for d in selected if d.counterfactual_r is not None]

    return ValueAdded(
        executed=_filter_value(executed),
        skipped_by_claude=_filter_value(
            counterfactuals(
                d for d in items if d.action in (DecisionAction.HOLD, DecisionAction.ABSTAIN)
            )
        ),
        vetoed_by_risk=_filter_value(counterfactuals(d for d in items if d.risk_vetoes)),
        blocked_by_owner=_filter_value(
            counterfactuals(
                d for d in items if not d.risk_vetoes and d.owner_response in BLOCKING_RESPONSES
            )
        ),
    )
