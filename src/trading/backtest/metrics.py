"""Métricas del gate de la F4 (plan §5; protocolo común C-05 a C-17; ACLARACIONES §5).

Todo se calcula sobre la lista de R netos de las operaciones. Los remuestreos usan
`random.Random(semilla)` para ser reproducibles; la semilla del protocolo es 20261023.
"""

from __future__ import annotations

import itertools
import math
import random
import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import NormalDist
from typing import Final

SEED: Final = 20261023
RESAMPLES: Final = 10_000
EULER_GAMMA: Final = 0.5772156649015329
RISK_PER_TRADE: Final = 0.005
_NORMAL: Final = NormalDist()


@dataclass(frozen=True, slots=True)
class Interval:
    low: float
    high: float


def expectancy(r: Sequence[float]) -> float:
    return statistics.fmean(r) if r else 0.0


def profit_factor(r: Sequence[float]) -> float:
    """Suma de R positivos / |suma de R negativos| (inf si no hay pérdidas)."""
    gains = sum(x for x in r if x > 0)
    losses = -sum(x for x in r if x < 0)
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def bootstrap_mean_ci(
    r: Sequence[float], *, level: float = 0.90, resamples: int = RESAMPLES, seed: int = SEED
) -> Interval:
    """IC percentil bilateral de la media por bootstrap iid (C-08)."""
    if not r:
        return Interval(0.0, 0.0)
    rng = random.Random(seed)  # noqa: S311 - remuestreo reproducible, no criptografía
    n = len(r)
    means = sorted(statistics.fmean(rng.choices(r, k=n)) for _ in range(resamples))
    tail = (1 - level) / 2
    return Interval(_quantile(means, tail), _quantile(means, 1 - tail))


def max_drawdown(path: Sequence[float]) -> float:
    """Máxima caída relativa desde un máximo (0.25 = 25%)."""
    peak, worst = -math.inf, 0.0
    for value in path:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def monte_carlo_max_drawdown(
    monthly_r: Sequence[Sequence[float]],
    *,
    months: int,
    resamples: int = RESAMPLES,
    seed: int = SEED,
    quantile: float = 0.95,
) -> float:
    """p95 del MaxDD remuestreando meses con reemplazo (C-09; ACLARACIONES §5.3)."""
    if not monthly_r or months <= 0:
        return 0.0
    rng = random.Random(seed)  # noqa: S311 - remuestreo reproducible, no criptografía
    drawdowns = []
    for _ in range(resamples):
        equity, path = 1.0, [1.0]
        for month in rng.choices(monthly_r, k=months):
            for r in month:
                equity *= 1 + RISK_PER_TRADE * r
                path.append(equity)
        drawdowns.append(max_drawdown(path))
    return _quantile(sorted(drawdowns), quantile)


def sharpe_per_trade(r: Sequence[float]) -> float:
    if len(r) < 2:
        return 0.0
    deviation = statistics.stdev(r)
    return statistics.fmean(r) / deviation if deviation > 0 else 0.0


def deflated_sharpe(r: Sequence[float], trial_sharpes: Sequence[float]) -> float:
    """DSR de Bailey y López de Prado con N = número de pruebas principales (C-11; §5.4)."""
    t = len(r)
    if t < 3:
        return 0.0
    sr = sharpe_per_trade(r)
    n = len(trial_sharpes)
    if n <= 1:
        sr0 = 0.0
    else:
        variance = statistics.variance(trial_sharpes)
        sr0 = math.sqrt(variance) * (
            (1 - EULER_GAMMA) * _NORMAL.inv_cdf(1 - 1 / n)
            + EULER_GAMMA * _NORMAL.inv_cdf(1 - 1 / (n * math.e))
        )
    skew, kurt = _skewness(r), _kurtosis(r)
    denominator = 1 - skew * sr + (kurt - 1) / 4 * sr**2
    if denominator <= 0:
        return 0.0
    return _NORMAL.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(denominator))


def pbo_cscv(matrix: Sequence[Sequence[float]], blocks: int = 16) -> float:
    """Probabilidad de sobreajuste por CSCV (C-10; ACLARACIONES §5.5).

    `matrix[mes][variante]` = suma de R del mes. Los meses se reparten en `blocks` bloques
    contiguos lo más iguales posible; para cada combinación de la mitad de los bloques como
    muestra de entrenamiento se elige la mejor variante (media/desviación de sus meses) y se
    mira su rango en el resto. PBO = fracción de combinaciones con logit ≤ 0.
    """
    months = len(matrix)
    variants = len(matrix[0]) if months else 0
    if months < blocks or variants < 2 or blocks % 2:
        raise ValueError("se necesitan al menos tantos meses como bloques y 2 variantes")
    edges = _block_edges(months, blocks)
    # Sumas por bloque y variante: cada combinación se resuelve sumando 8 bloques.
    sums = [
        [sum(matrix[i][v] for i in range(*edges[b])) for b in range(blocks)]
        for v in range(variants)
    ]
    squares = [
        [sum(matrix[i][v] ** 2 for i in range(*edges[b])) for b in range(blocks)]
        for v in range(variants)
    ]
    sizes = [end - start for start, end in edges]
    totals = [sum(row) for row in sums]
    total_squares = [sum(row) for row in squares]
    below = total = 0
    for chosen in itertools.combinations(range(blocks), blocks // 2):
        n_train = sum(sizes[b] for b in chosen)
        n_test = months - n_train
        train, test = [], []
        for v in range(variants):
            s_train = sum(sums[v][b] for b in chosen)
            q_train = sum(squares[v][b] for b in chosen)
            train.append(_moment_ratio(s_train, q_train, n_train))
            test.append(_moment_ratio(totals[v] - s_train, total_squares[v] - q_train, n_test))
        best = max(range(variants), key=lambda v: (train[v], -v))
        rank = sum(1 for v in range(variants) if test[v] < test[best]) + 1
        omega = rank / (variants + 1)
        below += math.log(omega / (1 - omega)) <= 0
        total += 1
    return below / total


def regime_expectancy(
    r: Sequence[float], labels: Sequence[str | None]
) -> dict[str, tuple[int, float]]:
    """Por régimen: (operaciones, esperanza)."""
    groups: dict[str, list[float]] = defaultdict(list)
    for value, label in zip(r, labels, strict=True):
        groups[label or "sin etiqueta"].append(value)
    return {k: (len(v), expectancy(v)) for k, v in sorted(groups.items())}


def monthly_sums(r: Sequence[float], exit_times: Sequence[datetime]) -> dict[str, float]:
    sums: dict[str, float] = defaultdict(float)
    for value, moment in zip(r, exit_times, strict=True):
        sums[f"{moment:%Y-%m}"] += value
    return dict(sorted(sums.items()))


def max_month_share(monthly: Mapping[str, float]) -> float | None:
    """Mayor aporte de un mes al total (C-17). None si el total es ≤ 0 (el criterio falla)."""
    total = sum(monthly.values())
    if total <= 0:
        return None
    return max(monthly.values()) / total


def random_filter_p90(
    r: Sequence[float], removed: int, *, resamples: int = RESAMPLES, seed: int = SEED
) -> float:
    """p90 de la esperanza tras quitar `removed` operaciones al azar (H4-06; §5.8)."""
    if removed <= 0 or removed >= len(r):
        raise ValueError("hay que quitar entre 1 y n − 1 operaciones")
    rng = random.Random(seed)  # noqa: S311 - remuestreo reproducible, no criptografía
    keep = len(r) - removed
    means = sorted(statistics.fmean(rng.sample(r, keep)) for _ in range(resamples))
    return _quantile(means, 0.90)


# --- utilidades ------------------------------------------------------------------------------


def _quantile(ordered: Sequence[float], q: float) -> float:
    """Cuantil con interpolación lineal sobre una lista ordenada."""
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _block_edges(months: int, blocks: int) -> list[tuple[int, int]]:
    base, extra = divmod(months, blocks)
    edges, start = [], 0
    for b in range(blocks):
        size = base + (1 if b < extra else 0)
        edges.append((start, start + size))
        start += size
    return edges


def _moment_ratio(total: float, squares: float, n: int) -> float:
    """Media / desviación (poblacional) a partir de la suma y la suma de cuadrados."""
    if n < 2:
        return 0.0
    mean = total / n
    variance = squares / n - mean * mean
    if variance <= 1e-18:
        return 0.0 if abs(mean) <= 1e-12 else math.copysign(math.inf, mean)
    return mean / math.sqrt(variance)


def _skewness(r: Sequence[float]) -> float:
    mean, deviation = statistics.fmean(r), statistics.pstdev(r)
    if deviation == 0:
        return 0.0
    return statistics.fmean(((x - mean) / deviation) ** 3 for x in r)


def _kurtosis(r: Sequence[float]) -> float:
    """Curtosis (no exceso): 3 para una normal."""
    mean, deviation = statistics.fmean(r), statistics.pstdev(r)
    if deviation == 0:
        return 3.0
    return statistics.fmean(((x - mean) / deviation) ** 4 for x in r)
