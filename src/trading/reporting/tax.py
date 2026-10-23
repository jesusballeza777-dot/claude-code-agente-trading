"""Reporte fiscal de operaciones reales (pantalla "Reportes" de la app).

Entrega los datos; la interpretación fiscal es del contador. Convenciones **por validar
con el contador** (docs/f1-verificacion-plataforma.md §4):
- Solo operaciones en modo LIVE; las de sombra y backtest nunca entran.
- El año y la fecha fiscal son los del cierre en hora de Ciudad de México.
- Tipo de cambio: el último publicado en o antes de esa fecha (p. ej., FIX de Banxico),
  como máximo `max_lookback_days` días antes; si no hay, el reporte falla en vez de inventarlo.
- Importes en USD redondeados al centavo por fila; MXN = USD redondeado por el tipo de cambio,
  redondeado al centavo. Los totales suman las filas, para que cuadren con el CSV.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from zoneinfo import ZoneInfo

from trading.audit.records import TradeRecord, TradingMode

MEXICO_CITY = ZoneInfo("America/Mexico_City")
CENT = Decimal("0.01")


class MissingFxRateError(LookupError):
    """No hay tipo de cambio publicado para la fecha (ni en los días anteriores permitidos)."""


@dataclass(frozen=True, slots=True)
class TaxRow:
    trade_id: str
    venue: str
    symbol: str
    side: str
    opened_at_utc: datetime
    closed_at_utc: datetime
    fiscal_date: date
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl_usd: Decimal
    fees_usd: Decimal
    funding_usd: Decimal
    net_pnl_usd: Decimal
    fx_date: date
    fx_rate: Decimal
    net_pnl_mxn: Decimal


@dataclass(frozen=True, slots=True)
class TaxTotals:
    trades: int
    gains_usd: Decimal
    losses_usd: Decimal
    net_usd: Decimal
    fees_usd: Decimal
    funding_usd: Decimal
    gains_mxn: Decimal
    losses_mxn: Decimal
    net_mxn: Decimal


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_EVEN)


def fiscal_date(moment: datetime) -> date:
    """Fecha en hora de Ciudad de México."""
    return moment.astimezone(MEXICO_CITY).date()


def fx_rate_for(
    day: date, rates: Mapping[date, Decimal], max_lookback_days: int = 7
) -> tuple[date, Decimal]:
    """Último tipo de cambio publicado en o antes de `day`."""
    for offset in range(max_lookback_days + 1):
        candidate = day - timedelta(days=offset)
        rate = rates.get(candidate)
        if rate is not None:
            if rate <= 0:
                raise ValueError(f"tipo de cambio no positivo el {candidate}")
            return candidate, rate
    raise MissingFxRateError(
        f"sin tipo de cambio entre {day - timedelta(max_lookback_days)} y {day}"
    )


def tax_rows(
    trades: Iterable[TradeRecord],
    rates: Mapping[date, Decimal],
    year: int,
    max_lookback_days: int = 7,
) -> list[TaxRow]:
    """Filas del año fiscal `year`, en orden de cierre. Solo operaciones LIVE."""
    rows: list[TaxRow] = []
    selected = (
        t for t in trades if t.mode is TradingMode.LIVE and fiscal_date(t.closed_at).year == year
    )
    for trade in sorted(selected, key=lambda t: (t.closed_at, t.trade_id)):
        day = fiscal_date(trade.closed_at)
        fx_day, rate = fx_rate_for(day, rates, max_lookback_days)
        gross = _cents(trade.gross_pnl)
        fees = _cents(trade.fees)
        funding = _cents(trade.funding)
        net = gross - fees - funding
        rows.append(
            TaxRow(
                trade_id=trade.trade_id,
                venue=trade.venue.value,
                symbol=trade.symbol,
                side=trade.side.value,
                opened_at_utc=trade.opened_at.astimezone(ZoneInfo("UTC")),
                closed_at_utc=trade.closed_at.astimezone(ZoneInfo("UTC")),
                fiscal_date=day,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                gross_pnl_usd=gross,
                fees_usd=fees,
                funding_usd=funding,
                net_pnl_usd=net,
                fx_date=fx_day,
                fx_rate=rate,
                net_pnl_mxn=_cents(net * rate),
            )
        )
    return rows


def tax_totals(rows: Iterable[TaxRow]) -> TaxTotals:
    items = list(rows)
    zero = Decimal("0.00")
    return TaxTotals(
        trades=len(items),
        gains_usd=sum((r.net_pnl_usd for r in items if r.net_pnl_usd > 0), zero),
        losses_usd=sum((r.net_pnl_usd for r in items if r.net_pnl_usd < 0), zero),
        net_usd=sum((r.net_pnl_usd for r in items), zero),
        fees_usd=sum((r.fees_usd for r in items), zero),
        funding_usd=sum((r.funding_usd for r in items), zero),
        gains_mxn=sum((r.net_pnl_mxn for r in items if r.net_pnl_mxn > 0), zero),
        losses_mxn=sum((r.net_pnl_mxn for r in items if r.net_pnl_mxn < 0), zero),
        net_mxn=sum((r.net_pnl_mxn for r in items), zero),
    )


CSV_HEADER = (
    "id_operacion",
    "plataforma",
    "instrumento",
    "lado",
    "apertura_utc",
    "cierre_utc",
    "fecha_fiscal_cdmx",
    "cantidad",
    "precio_entrada",
    "precio_salida",
    "pnl_bruto_usd",
    "comisiones_usd",
    "funding_usd",
    "pnl_neto_usd",
    "fecha_tipo_cambio",
    "tipo_cambio_mxn_usd",
    "pnl_neto_mxn",
)


def to_csv(rows: Iterable[TaxRow]) -> str:
    """CSV con cabecera en español, fechas ISO 8601 y decimales con punto."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for r in rows:
        writer.writerow(
            (
                r.trade_id,
                r.venue,
                r.symbol,
                r.side,
                r.opened_at_utc.isoformat(),
                r.closed_at_utc.isoformat(),
                r.fiscal_date.isoformat(),
                str(r.quantity),
                str(r.entry_price),
                str(r.exit_price),
                str(r.gross_pnl_usd),
                str(r.fees_usd),
                str(r.funding_usd),
                str(r.net_pnl_usd),
                r.fx_date.isoformat(),
                str(r.fx_rate),
                str(r.net_pnl_mxn),
            )
        )
    return buffer.getvalue()
