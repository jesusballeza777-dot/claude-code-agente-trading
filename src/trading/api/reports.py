"""Reportes descargables del Centro de Mando (prompt v3 §5; ADR-017).

Se generan al vuelo (no hay que guardar nada para descargarlos) y cada generación se anota
en `data/app/reportes.jsonl` para el historial de la página de reportes.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess  # nosec B404 - solo git local
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import polars as pl

from trading.api.copilot import daily_brief
from trading.api.services import PREREG_COMMIT, Services, demo_account, demo_decisions
from trading.audit.log import chain, to_csv, to_json
from trading.reporting import accountant
from trading.reporting.documents import ReportMeta, render_pdf, svg_line, workbook

REPORTS: Final = {
    ("semanal", "pdf"): ("application/pdf", "Reporte semanal"),
    ("mensual", "pdf"): ("application/pdf", "Reporte mensual"),
    ("mensual", "xlsx"): (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Reporte mensual",
    ),
    ("ficha", "pdf"): ("application/pdf", "Ficha de estrategia"),
    ("contador", "xlsx"): (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Reporte para el contador",
    ),
    ("contador", "csv"): ("text/csv", "Reporte para el contador"),
    ("auditoria", "json"): ("application/json", "Auditoría"),
    ("auditoria", "csv"): ("text/csv", "Auditoría"),
    ("datos", "csv"): ("text/csv", "Datos"),
    ("datos", "parquet"): ("application/vnd.apache.parquet", "Datos"),
}


class ReportService:
    def __init__(self, services: Services, state: Path) -> None:
        self.services = services
        self.history_path = state / "reportes.jsonl"

    # --- catálogo e historial ------------------------------------------------------------------

    def catalog(self) -> dict[str, Any]:
        history = []
        if self.history_path.exists():
            history = [
                json.loads(x) for x in self.history_path.read_text("utf-8").splitlines() if x
            ]
        return {
            "origen": "real",
            "reportes": [
                {"tipo": kind, "formato": fmt, "nombre": name, "mime": mime}
                for (kind, fmt), (mime, name) in REPORTS.items()
            ],
            "historial": list(reversed(history))[:50],
        }

    def build(self, kind: str, fmt: str, *, hypothesis: str = "H2-v1") -> tuple[bytes, str, str]:
        mime, _name = REPORTS[(kind, fmt)]
        builder = getattr(self, f"_{kind}")
        content, demo = builder(fmt, hypothesis)
        stamp = datetime.now(UTC)
        suffix = "-DEMO" if demo else ""
        filename = f"{kind}-{stamp:%Y%m%d-%H%M}{suffix}.{fmt}"
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("a", encoding="utf-8") as handle:
            entry = {
                "fecha_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tipo": kind,
                "formato": fmt,
                "archivo": filename,
                "demo": demo,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return content, mime, filename

    # --- procedencia ---------------------------------------------------------------------------

    def meta(self, title: str, *, demo: bool) -> ReportMeta:
        status = self.services.status()
        data = status["datos"]
        origin = (
            f"Archivo público de Binance, dataset {data['dataset_id'][:16]}… (2020-2024)"
            if data.get("disponible")
            else "sin datos de mercado descargados"
        )
        return ReportMeta.create(
            title,
            code_commit=_git_head(self.services.repo),
            preregistration=f"{PREREG_COMMIT[:7]} (congelado) + aclaraciones v1.2",
            limits_version="F7-F8 firmados (ADR-007), "
            + status["motor_de_riesgo"]["version_limites"],
            data_origin=origin,
            demo=demo,
        )

    # --- reportes ------------------------------------------------------------------------------

    def _context_week(self) -> dict[str, Any]:
        status = self.services.status()
        account = demo_account()
        return {
            "parte": daily_brief(status, self.services.lab_overview())["texto"],
            "cuenta": account,
            "curva_svg": svg_line([p["capital"] for p in account["curva"]]),
            "decisiones": demo_decisions()["decisiones"][:10],
            "vetos": self.services.veto_history()["vetos"],
            "incidentes": "Sin incidentes registrados: todavía no hay operación en sombra ni real.",
            "pasos": status["pendientes_propietario"],
        }

    def _semanal(self, fmt: str, hypothesis: str) -> tuple[bytes, bool]:
        meta = self.meta("Reporte semanal", demo=True)
        return render_pdf("semanal.html", meta, self._context_week()), True

    def _monthly_hypotheses(self) -> list[dict[str, Any]]:
        rows = []
        gates = self.services.gates()
        for item in self.services.lab_overview()["hipotesis"]:
            summary = item.get("resumen")
            if not summary:
                continue
            gate = gates.get(item["id"], {})
            rows.append(
                {
                    "id": item["id"],
                    "n": summary["operaciones"],
                    "esperanza": summary["esperanza_r"],
                    "ic": summary["ic90_r"],
                    "pf": "—" if summary["pf"] is None else f"{summary['pf']:.2f}",
                    "pasa": bool(gate.get("pasa_gate_sin_holdout")),
                }
            )
        return rows

    def _mensual(self, fmt: str, hypothesis: str) -> tuple[bytes, bool]:
        meta = self.meta("Reporte mensual", demo=True)
        project = self.services.project()
        hypotheses = self._monthly_hypotheses()
        if fmt == "pdf":
            context = self._context_week() | {
                "hipotesis": hypotheses,
                "costes": project["costes"]["conceptos"],
                "fases": project["fases"],
            }
            return render_pdf("mensual.html", meta, context), True
        sheets: dict[str, tuple[Sequence[str], Sequence[Sequence[Any]]]] = {
            "Hipótesis": (
                (
                    "hipotesis",
                    "operaciones",
                    "esperanza_r",
                    "ic90_bajo",
                    "ic90_alto",
                    "pf",
                    "pasa_gate_1_8",
                ),
                [
                    (h["id"], h["n"], h["esperanza"], h["ic"][0], h["ic"][1], h["pf"], h["pasa"])
                    for h in hypotheses
                ],
            ),
            "Cuenta (demo)": (
                ("fecha", "capital_usd"),
                [(p["t"], p["capital"]) for p in demo_account()["curva"]],
            ),
            "Costes": (
                ("concepto", "usd_mes", "estado"),
                [
                    (c["concepto"], c["usd_mes"], c["estado"])
                    for c in project["costes"]["conceptos"]
                ],
            ),
            "Roadmap": (
                ("fase", "nombre", "estado"),
                [(f["id"], f["nombre"], f["estado"]) for f in project["fases"]],
            ),
        }
        return workbook(meta, sheets), True

    def _ficha(self, fmt: str, hypothesis: str) -> tuple[bytes, bool]:
        detail = self.services.lab_detail(hypothesis)
        if detail is None:
            raise LookupError(f"sin resultados de {hypothesis}")
        meta = self.meta(f"Ficha de estrategia {hypothesis}", demo=False)
        gate = detail.get("gate") or {"criterios": {}, "valores": {}}
        values = gate.get("valores", {})
        summary = detail["resumen"]
        groups = list(summary["por_regimen"].items()) + [
            (f"dirección {k}", v) for k, v in summary["por_direccion"].items()
        ]
        context = {
            "titulo": detail["titulo"],
            "trial_id": detail["trial_id"],
            "parametros": json.dumps(detail["parametros"], ensure_ascii=False),
            "resumen": summary,
            "intentos": self.services.lab_overview()["intentos"]["principales"],
            "curva_svg": svg_line([p["capital"] for p in detail["curva"]]),
            "criterios": list(gate["criterios"].items()),
            "valores": [
                (k, _fmt(v))
                for k, v in values.items()
                if k in {"pf", "dsr", "pbo", "maxdd_p95_mc", "max_peso_mes", "c16_cortos"}
            ],
            "grupos": groups,
            "prereg": PREREG_COMMIT,
        }
        return render_pdf("ficha.html", meta, context), False

    def _accountant_rows(self) -> list[list[str]]:
        trades = []
        for item in self.services.journal()["operaciones"]:
            trades.append(
                accountant.AccountantTrade(
                    trade_id=item["id"],
                    opened_at=datetime.fromisoformat(item["entrada"]),
                    closed_at=datetime.fromisoformat(item["salida"]),
                    symbol=item["simbolo"],
                    instrument="perpetuo",
                    side=item["lado"],
                    quantity=Decimal(item["cantidad"]),
                    entry_price=Decimal(item["precio_entrada"]),
                    exit_price=Decimal(item["precio_salida"]),
                    fees=Decimal(item["comisiones"]),
                    funding=Decimal(item["funding"]),
                    net_pnl=Decimal(item["pnl"]),
                )
            )
        fix: dict[date, Decimal] = {}  # Banxico SF43718: por verificar (sin acceso desde aquí)
        return accountant.rows(trades, fix)

    def _contador(self, fmt: str, hypothesis: str) -> tuple[bytes, bool]:
        # Aún no hay operaciones reales: el reporte usa las del backtest, marcado DEMO, para que
        # el contador valide el formato antes de la F8.
        meta = self.meta("Reporte para el contador", demo=True)
        table = self._accountant_rows()
        if fmt == "csv":
            title = (
                "DATOS DE DEMOSTRACIÓN (operaciones del backtest): validar formato con el contador"
            )
            return accountant.to_csv(table, title=title), True
        totals = accountant.totals(table)
        summary = [
            ("operaciones", totals.trades),
            ("resultado_neto_usd", str(totals.net_usd)),
            ("comisiones_usd", str(totals.fees_usd)),
            ("funding_usd", str(totals.funding_usd)),
            (
                "resultado_neto_mxn",
                str(totals.net_mxn) if totals.net_mxn is not None else accountant.PENDING,
            ),
            ("filas_sin_tipo_de_cambio", totals.pending_fx),
        ]
        sheets: dict[str, tuple[Sequence[str], Sequence[Sequence[Any]]]] = {
            "Operaciones": (accountant.HEADER, table),
            "Totales": (("concepto", "valor"), summary),
        }
        return workbook(meta, sheets), True

    def _auditoria(self, fmt: str, hypothesis: str) -> tuple[bytes, bool]:
        decisions = demo_decisions()["decisiones"]
        entries = chain(
            (
                "decision",
                {k: v for k, v in d.items() if k != "json"} | {"demo": True},
                datetime.fromisoformat(d["t"]),
            )
            for d in decisions
        )
        return (to_json(entries) if fmt == "json" else to_csv(entries)), True

    def _datos(self, fmt: str, hypothesis: str) -> tuple[bytes, bool]:
        trades = self.services.journal()["operaciones"]
        frame = pl.DataFrame(trades) if trades else pl.DataFrame({"id": []})
        if fmt == "parquet":
            buffer = io.BytesIO()
            frame.write_parquet(buffer)
            return buffer.getvalue(), False
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(frame.columns)
        writer.writerows(frame.iter_rows())
        return out.getvalue().encode("utf-8"), False


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _git_head(repo: Path) -> str:
    """Commit del código. En la imagen Docker no hay git: lo fija el build (TRADING_CODE_COMMIT)."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo), "rev-parse", "--short=12", "HEAD"],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return os.environ.get("TRADING_CODE_COMMIT", "").strip()[:12] or "desconocido"
    return result.stdout.strip() or "desconocido"
