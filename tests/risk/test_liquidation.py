"""Precio de liquidación estimado en margen aislado."""

from decimal import Decimal

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from trading.risk import Side, adverse_distance, isolated_liquidation_price
from trading.risk.models import RISK_DECIMAL_CONTEXT


def _lp(
    side: Side,
    *,
    quantity: str = "1",
    entry: str = "100",
    margin: str = "10",
    mmr: str = "0",
    cum: str = "0",
) -> Decimal | None:
    return isolated_liquidation_price(
        side=side,
        quantity=Decimal(quantity),
        entry_price=Decimal(entry),
        isolated_margin=Decimal(margin),
        maintenance_margin_rate=Decimal(mmr),
        maintenance_amount=Decimal(cum),
    )


def test_without_maintenance_margin_liquidation_is_entry_times_one_minus_inverse_leverage() -> None:
    # 5x: margen de 20 sobre 100 de nocional; sin margen de mantenimiento liquida a -20% / +20%.
    assert _lp(Side.LONG, margin="20") == Decimal(80)
    assert _lp(Side.SHORT, margin="20") == Decimal(120)


def test_matches_published_formula_with_maintenance_margin() -> None:
    # 10x con MMR 0.4%: LP = (WB - Q*EP) / (Q*MMR - Q) para el largo.
    ctx = RISK_DECIMAL_CONTEXT
    assert _lp(Side.LONG, mmr="0.004") == ctx.divide(Decimal(-90), Decimal("-0.996"))
    assert _lp(Side.SHORT, mmr="0.004") == ctx.divide(Decimal(110), Decimal("1.004"))


def test_maintenance_amount_moves_liquidation_away() -> None:
    assert _lp(Side.LONG, cum="5") == Decimal(85)
    assert _lp(Side.SHORT, cum="5") == Decimal(115)


@pytest.mark.parametrize("mmr", ["0", "0.004"])
def test_fully_collateralised_long_cannot_be_liquidated(mmr: str) -> None:
    assert _lp(Side.LONG, margin="100", mmr=mmr) is None


def test_undercollateralised_position_is_liquidated_on_entry() -> None:
    # Margen por debajo del de mantenimiento: liquidación al otro lado de la entrada.
    long_lp = _lp(Side.LONG, margin="0.1", mmr="0.01")
    short_lp = _lp(Side.SHORT, margin="0.1", mmr="0.01")
    assert long_lp is not None
    assert short_lp is not None
    assert adverse_distance(Side.LONG, Decimal(100), long_lp) < 0
    assert adverse_distance(Side.SHORT, Decimal(100), short_lp) < 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"quantity": "0"},
        {"entry": "0"},
        {"margin": "-1"},
        {"mmr": "1"},
        {"mmr": "-0.001"},
        {"cum": "-1"},
    ],
)
def test_invalid_inputs_raise(kwargs: dict[str, str]) -> None:
    with pytest.raises(ValueError):  # noqa: PT011 - cualquier entrada inválida
        _lp(Side.LONG, **kwargs)


leverages = st.decimals(min_value=Decimal(1), max_value=Decimal(125), places=1)
mmrs = st.decimals(min_value=Decimal(0), max_value=Decimal("0.05"), places=4)
entries = st.decimals(min_value=Decimal(1), max_value=Decimal(200000), places=2)
quantities = st.decimals(min_value=Decimal("0.001"), max_value=Decimal(100), places=3)


@given(
    side=st.sampled_from(Side),
    entry=entries,
    quantity=quantities,
    low=leverages,
    high=leverages,
    mmr=mmrs,
)
def test_more_exchange_leverage_never_moves_liquidation_away(
    side: Side, entry: Decimal, quantity: Decimal, low: Decimal, high: Decimal, mmr: Decimal
) -> None:
    assume(low < high)
    notional = quantity * entry
    args = {
        "side": side,
        "quantity": quantity,
        "entry_price": entry,
        "maintenance_margin_rate": mmr,
        "maintenance_amount": Decimal(0),
    }
    lp_low = isolated_liquidation_price(isolated_margin=notional / low, **args)  # type: ignore[arg-type]
    lp_high = isolated_liquidation_price(isolated_margin=notional / high, **args)  # type: ignore[arg-type]
    assert lp_high is not None
    distance_high = adverse_distance(side, entry, lp_high)
    if lp_low is None:
        return
    assert adverse_distance(side, entry, lp_low) >= distance_high
    # Con margen por encima del de mantenimiento, la liquidación queda en el lado adverso.
    if notional / high > notional * mmr:
        assert distance_high > 0
