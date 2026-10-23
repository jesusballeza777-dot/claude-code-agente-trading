"""Reporte para el contador: una fila por operación, en USD y en MXN al FIX de Banxico.

El tipo de cambio es el FIX publicado por Banxico (serie SF43718 del SIE) en la fecha fiscal
(Ciudad de México) del cierre, o el último publicado antes. Si no hay tipo de cambio para esa
fecha, la columna MXN queda vacía y marcada "por completar": nunca se inventa un tipo.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from trading.reporting.tax import fiscal_date

CENT: Final = Decimal("0.01")
PENDING: Final = "por completar"
HEADER: Final = (
    "id_operacion",
    "fecha_fiscal_cdmx",
    "apertura_utc",
    "cierre_utc",
    "activo",
    "tipo",
    "direccion",
    "cantidad",
    "precio_entrada",
    "precio_salida",
    "comisiones_usd",
    "funding_usd",
    "resultado_neto_usd",
    "fix_fecha",
    "fix_mxn_por_usd",
    "resultado_neto_mxn",
)


@dataclass(frozen=True, slots=True)
class AccountantTrade:
    trade_id: str
    opened_at: datetime
    closed_at: datetime
    symbol: str
    instrument: str  # "spot" o "perpetuo"
    side: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    fees: Decimal
    funding: Decimal  # positivo = pagado
    net_pnl: Decimal


@dataclass(frozen=True, slots=True)
class AccountantTotals:
    trades: int
    net_usd: Decimal
    fees_usd: Decimal
    funding_usd: Decimal
    net_mxn: Decimal | None  # None si falta algún tipo de cambio
    pending_fx: int


def rows(
    trades: Sequence[AccountantTrade],
    fix: Mapping[date, Decimal],
    *,
    max_lookback_days: int = 7,
) -> list[list[str]]:
    out = []
    for trade in sorted(trades, key=lambda t: (t.closed_at, t.trade_id)):
        day = fiscal_date(trade.closed_at)
        fx = _fix_for(day, fix, max_lookback_days)
        net = _cents(trade.net_pnl)
        out.append(
            [
                trade.trade_id,
                day.isoformat(),
                trade.opened_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                trade.closed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                trade.symbol,
                trade.instrument,
                trade.side,
                str(trade.quantity),
                str(trade.entry_price),
                str(trade.exit_price),
                str(_cents(trade.fees)),
                str(_cents(trade.funding)),
                str(net),
                fx[0].isoformat() if fx else PENDING,
                str(fx[1]) if fx else PENDING,
                str(_cents(net * fx[1])) if fx else PENDING,
            ]
        )
    return out


def totals(table: Sequence[Sequence[str]]) -> AccountantTotals:
    pending = sum(1 for r in table if r[-1] == PENDING)
    return AccountantTotals(
        trades=len(table),
        net_usd=sum((Decimal(r[12]) for r in table), Decimal("0.00")),
        fees_usd=sum((Decimal(r[10]) for r in table), Decimal("0.00")),
        funding_usd=sum((Decimal(r[11]) for r in table), Decimal("0.00")),
        net_mxn=None if pending else sum((Decimal(r[15]) for r in table), Decimal("0.00")),
        pending_fx=pending,
    )


def to_csv(table: Sequence[Sequence[str]], *, title: str = "") -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    if title:
        writer.writerow([title])
    writer.writerow(HEADER)
    writer.writerows(table)
    return buffer.getvalue().encode("utf-8")


def _fix_for(day: date, fix: Mapping[date, Decimal], lookback: int) -> tuple[date, Decimal] | None:
    for offset in range(lookback + 1):
        candidate = day - timedelta(days=offset)
        if candidate in fix and fix[candidate] > 0:
            return candidate, fix[candidate]
    return None


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_EVEN)
