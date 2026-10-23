"""Indicadores deterministas y causales (solo usan datos hasta la vela actual).

Convenciones (ACLARACIONES-v1 §3.1 y §6.1):
- Rango verdadero TR_i = max(H_i − L_i, |H_i − C_{i−1}|, |L_i − C_{i−1}|), definido desde la
  segunda vela de la serie (la primera no tiene cierre anterior).
- ATR(n) de Wilder: semilla = media simple de TR_1 … TR_n (disponible en la vela n);
  después ATR_i = (ATR_{i−1} × (n − 1) + TR_i) / n.
- Los canales usan las n velas *anteriores* a la actual, sin incluirla.

Las listas devueltas tienen la misma longitud que la entrada; `None` donde no hay datos
suficientes.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence


def true_ranges(
    high: Sequence[float], low: Sequence[float], close: Sequence[float]
) -> list[float | None]:
    _same_length(high, low, close)
    ranges: list[float | None] = [None] * len(close)
    for i in range(1, len(close)):
        previous = close[i - 1]
        ranges[i] = max(high[i] - low[i], abs(high[i] - previous), abs(low[i] - previous))
    return ranges


def wilder_atr(
    high: Sequence[float], low: Sequence[float], close: Sequence[float], n: int
) -> list[float | None]:
    if n < 1:
        raise ValueError("n debe ser >= 1")
    ranges = true_ranges(high, low, close)
    atr: list[float | None] = [None] * len(close)
    if len(close) <= n:
        return atr
    seed = sum(r for r in ranges[1 : n + 1] if r is not None) / n
    atr[n] = seed
    value = seed
    for i in range(n + 1, len(close)):
        current = ranges[i]
        if current is None:  # pragma: no cover - imposible desde la segunda vela
            raise ValueError("rango verdadero ausente")
        value = (value * (n - 1) + current) / n
        atr[i] = value
    return atr


def prior_max(values: Sequence[float], n: int) -> list[float | None]:
    """Máximo de las n velas anteriores a cada vela (sin incluirla)."""
    return _prior_extreme(values, n, maximum=True)


def prior_min(values: Sequence[float], n: int) -> list[float | None]:
    """Mínimo de las n velas anteriores a cada vela (sin incluirla)."""
    return _prior_extreme(values, n, maximum=False)


def lag_return(close: Sequence[float], n: int) -> list[float | None]:
    """C_i / C_{i−n} − 1."""
    if n < 1:
        raise ValueError("n debe ser >= 1")
    return [None if i < n else close[i] / close[i - n] - 1 for i in range(len(close))]


def sma(values: Sequence[float], n: int) -> list[float | None]:
    if n < 1:
        raise ValueError("n debe ser >= 1")
    out: list[float | None] = [None] * len(values)
    total = 0.0
    for i, value in enumerate(values):
        total += value
        if i >= n:
            total -= values[i - n]
        if i >= n - 1:
            out[i] = total / n
    return out


def _prior_extreme(values: Sequence[float], n: int, *, maximum: bool) -> list[float | None]:
    """Ventana deslizante monótona: O(len) en lugar de O(len × n)."""
    if n < 1:
        raise ValueError("n debe ser >= 1")
    out: list[float | None] = [None] * len(values)
    window: deque[int] = deque()
    for i in range(len(values)):
        if i >= n:
            out[i] = values[window[0]]
        # Añadir la vela i para las siguientes y quitar las que salen de la ventana.
        while window and (
            values[window[-1]] <= values[i] if maximum else values[window[-1]] >= values[i]
        ):
            window.pop()
        window.append(i)
        while window[0] <= i - n:
            window.popleft()
    return out


def _same_length(*series: Sequence[float]) -> None:
    if len({len(s) for s in series}) != 1:
        raise ValueError("las series deben tener la misma longitud")
