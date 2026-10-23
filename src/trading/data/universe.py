"""Universo point-in-time de H2 (pre-registro H2-v1 §3; ACLARACIONES-v1 §2).

Reconstitución el día 1 de cada mes a las 00:00 UTC (`D`) usando solo velas diarias de
perpetuos USDⓈ-M anteriores a `D`:

1. Candidatos: símbolos que terminan en `USDT` y no contienen `_`, sin las exclusiones.
2. Elegibles: primera vela diaria abierta ≤ D - 90 días y vela del día D - 1.
3. Orden: mediana del `quote_volume` de los días D-30 … D-1 con datos; empates por símbolo.
4. Universo: BTCUSDT y ETHUSDT (si son elegibles) más las 8 alts mejor ordenadas.

La lista de símbolos sale del archivo, que conserva los deslistados (verificado en la F3:
LUNAUSDT, ANCUSDT, TOMOUSDT), así que no hay sesgo de supervivencia por construcción.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

import polars as pl

EXCLUDED_BASES: Final = frozenset(
    {
        # Stablecoins y divisas
        "USDC",
        "BUSD",
        "TUSD",
        "FDUSD",
        "USDP",
        "DAI",
        "USDE",
        "PYUSD",
        "EUR",
        "AEUR",
        "USTC",
        "USD1",
        "RLUSD",
        "USDBRL",
        # Índices
        "BTCDOM",
        "DEFI",
        "FOOTBALL",
        "BLUEBIRD",
        # Activos tokenizados (acciones y metales)
        "AAPL",
        "AMZN",
        "COIN",
        "CRCL",
        "GOOGL",
        "HOOD",
        "META",
        "MSFT",
        "MSTR",
        "NVDA",
        "QQQ",
        "SPY",
        "TSLA",
        "PAXG",
        "XAUT",
        "XAU",
        "XAG",
        # Envoltorios de BTC o ETH
        "WBTC",
        "WETH",
        "WBETH",
        "BETH",
        "STETH",
        "WSTETH",
        "CBETH",
    }
)
CORE_SYMBOLS: Final = ("BTCUSDT", "ETHUSDT")
N_ALTS: Final = 8
MIN_HISTORY: Final = timedelta(days=90)
VOLUME_WINDOW: Final = timedelta(days=30)


def base_asset(symbol: str) -> str:
    if not symbol.endswith("USDT"):
        raise ValueError(f"{symbol} no termina en USDT")
    return symbol.removesuffix("USDT")


def candidate_symbols(symbols: Iterable[str]) -> list[str]:
    return sorted(
        s
        for s in set(symbols)
        if s.endswith("USDT")
        and "_" not in s
        and len(s) > len("USDT")
        and base_asset(s) not in EXCLUDED_BASES
    )


@dataclass(frozen=True, slots=True)
class Ranked:
    symbol: str
    median_quote_volume: float
    first_open: datetime


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    date: datetime
    members: tuple[str, ...]  # BTC, ETH y luego las alts por orden de liquidez
    ranking: tuple[Ranked, ...]  # todos los elegibles, por orden


def reconstitution_dates(start: datetime, end: datetime) -> list[datetime]:
    """Días 1 de cada mes a las 00:00 UTC en [start, end)."""
    current = datetime(start.year, start.month, 1, tzinfo=UTC)
    if current < start:
        current = _next_month(current)
    dates = []
    while current < end:
        dates.append(current)
        current = _next_month(current)
    return dates


def universe_at(date: datetime, daily: Mapping[str, pl.DataFrame]) -> UniverseSnapshot:
    """Universo en `date` a partir de las velas diarias de cada candidato.

    Solo se miran velas con apertura < `date`: lo demás se descarta aquí aunque venga en
    `daily`, para que el universo no pueda usar información posterior.
    """
    if date.tzinfo is None or (date.hour, date.minute, date.second, date.day) != (0, 0, 0, 1):
        raise ValueError("la reconstitución es el día 1 del mes a las 00:00 UTC")
    previous_day = date - timedelta(days=1)
    ranked: list[Ranked] = []
    for symbol in candidate_symbols(daily):
        frame = daily[symbol].filter(pl.col("open_time") < date)
        if frame.height == 0:
            continue
        first_open = frame.get_column("open_time").min()
        if not isinstance(first_open, datetime) or first_open > date - MIN_HISTORY:
            continue
        if frame.filter(pl.col("open_time") == previous_day).height == 0:
            continue
        window = frame.filter(pl.col("open_time") >= date - VOLUME_WINDOW)
        median = window.get_column("quote_volume").median()
        if not isinstance(median, float):
            raise ValueError(f"{symbol}: volumen no numérico en la ventana de {date.date()}")
        ranked.append(Ranked(symbol, median, first_open))
    ranked.sort(key=lambda r: (-r.median_quote_volume, r.symbol))
    core = tuple(s for s in CORE_SYMBOLS if any(r.symbol == s for r in ranked))
    alts = tuple(r.symbol for r in ranked if r.symbol not in CORE_SYMBOLS)[:N_ALTS]
    return UniverseSnapshot(date=date, members=core + alts, ranking=tuple(ranked))


def _next_month(moment: datetime) -> datetime:
    if moment.month == 12:
        return moment.replace(year=moment.year + 1, month=1)
    return moment.replace(month=moment.month + 1)
