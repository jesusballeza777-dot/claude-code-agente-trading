"""Copiloto, tablas Markdown, cadena de auditoría y reporte del contador."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading.api import copilot
from trading.api.markdown import plain, tables
from trading.audit.log import AuditLog, chain, to_csv, to_json, verify_chain
from trading.reporting import accountant
from trading.reporting.documents import ReportMeta, render_html, svg_line


def test_copilot_validator_and_hints() -> None:
    assert copilot.validate("Vas usando 0.8% de tu 2% de pérdida diaria.", ["0.8", "2"])
    assert not copilot.validate("Tienes 73% de probabilidad de ganar.", ["2"])
    assert copilot.numbers_in("2020-2024 y 1,500.25") == {"2020", "2024", "1500.25"}
    assert (
        copilot.budget_hint(0.008, 0.02)
        == "Vas usando 0.8% de tu 2% de pérdida diaria. Margen de sobra."
    )
    assert copilot.budget_hint(0.015, 0.02).endswith("Ve con calma.")
    assert copilot.budget_hint(0.019, 0.02).endswith("Casi al límite.")
    assert copilot.gate_hint(250) == "Tiene 250 operaciones: la muestra alcanza el mínimo de 200."
    brief = copilot.daily_brief({"datos": {}}, {"hipotesis": []})
    assert "Todavía no hay backtests" in brief["texto"]
    assert brief["validado"]


def test_markdown_tables() -> None:
    text = "# T\n\n| A | B |\n|---|:-:|\n| **x** | [enlace](u) |\n| `y` | a \\| b |\n\nfin\n"
    (table,) = tables(text)
    assert table == [{"A": "**x**", "B": "[enlace](u)"}, {"A": "`y`", "B": "a | b"}]
    assert [plain(r["A"]) for r in table] == ["x", "y"]
    assert plain("[enlace](u)") == "enlace"


def test_audit_chain_detects_tampering(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    assert log.entries() == []
    moment = datetime(2026, 10, 23, tzinfo=UTC)
    for i in range(3):
        log.append("decision", {"n": i, "monto": Decimal("1.5")}, moment)
    entries = log.entries()
    assert verify_chain(entries).valid
    assert entries[1]["hash_anterior"] == entries[0]["hash"]
    tampered = [dict(e) for e in entries]
    tampered[1]["datos"] = {"n": 99, "monto": "1.5"}
    check = verify_chain(tampered)
    assert (check.valid, check.first_broken) == (False, 1)
    assert verify_chain([entries[0], entries[2]]).reason == "índice fuera de secuencia"
    swapped = [dict(entries[0]), dict(entries[1])]
    swapped[1]["hash_anterior"] = "f" * 64
    assert verify_chain(swapped).reason == "hash_anterior no coincide"
    lines = (tmp_path / "audit.jsonl").read_text("utf-8").splitlines()
    (tmp_path / "audit.jsonl").write_text(
        "\n".join([*lines[:1], lines[2]]) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="cadena rota"):
        log.append("decision", {"n": 3})
    built = chain([("x", {"a": 1}, moment), ("y", {"b": 2}, moment)])
    assert json.loads(to_json(built))["verificacion"]["valida"]
    assert to_csv(built).decode().count("\n") == 3


def _trade(day: int, pnl: str) -> accountant.AccountantTrade:
    closed = datetime(2026, 3, day, 23, 30, tzinfo=UTC)  # 17:30 en CDMX
    return accountant.AccountantTrade(
        trade_id=f"t{day}",
        opened_at=closed,
        closed_at=closed,
        symbol="BTCUSDT",
        instrument="perpetuo",
        side="LONG",
        quantity=Decimal("0.01"),
        entry_price=Decimal(60000),
        exit_price=Decimal(61000),
        fees=Decimal("0.6049"),
        funding=Decimal("-0.012"),
        net_pnl=Decimal(pnl),
    )


def test_accountant_rows_use_fix_or_mark_pending() -> None:
    fix = {date(2026, 3, 2): Decimal("17.2000")}
    table = accountant.rows([_trade(3, "9.40"), _trade(2, "-1.235")], fix)
    first, second = table
    assert first[0] == "t2"
    assert first[13:] == ["2026-03-02", "17.2000", "-21.33"]
    assert second[13:] == ["2026-03-02", "17.2000", "161.68"]  # usa el FIX publicado antes
    totals = accountant.totals(table)
    assert (totals.net_usd, totals.net_mxn, totals.pending_fx) == (
        Decimal("8.16"),
        Decimal("140.35"),
        0,
    )
    pending = accountant.rows([_trade(20, "1")], fix)
    assert pending[0][-1] == accountant.PENDING
    assert accountant.totals(pending).net_mxn is None
    assert accountant.to_csv(pending, title="DEMO").decode().splitlines()[0] == "DEMO"


def test_documents_render_provenance() -> None:
    meta = ReportMeta.create(
        "Prueba",
        code_commit="abc",
        preregistration="4614d65",
        limits_version="v",
        data_origin="sintético",
        demo=True,
        now=datetime(2026, 10, 23, 12, tzinfo=UTC),
    )
    html = render_html(
        "ficha.html",
        meta,
        {
            "titulo": "T",
            "trial_id": "T1",
            "parametros": "{}",
            "intentos": 4,
            "resumen": {"operaciones": 1, "esperanza_r": 0.1, "ic90_r": [-0.1, 0.3]},
            "curva_svg": svg_line([1.0, 2.0, 1.5]),
            "criterios": [("a", True)],
            "valores": [("pf", "1.2")],
            "grupos": [("alcista", {"n": 1, "esperanza_r": 0.1})],
            "prereg": "4614d65",
        },
    )
    assert "DATOS DE DEMOSTRACIÓN" in html
    assert "No es asesoría financiera, legal ni fiscal." in html
    assert "2026-10-23 12:00 UTC" in html
    assert "<polyline" in html
    assert svg_line([1.0]) == ""


def test_code_commit_without_git_comes_from_the_image(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trading.api import reports

    def no_git(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(reports.subprocess, "run", no_git)
    monkeypatch.setenv("TRADING_CODE_COMMIT", "0123456789abcdef")
    assert reports._git_head(tmp_path) == "0123456789ab"
    monkeypatch.delenv("TRADING_CODE_COMMIT")
    assert reports._git_head(tmp_path) == "desconocido"


def test_owner_todo_is_empty_without_the_status_document(tmp_path: Path) -> None:
    from trading.api.services import Services

    assert Services(tmp_path, tmp_path / "data", tmp_path / "estado").owner_todo() == []
