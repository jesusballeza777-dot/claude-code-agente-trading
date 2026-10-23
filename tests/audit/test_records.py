"""Registros de auditoría: cálculos de cada operación e invariantes de las decisiones."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from factories import T0, make_trade
from trading.audit import DecisionAction, DecisionRecord, OwnerResponse
from trading.risk import Side


def test_long_trade_pnl_and_r() -> None:
    trade = make_trade()
    assert trade.gross_pnl == Decimal(12)
    assert trade.net_pnl == Decimal("11.2")
    assert trade.r_multiple == Decimal("11.2") / Decimal(12)


def test_short_trade_pnl() -> None:
    short = make_trade(
        side=Side.SHORT,
        exit_price=Decimal(58800),
        expected_exit_price=Decimal(58800),
        stop_price=Decimal(61200),
        fees=Decimal(0),
        funding=Decimal("-0.5"),  # funding cobrado suma
    )
    assert short.gross_pnl == Decimal(12)
    assert short.net_pnl == Decimal("12.5")


def test_slippage_is_positive_when_worse_in_both_directions() -> None:
    long_ = make_trade(entry_price=Decimal(60030), exit_price=Decimal("61169.4"))
    assert long_.entry_slippage_bps == Decimal(5)
    assert long_.exit_slippage_bps == Decimal(5)
    short = make_trade(
        side=Side.SHORT,
        stop_price=Decimal(61200),
        entry_price=Decimal(59970),
        exit_price=Decimal(58800),
        expected_exit_price=Decimal(58800),
    )
    assert short.entry_slippage_bps == Decimal(5)
    assert short.exit_slippage_bps == Decimal(0)


def test_excursions_in_r() -> None:
    trade = make_trade(max_adverse_price=Decimal(59400), max_favorable_price=Decimal(62400))
    assert trade.mae_r == Decimal("-0.5")
    assert trade.mfe_r == Decimal(2)
    never_against = make_trade(max_adverse_price=Decimal(60100), max_favorable_price=Decimal(59000))
    assert never_against.mae_r == 0
    assert never_against.mfe_r == 0
    assert make_trade().mae_r is None
    assert make_trade().mfe_r is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"closed_at": T0 - timedelta(seconds=1)},
        {"stop_price": Decimal(61000)},
        {"fees": Decimal("-0.01")},
        {"quantity": Decimal(0)},
        {"planned_risk": Decimal(0)},
        {"trade_id": ""},
        {"max_adverse_price": Decimal(0)},
        {"opened_at": datetime(2026, 1, 5, 12, 0)},  # noqa: DTZ001 - sin zona horaria
    ],
)
def test_invalid_trades_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError):  # noqa: PT011 - cualquier campo inválido
        make_trade(**overrides)


def _decision(**overrides: Any) -> DecisionRecord:
    fields: dict[str, Any] = {
        "decision_id": "d1",
        "decided_at": T0,
        "strategy_id": "H2",
        "symbol": "BTCUSDT",
        "action": DecisionAction.ENTER_LONG,
        "rationale": "ruptura con volatilidad creciente",
    }
    fields.update(overrides)
    return DecisionRecord(**fields)


def test_executed_decision() -> None:
    decision = _decision(trade_id="t1", owner_response=OwnerResponse.APPROVED)
    assert decision.executed
    assert decision.is_entry
    assert not _decision(action=DecisionAction.ABSTAIN).is_entry


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"action": DecisionAction.HOLD}, "entrada"),
        ({"risk_vetoes": ("RISK_PER_TRADE",)}, "vetada"),
        ({"owner_response": OwnerResponse.REJECTED}, "REJECTED"),
        ({"owner_response": OwnerResponse.EXPIRED}, "EXPIRED"),
        ({"owner_response": OwnerResponse.VETOED}, "VETOED"),
        ({"counterfactual_r": Decimal(1)}, "contrafactual"),
    ],
)
def test_impossible_executions_are_rejected(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _decision(trade_id="t1", **overrides)


def test_decision_requires_timezone_and_ids() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        _decision(decided_at=datetime(2026, 1, 5))  # noqa: DTZ001 - caso que debe rechazarse
    with pytest.raises(ValueError, match="decision_id"):
        _decision(decision_id=" d1")
    with pytest.raises(ValueError, match="trade_id"):
        _decision(trade_id="")
    with pytest.raises(TypeError):
        _decision(counterfactual_r=0.5)
