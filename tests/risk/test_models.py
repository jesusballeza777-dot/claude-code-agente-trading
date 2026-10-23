"""Validación de entradas: una entrada mal formada no llega a evaluarse (fallo cerrado)."""

from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from trading.risk import (
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


def test_perpetual_requires_terms(long_btc: EntryProposal) -> None:
    with pytest.raises(ValueError, match="PerpetualTerms"):
        replace(long_btc, perpetual=None)


def test_spot_rejects_terms(long_btc: EntryProposal) -> None:
    with pytest.raises(ValueError, match="spot"):
        replace(long_btc, market=MarketType.SPOT)


@pytest.mark.parametrize(
    "changes",
    [
        {"entry_price": Decimal(0)},
        {"stop_price": Decimal(-1)},
        {"quantity": Decimal("NaN")},
        {"symbol": ""},
        {"base_asset": " BTC"},
        {"strategy_id": 7},
    ],
)
def test_proposal_validation(long_btc: EntryProposal, changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):  # noqa: PT011 - cualquier campo inválido
        replace(long_btc, **changes)


def test_proposal_rejects_floats(long_btc: EntryProposal) -> None:
    with pytest.raises(TypeError):
        replace(long_btc, entry_price=60000.0)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"exchange_leverage": Decimal("0.5")},
        {"maintenance_margin_rate": Decimal(1)},
        {"maintenance_margin_rate": Decimal("-0.1")},
        {"maintenance_amount": Decimal(-1)},
    ],
)
def test_perpetual_terms_validation(perp_terms: PerpetualTerms, changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        replace(perp_terms, **changes)


@pytest.mark.parametrize(
    ("fee", "slippage"), [(Decimal(1), Decimal(0)), (Decimal(0), Decimal("-0.0001"))]
)
def test_cost_model_validation(fee: Decimal, slippage: Decimal) -> None:
    with pytest.raises(ValueError, match="_rate"):
        CostModel(fee_rate=fee, slippage_rate=slippage)


def test_open_position_validation() -> None:
    with pytest.raises(ValueError, match="notional"):
        OpenPosition("SOLUSDT", "SOL", Side.LONG, notional=Decimal(-1), risk_to_stop=Decimal(0))
    with pytest.raises(ValueError, match="risk_to_stop"):
        OpenPosition("SOLUSDT", "SOL", Side.LONG, notional=Decimal(1), risk_to_stop=Decimal(-1))


def test_account_validation_and_totals(account: AccountState) -> None:
    with pytest.raises(ValueError, match="peak_equity"):
        replace(account, peak_equity=Decimal(0))
    positions = (
        OpenPosition("SOLUSDT", "SOL", Side.LONG, notional=Decimal(300), risk_to_stop=Decimal(5)),
        OpenPosition("BTCUSDT", "BTC", Side.SHORT, notional=Decimal(200), risk_to_stop=Decimal(2)),
    )
    with_positions = replace(account, open_positions=positions)
    assert with_positions.open_notional == Decimal(500)
    assert with_positions.open_risk == Decimal(7)
    assert account.open_notional == 0


def test_market_snapshot_requires_timezone(market: MarketSnapshot) -> None:
    naive = datetime(2026, 10, 23, 12, 0)  # noqa: DTZ001 - caso que debe rechazarse
    with pytest.raises(ValueError, match="zona horaria"):
        replace(market, price_time=naive)
    with pytest.raises(TypeError, match="datetime"):
        replace(market, last_bar_close_time="2026-10-23")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="bar_interval"):
        replace(market, bar_interval=timedelta(0))


def test_margin_mode_values() -> None:
    assert {m.value for m in MarginMode} == {"ISOLATED", "CROSS"}


def test_perpetual_terms_require_a_liquidation_model(perp_terms: PerpetualTerms) -> None:
    with pytest.raises(TypeError, match="LiquidationModel"):
        replace(perp_terms, liquidation_model="BINANCE_USDM_ISOLATED")  # type: ignore[arg-type]


def test_min_notional_cannot_be_negative(long_btc: EntryProposal) -> None:
    with pytest.raises(ValueError, match="min_notional"):
        replace(long_btc, min_notional=Decimal(-1))
