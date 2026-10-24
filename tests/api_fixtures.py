"""Repositorio y almacén sintéticos para probar la API sin datos reales."""

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
from fastapi.testclient import TestClient

from trading.api.app import create_app
from trading.api.settings import ApiSettings
from trading.backtest.trials import HEADER
from trading.data.holdout import REPO_ROOT
from trading.data.parse import FUNDING_SCHEMA, KLINE_SCHEMA
from trading.data.store import Store

START = datetime(2024, 1, 1, tzinfo=UTC)
END = datetime(2025, 1, 1, tzinfo=UTC)


def _klines(start: datetime, step: timedelta, count: int, price: float) -> pl.DataFrame:
    times = [start + i * step for i in range(count)]
    closes = [price * (1 + 0.001 * ((i % 17) - 8)) for i in range(count)]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [1.0] * count,
            "close_time": [t + step - timedelta(milliseconds=1) for t in times],
            "quote_volume": [1e6] * count,
            "trades": [1] * count,
            "taker_buy_volume": [0.5] * count,
            "taker_buy_quote_volume": [0.5] * count,
        },
        schema=KLINE_SCHEMA,
    )


def _trade(i: int, r: float) -> dict[str, object]:
    entry = START + timedelta(days=3 * i)
    return {
        "simbolo": "BTCUSDT",
        "lado": "LONG" if i % 2 else "SHORT",
        "senal": entry.isoformat(),
        "entrada": entry.isoformat(),
        "precio_entrada": "40000",
        "stop": "39000",
        "cantidad": "0.0075",
        "riesgo_planificado": "7.5",
        "salida": (entry + timedelta(days=1)).isoformat(),
        "precio_salida": str(40000 + 1000 * r),
        "motivo_salida": "STOP" if r < 0 else "SEÑAL",
        "comisiones": "0.30",
        "funding": "0.05",
        "pnl": str(round(7.5 * r, 6)),
        "r": r,
        "regimen": "alcista",
    }


def _result(
    trial: str, hypothesis: str, sample: str, params: dict[str, object], with_trades: bool
) -> dict[str, object]:
    r = [1.5, -1.0, 0.5, -1.0, 2.0, -0.5]
    payload: dict[str, object] = {
        "trial_id": trial,
        "hipotesis": hypothesis,
        "variante": "base" if sample == "principal" else "x",
        "tipo_muestra": sample,
        "parametros": params,
        "dataset_id": "d" * 64,
        "prereg": "p",
        "codigo_commit": "c" * 40,
        "resumen": {
            "operaciones": len(r),
            "esperanza_r": sum(r) / len(r),
            "ic90_r": [-0.4, 0.9],
            "pf": 1.6,
            "sharpe_por_operacion": 0.2,
            "tasa_acierto": 0.5,
            "por_direccion": {
                "LONG": {"n": 3, "esperanza_r": 0.3},
                "SHORT": {"n": 3, "esperanza_r": 0.0},
            },
            "por_semestre": {},
            "por_regimen": {"alcista": {"n": 6, "esperanza_r": 0.25}},
            "suma_r_mensual": {},
            "max_peso_mes": 0.5,
            "senales": {"EJECUTADA": 6},
            "vetos": {"RISK_PER_TRADE": 2, "BELOW_MIN_NOTIONAL": 1, "NO_EXISTE": 1},
            "salidas": {"STOP": 3, "SEÑAL": 3},
        },
        "r_mensual": [0.0] * 60,
    }
    if with_trades:
        payload["operaciones"] = [_trade(i, value) for i, value in enumerate(r)]
        payload["curva_capital"] = [
            [(START + timedelta(days=i)).isoformat(), str(1500 + 5 * i - 12 * (i % 4))]
            for i in range(30)
        ]
    return payload


def build_repo(root: Path, *, with_data: bool) -> Path:
    for relative in (
        "docs/adr/README.md",
        "docs/risk_register.md",
        "docs/presupuesto.md",
        "docs/datos/calidad-f3.md",
        "docs/estado-y-faltantes.md",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / relative, target)
    results = root / "research" / "results"
    results.mkdir(parents=True)
    rows = [",".join(HEADER)]
    trials: list[tuple[str, str, str, dict[str, object], bool]] = [
        (
            "T0001",
            "H1-v1",
            "principal",
            {"lookback": 7, "atr_period": 14, "atr_multiple": 2.0},
            True,
        ),
        (
            "T0002",
            "H1-v1",
            "robustez",
            {"lookback": 6, "atr_period": 14, "atr_multiple": 2.0},
            False,
        ),
        (
            "T0003",
            "H1-v1",
            "costes_x1.5",
            {"lookback": 7, "atr_period": 14, "atr_multiple": 2.0},
            False,
        ),
        ("T0004", "H2-v1", "principal", {"channel": 60}, True),
    ]
    for trial, hypothesis, sample, params, with_trades in trials:
        (results / f"{trial}.json").write_text(
            json.dumps(_result(trial, hypothesis, sample, params, with_trades)), encoding="utf-8"
        )
        rows.append(
            f"{trial},2026-10-23T00:00:00Z,{hypothesis},p,v,{{}},d,2020-01-01,2024-12-31,{sample},6,r,a,"
        )
    (root / "research" / "trials.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    gate = {
        "hipotesis": "H1-v1",
        "criterios": {"1_operaciones_>=200": False, "2_ic90_inferior_>0": False},
        "pasa_gate_sin_holdout": False,
        "valores": {
            "pf": 1.6,
            "dsr": 0.4,
            "pbo": 0.2,
            "maxdd_p95_mc": 0.1,
            "max_peso_mes": 0.5,
            "c16_cortos": "no",
        },
    }
    (results / "gate-f4.json").write_text(json.dumps({"gates": [gate]}), encoding="utf-8")
    if with_data:
        store = Store(root / "data")
        for symbol, price in (("BTCUSDT", 40000.0), ("ETHUSDT", 2500.0)):
            store.write_klines(
                _klines(START, timedelta(hours=4), 2196, price), "futures_um", "4h", symbol
            )
            store.write_klines(
                _klines(START - timedelta(days=300), timedelta(days=1), 666, price),
                "futures_um",
                "1d",
                symbol,
            )
            times = [START + i * timedelta(hours=8) for i in range(1098)]
            store.write_funding(
                pl.DataFrame(
                    {
                        "calc_time": times,
                        "funding_interval_hours": [8] * 1098,
                        "funding_rate": [0.0001] * 1098,
                    },
                    schema=FUNDING_SCHEMA,
                ),
                symbol,
            )
        store.write_klines(
            _klines(datetime(2019, 1, 1, tzinfo=UTC), timedelta(days=1), 2192, 30000.0),
            "spot",
            "1d",
            "BTCUSDT",
        )
        store.write_manifest({"a": "1"})
    return root


def client_for(root: Path, **changes: object) -> TestClient:
    settings = ApiSettings(
        auth_enabled=False,
        repo_root=root,
        data_root=root / "data",
        app_state=root / "app",
        web_dist=root / "dist",
    )
    for key, value in changes.items():
        object.__setattr__(settings, key, value)
    return TestClient(create_app(settings))
