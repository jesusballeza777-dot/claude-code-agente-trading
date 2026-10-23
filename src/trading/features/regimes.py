"""Etiquetas de régimen de mercado (protocolo común C-05; ACLARACIONES-v1 §1.6).

Con el cierre diario del par spot BTCUSDT:
- alcista: cierre > media de 200 días y la media sube frente a 20 días antes;
- bajista: cierre < media y la media baja;
- lateral: el resto.
Solo sirven para etiquetar operaciones; ninguna regla de trading las usa.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum

from trading.features.indicators import sma

SMA_DAYS = 200
SLOPE_DAYS = 20


class Regime(StrEnum):
    BULL = "alcista"
    BEAR = "bajista"
    SIDEWAYS = "lateral"


def regime_labels(
    days: Sequence[datetime], closes: Sequence[float]
) -> dict[datetime, Regime | None]:
    """Etiqueta de cada día (apertura de la vela diaria); None sin 220 días de historia."""
    if len(days) != len(closes):
        raise ValueError("días y cierres deben tener la misma longitud")
    average = sma(closes, SMA_DAYS)
    labels: dict[datetime, Regime | None] = {}
    for i, day in enumerate(days):
        current = average[i]
        before = average[i - SLOPE_DAYS] if i >= SLOPE_DAYS else None
        if current is None or before is None:
            labels[day] = None
        elif closes[i] > current and current > before:
            labels[day] = Regime.BULL
        elif closes[i] < current and current < before:
            labels[day] = Regime.BEAR
        else:
            labels[day] = Regime.SIDEWAYS
    return labels
