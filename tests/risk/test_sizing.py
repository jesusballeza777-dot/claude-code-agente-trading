"""Tamaño por riesgo: tabla del plan §3, costes, topes y propiedades."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.risk import CostModel, effective_leverage, size_by_risk, trade_risk, unit_risk

ZERO_COSTS = CostModel(fee_rate=Decimal(0), slippage_rate=Decimal(0))
CAPITAL = Decimal(1500)
RISK = Decimal("0.005")


@pytest.mark.parametrize(
    ("stop_distance", "expected_notional", "expected_leverage"),
    [
        (Decimal("0.02"), Decimal(375), Decimal("0.25")),
        (Decimal("0.005"), Decimal(1500), Decimal(1)),
        (Decimal("0.0025"), Decimal(3000), Decimal(2)),
    ],
)
def test_reproduces_plan_table(
    stop_distance: Decimal, expected_notional: Decimal, expected_leverage: Decimal
) -> None:
    entry = Decimal(60000)
    stop = entry * (1 - stop_distance)
    quantity = size_by_risk(
        equity=CAPITAL, entry_price=entry, stop_price=stop, risk_fraction=RISK, costs=ZERO_COSTS
    )
    notional = quantity * entry
    assert notional == expected_notional
    assert effective_leverage(notional, CAPITAL) == expected_leverage
    assert trade_risk(quantity, entry, stop, ZERO_COSTS) == Decimal("7.5")


def test_short_is_symmetric() -> None:
    quantity = size_by_risk(
        equity=CAPITAL,
        entry_price=Decimal(60000),
        stop_price=Decimal(61200),
        risk_fraction=RISK,
        costs=ZERO_COSTS,
    )
    assert quantity * Decimal(60000) == Decimal(375)


def test_costs_are_inside_the_risk_budget() -> None:
    costs = CostModel(fee_rate=Decimal("0.0005"), slippage_rate=Decimal("0.0005"))
    entry, stop = Decimal(60000), Decimal(58800)
    assert unit_risk(entry, stop, costs) == Decimal("1318.8")
    quantity = size_by_risk(
        equity=CAPITAL, entry_price=entry, stop_price=stop, risk_fraction=RISK, costs=costs
    )
    assert quantity < Decimal("0.00625")
    risk = trade_risk(quantity, entry, stop, costs)
    assert risk <= Decimal("7.5")
    assert risk > Decimal("7.4999")


def test_leverage_cap_binds_on_tight_stop() -> None:
    entry = Decimal(60000)
    quantity = size_by_risk(
        equity=CAPITAL,
        entry_price=entry,
        stop_price=Decimal(59940),  # stop al 0.1%: el riesgo pediría USD 7,500 de nocional
        risk_fraction=RISK,
        costs=ZERO_COSTS,
        max_notional=2 * CAPITAL,
    )
    assert quantity * entry == Decimal(3000)


def test_quantity_step_rounds_down() -> None:
    quantity = size_by_risk(
        equity=CAPITAL,
        entry_price=Decimal(60000),
        stop_price=Decimal(58800),
        risk_fraction=RISK,
        costs=ZERO_COSTS,
        quantity_step=Decimal("0.001"),
    )
    assert quantity == Decimal("0.006")


@pytest.mark.parametrize("equity", [Decimal(0), Decimal(-10)])
def test_no_budget_without_equity(equity: Decimal) -> None:
    assert (
        size_by_risk(
            equity=equity,
            entry_price=Decimal(100),
            stop_price=Decimal(98),
            risk_fraction=RISK,
            costs=ZERO_COSTS,
        )
        == 0
    )


def test_negative_notional_cap_gives_zero() -> None:
    quantity = size_by_risk(
        equity=CAPITAL,
        entry_price=Decimal(100),
        stop_price=Decimal(98),
        risk_fraction=RISK,
        costs=ZERO_COSTS,
        max_notional=Decimal(-5),
    )
    assert quantity == 0


@pytest.mark.parametrize(
    ("entry", "stop", "error"),
    [
        (Decimal(100), Decimal(100), ValueError),
        (Decimal(0), Decimal(98), ValueError),
        (Decimal(100), Decimal(-1), ValueError),
        (100.0, Decimal(98), TypeError),
    ],
)
def test_invalid_prices_raise(entry: Decimal, stop: Decimal, error: type[Exception]) -> None:
    with pytest.raises(error):
        unit_risk(entry, stop, ZERO_COSTS)


def test_invalid_risk_fraction_and_step_raise() -> None:
    kwargs = {
        "equity": CAPITAL,
        "entry_price": Decimal(100),
        "stop_price": Decimal(98),
        "costs": ZERO_COSTS,
    }
    with pytest.raises(ValueError, match="risk_fraction"):
        size_by_risk(risk_fraction=Decimal(0), **kwargs)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="quantity_step"):
        size_by_risk(risk_fraction=RISK, quantity_step=Decimal(0), **kwargs)  # type: ignore[arg-type]


def test_effective_leverage_requires_positive_equity() -> None:
    with pytest.raises(ValueError, match="equity"):
        effective_leverage(Decimal(100), Decimal(0))


# --- propiedades -----------------------------------------------------------------------------

prices = st.decimals(min_value=Decimal("0.01"), max_value=Decimal(200000), places=2)
fractions = st.decimals(min_value=Decimal("0.0001"), max_value=Decimal("0.01"), places=4)
rates = st.decimals(min_value=Decimal(0), max_value=Decimal("0.005"), places=5)
equities = st.decimals(min_value=Decimal(1), max_value=Decimal(1_000_000), places=2)
caps = st.none() | st.decimals(min_value=Decimal(0), max_value=Decimal(3_000_000), places=2)
steps = st.none() | st.sampled_from([Decimal("0.001"), Decimal("0.01"), Decimal(1)])


@given(
    equity=equities,
    entry=prices,
    stop=prices,
    risk_fraction=fractions,
    fee=rates,
    slippage=rates,
    cap=caps,
    step=steps,
)
def test_size_never_exceeds_risk_budget_or_notional_cap(
    equity: Decimal,
    entry: Decimal,
    stop: Decimal,
    risk_fraction: Decimal,
    fee: Decimal,
    slippage: Decimal,
    cap: Decimal | None,
    step: Decimal | None,
) -> None:
    if entry == stop:
        return
    costs = CostModel(fee_rate=fee, slippage_rate=slippage)
    quantity = size_by_risk(
        equity=equity,
        entry_price=entry,
        stop_price=stop,
        risk_fraction=risk_fraction,
        costs=costs,
        max_notional=cap,
        quantity_step=step,
    )
    assert quantity >= 0
    assert trade_risk(quantity, entry, stop, costs) <= equity * risk_fraction
    if cap is not None:
        assert quantity * entry <= cap
    if step is not None:
        assert quantity % step == 0
