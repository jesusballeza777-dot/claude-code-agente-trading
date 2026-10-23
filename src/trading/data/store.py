"""Almacén Parquet de datos públicos, con la guardia del holdout en cada lectura.

Estructura (fuera de git, en `data/`):

    data/raw/<clave del archivo>                         zips y .CHECKSUM originales
    data/parquet/klines/<mercado>/<intervalo>/<SÍMBOLO>.parquet
    data/parquet/funding/<SÍMBOLO>.parquet
    data/manifest.json                                    ficheros, SHA-256 e id del dataset

Una vela de intervalo I abierta en t pertenece al rango [inicio, fin) si t ≥ inicio y
t + I ≤ fin (ACLARACIONES-v1 §1.2-1.3). El funding pertenece si inicio ≤ calc_time < fin.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Literal

import polars as pl

from trading.data.holdout import REPO_ROOT, ensure_research_window
from trading.data.parse import FUNDING_SCHEMA, KLINE_SCHEMA

DATA_ROOT: Final = REPO_ROOT / "data"
Market = Literal["spot", "futures_um"]
INTERVALS: Final = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}


@dataclass(frozen=True, slots=True)
class Store:
    root: Path = DATA_ROOT

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    def kline_path(self, market: Market, interval: str, symbol: str) -> Path:
        _check_interval(interval)
        return self.root / "parquet" / "klines" / market / interval / f"{symbol}.parquet"

    def funding_path(self, symbol: str) -> Path:
        return self.root / "parquet" / "funding" / f"{symbol}.parquet"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    # --- escritura ---------------------------------------------------------------------------

    def write_klines(self, frame: pl.DataFrame, market: Market, interval: str, symbol: str) -> Path:
        path = self.kline_path(market, interval, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.sort("open_time").write_parquet(path)
        return path

    def write_funding(self, frame: pl.DataFrame, symbol: str) -> Path:
        path = self.funding_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.sort("calc_time").write_parquet(path)
        return path

    def write_manifest(self, entries: dict[str, str]) -> str:
        """Guarda {clave: sha256} y devuelve el id del dataset (SHA-256 del manifiesto)."""
        dataset_id = dataset_id_of(entries)
        payload = {"dataset_id": dataset_id, "files": dict(sorted(entries.items()))}
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        return dataset_id

    def read_manifest(self) -> tuple[str, dict[str, str]]:
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return str(payload["dataset_id"]), dict(payload["files"])

    # --- lectura con guardia -----------------------------------------------------------------

    def read_klines(
        self,
        market: Market,
        interval: str,
        symbol: str,
        start: datetime,
        end: datetime,
        *,
        hypothesis: str | None = None,
    ) -> pl.DataFrame:
        """Velas completas dentro de [start, end). Se niega a leer el holdout sin autorización."""
        ensure_research_window(start, end, hypothesis=hypothesis)
        path = self.kline_path(market, interval, symbol)
        if not path.exists():
            return pl.DataFrame(schema=KLINE_SCHEMA)
        step = INTERVALS[interval]
        return (
            pl.scan_parquet(path)
            .filter(
                (pl.col("open_time") >= _utc(start)) & (pl.col("open_time") + step <= _utc(end))
            )
            .sort("open_time")
            .collect()
        )

    def read_funding(
        self, symbol: str, start: datetime, end: datetime, *, hypothesis: str | None = None
    ) -> pl.DataFrame:
        """Funding con calc_time en [start, end). Misma guardia que las velas."""
        ensure_research_window(start, end, hypothesis=hypothesis)
        path = self.funding_path(symbol)
        if not path.exists():
            return pl.DataFrame(schema=FUNDING_SCHEMA)
        return (
            pl.scan_parquet(path)
            .filter((pl.col("calc_time") >= _utc(start)) & (pl.col("calc_time") < _utc(end)))
            .sort("calc_time")
            .collect()
        )

    def symbols(self, market: Market, interval: str) -> list[str]:
        folder = self.kline_path(market, interval, "X").parent
        return sorted(p.stem for p in folder.glob("*.parquet"))


def dataset_id_of(entries: dict[str, str]) -> str:
    lines = "".join(f"{key} {sha}\n" for key, sha in sorted(entries.items()))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def _check_interval(interval: str) -> None:
    if interval not in INTERVALS:
        raise ValueError(f"intervalo no soportado: {interval}")


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC)
