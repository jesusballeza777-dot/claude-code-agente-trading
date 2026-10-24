"""Datos del Centro de Mando: todo se calcula aquí con código determinista; la app solo pinta.

Cada respuesta indica su `origen`:
- `real`: datos públicos de la F3 o documentos del repositorio;
- `backtest`: resultados de la F4 sobre 2020-2024 (no son operaciones reales);
- `demo`: datos de demostración, que la app marca siempre con "DATOS DE DEMOSTRACIÓN".
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Final

from trading.api import copilot
from trading.api.markdown import plain, read_tables
from trading.backtest.metrics import max_drawdown
from trading.data.holdout import HOLDOUT_START, research_cutoff
from trading.data.store import INTERVALS, Store
from trading.features.indicators import lag_return, prior_max, prior_min, sma, wilder_atr
from trading.features.regimes import regime_labels
from trading.risk import (
    AccountState,
    CostModel,
    EntryProposal,
    LiquidationModel,
    MarginMode,
    MarketSnapshot,
    MarketType,
    PerpetualTerms,
    Side,
    evaluate_entry,
    explain_decision,
    load_extended_limits_v1_propuesto,
    load_plan_limits_f7_f8,
    size_by_risk,
)
from trading.risk import limits as plan_limits
from trading.risk.explain import TEMPLATES
from trading.risk.models import RISK_DECIMAL_CONTEXT
from trading.settings import LIVE_TRADING

HYPOTHESES: Final = ("H1-v1", "H2-v1", "H4-H1-v1", "H4-H2-v1")
PREREG_COMMIT: Final = "4614d659247e57ef6f01614b4986c125fe5468f9"
MONTHS: Final = tuple(f"{y}-{m:02d}" for y in range(2020, 2025) for m in range(1, 13))
CORE: Final = frozenset({"BTC", "ETH"})
MXN_PER_USD_PLAN: Final = Decimal("18.70")  # plan §6; por verificar con el FIX de Banxico

PHASES: Final = (
    ("F0", "Alcance y gobernanza", "cerrada"),
    ("F1", "Plataforma (verificaciones del propietario)", "pendiente del propietario"),
    ("F2", "Fundaciones: CI, motor de riesgo, auditoría", "en curso"),
    ("F3", "Datos públicos sin claves", "hecha (2020-2024)"),
    ("F4", "Investigación y backtests", "en curso: holdout sellado"),
    ("F5", "Analista Claude", "no empezada"),
    ("F6", "Riesgo y ejecución", "no empezada"),
    ("F7", "Simulación en sombra (≥12 semanas)", "no empezada"),
    ("F8", "Piloto real con USD 1,500", "no empezada"),
    ("F9", "Escala", "no empezada"),
)

OWNER_TODO: Final = (
    (
        "Verificar en Binance que tu cuenta permite futuros USDⓈ-M, comisiones y nocional mínimo",
        "docs/f1-verificacion-plataforma.md",
    ),
    ("Generar tu clave age y compartir solo la pública para SOPS", "ops/secrets.md"),
    (
        "Aprobar o ajustar el ADR-013 (reglas de riesgo más restrictivas)",
        "docs/adr/013-motor-de-riesgo-v1-reglas-ampliadas.md",
    ),
    ("Reclamar los créditos de API de Max 5x en la consola", "docs/presupuesto.md"),
    (
        "Revisar los resultados de la F4 y decidir los siguientes pre-registros",
        "docs/resultados/f4-2020-2024.md",
    ),
    ("Validar el formato del reporte fiscal con tu contador", "docs/app/especificacion.md"),
)


class Services:
    def __init__(self, repo_root: Path, data_root: Path, app_state: Path) -> None:
        self.repo = repo_root
        self.store = Store(data_root)
        self.state = app_state
        self.results = repo_root / "research" / "results"

    # --- utilidades ----------------------------------------------------------------------------

    def _json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def trials(self) -> list[dict[str, str]]:
        path = self.repo / "research" / "trials.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def principal(self, hypothesis: str) -> dict[str, Any] | None:
        rows = [
            r
            for r in self.trials()
            if r["hipotesis_id"] == hypothesis and r["tipo_muestra"] == "principal"
        ]
        return self._json(self.results / f"{rows[-1]['trial_id']}.json") if rows else None

    def gates(self) -> dict[str, dict[str, Any]]:
        payload = self._json(self.results / "gate-f4.json") or {}
        return {g["hipotesis"]: g for g in payload.get("gates", [])}

    def data_available(self) -> bool:
        return self.store.manifest_path.exists()

    # --- estado ------------------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        data: dict[str, Any] = {"disponible": self.data_available()}
        if data["disponible"]:
            dataset_id, files = self.store.read_manifest()
            data |= {"dataset_id": dataset_id, "ficheros": len(files), "ultima_vela": "2024-12-31"}
        quality = self.repo / "docs" / "datos" / "calidad-f3.md"
        if quality.exists():
            match = re.search(
                r"Completitud global de velas \| ([\d.]+)%", quality.read_text("utf-8")
            )
            if match:
                data["completitud"] = float(match.group(1)) / 100
        limits_text = resources.files("trading.risk").joinpath("limits_f7_f8.toml").read_bytes()
        trials = self.trials()
        return {
            "origen": "real",
            "fase_actual": "F4 en curso (investigación con datos públicos); "
            "F1 pendiente del propietario",
            "fases": [{"id": f, "nombre": n, "estado": s} for f, n, s in PHASES],
            "live_trading": LIVE_TRADING,
            "holdout": {
                "desde": HOLDOUT_START.date().isoformat(),
                "sellado": research_cutoff() is not None,
            },
            "datos": data,
            "motor_de_riesgo": {
                "limites": "F7-F8 firmados (ADR-007)",
                "version_limites": hashlib.sha256(limits_text).hexdigest()[:12],
                "reglas_v1": "propuestas (ADR-013), activas en simulación",
                "estado": "operativo",
            },
            "intentos": {
                "principales": sum(1 for r in trials if r["tipo_muestra"] == "principal"),
                "total": len(trials),
            },
            "pendientes_propietario": [{"tarea": t, "documento": d} for t, d in OWNER_TODO],
        }

    def today(self) -> dict[str, Any]:
        status = self.status()
        lab = self.lab_overview()
        demo = demo_account()
        return {
            "estado": status,
            "parte_del_dia": copilot.daily_brief(status, lab),
            "cuenta": demo,
            "posiciones": {
                "origen": "real",
                "items": [],
                "vacio": copilot.EMPTY_STATES["posiciones"],
            },
            "eventos_macro": {
                "origen": "real",
                "items": [],
                "vacio": copilot.EMPTY_STATES["eventos"],
            },
        }

    # --- laboratorio -------------------------------------------------------------------------

    def lab_overview(self) -> dict[str, Any]:
        gates = self.gates()
        trials = self.trials()
        items = []
        for hypothesis in HYPOTHESES:
            principal = self.principal(hypothesis)
            gate = gates.get(hypothesis)
            evaluated = principal is not None
            items.append(
                {
                    "id": hypothesis,
                    "titulo": TITLES[hypothesis],
                    "evaluada": evaluated,
                    "ciclo": lifecycle(evaluated, gate),
                    "resumen": principal["resumen"] if principal else None,
                    "gate": {
                        "pasa_sin_holdout": gate["pasa_gate_sin_holdout"],
                        "criterios": gate["criterios"],
                    }
                    if gate
                    else None,
                    "pista": copilot.gate_hint(principal["resumen"]["operaciones"])
                    if principal
                    else None,
                    "corridas": sum(1 for r in trials if r["hipotesis_id"] == hypothesis),
                }
            )
        items.append(
            {
                "id": "H3",
                "titulo": "Reversión tras liquidaciones (aplazada)",
                "evaluada": False,
                "ciclo": [{"etapa": "pre-registrada", "estado": "aplazada"}],
                "resumen": None,
                "gate": None,
                "pista": "Aplazada en el pre-registro: necesita datos de liquidaciones que el "
                "archivo público no tiene.",
                "corridas": 0,
            }
        )
        return {
            "origen": "backtest",
            "hipotesis": items,
            "intentos": {
                "principales": sum(1 for r in trials if r["tipo_muestra"] == "principal"),
                "total": len(trials),
                "explicacion": "Cada especificación principal probada entra en el N del DSR: "
                "cuantas más pruebas, más exigente es el examen.",
            },
            "prereg_commit": PREREG_COMMIT,
        }

    def lab_detail(self, hypothesis: str) -> dict[str, Any] | None:
        if hypothesis not in HYPOTHESES:
            return None
        principal = self.principal(hypothesis)
        if principal is None:
            return None
        trades = principal.get("operaciones", [])
        r = [t["r"] for t in trades]
        curve = [(t, float(e)) for t, e in principal.get("curva_capital", [])]
        peak = -math.inf
        underwater = []
        for moment, equity in curve:
            peak = max(peak, equity)
            underwater.append({"t": moment[:10], "dd": (equity - peak) / peak if peak > 0 else 0.0})
        robustness = [
            self._json(self.results / f"{row['trial_id']}.json")
            for row in self.trials()
            if row["hipotesis_id"] == hypothesis and row["tipo_muestra"] == "robustez"
        ]
        stress = [
            self._json(self.results / f"{row['trial_id']}.json")
            for row in self.trials()
            if row["hipotesis_id"] == hypothesis
            and row["tipo_muestra"] in {"costes_x1.5", "sensibilidad"}
        ]
        return {
            "origen": "backtest",
            "id": hypothesis,
            "titulo": TITLES[hypothesis],
            "trial_id": principal["trial_id"],
            "parametros": principal["parametros"],
            "codigo_commit": principal.get("codigo_commit", ""),
            "dataset_id": principal["dataset_id"],
            "resumen": principal["resumen"],
            "gate": self.gates().get(hypothesis),
            "curva": [{"t": t[:10], "capital": e} for t, e in curve],
            "underwater": underwater,
            "distribucion_r": histogram(r),
            "mapa_mensual": [
                {"mes": month, "r": value}
                for month, value in zip(MONTHS, principal["r_mensual"], strict=False)
            ],
            "abanico_monte_carlo": monte_carlo_fan(r),
            "sensibilidad": sensitivity(principal["parametros"], robustness),
            "variantes_extra": [
                {"variante": s["variante"], "tipo": s["tipo_muestra"], "resumen": s["resumen"]}
                for s in stress
                if s
            ],
            "h4": principal.get("h4"),
            "vetos": explain_counts(principal["resumen"].get("vetos", {})),
            "operaciones": trades[-300:],
        }

    # --- mercado -----------------------------------------------------------------------------

    def symbols(self) -> dict[str, Any]:
        if not self.data_available():
            return {"origen": "demo", "simbolos": ["BTCUSDT", "ETHUSDT"]}
        four = self.store.symbols("futures_um", "4h")
        core = [s for s in ("BTCUSDT", "ETHUSDT") if s in four]
        return {"origen": "real", "simbolos": core + [s for s in four if s not in core]}

    def candles(self, symbol: str, interval: str, days: int) -> dict[str, Any]:
        if interval not in ("4h", "1d"):
            raise ValueError("intervalo no soportado")
        if not self.data_available():
            return demo_candles(symbol, interval, days)
        end = HOLDOUT_START
        start = end - timedelta(days=days + 450)
        frame = self.store.read_klines("futures_um", interval, symbol, start, end)
        if frame.height == 0:
            raise LookupError(f"sin velas de {symbol} {interval}")
        times = [t.isoformat() for t in frame.get_column("open_time").to_list()]
        o, h, lo, c = (frame.get_column(k).to_list() for k in ("open", "high", "low", "close"))
        indicators: dict[str, list[float | None]] = {"atr14": wilder_atr(h, lo, c, 14)}
        if interval == "4h":
            indicators |= {
                "canal_alto": prior_max(h, 60),
                "canal_bajo": prior_min(lo, 60),
                "salida_alta": prior_max(h, 20),
                "salida_baja": prior_min(lo, 20),
                "atr100": wilder_atr(h, lo, c, 100),
            }
        else:
            returns = lag_return(c, 7)
            indicators |= {
                "senal_h1": [
                    None if x is None else (1.0 if x > 0 else -1.0 if x < 0 else 0.0)
                    for x in returns
                ],
                "sma200": sma(c, 200),
            }
        cutoff = (end - timedelta(days=days)).isoformat()
        keep = [i for i, t in enumerate(times) if t >= cutoff]
        markers = self._markers(symbol, interval, cutoff)
        return {
            "origen": "real",
            "simbolo": symbol,
            "intervalo": interval,
            "velas": [{"t": times[i], "o": o[i], "h": h[i], "l": lo[i], "c": c[i]} for i in keep],
            "indicadores": {k: [v[i] for i in keep] for k, v in indicators.items()},
            "marcadores": markers,
            "funding": self._funding(symbol, cutoff),
        }

    def _markers(self, symbol: str, interval: str, cutoff: str) -> list[dict[str, Any]]:
        hypothesis = "H2-v1" if interval == "4h" else "H1-v1"
        principal = self.principal(hypothesis)
        if principal is None:
            return []
        markers = []
        for trade in principal.get("operaciones", []):
            if trade["simbolo"] != symbol or trade["entrada"] < cutoff:
                continue
            markers.append(
                {"t": trade["entrada"], "tipo": "entrada", "lado": trade["lado"], "r": trade["r"]}
            )
            markers.append(
                {
                    "t": trade["salida"],
                    "tipo": "salida",
                    "motivo": trade["motivo_salida"],
                    "r": trade["r"],
                }
            )
        return markers

    def _funding(self, symbol: str, cutoff: str) -> list[dict[str, Any]]:
        start = datetime.fromisoformat(cutoff)
        frame = self.store.read_funding(symbol, start, HOLDOUT_START)
        return [
            {"t": t.isoformat(), "tasa_8h": rate * 8 / hours}
            for t, hours, rate in frame.select(
                "calc_time", "funding_interval_hours", "funding_rate"
            ).iter_rows()
        ]

    def regimes(self) -> dict[str, Any]:
        if not self.data_available():
            return {"origen": "demo", "tramos": []}
        spot = self.store.read_klines(
            "spot", "1d", "BTCUSDT", datetime(2019, 1, 1, tzinfo=UTC), HOLDOUT_START
        )
        labels = regime_labels(
            spot.get_column("open_time").to_list(), spot.get_column("close").to_list()
        )
        segments: list[dict[str, Any]] = []
        for day, label in labels.items():
            value = label.value if label else "sin etiqueta"
            if segments and segments[-1]["regimen"] == value:
                segments[-1]["hasta"] = day.date().isoformat()
            else:
                segments.append(
                    {
                        "regimen": value,
                        "desde": day.date().isoformat(),
                        "hasta": day.date().isoformat(),
                    }
                )
        return {"origen": "real", "tramos": segments}

    def correlations(self) -> dict[str, Any]:
        if not self.data_available():
            return {"origen": "demo", "simbolos": [], "matriz": []}
        symbols = self._latest_universe() or self.symbols()["simbolos"][:10]
        start = HOLDOUT_START - timedelta(days=91)
        returns: dict[str, dict[datetime, float]] = {}
        for symbol in symbols:
            frame = self.store.read_klines("futures_um", "1d", symbol, start, HOLDOUT_START)
            closes = frame.get_column("close").to_list()
            days = frame.get_column("open_time").to_list()
            returns[symbol] = {
                days[i]: math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
            }
        matrix = [[_correlation(returns[a], returns[b]) for b in symbols] for a in symbols]
        return {
            "origen": "real",
            "ventana": "90 días hasta 2024-12-31",
            "simbolos": symbols,
            "matriz": matrix,
        }

    def _latest_universe(self) -> list[str]:
        """Miembros del último universo de H2 (docs/datos/universo-h2-v1.md), por liquidez."""
        for table in read_tables(self.repo / "docs" / "datos" / "universo-h2-v1.md"):
            rows = [plain(r.get("Miembros (por liquidez)", "")) for r in table]
            if rows and rows[-1] not in ("", "—"):
                return [s.strip() for s in rows[-1].split(",")]
        return []

    # --- riesgo ------------------------------------------------------------------------------

    def limits(self) -> dict[str, Any]:
        limits = load_plan_limits_f7_f8()
        extended = load_extended_limits_v1_propuesto()
        rows = [
            (
                "Riesgo por operación",
                limits.risk_per_trade,
                plan_limits.CEILING_RISK_PER_TRADE,
                "fracción",
            ),
            (
                "Apalancamiento efectivo",
                limits.max_effective_leverage,
                plan_limits.CEILING_EFFECTIVE_LEVERAGE,
                "veces",
            ),
            (
                "Liquidación / distancia al stop (mínimo)",
                limits.min_liquidation_to_stop_ratio,
                plan_limits.FLOOR_LIQUIDATION_TO_STOP_RATIO,
                "veces",
            ),
            ("Pérdida diaria", limits.max_daily_loss, plan_limits.CEILING_DAILY_LOSS, "fracción"),
            (
                "Pérdida semanal",
                limits.max_weekly_loss,
                plan_limits.CEILING_WEEKLY_LOSS,
                "fracción",
            ),
            ("Drawdown: parada", limits.drawdown_halt, plan_limits.CEILING_DRAWDOWN, "fracción"),
            (
                "Drawdown: corte duro",
                limits.drawdown_hard_stop,
                plan_limits.CEILING_DRAWDOWN,
                "fracción",
            ),
        ]
        return {
            "origen": "real",
            "editable": False,
            "aviso": "Los límites no se editan desde la app: solo cambian con un ADR aprobado "
            "por ti.",
            "vigentes": [
                {"nombre": n, "valor": str(v), "techo_plan": str(c), "unidad": u, "adr": "ADR-007"}
                for n, v, c, u in rows
            ],
            "grupos_correlacionados": [sorted(g) for g in limits.correlated_groups],
            "propuestos_adr_013": {
                k: str(v) if isinstance(v, Decimal) else v
                for k, v in _extended_dict(extended).items()
            },
        }

    def calculator(
        self,
        *,
        symbol: str,
        side: str,
        entry: str,
        stop: str,
        exchange_leverage: str,
        capital: str,
        market: str,
    ) -> dict[str, Any]:
        """Calculadora con el motor real: tamaño por riesgo y todos los vetos explicados."""
        try:
            values = {
                k: Decimal(v)
                for k, v in (
                    ("entry", entry),
                    ("stop", stop),
                    ("lev", exchange_leverage),
                    ("cap", capital),
                )
            }
        except InvalidOperation as exc:
            raise ValueError("los importes deben ser números") from exc
        if any(not v.is_finite() or v <= 0 for v in values.values()):
            raise ValueError("los importes deben ser positivos")
        base = symbol.removesuffix("USDT")
        core = base in CORE
        slippage = Decimal("0.0005") if core else Decimal("0.0010")
        costs = CostModel(fee_rate=Decimal("0.0005"), slippage_rate=slippage)
        limits = load_plan_limits_f7_f8()
        is_spot = market == "SPOT"
        trade_side = Side(side)
        now = datetime.now(UTC)
        with_ctx = RISK_DECIMAL_CONTEXT
        equity = values["cap"]
        quantity = Decimal(0)
        if values["entry"] != values["stop"]:
            quantity = size_by_risk(
                equity=equity,
                entry_price=values["entry"],
                stop_price=values["stop"],
                risk_fraction=limits.risk_per_trade,
                costs=costs,
                max_notional=limits.max_effective_leverage * equity,
            )
        proposal = EntryProposal(
            strategy_id="calculadora",
            symbol=symbol,
            base_asset=base,
            market=MarketType.SPOT if is_spot else MarketType.PERPETUAL,
            side=trade_side,
            entry_price=values["entry"],
            stop_price=values["stop"],
            quantity=quantity,
            perpetual=None
            if is_spot
            else PerpetualTerms(
                margin_mode=MarginMode.ISOLATED,
                exchange_leverage=max(values["lev"], Decimal(1)),
                maintenance_margin_rate=Decimal("0.004") if core else Decimal("0.025"),
                maintenance_amount=Decimal(0),
                liquidation_model=LiquidationModel.BINANCE_USDM_ISOLATED,
            ),
            min_notional=Decimal(100) if core else Decimal(20),
        )
        account = AccountState(equity, equity, equity, equity)
        snapshot = MarketSnapshot(symbol, now, now, timedelta(hours=4))
        decision = evaluate_entry(proposal, account, snapshot, limits, costs, now)
        notional = with_ctx.multiply(quantity, values["entry"])
        return {
            "origen": "real",
            "motor": "evaluate_entry con los límites F7-F8 firmados",
            "aprobada": decision.approved,
            "cantidad": str(quantity),
            "nocional": str(notional),
            "riesgo_usd": str(decision.trade_risk) if decision.trade_risk is not None else None,
            "presupuesto_usd": str(with_ctx.multiply(equity, limits.risk_per_trade)),
            "apalancamiento_efectivo": str(decision.effective_leverage_after)
            if decision.effective_leverage_after is not None
            else None,
            "precio_liquidacion": str(decision.liquidation_price)
            if decision.liquidation_price is not None
            else None,
            "costes": {"comision": "0.0005", "slippage": str(slippage)},
            "vetos": [asdict(e) for e in explain_decision(decision)],
        }

    def veto_history(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for hypothesis in HYPOTHESES:
            principal = self.principal(hypothesis)
            for reason, n in (principal or {}).get("resumen", {}).get("vetos", {}).items():
                counts[reason] = counts.get(reason, 0) + n
        return {
            "origen": "backtest",
            "nota": "Vetos de las corridas principales de la F4. El historial con 'qué habría "
            "pasado' llega con la sombra (F7).",
            "vetos": explain_counts(counts),
        }

    # --- proyecto ----------------------------------------------------------------------------

    def project(self) -> dict[str, Any]:
        adrs = []
        for table in read_tables(self.repo / "docs" / "adr" / "README.md"):
            for row in table:
                if (
                    row.get("ADR", "").strip("[]").startswith(("0", "1"))
                    and plain(row.get("ADR", "")) != "000"
                ):
                    adrs.append(
                        {
                            "id": plain(row["ADR"]),
                            "titulo": plain(row.get("Título", "")),
                            "estado": plain(row.get("Estado", "")),
                        }
                    )
        risks = []
        for table in read_tables(self.repo / "docs" / "risk_register.md"):
            for row in table:
                if re.fullmatch(r"R\d+", plain(row.get("ID", ""))):
                    risks.append(
                        {
                            "id": plain(row["ID"]),
                            "riesgo": plain(row.get("Riesgo", "")),
                            "probabilidad": plain(row.get("Prob.", "")),
                            "impacto": plain(row.get("Impacto", "")),
                        }
                    )
        costs = []
        tables = read_tables(self.repo / "docs" / "presupuesto.md")
        for row in tables[0] if tables else []:
            concept = plain(row.get("Concepto", ""))
            costs.append(
                {
                    "concepto": concept,
                    "usd_mes": plain(row.get("USD/mes", "")),
                    "estado": plain(row.get("Estado", "")),
                }
            )
        return {
            "origen": "real",
            "fases": [{"id": f, "nombre": n, "estado": s} for f, n, s in PHASES],
            "adr": adrs,
            "riesgos": risks,
            "pendientes_propietario": [{"tarea": t, "documento": d} for t, d in OWNER_TODO],
            "costes": {
                "conceptos": costs,
                "tipo_de_cambio": {
                    "mxn_por_usd": str(MXN_PER_USD_PLAN),
                    "estado": "por verificar (FIX de Banxico)",
                },
                "uso_api_claude": demo_api_usage(),
            },
        }

    # --- diario ------------------------------------------------------------------------------

    def journal(self) -> dict[str, Any]:
        trades = []
        for hypothesis in ("H1-v1", "H2-v1"):
            principal = self.principal(hypothesis)
            for i, trade in enumerate((principal or {}).get("operaciones", [])):
                trades.append({"id": f"{hypothesis}-{i + 1:04d}", "hipotesis": hypothesis, **trade})
        trades.sort(key=lambda t: t["entrada"], reverse=True)
        return {
            "origen": "backtest",
            "aviso": "Operaciones simuladas del backtest 2020-2024: no son operaciones reales "
            "ni de sombra.",
            "vacio": copilot.EMPTY_STATES["diario"],
            "operaciones": trades[:400],
            "notas": self.notes(),
        }

    def notes(self) -> list[dict[str, Any]]:
        path = self.state / "notas.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]

    def add_note(self, reference: str, text: str) -> dict[str, Any]:
        text, reference = text.strip(), reference.strip()
        if not text or len(text) > 2000 or len(reference) > 80:
            raise ValueError("la nota debe tener entre 1 y 2,000 caracteres")
        note = {
            "id": hashlib.sha256(f"{datetime.now(UTC).isoformat()}{text}".encode()).hexdigest()[
                :12
            ],
            "fecha_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "referencia": reference,
            "texto": text,
        }
        self.state.mkdir(parents=True, exist_ok=True)
        with (self.state / "notas.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(note, ensure_ascii=False) + "\n")
        return note


# --- funciones auxiliares ------------------------------------------------------------------------

TITLES: Final = {
    "H1-v1": "Momentum diario en BTC",
    "H2-v1": "Ruptura de canal de 4h con filtro de volatilidad",
    "H4-H1-v1": "Filtro de funding sobre H1",
    "H4-H2-v1": "Filtro de funding sobre H2",
}


def lifecycle(evaluated: bool, gate: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if gate is None:
        gate_state = "pendiente"
    elif gate["pasa_gate_sin_holdout"]:
        gate_state = "aprobado sin holdout (falta el criterio 9)"
    else:
        gate_state = "rechazado"
    return [
        {"etapa": "pre-registrada", "estado": "hecho"},
        {"etapa": "congelada", "estado": f"hecho ({PREREG_COMMIT[:7]})"},
        {"etapa": "backtest", "estado": "hecho" if evaluated else "pendiente"},
        {"etapa": "gate F4", "estado": gate_state},
        {"etapa": "sombra", "estado": "pendiente"},
        {"etapa": "real", "estado": "pendiente"},
    ]


def histogram(r: Sequence[float], width: float = 0.25) -> list[dict[str, Any]]:
    if not r:
        return []
    low, high = math.floor(min(r) / width) * width, math.ceil(max(r) / width) * width
    bins: list[dict[str, Any]] = []
    edge = low
    while edge < high or not bins:
        count = sum(1 for x in r if edge <= x < edge + width)
        bins.append({"desde": round(edge, 4), "hasta": round(edge + width, 4), "n": count})
        edge += width
    bins[-1]["n"] += sum(1 for x in r if x == high)
    return bins


def monte_carlo_fan(
    r: Sequence[float], paths: int = 400, seed: int = 20261023
) -> list[dict[str, float]]:
    """Abanico p5-p95 del capital (1 = inicial) remuestreando operaciones al 0.5% de riesgo."""
    if not r:
        return []
    rng = random.Random(seed)  # noqa: S311 - remuestreo reproducible
    n = len(r)
    curves = []
    for _ in range(paths):
        equity, curve = 1.0, []
        for value in rng.choices(r, k=n):
            equity *= 1 + 0.005 * value
            curve.append(equity)
        curves.append(curve)
    step = max(1, n // 60)
    fan = []
    for i in range(0, n, step):
        column = sorted(c[i] for c in curves)

        def pick(q: float, column: list[float] = column) -> float:
            return column[min(int(q * (paths - 1)), paths - 1)]

        fan.append(
            {
                "operacion": i + 1,
                "p5": pick(0.05),
                "p25": pick(0.25),
                "p50": pick(0.5),
                "p75": pick(0.75),
                "p95": pick(0.95),
            }
        )
    return fan


def sensitivity(
    base: Mapping[str, Any], runs: Sequence[Mapping[str, Any] | None]
) -> list[dict[str, Any]]:
    """Esperanza al mover cada parámetro ±20% (uno cada vez), para el mapa de calor."""
    out = []
    for key, value in base.items():
        row: dict[str, Any] = {"parametro": key, "base": value, "valores": []}
        for run in runs:
            if not run:
                continue
            params = run["parametros"]
            if all(params[k] == base[k] for k in base if k != key) and params[key] != value:
                row["valores"].append(
                    {
                        "valor": params[key],
                        "esperanza_r": run["resumen"]["esperanza_r"],
                        "operaciones": run["resumen"]["operaciones"],
                    }
                )
        row["valores"].sort(key=lambda v: v["valor"])
        out.append(row)
    return out


def explain_counts(counts: Mapping[str, int]) -> list[dict[str, Any]]:
    from trading.risk import VetoReason

    items = []
    for code, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        try:
            template = TEMPLATES[VetoReason(code)]
        except ValueError:
            continue
        items.append(
            {"codigo": code, "titulo": template.title, "explicacion": template.fallback, "veces": n}
        )
    return items


def _extended_dict(extended: Any) -> dict[str, Any]:
    out = {}
    for name in extended.__dataclass_fields__:
        value = getattr(extended, name)
        if isinstance(value, frozenset):
            value = sorted(value)
        elif isinstance(value, timedelta):
            value = f"{int(value.total_seconds() // 60)} min"
        out[name] = value
    return out


def _correlation(a: Mapping[datetime, float], b: Mapping[datetime, float]) -> float | None:
    days = sorted(set(a) & set(b))
    if len(days) < 20:
        return None
    x, y = [a[d] for d in days], [b[d] for d in days]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    if sx == 0 or sy == 0:
        return None
    return sum((p - mx) * (q - my) for p, q in zip(x, y, strict=True)) / (sx * sy)


# --- demostración --------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def demo_account() -> dict[str, Any]:
    """Cuenta de demostración: no hay sombra ni dinero real hasta la F7."""
    rng = random.Random(7)  # noqa: S311
    equity = 1500.0
    curve: list[dict[str, Any]] = []
    start = datetime(2026, 9, 1, tzinfo=UTC)
    for i in range(53):
        equity *= 1 + rng.gauss(0.0004, 0.004)
        curve.append(
            {"t": (start + timedelta(days=i)).date().isoformat(), "capital": round(equity, 2)}
        )
    peak = max(p["capital"] for p in curve)
    drawdown = max_drawdown([p["capital"] for p in curve])
    daily_used, weekly_used = 0.004, 0.011
    return {
        "origen": "demo",
        "capital": f"{equity:.2f}",
        "maximo": f"{peak:.2f}",
        "drawdown": drawdown,
        "umbrales": {"parada": 0.15, "corte_duro": 0.20},
        "presupuesto": {
            "diario": {
                "usado": daily_used,
                "limite": 0.02,
                "texto": copilot.budget_hint(daily_used, 0.02),
            },
            "semanal": {"usado": weekly_used, "limite": 0.04},
        },
        "curva": curve,
    }


def demo_candles(symbol: str, interval: str, days: int) -> dict[str, Any]:
    rng = random.Random(zlib.crc32(symbol.encode()))  # noqa: S311
    step = INTERVALS[interval]
    count = min(int(timedelta(days=days) / step), 600)
    price, rows = 100.0, []
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(count):
        o = price
        c = max(o * (1 + rng.gauss(0, 0.01)), 1)
        rows.append(
            {
                "t": (start + i * step).isoformat(),
                "o": o,
                "h": max(o, c) * 1.004,
                "l": min(o, c) * 0.996,
                "c": c,
            }
        )
        price = c
    return {
        "origen": "demo",
        "simbolo": symbol,
        "intervalo": interval,
        "velas": rows,
        "indicadores": {},
        "marcadores": [],
        "funding": [],
    }


@lru_cache(maxsize=1)
def demo_api_usage() -> dict[str, Any]:
    return {
        "origen": "demo",
        "nota": "El analista Claude empieza en la F5; el uso real de la API se mostrará aquí.",
        "meses": [{"mes": "2026-10", "tokens": 0, "usd": "0.00"}],
    }


@lru_cache(maxsize=1)
def demo_decisions() -> dict[str, Any]:
    rng = random.Random(11)  # noqa: S311
    actions = ["ABSTAIN", "HOLD", "ENTER_LONG", "EXIT", "ABSTAIN", "ENTER_SHORT", "HOLD"]
    start = datetime(2026, 10, 1, 4, tzinfo=UTC)
    items = []
    for i in range(18):
        action = actions[i % len(actions)]
        vetoed = action.startswith("ENTER") and rng.random() < 0.3
        items.append(
            {
                "t": (start + timedelta(hours=8 * i)).isoformat(),
                "accion": action,
                "nivel": "B" if action.startswith("ENTER") else "A",
                "motivo": "Ejemplo: ruptura del canal con volatilidad creciente"
                if action.startswith("ENTER")
                else "Ejemplo: sin señal válida",
                "evidencia": ["H2-v1 §4", "motor de riesgo"] if action.startswith("ENTER") else [],
                "veto": "RISK_PER_TRADE" if vetoed else None,
                "json": {
                    "action": action,
                    "hypothesis": "H2-v1",
                    "symbol": "BTCUSDT",
                    "demo": True,
                },
            }
        )
    return {
        "origen": "demo",
        "vacio": copilot.EMPTY_STATES["decisiones"],
        "decisiones": items,
        "libros": [
            {"libro": "A: regla pura", "operaciones": 0, "esperanza_r": None},
            {"libro": "B: regla + veto de Claude", "operaciones": 0, "esperanza_r": None},
            {"libro": "C: placebo de vetos aleatorios", "operaciones": 0, "esperanza_r": None},
        ],
    }
