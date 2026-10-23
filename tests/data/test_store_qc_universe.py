"""Almacén con guardia, control de calidad y universo point-in-time."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from fake_archive import kline_rows
from trading.data.holdout import HOLDOUT_START, HoldoutSealedError
from trading.data.parse import parse_funding, parse_klines
from trading.data.qc import clean_klines, cross_check_closes, qc_funding, qc_klines
from trading.data.store import Store, dataset_id_of
from trading.data.universe import (
    base_asset,
    candidate_symbols,
    reconstitution_dates,
    universe_at,
)

DAY = timedelta(days=1)
FOUR_HOURS = timedelta(hours=4)


def _klines(start: datetime, step: timedelta, count: int, **kw: float) -> pl.DataFrame:
    return parse_klines("\n".join(kline_rows(start, step, count, **kw))).frame


# --- almacén ---------------------------------------------------------------------------------


def test_store_round_trip_and_range_boundaries(tmp_path: Path) -> None:
    store = Store(tmp_path)
    start = datetime(2024, 12, 31, tzinfo=UTC)
    frame = _klines(start, FOUR_HOURS, 6)
    store.write_klines(frame, "futures_um", "4h", "BTCUSDT")
    got = store.read_klines("futures_um", "4h", "BTCUSDT", start, HOLDOUT_START)
    assert got.height == 6  # la última vela cierra justo a las 00:00 del 1-ene-2025
    got = store.read_klines("futures_um", "4h", "BTCUSDT", start, HOLDOUT_START - FOUR_HOURS)
    assert got.height == 5
    assert store.symbols("futures_um", "4h") == ["BTCUSDT"]
    assert store.read_klines("futures_um", "4h", "ETHUSDT", start, HOLDOUT_START).height == 0


def test_store_refuses_the_holdout(tmp_path: Path) -> None:
    store = Store(tmp_path)
    with pytest.raises(HoldoutSealedError):
        store.read_klines("futures_um", "1d", "BTCUSDT", HOLDOUT_START - DAY, HOLDOUT_START + DAY)
    with pytest.raises(HoldoutSealedError):
        store.read_funding("BTCUSDT", HOLDOUT_START, HOLDOUT_START + DAY)


def test_store_funding_and_manifest(tmp_path: Path) -> None:
    from fake_archive import month_funding

    store = Store(tmp_path)
    store.write_funding(parse_funding(month_funding(2024, 12)), "BTCUSDT")
    december = datetime(2024, 12, 1, tzinfo=UTC)
    assert store.read_funding("BTCUSDT", december, HOLDOUT_START).height == 93
    assert store.read_funding("ETHUSDT", december, HOLDOUT_START).height == 0
    dataset_id = store.write_manifest({"b": "2", "a": "1"})
    assert dataset_id == dataset_id_of({"a": "1", "b": "2"})
    assert store.read_manifest() == (dataset_id, {"a": "1", "b": "2"})
    with pytest.raises(ValueError, match="intervalo"):
        store.kline_path("spot", "15m", "BTCUSDT")


# --- calidad ---------------------------------------------------------------------------------


def test_qc_of_a_clean_series() -> None:
    qc = qc_klines(
        _klines(datetime(2020, 1, 1, tzinfo=UTC), FOUR_HOURS, 30), "futures_um", "4h", "X"
    )
    assert qc.clean
    assert (qc.rows, qc.expected, qc.missing, qc.completeness) == (30, 30, 0, 1.0)
    assert qc.largest_gap == timedelta(0)


def test_qc_detects_every_defect() -> None:
    frame = _klines(datetime(2020, 1, 1, tzinfo=UTC), FOUR_HOURS, 10)
    gap = frame.filter(pl.col("open_time") != datetime(2020, 1, 1, 8, tzinfo=UTC))
    shuffled = pl.concat([gap.slice(5), gap.slice(0, 5), gap.slice(0, 1)])  # desorden y duplicado
    broken = shuffled.with_columns(
        pl.when(pl.col("open_time") == datetime(2020, 1, 1, 12, tzinfo=UTC))
        .then(pl.col("low") + 1000)
        .otherwise(pl.col("low"))
        .alias("low"),
        pl.when(pl.col("open_time") == datetime(2020, 1, 1, 16, tzinfo=UTC))
        .then(pl.col("close_time") + timedelta(minutes=1))
        .otherwise(pl.col("close_time"))
        .alias("close_time"),
    )
    misaligned = broken.with_columns(
        pl.when(pl.col("open_time") == datetime(2020, 1, 2, 12, tzinfo=UTC))
        .then(pl.col("open_time") + timedelta(minutes=1))
        .otherwise(pl.col("open_time"))
        .alias("open_time")
    )
    qc = qc_klines(misaligned, "futures_um", "4h", "X")
    assert not qc.clean
    assert qc.duplicates == 1
    assert qc.out_of_order >= 1
    assert qc.misaligned == 1
    assert qc.bad_ohlc == 1
    assert qc.bad_close_time == 2  # la de close_time cambiado y la de open_time desalineado
    assert qc.missing >= 1
    assert qc.completeness < 1
    clean = clean_klines(gap.vstack(gap.slice(0, 1)))
    assert clean.height == gap.height
    assert clean.get_column("open_time").is_sorted()


def test_qc_of_an_empty_series() -> None:
    from trading.data.parse import KLINE_SCHEMA

    qc = qc_klines(pl.DataFrame(schema=KLINE_SCHEMA), "spot", "1d", "X")
    assert (qc.rows, qc.completeness, qc.first_open) == (0, 1.0, None)


def test_cross_check_and_funding_qc() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    spot = _klines(start, DAY, 10, price=100.0)
    perp = _klines(start, DAY, 10, price=101.0)
    check = cross_check_closes("BTCUSDT", spot, perp)
    assert check.days == 10
    assert check.max_abs_diff == pytest.approx(1 / 101)
    assert check.days_over_1pct == 0
    assert cross_check_closes("X", spot, perp.clear()).days == 0
    from fake_archive import month_funding

    funding = parse_funding(month_funding(2020, 1))
    qc = qc_funding(pl.concat([funding, funding.slice(0, 1)]), "BTCUSDT")
    assert (qc.duplicates, qc.intervals, qc.largest_gap) == (1, (8,), timedelta(hours=8))
    assert qc_funding(funding.clear(), "X").rows == 0


# --- universo --------------------------------------------------------------------------------


def test_candidate_symbols_apply_the_exclusions() -> None:
    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "TUSDT",  # el token T, no TUSD
        "BUSDT",  # el token B
        "TUSDUSDT",
        "USDCUSDT",
        "BTCDOMUSDT",
        "BTCUSDT_240628",
        "PAXGUSDT",
        "WBTCUSDT",
        "SOLUSDC",
        "USDT",
    ]
    assert candidate_symbols(symbols) == ["BTCUSDT", "BUSDT", "ETHUSDT", "TUSDT"]
    assert base_asset("1000SHIBUSDT") == "1000SHIB"
    with pytest.raises(ValueError, match="USDT"):
        base_asset("BTCUSDC")


def test_reconstitution_dates() -> None:
    dates = reconstitution_dates(
        datetime(2020, 1, 15, tzinfo=UTC), datetime(2020, 4, 1, tzinfo=UTC)
    )
    assert dates == [
        datetime(2020, 2, 1, tzinfo=UTC),
        datetime(2020, 3, 1, tzinfo=UTC),
    ]
    assert reconstitution_dates(
        datetime(2020, 12, 1, tzinfo=UTC), datetime(2021, 1, 2, tzinfo=UTC)
    )[-1] == datetime(2021, 1, 1, tzinfo=UTC)


def _daily(first: datetime, last: datetime, volume: float) -> pl.DataFrame:
    return _klines(first, DAY, (last - first) // DAY + 1, volume=volume)


def test_universe_eligibility_ranking_and_point_in_time() -> None:
    d = datetime(2020, 6, 1, tzinfo=UTC)
    before = d - DAY
    old = datetime(2020, 1, 1, tzinfo=UTC)
    daily = {
        "BTCUSDT": _daily(old, before, 9e9),
        "ETHUSDT": _daily(old, before, 8e9),
        **{f"ALT{i}USDT": _daily(old, before, 1e6 * (i + 1)) for i in range(10)},
        "TIEAUSDT": _daily(old, before, 5.5e6),
        "TIEBUSDT": _daily(old, before, 5.5e6),
        # Exactamente 90 días de historia: elegible.
        "EDGEUSDT": _daily(d - timedelta(days=90), before, 1e12),
        # 89 días: no elegible.
        "YOUNGUSDT": _daily(d - timedelta(days=89), before, 1e12),
        # Sin vela de D - 1 (deslistado): no elegible.
        "GONEUSDT": _daily(old, before - DAY, 1e12),
        # Volumen enorme solo después de D: no puede contar.
        "FUTUREUSDT": pl.concat(
            [_daily(old, before, 1.0), _daily(d, d + timedelta(days=20), 1e15)]
        ),
        "USDCUSDT": _daily(old, before, 1e13),
    }
    snapshot = universe_at(d, daily)
    assert snapshot.members[:2] == ("BTCUSDT", "ETHUSDT")
    assert snapshot.members[2:] == (
        "EDGEUSDT",
        "ALT9USDT",
        "ALT8USDT",
        "ALT7USDT",
        "ALT6USDT",
        "ALT5USDT",
        "TIEAUSDT",  # empate con TIEBUSDT: orden alfabético
        "TIEBUSDT",
    )
    ranked = {r.symbol for r in snapshot.ranking}
    assert {"YOUNGUSDT", "GONEUSDT", "USDCUSDT"}.isdisjoint(ranked)
    assert "FUTUREUSDT" in ranked
    assert snapshot.ranking[-1].symbol == "FUTUREUSDT"


def test_universe_uses_the_median_of_the_last_30_days() -> None:
    d = datetime(2020, 6, 1, tzinfo=UTC)
    old = datetime(2020, 1, 1, tzinfo=UTC)
    spike = pl.concat(
        [_daily(old, d - timedelta(days=31), 1e12), _daily(d - timedelta(days=30), d - DAY, 1.0)]
    )
    steady = _daily(old, d - DAY, 1e3)
    snapshot = universe_at(d, {"SPIKEUSDT": spike, "STEADYUSDT": steady})
    assert snapshot.members == ("STEADYUSDT", "SPIKEUSDT")


def test_universe_date_must_be_a_month_start() -> None:
    with pytest.raises(ValueError, match="día 1"):
        universe_at(datetime(2020, 6, 2, tzinfo=UTC), {})
    from trading.data.parse import KLINE_SCHEMA

    empty = pl.DataFrame(schema=KLINE_SCHEMA)
    assert universe_at(datetime(2020, 6, 1, tzinfo=UTC), {"XUSDT": empty}).members == ()
