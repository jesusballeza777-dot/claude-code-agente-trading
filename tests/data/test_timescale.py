"""Carga en TimescaleDB. Necesita la base de `docker compose up db`; si no está, se omite."""

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

from fake_archive import kline_rows, month_funding
from trading.data.parse import parse_funding, parse_klines
from trading.data.store import Store
from trading.data.timescale import DEFAULT_DSN, load

DSN = os.environ.get("TRADING_DB_DSN", DEFAULT_DSN)


def _server_available() -> bool:
    try:
        with psycopg.connect(DSN, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _server_available(), reason="sin TimescaleDB local")


@pytest.fixture
def database() -> Iterator[str]:
    name = f"trading_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    yield DSN.rsplit("/", 1)[0] + f"/{name}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


def test_load_is_idempotent_and_respects_the_holdout(tmp_path: Path, database: str) -> None:
    store = Store(tmp_path)
    start = datetime(2024, 12, 30, tzinfo=UTC)
    frame = parse_klines("\n".join(kline_rows(start, timedelta(hours=4), 18))).frame
    store.write_klines(frame, "futures_um", "4h", "BTCUSDT")  # 6 velas caen en 2025
    store.write_funding(parse_funding(month_funding(2024, 12)), "BTCUSDT")
    store.write_manifest({"a": "1"})

    first = load(store, database)
    second = load(store, database)
    assert first == second
    assert (first.klines, first.funding) == (12, 93)
    with psycopg.connect(database) as conn:
        rows = conn.execute("SELECT count(*), max(open_time) FROM klines").fetchone()
        assert rows == (12, datetime(2024, 12, 31, 20, tzinfo=UTC))
        hypertables = conn.execute(
            "SELECT hypertable_name FROM timescaledb_information.hypertables ORDER BY 1"
        ).fetchall()
        assert hypertables == [("funding",), ("klines",)]
