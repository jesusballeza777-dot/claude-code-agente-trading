"""Fábricas de registros para los tests de auditoría y reportes."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from trading.audit import ExitReason, TradeRecord, TradingMode, Venue
from trading.risk import Side

T0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


def make_trade(**overrides: Any) -> TradeRecord:
    """Largo en BTC: 0.01 BTC de 60,000 a 61,200 con stop en 58,800 y 1 R = USD 12.

    Bruto USD 12, comisiones 0.60, funding 0.20 pagado: neto USD 11.20 (0.9333 R).
    """
    fields: dict[str, Any] = {
        "trade_id": "t1",
        "venue": Venue.BINANCE,
        "mode": TradingMode.LIVE,
        "strategy_id": "H2",
        "symbol": "BTCUSDT",
        "base_asset": "BTC",
        "side": Side.LONG,
        "opened_at": T0,
        "closed_at": T0 + timedelta(hours=8),
        "quantity": Decimal("0.01"),
        "entry_price": Decimal(60000),
        "exit_price": Decimal(61200),
        "expected_entry_price": Decimal(60000),
        "expected_exit_price": Decimal(61200),
        "stop_price": Decimal(58800),
        "planned_risk": Decimal(12),
        "fees": Decimal("0.6"),
        "funding": Decimal("0.2"),
        "exit_reason": ExitReason.SIGNAL,
    }
    fields.update(overrides)
    return TradeRecord(**fields)


def r_trade(trade_id: str, r: Decimal | int, closed_hours: int, **overrides: Any) -> TradeRecord:
    """Operación sin costes cuyo resultado es exactamente `r` R (1 R = USD 10)."""
    r = Decimal(r)
    return make_trade(
        trade_id=trade_id,
        quantity=Decimal(1),
        entry_price=Decimal(100),
        expected_entry_price=Decimal(100),
        exit_price=Decimal(100) + 10 * r,
        expected_exit_price=Decimal(100) + 10 * r,
        stop_price=Decimal(90),
        planned_risk=Decimal(10),
        fees=Decimal(0),
        funding=Decimal(0),
        closed_at=T0 + timedelta(hours=closed_hours),
        **overrides,
    )
