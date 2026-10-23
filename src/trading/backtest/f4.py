"""Ejecutor de la F4: H1, H2 y H4 sobre 2020-2024 con registro obligatorio (ACLARACIONES §7.16).

Uso: `uv run python -m trading.backtest.f4`. Antes de correr nada comprueba que el
pre-registro sigue congelado (`4614d65`) y que `trials.csv` es utilizable. Cada corrida se
anota en `research/trials.csv` y deja su resultado en `research/results/<trial>.json`.
El holdout no se toca: los datos se leen con la guardia y terminan el 2025-01-01.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Final

import polars as pl

from trading.backtest import metrics as m
from trading.backtest.data import load_market
from trading.backtest.engine import BacktestConfig, CostConfig, run_backtest
from trading.backtest.model import BacktestResult, MarketData, Strategy, Trade
from trading.backtest.trials import PREREG_COMMIT, TrialRegistry, verify_frozen_preregistration
from trading.data.holdout import HOLDOUT_START, REPO_ROOT
from trading.data.store import Store
from trading.data.universe import UniverseSnapshot, base_asset, reconstitution_dates, universe_at
from trading.features.regimes import Regime, regime_labels
from trading.risk import RiskLimits, load_extended_limits_v1_propuesto, load_plan_limits_f7_f8
from trading.risk.models import RISK_DECIMAL_CONTEXT
from trading.signals.h1 import H1Params, H1Strategy
from trading.signals.h2 import H2Params, H2Strategy, IndicatorCache
from trading.signals.h4 import FundingFilter, H4Params, blocks, mean_funding_before

START: Final = datetime(2020, 1, 1, tzinfo=UTC)
END: Final = HOLDOUT_START
PERIOD: Final = (START, END - timedelta(days=1))
RESULTS_DIR: Final = REPO_ROOT / "research" / "results"
SUMMARY_PATH: Final = REPO_ROOT / "docs" / "resultados" / "f4-2020-2024.md"
GATE_TRADES: Final = 200

H1_GRID: Final = {
    "lookback": (6, 7, 8),
    "atr_period": (11, 14, 17),
    "atr_multiple": (1.6, 2.0, 2.4),
}
H2_GRID: Final = {
    "channel": (48, 60, 72),
    "exit_channel": (16, 20, 24),
    "atr_short": (11, 14, 17),
    "atr_long": (80, 100, 120),
    "atr_multiple": (1.6, 2.0, 2.4),
}
H4_GRID: Final = {"threshold_8h": (0.0004, 0.0005, 0.0006), "count": (2, 3, 4)}


@dataclass
class Context:
    store: Store
    registry: TrialRegistry
    dataset_id: str
    prereg: str
    results_dir: Path
    regimes: dict[datetime, Regime | None]
    log: Callable[[str], None] = print
    code_commit: str = ""
    principal_sharpes: dict[str, float] = field(default_factory=dict)
    start: datetime = START
    end: datetime = END
    grids: Mapping[str, Mapping[str, Sequence[Any]]] = field(
        default_factory=lambda: {"H1": H1_GRID, "H2": H2_GRID, "H4": H4_GRID}
    )

    @property
    def months(self) -> list[str]:
        return month_keys(self.start, self.end)


# --- métricas de una corrida -------------------------------------------------------------------


def r_values(trades: Sequence[Trade]) -> list[float]:
    return [float(t.r_multiple) for t in trades]


def summarize(result: BacktestResult, regimes: Mapping[datetime, Regime | None]) -> dict[str, Any]:
    trades = result.trades
    r = r_values(trades)
    ci = m.bootstrap_mean_ci(r)
    labels = [_label(regimes, t.entry_time) for t in trades]
    monthly = m.monthly_sums(r, [t.exit_time for t in trades])
    by_side = {
        side: [float(t.r_multiple) for t in trades if t.side.value == side]
        for side in ("LONG", "SHORT")
    }
    semesters: dict[str, list[float]] = {}
    for trade in trades:
        key = f"{trade.exit_time.year}-S{1 if trade.exit_time.month <= 6 else 2}"
        semesters.setdefault(key, []).append(float(trade.r_multiple))
    outcomes: dict[str, int] = {}
    veto_reasons: dict[str, int] = {}
    for signal in result.signals:
        outcomes[signal.outcome.value] = outcomes.get(signal.outcome.value, 0) + 1
        for reason in signal.reasons:
            veto_reasons[reason.value] = veto_reasons.get(reason.value, 0) + 1
    exits: dict[str, int] = {}
    for trade in trades:
        exits[trade.exit_reason.value] = exits.get(trade.exit_reason.value, 0) + 1
    return {
        "operaciones": len(trades),
        "esperanza_r": m.expectancy(r),
        "ic90_r": [ci.low, ci.high],
        "pf": _finite(m.profit_factor(r)),
        "sharpe_por_operacion": m.sharpe_per_trade(r),
        "tasa_acierto": sum(1 for x in r if x > 0) / len(r) if r else 0.0,
        "capital_final": str(result.final_equity),
        "corte_duro": result.halted_at.isoformat() if result.halted_at else None,
        "max_dd_curva": m.max_drawdown([float(e) for _, e in result.equity_curve]),
        "por_direccion": {
            k: {"n": len(v), "esperanza_r": m.expectancy(v)} for k, v in by_side.items()
        },
        "por_semestre": {
            k: {"n": len(v), "esperanza_r": m.expectancy(v)} for k, v in sorted(semesters.items())
        },
        "por_regimen": {
            k: {"n": n, "esperanza_r": e} for k, (n, e) in m.regime_expectancy(r, labels).items()
        },
        "suma_r_mensual": monthly,
        "max_peso_mes": m.max_month_share(monthly),
        "senales": outcomes,
        "vetos": dict(sorted(veto_reasons.items())),
        "salidas": exits,
    }


def trades_payload(
    trades: Sequence[Trade], regimes: Mapping[datetime, Regime | None]
) -> list[dict[str, Any]]:
    return [
        {
            "simbolo": t.symbol,
            "lado": t.side.value,
            "senal": t.signal_time.isoformat(),
            "entrada": t.entry_time.isoformat(),
            "precio_entrada": str(t.entry_price),
            "stop": str(t.stop_price),
            "cantidad": str(t.quantity),
            "riesgo_planificado": str(t.planned_risk),
            "salida": t.exit_time.isoformat(),
            "precio_salida": str(t.exit_price),
            "motivo_salida": t.exit_reason.value,
            "comisiones": str(t.fees),
            "funding": str(t.funding),
            "pnl": str(t.pnl),
            "r": float(t.r_multiple),
            "regimen": (_label(regimes, t.entry_time) or ""),
        }
        for t in trades
    ]


def _label(regimes: Mapping[datetime, Regime | None], moment: datetime) -> str | None:
    day = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    label = regimes.get(day)
    return label.value if label else None


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def month_keys(start: datetime, end: datetime) -> list[str]:
    """Meses naturales del periodo (60 en 2020-2024)."""
    return [f"{d:%Y-%m}" for d in reconstitution_dates(start, end)] or [f"{start:%Y-%m}"]


def monthly_vector(trades: Sequence[Trade], months: Sequence[str]) -> list[float]:
    """Suma de R por mes natural de salida."""
    sums = m.monthly_sums(r_values(trades), [t.exit_time for t in trades])
    return [sums.get(month, 0.0) for month in months]


# --- corridas ---------------------------------------------------------------------------------


def record(
    ctx: Context,
    *,
    hypothesis: str,
    variant: str,
    params: Mapping[str, Any],
    sample: str,
    result: BacktestResult,
    notes: str = "",
    extra: Mapping[str, Any] | None = None,
    keep_trades: bool = False,
) -> dict[str, Any]:
    summary = summarize(result, ctx.regimes)
    payload: dict[str, Any] = {
        "hipotesis": hypothesis,
        "variante": variant,
        "tipo_muestra": sample,
        "parametros": dict(params),
        "dataset_id": ctx.dataset_id,
        "prereg": ctx.prereg,
        "codigo_commit": ctx.code_commit,
        "resumen": summary,
        "r_mensual": monthly_vector(result.trades, ctx.months),
        **(extra or {}),
    }
    if keep_trades:
        payload["operaciones"] = trades_payload(result.trades, ctx.regimes)
        payload["curva_capital"] = [
            [t.isoformat(), str(e)] for t, e in result.equity_curve if t.hour == 0
        ]
    row = ctx.registry.record_run(
        hypothesis=hypothesis,
        variant=variant,
        params=params,
        dataset_id=ctx.dataset_id,
        period=(ctx.start, ctx.end - timedelta(days=1)),
        sample=sample,
        trades=len(result.trades),
        result=payload,
        results_dir=ctx.results_dir,
        prereg=ctx.prereg,
        notes=notes,
    )
    ctx.log(
        f"  {row.trial_id} {hypothesis} {variant} [{sample}]: "
        f"{summary['operaciones']} operaciones, esperanza {summary['esperanza_r']:+.3f} R"
    )
    return {"trial_id": row.trial_id, **payload}


def research_limits(strategy_id: str) -> RiskLimits:
    """Límites F7-F8 firmados con cortos habilitados para la hipótesis evaluada (§7.5)."""
    return replace(load_plan_limits_f7_f8(), short_enabled_strategies=frozenset({strategy_id}))


def config_for(data: MarketData, strategy_id: str, **changes: Any) -> BacktestConfig:
    return replace(
        BacktestConfig(limits=research_limits(strategy_id), start=data.start, end=data.end),
        **changes,
    )


def grid(spec: Mapping[str, Sequence[object]]) -> list[dict[str, Any]]:
    keys = list(spec)
    return [dict(zip(keys, values, strict=True)) for values in itertools.product(*spec.values())]


def one_at_a_time(
    spec: Mapping[str, Sequence[object]], base: Mapping[str, Any]
) -> list[dict[str, Any]]:
    variants = []
    for key, values in spec.items():
        for value in values:
            if value != base[key]:
                variants.append({**base, key: value})
    return variants


def variant_name(params: Mapping[str, Any], base: Mapping[str, Any]) -> str:
    changed = [f"{k}={v}" for k, v in params.items() if v != base[k]]
    return "base" if not changed else ",".join(changed)


@dataclass
class SuiteResult:
    hypothesis: str
    principal: dict[str, Any]
    grid_runs: list[dict[str, Any]]
    stress: dict[str, Any]
    sensitivities: list[dict[str, Any]]
    base_params: dict[str, Any]
    grid_spec: Mapping[str, Sequence[object]]
    principal_result: BacktestResult
    extra: dict[str, Any] = field(default_factory=dict)


def run_suite(
    ctx: Context,
    hypothesis: str,
    strategy_id: str,
    data: MarketData,
    make: Callable[[dict[str, Any]], Strategy],
    base: dict[str, Any],
    spec: Mapping[str, Sequence[object]],
    sensitivities: Iterable[tuple[str, dict[str, Any], str]] = (),
    extra_principal: Callable[[BacktestResult, Strategy], dict[str, Any]] | None = None,
) -> SuiteResult:
    ctx.log(f"{hypothesis}: corrida principal")
    strategy = make(base)
    result = run_backtest(strategy, data, config_for(data, strategy_id))
    extra = extra_principal(result, strategy) if extra_principal else {}
    principal = record(
        ctx,
        hypothesis=hypothesis,
        variant="base",
        params=base,
        sample="principal",
        result=result,
        keep_trades=True,
        extra=extra,
    )
    ctx.principal_sharpes[hypothesis] = float(principal["resumen"]["sharpe_por_operacion"])
    runs = []
    for params in grid(spec):
        if params == base:
            runs.append(principal)
            continue
        variant_result = run_backtest(make(params), data, config_for(data, strategy_id))
        runs.append(
            record(
                ctx,
                hypothesis=hypothesis,
                variant=variant_name(params, base),
                params=params,
                sample="robustez",
                result=variant_result,
            )
        )
    ctx.log(f"{hypothesis}: costes x1.5")
    stressed = run_backtest(
        make(base), data, config_for(data, strategy_id, costs=CostConfig(scale=Decimal("1.5")))
    )
    stress = record(
        ctx,
        hypothesis=hypothesis,
        variant="costes_x1.5",
        params=base,
        sample="costes_x1.5",
        result=stressed,
    )
    sens = []
    for name, changes, note in sensitivities:
        ctx.log(f"{hypothesis}: sensibilidad {name}")
        sensitivity = run_backtest(make(base), data, config_for(data, strategy_id, **changes))
        sens.append(
            record(
                ctx,
                hypothesis=hypothesis,
                variant=name,
                params=base,
                sample="sensibilidad",
                result=sensitivity,
                notes=note,
            )
        )
    return SuiteResult(hypothesis, principal, runs, stress, sens, base, spec, result, extra)


# --- gate -------------------------------------------------------------------------------------


def gate(
    suite: SuiteResult,
    principal_sharpes: Sequence[float],
    months: Sequence[str],
    *,
    h4: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = suite.principal["resumen"]
    trades = suite.principal_result.trades
    r = r_values(trades)
    n = len(r)
    ci = summary["ic90_r"]
    pf = summary["pf"]
    dsr = m.deflated_sharpe(r, principal_sharpes)
    matrix = [list(row) for row in zip(*(run["r_mensual"] for run in suite.grid_runs), strict=True)]
    pbo = m.pbo_cscv(matrix) if n else 1.0
    monthly_groups: dict[str, list[float]] = {}
    for trade in trades:
        monthly_groups.setdefault(f"{trade.exit_time:%Y-%m}", []).append(float(trade.r_multiple))
    groups = [monthly_groups.get(month, []) for month in months]
    mc_dd = m.monte_carlo_max_drawdown(groups, months=len(months))
    one_param = one_at_a_time(suite.grid_spec, suite.base_params)
    robust = [run for run in suite.grid_runs if run["parametros"] in one_param]
    robust_ok = all(run["resumen"]["esperanza_r"] > 0 for run in robust)
    stress_ci = suite.stress["resumen"]["ic90_r"]
    regimes = summary["por_regimen"]
    positive_regimes = [
        k
        for k, v in regimes.items()
        if k != "sin etiqueta" and v["n"] >= 20 and v["esperanza_r"] > 0
    ]
    share = summary["max_peso_mes"]
    criteria = {
        "1_operaciones_>=200": n >= GATE_TRADES,
        "2_ic90_inferior_>0": ci[0] > 0,
        "3_pf_>=1.25": pf is None or pf >= 1.25,
        "4a_dsr_>=0.90": dsr >= 0.90,
        "4b_pbo_<=0.30": pbo <= 0.30,
        "5_maxdd_p95_mc_<=25%": mc_dd <= 0.25,
        "6a_parametros_±20%_esperanza_>0": robust_ok,
        "6b_costes_x1.5_ic90_inferior_>0": stress_ci[0] > 0,
        "7_positiva_en_>=2_de_3_regimenes": len(positive_regimes) >= 2,
        "8_ningun_mes_>30%": share is not None and share <= 0.30,
    }
    if h4 is not None:
        criteria.update({k: bool(v) for k, v in h4.items() if k.startswith("h4_")})
    sides = summary["por_direccion"]
    return {
        "hipotesis": suite.hypothesis,
        "criterios": criteria,
        "pasa_gate_sin_holdout": all(criteria.values()),
        "holdout": "sellado: el criterio 9 se evalúa una sola vez en el gate con autorización",
        "valores": {
            "operaciones": n,
            "esperanza_r": summary["esperanza_r"],
            "ic90_r": ci,
            "pf": pf,
            "dsr": dsr,
            "pbo": pbo,
            "maxdd_p95_mc": mc_dd,
            "variantes_±20%": {run["variante"]: run["resumen"]["esperanza_r"] for run in robust},
            "costes_x1.5_ic90": stress_ci,
            "regimenes_positivos": positive_regimes,
            "max_peso_mes": share,
            "por_direccion": sides,
            "c16_cortos": (
                "habilitables solo si el gate pasa y cada dirección tiene esperanza > 0: "
                + (
                    "sí"
                    if all(criteria.values()) and all(v["esperanza_r"] > 0 for v in sides.values())
                    else "no"
                )
            ),
        },
    }


# --- preparación de datos -------------------------------------------------------------------


def daily_frames(store: Store, start: datetime, end: datetime) -> dict[str, pl.DataFrame]:
    return {
        symbol: store.read_klines("futures_um", "1d", symbol, start, end)
        for symbol in store.symbols("futures_um", "1d")
    }


def regimes_from_spot(store: Store, end: datetime = END) -> dict[datetime, Regime | None]:
    spot = store.read_klines("spot", "1d", "BTCUSDT", datetime(2019, 1, 1, tzinfo=UTC), end)
    return regime_labels(spot.get_column("open_time").to_list(), spot.get_column("close").to_list())


def betas_by_month(
    daily: Mapping[str, pl.DataFrame], dates: Sequence[datetime]
) -> dict[datetime, dict[str, Decimal]]:
    """Beta MCO de 90 días frente a BTC antes de cada reconstitución (ACLARACIONES §7.15)."""
    btc = daily["BTCUSDT"].select("open_time", pl.col("close").log().diff().alias("btc"))
    out: dict[datetime, dict[str, Decimal]] = {}
    for date in dates:
        window_start = date - timedelta(days=90)
        betas = {"BTC": Decimal(1)}
        btc_window = btc.filter(
            (pl.col("open_time") >= window_start) & (pl.col("open_time") < date)
        )
        for symbol, frame in daily.items():
            if symbol == "BTCUSDT":
                continue
            asset = frame.select("open_time", pl.col("close").log().diff().alias("x")).filter(
                (pl.col("open_time") >= window_start) & (pl.col("open_time") < date)
            )
            joined = asset.join(btc_window, on="open_time").drop_nulls()
            if joined.height < 30:
                continue
            x, y = joined.get_column("btc").to_list(), joined.get_column("x").to_list()
            variance = statistics.pvariance(x)
            if variance > 0:
                mean_x, mean_y = statistics.fmean(x), statistics.fmean(y)
                cov = statistics.fmean(
                    (a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True)
                )
                betas[base_asset(symbol)] = Decimal(repr(cov / variance))
        out[date] = betas
    return out


# --- principal ------------------------------------------------------------------------------


def run_f4(ctx: Context) -> dict[str, Any]:
    store = ctx.store
    start, end = ctx.start, ctx.end
    daily = daily_frames(store, start, end)
    dates = reconstitution_dates(start, end)
    universe: list[UniverseSnapshot] = [universe_at(d, daily) for d in dates]
    union = sorted({s for u in universe for s in u.members})

    # --- H1 ---
    h1_data = load_market(store, "1d", ["BTCUSDT"], start, end)
    h1_base = asdict(H1Params())
    h1_make = lambda p: H1Strategy(h1_data.series["BTCUSDT"], H1Params(**p), "H1")  # noqa: E731
    h1 = run_suite(
        ctx,
        "H1-v1",
        "H1",
        h1_data,
        h1_make,
        h1_base,
        ctx.grids["H1"],
        sensitivities=[("+1 vela", {"delay_bars": 1}, "prueba anti look-ahead (§7.8)")],
    )

    # --- H2 ---
    h2_data = load_market(store, "4h", union, start, end)
    cache = IndicatorCache()
    h2_base = asdict(H2Params())
    h2_make = lambda p: H2Strategy(h2_data.series, universe, H2Params(**p), cache, "H2")  # noqa: E731
    betas = betas_by_month(daily, dates)

    def betas_at(moment: datetime) -> Mapping[str, Decimal]:
        eligible = [d for d in dates if d <= moment]
        return betas[eligible[-1]] if eligible else {"BTC": Decimal(1)}

    h2 = run_suite(
        ctx,
        "H2-v1",
        "H2",
        h2_data,
        h2_make,
        h2_base,
        ctx.grids["H2"],
        sensitivities=[
            ("C-18 entrada 16:00", {"deferred_entry_hours": {8: 16, 12: 16}}, "C-18"),
            (
                "ADR-013 v1",
                {"extended": load_extended_limits_v1_propuesto(), "betas_at": betas_at},
                "reglas propuestas de exposición y funding (§7.15)",
            ),
            ("+1 vela", {"delay_bars": 1}, "prueba anti look-ahead (§7.8)"),
        ],
    )

    # --- H4 ---
    h4_suites = []
    for label, base_suite, data, make, strategy_id in (
        ("H4-H1-v1", h1, h1_data, h1_make, "H1"),
        ("H4-H2-v1", h2, h2_data, h2_make, "H2"),
    ):
        base_params = base_suite.base_params

        def make_filtered(p: dict[str, Any], _make=make, _data=data, _bp=base_params) -> Strategy:
            base = _make(dict(_bp))
            return FundingFilter(base, _data.funding, H4Params(**p), strategy_id=base.strategy_id)

        h4_base = asdict(H4Params())

        def k_blocked(
            result: BacktestResult, strategy: Strategy, _base=base_suite, _data=data
        ) -> dict[str, Any]:
            filtered = strategy.filtered if isinstance(strategy, FundingFilter) else []
            base_trades = _base.principal_result.trades
            k = sum(
                1
                for t in base_trades
                if blocks(
                    t.side,
                    mean_funding_before(_data.funding.get(t.symbol, ()), t.signal_time, 3),
                    H4Params(),
                )
            )
            base_r = r_values(base_trades)
            p90 = m.random_filter_p90(base_r, k) if 0 < k < len(base_r) else None
            return {
                "h4": {
                    "k_bloqueadas_en_base": k,
                    "entradas_filtradas": len(filtered),
                    "esperanza_base": m.expectancy(base_r),
                    "p90_filtros_aleatorios": p90,
                }
            }

        suite = run_suite(
            ctx,
            label,
            strategy_id,
            data,
            make_filtered,
            h4_base,
            ctx.grids["H4"],
            extra_principal=k_blocked,
        )
        h4_suites.append(suite)

    sharpes = list(ctx.principal_sharpes.values())
    gates = [gate(h1, sharpes, ctx.months), gate(h2, sharpes, ctx.months)]
    for suite in h4_suites:
        info: dict[str, Any] = suite.extra["h4"]
        filtered_e = suite.principal["resumen"]["esperanza_r"]
        k = info["k_bloqueadas_en_base"]
        p90 = info["p90_filtros_aleatorios"]
        gates.append(
            gate(
                suite,
                sharpes,
                ctx.months,
                h4={
                    "h4_k_>=20": k >= 20,
                    "h4_mejor_que_base": filtered_e > info["esperanza_base"],
                    "h4_mejor_que_p90_aleatorio": p90 is not None and filtered_e > p90,
                },
            )
        )
    return {"gates": gates, "universo": len(union), "sharpes_principales": ctx.principal_sharpes}


def clean_code_commit() -> str:
    """Commit del código usado; falla si `src/` tiene cambios sin commit (reproducibilidad)."""
    import subprocess  # nosec B404 - solo git local

    status = subprocess.run(  # noqa: S603
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", "src"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip():
        raise RuntimeError("src/ tiene cambios sin commit: el resultado no sería reproducible")
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_summary(outcome: Mapping[str, Any], ctx: Context, path: Path) -> None:
    """Resumen legible del gate (docs/resultados)."""
    lines = [
        "# Resultados de la F4 sobre 2020-2024 (sin holdout)",
        "",
        f"- **Generado:** {datetime.now(UTC):%Y-%m-%d %H:%M} UTC por `trading.backtest.f4`.",
        f"- **Dataset:** `{ctx.dataset_id}`.",
        f"- **Pre-registro:** `{ctx.prereg}`.",
        f"- **Código:** commit `{ctx.code_commit}`.",
        "- **Holdout (2025-01-01 → hoy):** sellado; el criterio 9 del gate no se ha evaluado.",
        "- **Registro:** cada corrida está en `research/trials.csv` y su detalle en",
        "  `research/results/<trial>.json`.",
        "- No es asesoría financiera, legal ni fiscal.",
        "",
    ]
    for item in outcome["gates"]:
        values = item["valores"]
        verdict = "PASA" if item["pasa_gate_sin_holdout"] else "NO PASA"
        lines += [
            f"## {item['hipotesis']}: {verdict} el gate (criterios 1-8)",
            "",
            "| Criterio | Resultado |",
            "|---|---|",
        ]
        lines += [f"| {name} | {'sí' if ok else 'no'} |" for name, ok in item["criterios"].items()]
        lines += [
            "",
            f"- Operaciones: {values['operaciones']}; esperanza {values['esperanza_r']:+.3f} R; "
            f"IC90% [{values['ic90_r'][0]:+.3f}, {values['ic90_r'][1]:+.3f}] R.",
            f"- PF: {values['pf']}; DSR: {values['dsr']:.3f}; PBO: {values['pbo']:.3f}; "
            f"MaxDD p95 (Monte Carlo): {values['maxdd_p95_mc']:.1%}.",
            f"- Costes ×1.5, IC90%: [{values['costes_x1.5_ic90'][0]:+.3f}, "
            f"{values['costes_x1.5_ic90'][1]:+.3f}] R.",
            "- Regímenes positivos (≥20 operaciones): "
            f"{', '.join(values['regimenes_positivos']) or 'ninguno'}.",
            f"- Mayor peso de un mes: {values['max_peso_mes']}.",
            f"- Por dirección: {json.dumps(values['por_direccion'], ensure_ascii=False)}.",
            f"- Cortos (C-16): {values['c16_cortos']}.",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F4: backtests de H1, H2 y H4 en 2020-2024")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    args = parser.parse_args(argv)
    clarifications = verify_frozen_preregistration()
    code_commit = clean_code_commit()
    store = Store()
    dataset_id, _ = store.read_manifest()
    ctx = Context(
        store=store,
        registry=TrialRegistry(),
        dataset_id=dataset_id,
        prereg=f"{PREREG_COMMIT};aclaraciones={clarifications}",
        results_dir=args.results_dir,
        regimes=regimes_from_spot(store),
        code_commit=code_commit,
    )
    with localcontext(RISK_DECIMAL_CONTEXT):
        outcome = run_f4(ctx)
    gate_path = args.results_dir / "gate-f4.json"
    gate_path.write_text(json.dumps(outcome, indent=1, default=str), encoding="utf-8")
    write_summary(outcome, ctx, args.summary)
    print(f"gate en {gate_path}; resumen en {args.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
