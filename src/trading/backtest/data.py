"""Carga de datos del almacén Parquet para el backtester, siempre a través de la guardia."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from trading.backtest.model import FundingEvent, MarketData, Series, Valuation
from trading.data.store import INTERVALS, Store
from trading.data.universe import base_asset


def load_series(
    store: Store, interval: str, symbol: str, start: datetime, end: datetime
) -> Series | None:
    frame = store.read_klines("futures_um", interval, symbol, start, end)
    if frame.height == 0:
        return None
    return Series(
        symbol=symbol,
        base_asset=base_asset(symbol),
        interval=INTERVALS[interval],
        times=tuple(frame.get_column("open_time").to_list()),
        open=tuple(frame.get_column("open").to_list()),
        high=tuple(frame.get_column("high").to_list()),
        low=tuple(frame.get_column("low").to_list()),
        close=tuple(frame.get_column("close").to_list()),
    )


def load_funding(
    store: Store, symbol: str, start: datetime, end: datetime
) -> tuple[FundingEvent, ...]:
    """Funding con calc_time redondeado hacia abajo al minuto (ACLARACIONES §7.1).

    El archivo registra cada liquidación con 0-47 ms de retraso sobre la hora en punto.
    """
    frame = store.read_funding(symbol, start, end)
    return tuple(
        FundingEvent(time=t.replace(second=0, microsecond=0), rate=r, interval_hours=h)
        for t, h, r in frame.select(
            "calc_time", "funding_interval_hours", "funding_rate"
        ).iter_rows()
    )


def load_market(
    store: Store, interval: str, symbols: Sequence[str], start: datetime, end: datetime
) -> MarketData:
    """Velas del intervalo, funding y cierres de 4h para valorar el funding (§4.3)."""
    series = {}
    valuation = {}
    funding = {}
    for symbol in symbols:
        loaded = load_series(store, interval, symbol, start, end)
        if loaded is None:
            continue
        series[symbol] = loaded
        four = loaded if interval == "4h" else load_series(store, "4h", symbol, start, end)
        if four is not None:
            valuation[symbol] = Valuation(
                close_times=tuple(t + timedelta(hours=4) for t in four.times),
                closes=four.close,
            )
        funding[symbol] = load_funding(store, symbol, start, end)
    return MarketData(
        interval=INTERVALS[interval],
        series=series,
        funding=funding,
        valuation=valuation,
        start=start,
        end=end,
    )
