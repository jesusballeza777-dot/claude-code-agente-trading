"""Lectura de los CSV del archivo de Binance (velas y funding) a tablas de polars.

Formatos (ACLARACIONES-v1 §1.5): las velas spot no tienen cabecera y las de futuros recientes
sí; las marcas de tiempo en microsegundos (spot desde 2025) se normalizan a milisegundos.
Los precios se guardan como float64 y se comprueba que vuelven exactos al texto original
(`Decimal(repr(float(x))) == Decimal(x)`): con ≤15 cifras significativas no se pierde nada.
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final

import polars as pl

KLINE_COLUMNS: Final = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_volume",
    "taker_buy_quote_volume",
)
PRICE_COLUMNS: Final = ("open", "high", "low", "close")
_FLOATS: Final = ("volume", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume")
_MICROSECONDS_THRESHOLD: Final = 10**14  # 1e14 ms es el año 5138; por encima son µs

KLINE_SCHEMA: Final = pl.Schema(
    {
        "open_time": pl.Datetime("ms", "UTC"),
        "open": pl.Float64(),
        "high": pl.Float64(),
        "low": pl.Float64(),
        "close": pl.Float64(),
        "volume": pl.Float64(),
        "close_time": pl.Datetime("ms", "UTC"),
        "quote_volume": pl.Float64(),
        "trades": pl.Int64(),
        "taker_buy_volume": pl.Float64(),
        "taker_buy_quote_volume": pl.Float64(),
    }
)
FUNDING_SCHEMA: Final = pl.Schema(
    {
        "calc_time": pl.Datetime("ms", "UTC"),
        "funding_interval_hours": pl.Int64(),
        "funding_rate": pl.Float64(),
    }
)


class ParseError(ValueError):
    """Fichero con un formato que no se reconoce."""


@dataclass(frozen=True, slots=True)
class Parsed:
    frame: pl.DataFrame
    inexact_prices: int  # precios que no vuelven exactos desde float64


def read_zip_csv(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ParseError(f"{path.name}: se esperaba un único CSV, hay {len(names)}")
        return archive.read(names[0]).decode("utf-8")


def parse_klines(text: str) -> Parsed:
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if rows and rows[0][0] == "open_time":
        rows = rows[1:]
    columns: dict[str, list[object]] = {name: [] for name in KLINE_COLUMNS}
    inexact = 0
    for row in rows:
        if len(row) != 12:
            raise ParseError(f"vela con {len(row)} columnas (se esperaban 12)")
        values = dict(zip(KLINE_COLUMNS, row, strict=False))
        columns["open_time"].append(_millis(values["open_time"]))
        columns["close_time"].append(_millis(values["close_time"]))
        for name in PRICE_COLUMNS:
            number = float(values[name])
            if Decimal(repr(number)) != Decimal(values[name]):
                inexact += 1
            columns[name].append(number)
        for name in _FLOATS:
            columns[name].append(float(values[name]))
        columns["trades"].append(int(values["trades"]))
    frame = pl.DataFrame(
        {
            name: pl.Series(name, data, dtype=pl.Int64 if name.endswith("time") else None)
            for name, data in columns.items()
        }
    )
    frame = frame.with_columns(
        pl.from_epoch("open_time", time_unit="ms").dt.replace_time_zone("UTC"),
        pl.from_epoch("close_time", time_unit="ms").dt.replace_time_zone("UTC"),
    )
    return Parsed(frame=frame.cast(KLINE_SCHEMA), inexact_prices=inexact)


def parse_funding(text: str) -> pl.DataFrame:
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if not rows or rows[0] != ["calc_time", "funding_interval_hours", "last_funding_rate"]:
        raise ParseError("funding sin la cabecera esperada")
    data = rows[1:]
    frame = pl.DataFrame(
        {
            "calc_time": pl.Series([_millis(r[0]) for r in data], dtype=pl.Int64),
            "funding_interval_hours": pl.Series([int(r[1]) for r in data], dtype=pl.Int64),
            "funding_rate": pl.Series([float(r[2]) for r in data], dtype=pl.Float64),
        }
    )
    frame = frame.with_columns(
        pl.from_epoch("calc_time", time_unit="ms").dt.replace_time_zone("UTC")
    )
    return frame.cast(FUNDING_SCHEMA)


def _millis(text: str) -> int:
    value = int(text)
    return value // 1000 if value >= _MICROSECONDS_THRESHOLD else value
