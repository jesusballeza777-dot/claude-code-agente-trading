"""Ficha de aprendizaje de cada operación (pantalla "Aprendizaje" de la app).

Las etiquetas son deterministas: describen lo que pasó con reglas fijas, sin interpretación
del modelo. Agregadas, muestran dónde se pierde dinero (ver docs/app/especificacion.md §5).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from trading.audit.records import ExitReason, TradeRecord

LOSS_BEYOND_R: Decimal = Decimal("-1.1")
RELEVANT_FUNDING_SHARE: Decimal = Decimal("0.10")
GIVEBACK_MFE_R: Decimal = Decimal(2)


class ReviewTag(StrEnum):
    GANADORA = "GANADORA"
    PERDEDORA = "PERDEDORA"
    SLIPPAGE_SOBRE_MODELO = "SLIPPAGE_SOBRE_MODELO"
    PERDIDA_MAYOR_QUE_R = "PERDIDA_MAYOR_QUE_R"
    FUNDING_RELEVANTE = "FUNDING_RELEVANTE"
    GANANCIA_DEVUELTA = "GANANCIA_DEVUELTA"
    STOP_LIMPIO = "STOP_LIMPIO"


@dataclass(frozen=True, slots=True)
class TradeReview:
    trade_id: str
    r_multiple: Decimal
    entry_slippage_bps: Decimal
    exit_slippage_bps: Decimal
    mae_r: Decimal | None
    mfe_r: Decimal | None
    tags: tuple[ReviewTag, ...]


@dataclass(frozen=True, slots=True)
class TagImpact:
    count: int
    total_r: Decimal


def review_trade(trade: TradeRecord, modeled_slippage_bps: Decimal) -> TradeReview:
    """Ficha de una operación.

    `modeled_slippage_bps` es el slippage por lado del modelo de costes.
    """
    r = trade.r_multiple
    tags: list[ReviewTag] = []
    if trade.net_pnl > 0:
        tags.append(ReviewTag.GANADORA)
    elif trade.net_pnl < 0:
        tags.append(ReviewTag.PERDEDORA)
    if max(trade.entry_slippage_bps, trade.exit_slippage_bps) > modeled_slippage_bps:
        tags.append(ReviewTag.SLIPPAGE_SOBRE_MODELO)
    if r < LOSS_BEYOND_R:
        tags.append(ReviewTag.PERDIDA_MAYOR_QUE_R)
    elif trade.exit_reason is ExitReason.STOP:
        tags.append(ReviewTag.STOP_LIMPIO)
    gross = abs(trade.gross_pnl)
    if gross > 0 and abs(trade.funding) > RELEVANT_FUNDING_SHARE * gross:
        tags.append(ReviewTag.FUNDING_RELEVANTE)
    mfe = trade.mfe_r
    if mfe is not None and mfe >= GIVEBACK_MFE_R and r <= 0:
        tags.append(ReviewTag.GANANCIA_DEVUELTA)
    return TradeReview(
        trade_id=trade.trade_id,
        r_multiple=r,
        entry_slippage_bps=trade.entry_slippage_bps,
        exit_slippage_bps=trade.exit_slippage_bps,
        mae_r=trade.mae_r,
        mfe_r=mfe,
        tags=tuple(tags),
    )


def tag_impact(reviews: Iterable[TradeReview]) -> dict[ReviewTag, TagImpact]:
    """Cuántas operaciones tiene cada etiqueta y cuánto suman en R."""
    counts: dict[ReviewTag, int] = {}
    totals: dict[ReviewTag, Decimal] = {}
    for review in reviews:
        for tag in review.tags:
            counts[tag] = counts.get(tag, 0) + 1
            totals[tag] = totals.get(tag, Decimal(0)) + review.r_multiple
    return {tag: TagImpact(counts[tag], totals[tag]) for tag in ReviewTag if tag in counts}
