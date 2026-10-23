"""Embudo de decisiones y valor añadido de Claude, del motor de riesgo y del propietario."""

from decimal import Decimal
from typing import Any

from factories import T0, r_trade
from trading.audit import DecisionAction, DecisionRecord, OwnerResponse
from trading.reporting import decision_funnel, value_added

A = DecisionAction


def _d(decision_id: str, action: DecisionAction, **kw: Any) -> DecisionRecord:
    return DecisionRecord(
        decision_id=decision_id,
        decided_at=T0,
        strategy_id="H2",
        symbol="BTCUSDT",
        action=action,
        rationale="texto",
        **kw,
    )


DECISIONS = [
    _d("1", A.ENTER_LONG, owner_response=OwnerResponse.APPROVED, trade_id="t1"),
    _d(
        "2",
        A.ENTER_SHORT,
        risk_vetoes=("CORRELATED_EXPOSURE", "RISK_PER_TRADE"),
        counterfactual_r=Decimal(-2),
    ),
    _d("3", A.ENTER_LONG, owner_response=OwnerResponse.REJECTED, counterfactual_r=Decimal(-1)),
    _d("4", A.ABSTAIN, counterfactual_r=Decimal("0.5")),
    _d("5", A.HOLD),
    _d("6", A.EXIT),
]


def test_funnel_counts() -> None:
    funnel = decision_funnel(DECISIONS)
    assert funnel.total == 6
    assert funnel.by_action[A.ENTER_LONG] == 2
    assert funnel.by_action[A.ENTER_SHORT] == 1
    assert funnel.by_action[A.ABSTAIN] == funnel.by_action[A.HOLD] == funnel.by_action[A.EXIT] == 1
    assert funnel.entries_proposed == 3
    assert funnel.risk_vetoed == 1
    assert funnel.risk_veto_reasons == {"CORRELATED_EXPOSURE": 1, "RISK_PER_TRADE": 1}
    assert funnel.owner_responses[OwnerResponse.APPROVED] == 1
    assert funnel.owner_responses[OwnerResponse.REJECTED] == 1
    assert funnel.owner_responses[OwnerResponse.NOT_REQUIRED] == 1
    assert funnel.executed == 1


def test_value_added_compares_executed_with_counterfactuals() -> None:
    value = value_added(DECISIONS, [r_trade("t1", Decimal("1.5"), 1)])
    assert (value.executed.measured, value.executed.mean_r) == (1, Decimal("1.5"))
    assert (value.skipped_by_claude.measured, value.skipped_by_claude.mean_r) == (1, Decimal("0.5"))
    assert value.vetoed_by_risk.mean_r == Decimal(-2)
    assert value.blocked_by_owner.mean_r == Decimal(-1)


def test_value_added_without_measurements() -> None:
    value = value_added([], [])
    assert value.executed.measured == 0
    assert value.executed.mean_r is None
