"""Control de calidad de las velas y del funding (F3).

Por cada serie se cuentan: huecos, duplicados, velas fuera de orden, velas desalineadas con
la rejilla UTC del intervalo, `close_time` incoherente, OHLC imposibles y precios no
positivos. La completitud es velas únicas / velas esperadas entre la primera y la última vela
de la serie dentro del periodo (un activo deslistado no cuenta como hueco después de su
última vela). Objetivo: > 99.5%.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

import polars as pl

from trading.data.store import INTERVALS

COMPLETENESS_TARGET: Final = 0.995


@dataclass(frozen=True, slots=True)
class SeriesQC:
    market: str
    interval: str
    symbol: str
    rows: int
    unique: int
    expected: int
    duplicates: int
    out_of_order: int
    misaligned: int
    bad_close_time: int
    bad_ohlc: int
    first_open: datetime | None
    last_open: datetime | None
    largest_gap: timedelta

    @property
    def missing(self) -> int:
        return max(self.expected - self.unique, 0)

    @property
    def completeness(self) -> float:
        return 1.0 if self.expected == 0 else min(self.unique / self.expected, 1.0)

    @property
    def clean(self) -> bool:
        return (
            self.duplicates == 0
            and self.out_of_order == 0
            and self.misaligned == 0
            and self.bad_close_time == 0
            and self.bad_ohlc == 0
        )


def qc_klines(frame: pl.DataFrame, market: str, interval: str, symbol: str) -> SeriesQC:
    """Calidad de una serie de velas tal como viene del archivo (sin ordenar ni depurar)."""
    step = INTERVALS[interval]
    step_ms = int(step.total_seconds() * 1000)
    if frame.height == 0:
        return SeriesQC(market, interval, symbol, 0, 0, 0, 0, 0, 0, 0, 0, None, None, timedelta(0))
    epoch = frame.get_column("open_time").dt.epoch("ms")
    unique_times = epoch.unique().sort()
    first, last = int(unique_times[0]), int(unique_times[-1])
    expected = (last - first) // step_ms + 1
    diffs = epoch.diff().drop_nulls()
    unique_diffs = unique_times.diff().drop_nulls()
    largest_gap = timedelta(milliseconds=_as_int(unique_diffs.max(), step_ms)) - step
    close_ms = frame.get_column("close_time").dt.epoch("ms")
    ohlc = frame.select(
        (
            (pl.col("low") > pl.min_horizontal("open", "close"))
            | (pl.col("high") < pl.max_horizontal("open", "close"))
            | (pl.col("low") <= 0)
            | (pl.col("volume") < 0)
        ).alias("bad")
    )
    return SeriesQC(
        market=market,
        interval=interval,
        symbol=symbol,
        rows=frame.height,
        unique=unique_times.len(),
        expected=expected,
        duplicates=frame.height - unique_times.len(),
        out_of_order=int((diffs < 0).sum()),
        misaligned=int((epoch % step_ms != 0).sum()),
        bad_close_time=int((close_ms != epoch + step_ms - 1).sum()),
        bad_ohlc=int(ohlc.get_column("bad").sum()),
        first_open=frame.get_column("open_time").min(),  # type: ignore[arg-type]
        last_open=frame.get_column("open_time").max(),  # type: ignore[arg-type]
        largest_gap=largest_gap,
    )


def clean_klines(frame: pl.DataFrame) -> pl.DataFrame:
    """Ordena y quita duplicados exactos de hora de apertura (se queda con el primero)."""
    return frame.unique(subset="open_time", keep="first", maintain_order=True).sort("open_time")


@dataclass(frozen=True, slots=True)
class CrossCheck:
    symbol: str
    days: int
    median_abs_diff: float
    p99_abs_diff: float
    max_abs_diff: float
    days_over_1pct: int


def cross_check_closes(symbol: str, spot: pl.DataFrame, perp: pl.DataFrame) -> CrossCheck:
    """Compara cierres diarios spot y perpetuo del mismo activo: |perp / spot - 1|."""
    joined = spot.select("open_time", pl.col("close").alias("spot")).join(
        perp.select("open_time", pl.col("close").alias("perp")), on="open_time", how="inner"
    )
    diff = (joined.get_column("perp") / joined.get_column("spot") - 1).abs()
    if diff.len() == 0:
        return CrossCheck(symbol, 0, 0.0, 0.0, 0.0, 0)
    return CrossCheck(
        symbol=symbol,
        days=diff.len(),
        median_abs_diff=float(diff.median() or 0.0),  # type: ignore[arg-type]
        p99_abs_diff=float(diff.quantile(0.99) or 0.0),
        max_abs_diff=float(diff.max() or 0.0),  # type: ignore[arg-type]
        days_over_1pct=int((diff > 0.01).sum()),
    )


@dataclass(frozen=True, slots=True)
class FundingQC:
    symbol: str
    rows: int
    duplicates: int
    out_of_order: int
    intervals: tuple[int, ...]
    largest_gap: timedelta


def qc_funding(frame: pl.DataFrame, symbol: str) -> FundingQC:
    if frame.height == 0:
        return FundingQC(symbol, 0, 0, 0, (), timedelta(0))
    epoch = frame.get_column("calc_time").dt.epoch("ms")
    unique_times = epoch.unique().sort()
    gaps = unique_times.diff().drop_nulls()
    return FundingQC(
        symbol=symbol,
        rows=frame.height,
        duplicates=frame.height - unique_times.len(),
        out_of_order=int((epoch.diff().drop_nulls() < 0).sum()),
        intervals=tuple(sorted(set(frame.get_column("funding_interval_hours").to_list()))),
        largest_gap=timedelta(milliseconds=_as_int(gaps.max(), 0)),
    )


def _as_int(value: object, default: int) -> int:
    return value if isinstance(value, int) else default
