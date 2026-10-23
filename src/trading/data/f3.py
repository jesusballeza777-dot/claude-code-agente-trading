"""Canalización de la F3 con datos públicos: descarga, verificación, Parquet, calidad y universo.

Uso: `uv run python -m trading.data.f3` (descarga solo meses ≤ 2024-12; ACLARACIONES §6.11).

Pasos:
1. Lista de perpetuos USDⓈ-M del archivo (incluye deslistados) y candidatos de H2.
2. Velas diarias de todos los candidatos (para el universo) y spot diario de BTC y ETH
   desde 2019 (regímenes y validación cruzada).
3. Universo point-in-time de cada mes de 2020-2024 y unión de sus miembros.
4. Velas de 4h y funding de la unión (más BTC y ETH).
5. Manifiesto con SHA-256 de cada fichero, id del dataset, informe de calidad y universo.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

import polars as pl

from trading.data.archive import (
    ArchiveFile,
    Fetch,
    download,
    http_fetch,
    list_files,
    list_prefixes,
)
from trading.data.holdout import HOLDOUT_START, REPO_ROOT, ensure_research_window
from trading.data.parse import parse_funding, parse_klines, read_zip_csv
from trading.data.qc import (
    COMPLETENESS_TARGET,
    CrossCheck,
    FundingQC,
    SeriesQC,
    clean_klines,
    cross_check_closes,
    qc_funding,
    qc_klines,
)
from trading.data.store import Market, Store
from trading.data.universe import (
    CORE_SYMBOLS,
    UniverseSnapshot,
    candidate_symbols,
    reconstitution_dates,
    universe_at,
)

RESEARCH_START: Final = datetime(2020, 1, 1, tzinfo=UTC)
REGIME_START: Final = datetime(2019, 1, 1, tzinfo=UTC)
FUTURES_KLINES: Final = "data/futures/um/monthly/klines/"
FUNDING: Final = "data/futures/um/monthly/fundingRate/"
SPOT_KLINES: Final = "data/spot/monthly/klines/"
REPORT_DIR: Final = REPO_ROOT / "docs" / "datos"

Log = Callable[[str], None]


@dataclass
class F3Result:
    dataset_id: str = ""
    files: dict[str, str] = field(default_factory=dict)
    kline_qc: list[SeriesQC] = field(default_factory=list)
    funding_qc: list[FundingQC] = field(default_factory=list)
    cross: list[CrossCheck] = field(default_factory=list)
    universe: list[UniverseSnapshot] = field(default_factory=list)
    inexact_prices: int = 0
    candidates: int = 0
    listed: int = 0


def month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=UTC)


def research_months(files: Iterable[ArchiveFile], since: datetime) -> list[ArchiveFile]:
    """Ficheros mensuales desde `since` y anteriores al holdout, con la guardia aplicada."""
    selected = []
    for item in files:
        start = month_start(*item.month)
        if start < since or start >= HOLDOUT_START:
            continue
        end = month_start(*item.month) + timedelta(days=32)
        ensure_research_window(start, min(end.replace(day=1), HOLDOUT_START))
        selected.append(item)
    return selected


def fetch_many(
    store: Store,
    requests: list[tuple[str, datetime]],
    fetch: Fetch,
    pool: ThreadPoolExecutor,
    result: F3Result,
) -> list[list[Path]]:
    """Lista y descarga en paralelo varias series (prefijo, desde); devuelve sus zips."""
    listings = list(
        pool.map(lambda req: research_months(list_files(req[0], fetch), req[1]), requests)
    )
    flat = [item for files in listings for item in files]
    done = dict(
        zip(
            (item.key for item in flat),
            pool.map(lambda item: download(item.key, store.raw, fetch), flat),
            strict=True,
        )
    )
    for key, (_, sha) in done.items():
        result.files[key] = sha
    return [[done[item.key][0] for item in files] for files in listings]


def build_klines(
    store: Store,
    paths: list[Path],
    market: Market,
    interval: str,
    symbol: str,
    result: F3Result,
) -> pl.DataFrame:
    frames = []
    for path in paths:
        parsed = parse_klines(read_zip_csv(path))
        result.inexact_prices += parsed.inexact_prices
        frames.append(parsed.frame)
    raw = pl.concat(frames) if frames else pl.DataFrame()
    qc = qc_klines(raw, market, interval, symbol)
    result.kline_qc.append(qc)
    clean = clean_klines(raw) if raw.height else raw
    if clean.height:
        store.write_klines(clean, market, interval, symbol)
    return clean


def build_funding(store: Store, paths: list[Path], symbol: str, result: F3Result) -> None:
    frames = [parse_funding(read_zip_csv(path)) for path in paths]
    if not frames:
        return
    raw = pl.concat(frames)
    result.funding_qc.append(qc_funding(raw, symbol))
    clean = raw.unique(subset="calc_time", keep="first").sort("calc_time")
    store.write_funding(clean, symbol)


def run_f3(
    store: Store, fetch: Fetch = http_fetch, workers: int = 16, log: Log = print
) -> F3Result:
    result = F3Result()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        listed = [p.rstrip("/").rsplit("/", 1)[-1] for p in list_prefixes(FUTURES_KLINES, fetch)]
        candidates = candidate_symbols(listed)
        result.listed, result.candidates = len(listed), len(candidates)
        log(f"perpetuos en el archivo: {len(listed)}; candidatos de H2: {len(candidates)}")

        daily: dict[str, pl.DataFrame] = {}
        requests = [(f"{FUTURES_KLINES}{s}/1d/", RESEARCH_START) for s in candidates]
        for symbol, paths in zip(
            candidates, fetch_many(store, requests, fetch, pool, result), strict=True
        ):
            if paths:
                daily[symbol] = build_klines(store, paths, "futures_um", "1d", symbol, result)
        log(f"velas diarias: {len(daily)} símbolos con datos en 2020-2024")

        requests = [(f"{SPOT_KLINES}{s}/1d/", REGIME_START) for s in CORE_SYMBOLS]
        for symbol, paths in zip(
            CORE_SYMBOLS, fetch_many(store, requests, fetch, pool, result), strict=True
        ):
            spot = build_klines(store, paths, "spot", "1d", symbol, result)
            if symbol in daily:
                result.cross.append(cross_check_closes(symbol, spot, daily[symbol]))

        result.universe = [
            universe_at(date, daily) for date in reconstitution_dates(RESEARCH_START, HOLDOUT_START)
        ]
        union = sorted(set(CORE_SYMBOLS) | {s for u in result.universe for s in u.members})
        log(f"universo de H2: {len(union)} símbolos distintos en 2020-2024")

        requests = [(f"{FUTURES_KLINES}{s}/4h/", RESEARCH_START) for s in union]
        four_hours = fetch_many(store, requests, fetch, pool, result)
        requests = [(f"{FUNDING}{s}/", RESEARCH_START) for s in union]
        funding = fetch_many(store, requests, fetch, pool, result)
        for symbol, kline_paths, funding_paths in zip(union, four_hours, funding, strict=True):
            build_klines(store, kline_paths, "futures_um", "4h", symbol, result)
            build_funding(store, funding_paths, symbol, result)

    result.dataset_id = store.write_manifest(result.files)
    log(f"dataset {result.dataset_id}: {len(result.files)} ficheros verificados")
    return result


# --- informes --------------------------------------------------------------------------------


def quality_report(result: F3Result, generated: datetime) -> str:
    daily = [q for q in result.kline_qc if q.market == "futures_um" and q.interval == "1d"]
    detailed = [q for q in result.kline_qc if not (q.market == "futures_um" and q.interval == "1d")]
    total_expected = sum(q.expected for q in result.kline_qc)
    total_missing = sum(q.missing for q in result.kline_qc)
    overall = 1 - total_missing / total_expected if total_expected else 1.0
    below = [q for q in result.kline_qc if q.completeness < COMPLETENESS_TARGET]
    dirty = [q for q in result.kline_qc if not q.clean]
    lines = [
        "# Informe de calidad de datos de la F3",
        "",
        f"- **Generado:** {generated:%Y-%m-%d %H:%M} UTC por `trading.data.f3`.",
        f"- **Dataset:** `{result.dataset_id}` (SHA-256 del manifiesto de ficheros).",
        f"- **Ficheros verificados con SHA-256:** {len(result.files):,}.",
        "- **Fuente:** archivo público de Binance (`data.binance.vision`, por su espejo en S3).",
        "  Sin claves y sin endpoints de cuenta. Solo meses hasta 2024-12: el holdout no se",
        "  descarga.",
        f"- **Perpetuos USDⓈ-M en el archivo:** {result.listed}; candidatos de H2 tras exclusiones:"
        f" {result.candidates}.",
        f"- **Precios que no vuelven exactos desde float64:** {result.inexact_prices}.",
        "",
        "## Resumen",
        "",
        "| Medida | Valor | Objetivo |",
        "|---|---|---|",
        f"| Completitud global de velas | {overall:.4%} | > {COMPLETENESS_TARGET:.1%} |",
        f"| Series por debajo del objetivo | {len(below)} de {len(result.kline_qc)} | 0 |",
        f"| Series con duplicados, desorden, desalineación o OHLC imposible | {len(dirty)} | 0 |",
        "",
        "La completitud de cada serie se mide entre su primera y su última vela dentro del",
        "periodo: un contrato deslistado no cuenta como hueco después de su última vela.",
        "",
        "## Velas de 4h, spot diario y regímenes",
        "",
        "| Mercado | Intervalo | Símbolo | Velas | Esperadas | Faltan | Completitud | Mayor hueco "
        "| Dup. | Desorden | Desalin. | close_time | OHLC | Primera | Última |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines += [_qc_row(q) for q in sorted(detailed, key=lambda q: (q.market, q.interval, q.symbol))]
    lines += [
        "",
        "## Velas diarias de perpetuos (universo de H2)",
        "",
        f"- Series: {len(daily)}; completitud media: "
        f"{sum(q.completeness for q in daily) / max(len(daily), 1):.4%}.",
        f"- Por debajo del objetivo: "
        f"{sum(1 for q in daily if q.completeness < COMPLETENESS_TARGET)}.",
        "",
    ]
    low_daily = [q for q in daily if q.completeness < COMPLETENESS_TARGET or not q.clean]
    if low_daily:
        lines += [
            "| Mercado | Intervalo | Símbolo | Velas | Esperadas | Faltan | Completitud | Mayor "
            "hueco | Dup. | Desorden | Desalin. | close_time | OHLC | Primera | Última |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        lines += [_qc_row(q) for q in sorted(low_daily, key=lambda q: q.symbol)]
        lines.append("")
    lines += [
        "## Funding",
        "",
        "| Símbolo | Liquidaciones | Duplicados | Desorden | Intervalos (h) | Mayor separación |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {f.symbol} | {f.rows:,} | {f.duplicates} | {f.out_of_order} | "
        f"{', '.join(map(str, f.intervals))} | {f.largest_gap} |"
        for f in sorted(result.funding_qc, key=lambda f: f.symbol)
    ]
    lines += [
        "",
        "## Validación cruzada: cierre diario spot frente a perpetuo",
        "",
        "Misma fuente, distinto mercado. Una segunda fuente independiente (otro exchange)",
        "queda **por verificar** (ver `docs/estado-y-faltantes.md`).",
        "",
        "| Activo | Días | Mediana \\|perp/spot - 1\\| | p99 | Máximo | Días > 1% |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {c.symbol} | {c.days:,} | {c.median_abs_diff:.4%} | {c.p99_abs_diff:.4%} | "
        f"{c.max_abs_diff:.4%} | {c.days_over_1pct} |"
        for c in result.cross
    ]
    return "\n".join(lines) + "\n"


def universe_report(result: F3Result, generated: datetime) -> str:
    lines = [
        "# Universo point-in-time de H2-v1",
        "",
        f"- **Generado:** {generated:%Y-%m-%d %H:%M} UTC; dataset `{result.dataset_id}`.",
        "- **Regla:** pre-registro H2-v1 §3 y ACLARACIONES-v1 §2. BTC y ETH más las 8 alts con",
        "  mayor mediana de volumen en USDT de los 30 días anteriores, entre los perpetuos con",
        "  90 días de historia en el archivo. Incluye contratos deslistados.",
        "- El archivo de perpetuos empieza en 2020-01, así que el primer universo con miembros",
        "  es el de 2020-04-01 (90 días de historia).",
        "",
        "| Fecha | Elegibles | Miembros (por liquidez) |",
        "|---|---|---|",
    ]
    lines += [
        f"| {u.date:%Y-%m-%d} | {len(u.ranking)} | {', '.join(u.members) or '—'} |"
        for u in result.universe
    ]
    return "\n".join(lines) + "\n"


def _qc_row(q: SeriesQC) -> str:
    first = f"{q.first_open:%Y-%m-%d}" if q.first_open else "—"
    last = f"{q.last_open:%Y-%m-%d}" if q.last_open else "—"
    return (
        f"| {q.market} | {q.interval} | {q.symbol} | {q.rows:,} | {q.expected:,} | {q.missing} | "
        f"{q.completeness:.4%} | {q.largest_gap} | {q.duplicates} | {q.out_of_order} | "
        f"{q.misaligned} | {q.bad_close_time} | {q.bad_ohlc} | {first} | {last} |"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F3: datos públicos de Binance, sin claves")
    parser.add_argument("--data-root", type=Path, default=Store().root)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args(argv)
    store = Store(args.data_root)
    result = run_f3(store, workers=args.workers)
    generated = datetime.now(UTC)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "calidad-f3.md").write_text(quality_report(result, generated), "utf-8")
    (args.report_dir / "universo-h2-v1.md").write_text(universe_report(result, generated), "utf-8")
    print(f"informes en {args.report_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
