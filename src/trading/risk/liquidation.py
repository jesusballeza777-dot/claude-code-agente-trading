"""Estimación del precio de liquidación en margen aislado (perpetuos USDⓈ-M, modo one-way).

Fórmula publicada por Binance para una sola posición en margen aislado:

    LP = (WB + cum - s * Q * EP) / (Q * MMR - s * Q)      s = +1 largo, -1 corto

WB: margen aislado de la posición; cum: importe de mantenimiento del tramo; Q: cantidad;
EP: precio de entrada; MMR: tasa de margen de mantenimiento del tramo.
Es una estimación previa a la operación: por verificar en la F6 contra la calculadora del
exchange y contra el precio de liquidación que devuelva la posición real.
"""

from __future__ import annotations

from decimal import Decimal

from trading.risk.models import (
    Side,
    in_risk_context,
    require_decimal,
    require_non_negative,
    require_positive,
)


@in_risk_context
def isolated_liquidation_price(
    *,
    side: Side,
    quantity: Decimal,
    entry_price: Decimal,
    isolated_margin: Decimal,
    maintenance_margin_rate: Decimal,
    maintenance_amount: Decimal,
) -> Decimal | None:
    """Precio de liquidación estimado, o None si un largo no puede liquidarse con precio > 0."""
    q = require_positive("quantity", quantity)
    ep = require_positive("entry_price", entry_price)
    wb = require_non_negative("isolated_margin", isolated_margin)
    mmr = require_decimal("maintenance_margin_rate", maintenance_margin_rate)
    if not Decimal(0) <= mmr < Decimal(1):
        raise ValueError("maintenance_margin_rate debe estar en [0, 1)")
    cum = require_non_negative("maintenance_amount", maintenance_amount)
    s = Decimal(1) if side is Side.LONG else Decimal(-1)
    price = (wb + cum - s * q * ep) / (q * mmr - s * q)
    if price <= 0:
        return None
    return price


@in_risk_context
def adverse_distance(side: Side, entry_price: Decimal, liquidation_price: Decimal) -> Decimal:
    """Distancia en precio de la entrada a la liquidación, en la dirección adversa.

    Negativa o cero si la posición quedaría liquidada nada más abrirse.
    """
    ep = require_positive("entry_price", entry_price)
    if side is Side.LONG:
        return ep - liquidation_price
    return liquidation_price - ep
