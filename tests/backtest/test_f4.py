"""Ejecutor de la F4 de punta a punta sobre un almacén sintético (sin datos reales)."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from synthetic import random_walk
from trading.backtest.f4 import Context, regimes_from_spot, run_f4, write_summary
from trading.backtest.trials import HEADER, TrialRegistry
from trading.data.parse import FUNDING_SCHEMA, KLINE_SCHEMA
from trading.data.store import Store

START = datetime(2020, 1, 1, tzinfo=UTC)
END = datetime(2021, 7, 1, tzinfo=UTC)


def _frame(start: datetime, step: timedelta, count: int, seed: int, price: float) -> pl.DataFrame:
    bars = random_walk(count, seed=seed, start_price=price, vol=0.01 if step.days else 0.004)
    times = [start + i * step for i in range(count)]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": [b[0] for b in bars],
            "high": [b[1] for b in bars],
            "low": [b[2] for b in bars],
            "close": [b[3] for b in bars],
            "volume": [1.0] * count,
            "close_time": [t + step - timedelta(milliseconds=1) for t in times],
            "quote_volume": [1e9 / (seed + 1)] * count,
            "trades": [1] * count,
            "taker_buy_volume": [0.5] * count,
            "taker_buy_quote_volume": [0.5] * count,
        },
        schema=KLINE_SCHEMA,
    )


def _store(root: Path) -> Store:
    store = Store(root)
    days = (END - START).days
    for seed, (symbol, price) in enumerate(
        [("BTCUSDT", 9000.0), ("ETHUSDT", 200.0), ("SOLUSDT", 2.0), ("XRPUSDT", 0.2)]
    ):
        store.write_klines(
            _frame(START, timedelta(days=1), days, seed, price), "futures_um", "1d", symbol
        )
        store.write_klines(
            _frame(START, timedelta(hours=4), days * 6, seed + 10, price),
            "futures_um",
            "4h",
            symbol,
        )
        times = [START + i * timedelta(hours=8) for i in range(days * 3)]
        funding = pl.DataFrame(
            {
                "calc_time": times,
                "funding_interval_hours": [8] * len(times),
                "funding_rate": [0.0001 if i % 7 else 0.0009 for i in range(len(times))],
            },
            schema=FUNDING_SCHEMA,
        )
        store.write_funding(funding, symbol)
    spot_start = datetime(2019, 1, 1, tzinfo=UTC)
    spot_days = (END - spot_start).days
    store.write_klines(
        _frame(spot_start, timedelta(days=1), spot_days, 99, 4000.0), "spot", "1d", "BTCUSDT"
    )
    store.write_manifest({"sintetico": "0" * 64})
    return store


def test_f4_runs_every_suite_and_records_every_run(tmp_path: Path) -> None:
    store = _store(tmp_path / "data")
    trials = tmp_path / "trials.csv"
    trials.write_text(",".join(HEADER) + "\n", encoding="utf-8")
    logs: list[str] = []
    ctx = Context(
        store=store,
        registry=TrialRegistry(trials),
        dataset_id=store.read_manifest()[0],
        prereg="sintetico",
        results_dir=tmp_path / "results",
        regimes=regimes_from_spot(store, END),
        log=logs.append,
        start=START,
        end=END,
        grids={
            "H1": {"lookback": (6, 7), "atr_period": (14,), "atr_multiple": (2.0,)},
            "H2": {
                "channel": (48, 60),
                "exit_channel": (20,),
                "atr_short": (14,),
                "atr_long": (100,),
                "atr_multiple": (2.0,),
            },
            "H4": {"threshold_8h": (0.0005, 0.0006), "count": (3,)},
        },
    )
    outcome = run_f4(ctx)

    rows = TrialRegistry(trials).rows()
    samples = [(r["hipotesis_id"], r["tipo_muestra"]) for r in rows]
    # H1: principal, 1 variante, costes, +1 vela; H2: principal, 1, costes, 3 sensibilidades;
    # H4-H1 y H4-H2: principal, 1 variante y costes.
    assert len(rows) == 4 + 6 + 3 + 3
    assert [h for h, kind in samples if kind == "principal"] == [
        "H1-v1",
        "H2-v1",
        "H4-H1-v1",
        "H4-H2-v1",
    ]
    assert all(r["prereg_commit"] == "sintetico" for r in rows)
    for row in rows:
        payload = json.loads((tmp_path / "results" / f"{row['trial_id']}.json").read_text("utf-8"))
        assert payload["resumen"]["operaciones"] == int(row["n_operaciones"])
        assert len(payload["r_mensual"]) == 18
    principal = json.loads((tmp_path / "results" / "T0001.json").read_text("utf-8"))
    assert "operaciones" in principal
    assert "curva_capital" in principal

    gates = {g["hipotesis"]: g for g in outcome["gates"]}
    assert set(gates) == {"H1-v1", "H2-v1", "H4-H1-v1", "H4-H2-v1"}
    assert "h4_k_>=20" in gates["H4-H2-v1"]["criterios"]
    assert all(0 <= g["valores"]["pbo"] <= 1 for g in gates.values())

    summary = tmp_path / "f4.md"
    write_summary(outcome, ctx, summary)
    text = summary.read_text("utf-8")
    assert "## H1-v1:" in text
    assert "sellado" in text
