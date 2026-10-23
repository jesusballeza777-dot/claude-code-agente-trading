"""Datos base de los tests del motor de riesgo: cuenta de USD 1,500 sin pérdidas ni posiciones."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading.risk import (
    AccountState,
    CostModel,
    EntryProposal,
    LiquidationModel,
    MarginMode,
    MarketSnapshot,
    MarketType,
    PerpetualTerms,
    RiskLimits,
    Side,
    load_plan_limits_f7_f8,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
FOUR_HOURS = timedelta(hours=4)
ZERO_COSTS = CostModel(fee_rate=Decimal(0), slippage_rate=Decimal(0))
CAPITAL = Decimal(1500)


@pytest.fixture
def limits() -> RiskLimits:
    return load_plan_limits_f7_f8()


@pytest.fixture
def account() -> AccountState:
    return AccountState(
        equity=CAPITAL,
        peak_equity=CAPITAL,
        day_start_equity=CAPITAL,
        week_start_equity=CAPITAL,
    )


@pytest.fixture
def market() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="BTCUSDT", price_time=NOW, last_bar_close_time=NOW, bar_interval=FOUR_HOURS
    )


@pytest.fixture
def perp_terms() -> PerpetualTerms:
    return PerpetualTerms(
        margin_mode=MarginMode.ISOLATED,
        exchange_leverage=Decimal(2),
        maintenance_margin_rate=Decimal("0.004"),
        maintenance_amount=Decimal(0),
        liquidation_model=LiquidationModel.BINANCE_USDM_ISOLATED,
    )


@pytest.fixture
def long_btc(perp_terms: PerpetualTerms) -> EntryProposal:
    """Largo en el perpetuo de BTC con stop al 2%: USD 375 de nocional y USD 7.50 de riesgo."""
    return EntryProposal(
        strategy_id="H2",
        symbol="BTCUSDT",
        base_asset="BTC",
        market=MarketType.PERPETUAL,
        side=Side.LONG,
        entry_price=Decimal(60000),
        stop_price=Decimal(58800),
        quantity=Decimal("0.00625"),
        perpetual=perp_terms,
    )


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def zero_costs() -> CostModel:
    return ZERO_COSTS
