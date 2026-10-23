"""Tamaño de posición por riesgo.

El riesgo de una operación es la pérdida si salta el stop, con comisiones y slippage en la
entrada y en la salida. Con costes cero reproduce la tabla del plan §3 (riesgo / distancia
al stop). Las divisiones redondean hacia abajo para que el tamaño nunca supere el presupuesto.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal, localcontext

from trading.risk.models import CostModel, in_risk_context, require_decimal, require_positive


@in_risk_context
def unit_risk(entry_price: Decimal, stop_price: Decimal, costs: CostModel) -> Decimal:
    """Pérdida por unidad si salta el stop: distancia al stop más costes de entrada y salida."""
    require_positive("entry_price", entry_price)
    require_positive("stop_price", stop_price)
    if entry_price == stop_price:
        raise ValueError("el stop no puede coincidir con la entrada")
    per_side = costs.fee_rate + costs.slippage_rate
    return abs(entry_price - stop_price) + (entry_price + stop_price) * per_side


@in_risk_context
def trade_risk(
    quantity: Decimal, entry_price: Decimal, stop_price: Decimal, costs: CostModel
) -> Decimal:
    """Pérdida total de la operación si salta el stop."""
    return abs(require_decimal("quantity", quantity)) * unit_risk(entry_price, stop_price, costs)


@in_risk_context
def size_by_risk(
    *,
    equity: Decimal,
    entry_price: Decimal,
    stop_price: Decimal,
    risk_fraction: Decimal,
    costs: CostModel,
    max_notional: Decimal | None = None,
    quantity_step: Decimal | None = None,
) -> Decimal:
    """Cantidad máxima cuyo riesgo no supera `risk_fraction` del capital.

    `max_notional` acota el nocional (por ejemplo, el apalancamiento que queda disponible).
    `quantity_step` redondea hacia abajo al paso de cantidad del contrato. Devuelve 0 si no
    hay presupuesto; nunca un valor negativo.
    """
    require_decimal("equity", equity)
    require_positive("risk_fraction", risk_fraction)
    per_unit = unit_risk(entry_price, stop_price, costs)
    if equity <= 0:
        return Decimal(0)
    with localcontext() as ctx:
        ctx.rounding = ROUND_FLOOR
        quantity = (equity * risk_fraction) / per_unit
        if max_notional is not None:
            cap = max(require_decimal("max_notional", max_notional), Decimal(0))
            quantity = min(quantity, cap / entry_price)
        if quantity_step is not None:
            step = require_positive("quantity_step", quantity_step)
            quantity = (quantity / step).to_integral_value(rounding=ROUND_FLOOR) * step
    return quantity


@in_risk_context
def effective_leverage(total_notional: Decimal, equity: Decimal) -> Decimal:
    """Apalancamiento efectivo: nocional total / capital (plan §3)."""
    return require_decimal("total_notional", total_notional) / require_positive("equity", equity)
