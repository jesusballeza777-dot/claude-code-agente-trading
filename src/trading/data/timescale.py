"""Carga del almacén Parquet en PostgreSQL + TimescaleDB (ADR-016).

Parquet es la fuente de verdad de la investigación; la base de datos es una copia para
consultas y para el Centro de Mando. La carga lee con la guardia del holdout, así que nunca
mete en la base datos ≥ 2025-01-01 sin autorización.

Conexión: `TRADING_DB_DSN` (por defecto, la base local de `docker compose`, sin contraseña y
solo accesible desde 127.0.0.1). En el VPS la base no publica puerto y la contraseña llega por
SOPS en la F6; nunca se escribe en el código (CLAUDE.md regla 1).

Uso: `uv run python -m trading.data.timescale`.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

import psycopg

from trading.data.holdout import HOLDOUT_START
from trading.data.store import Market, Store

DEFAULT_DSN: Final = "postgresql://trading@127.0.0.1:5432/trading"
EARLIEST: Final = datetime(2017, 1, 1, tzinfo=UTC)

SCHEMA_SQL: Final = """
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE TABLE IF NOT EXISTS klines (
    market text NOT NULL,
    interval text NOT NULL,
    symbol text NOT NULL,
    open_time timestamptz NOT NULL,
    open double precision NOT NULL,
    high double precision NOT NULL,
    low double precision NOT NULL,
    close double precision NOT NULL,
    volume double precision NOT NULL,
    quote_volume double precision NOT NULL,
    trades bigint NOT NULL,
    PRIMARY KEY (market, interval, symbol, open_time)
);
SELECT create_hypertable('klines', by_range('open_time'), if_not_exists => TRUE);
CREATE TABLE IF NOT EXISTS funding (
    symbol text NOT NULL,
    calc_time timestamptz NOT NULL,
    funding_interval_hours integer NOT NULL,
    funding_rate double precision NOT NULL,
    PRIMARY KEY (symbol, calc_time)
);
SELECT create_hypertable('funding', by_range('calc_time'), if_not_exists => TRUE);
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id text PRIMARY KEY,
    loaded_at timestamptz NOT NULL,
    klines bigint NOT NULL,
    funding bigint NOT NULL
);
"""

SERIES: Final[tuple[tuple[Market, str], ...]] = (
    ("futures_um", "1d"),
    ("futures_um", "4h"),
    ("spot", "1d"),
)


@dataclass(frozen=True, slots=True)
class LoadSummary:
    dataset_id: str
    klines: int
    funding: int


def load(store: Store, dsn: str) -> LoadSummary:
    dataset_id, _ = store.read_manifest()
    total_klines = total_funding = 0
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
        for market, interval in SERIES:
            for symbol in store.symbols(market, interval):
                frame = store.read_klines(market, interval, symbol, EARLIEST, HOLDOUT_START)
                cur.execute(
                    "DELETE FROM klines WHERE market = %s AND interval = %s AND symbol = %s",
                    (market, interval, symbol),
                )
                columns = "open_time, open, high, low, close, volume, quote_volume, trades"
                with cur.copy(
                    f"COPY klines (market, interval, symbol, {columns}) FROM STDIN"
                ) as copy:
                    for row in frame.select(columns.split(", ")).iter_rows():
                        copy.write_row((market, interval, symbol, *row))
                total_klines += frame.height
        for path in sorted((store.root / "parquet" / "funding").glob("*.parquet")):
            symbol = path.stem
            frame = store.read_funding(symbol, EARLIEST, HOLDOUT_START)
            cur.execute("DELETE FROM funding WHERE symbol = %s", (symbol,))
            with cur.copy(
                "COPY funding (symbol, calc_time, funding_interval_hours, funding_rate) FROM STDIN"
            ) as copy:
                for row in frame.iter_rows():
                    copy.write_row((symbol, *row))
            total_funding += frame.height
        cur.execute(
            "INSERT INTO datasets VALUES (%s, now(), %s, %s) ON CONFLICT (dataset_id) DO UPDATE "
            "SET loaded_at = now(), klines = EXCLUDED.klines, funding = EXCLUDED.funding",
            (dataset_id, total_klines, total_funding),
        )
    return LoadSummary(dataset_id, total_klines, total_funding)


def main() -> int:
    summary = load(Store(), os.environ.get("TRADING_DB_DSN", DEFAULT_DSN))
    print(
        f"dataset {summary.dataset_id}: {summary.klines:,} velas y "
        f"{summary.funding:,} liquidaciones de funding cargadas"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
