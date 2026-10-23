"""Rendimiento de un conjunto de operaciones cerradas (pantalla "Rendimiento" de la app)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trading.audit.records import TradeRecord


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    """Métricas en R y en USD. Las métricas sin datos suficientes son None.

    `profit_factor` es None si no hay pérdidas (no está definido).
    """

    trades: int
    wins: int
    losses: int
    win_rate: Decimal | None
    expectancy_r: Decimal | None
    profit_factor: Decimal | None
    avg_win_r: Decimal | None
    avg_loss_r: Decimal | None
    gross_pnl: Decimal
    fees: Decimal
    funding: Decimal
    net_pnl: Decimal
    max_drawdown_r: Decimal
    max_losing_streak: int


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


def summarize(trades: Iterable[TradeRecord]) -> PerformanceSummary:
    """Resume las operaciones en orden de cierre."""
    ordered = sorted(trades, key=lambda t: (t.closed_at, t.trade_id))
    r_values = [t.r_multiple for t in ordered]
    win_r = [r for r in r_values if r > 0]
    loss_r = [r for r in r_values if r < 0]
    gains = sum((t.net_pnl for t in ordered if t.net_pnl > 0), Decimal(0))
    losses = sum((t.net_pnl for t in ordered if t.net_pnl < 0), Decimal(0))

    equity_r = peak_r = drawdown_r = Decimal(0)
    streak = max_streak = 0
    for r in r_values:
        equity_r += r
        peak_r = max(peak_r, equity_r)
        drawdown_r = max(drawdown_r, peak_r - equity_r)
        streak = streak + 1 if r < 0 else 0
        max_streak = max(max_streak, streak)

    return PerformanceSummary(
        trades=len(ordered),
        wins=len(win_r),
        losses=len(loss_r),
        win_rate=Decimal(len(win_r)) / len(ordered) if ordered else None,
        expectancy_r=_mean(r_values),
        profit_factor=gains / -losses if losses < 0 else None,
        avg_win_r=_mean(win_r),
        avg_loss_r=_mean(loss_r),
        gross_pnl=sum((t.gross_pnl for t in ordered), Decimal(0)),
        fees=sum((t.fees for t in ordered), Decimal(0)),
        funding=sum((t.funding for t in ordered), Decimal(0)),
        net_pnl=sum((t.net_pnl for t in ordered), Decimal(0)),
        max_drawdown_r=drawdown_r,
        max_losing_streak=max_streak,
    )


def summarize_by(
    trades: Iterable[TradeRecord], key: Callable[[TradeRecord], str]
) -> dict[str, PerformanceSummary]:
    """Resumen por grupo (estrategia, activo, dirección, plataforma…)."""
    groups: dict[str, list[TradeRecord]] = {}
    for trade in trades:
        groups.setdefault(key(trade), []).append(trade)
    return {name: summarize(group) for name, group in sorted(groups.items())}


def rolling_expectancy(
    trades: Iterable[TradeRecord], window: int
) -> list[tuple[datetime, Decimal]]:
    """Esperanza en R de las últimas `window` operaciones, tras cada cierre."""
    if window < 1:
        raise ValueError("window debe ser >= 1")
    ordered = sorted(trades, key=lambda t: (t.closed_at, t.trade_id))
    points: list[tuple[datetime, Decimal]] = []
    for i in range(window, len(ordered) + 1):
        chunk = ordered[i - window : i]
        points.append(
            (chunk[-1].closed_at, sum((t.r_multiple for t in chunk), Decimal(0)) / window)
        )
    return points
