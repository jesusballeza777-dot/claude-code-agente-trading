"""Salvaguardas de gobernanza (CLAUDE.md, reglas 2 y 8)."""

import importlib
import re
from pathlib import Path

import pytest

import trading.settings

SRC = Path(__file__).resolve().parents[1] / "src" / "trading"


def _source_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_live_trading_is_disabled() -> None:
    assert trading.settings.LIVE_TRADING is False


def test_live_trading_ignores_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVE_TRADING", "true")
    reloaded = importlib.reload(trading.settings)
    assert reloaded.LIVE_TRADING is False


def test_no_source_file_enables_live_trading() -> None:
    pattern = re.compile(r"LIVE_TRADING\b[^=\n]*=\s*(True|1|['\"]true['\"])", re.IGNORECASE)
    offenders = [p for p in _source_files() if pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_no_withdrawal_or_transfer_endpoints() -> None:
    pattern = re.compile(r"withdraw|/capital/|/asset/transfer|/futures/transfer", re.IGNORECASE)
    offenders = [p for p in _source_files() if pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


# --- F3: solo datos públicos (prompt v3, Ola 5; ADR-016) -------------------------------------

FORBIDDEN_EXCHANGE_PATTERNS = re.compile(
    r"/api/v3/(order|account|myTrades|openOrders)"
    r"|/fapi/v\d/(order|account|positionRisk|leverage|marginType|listenKey|userTrades)"
    r"|/sapi/|listenKey|X-MBX-APIKEY|signature="
    r"|/exchange\b.*\"type\"\s*:\s*\"(order|withdraw|usdSend|spotSend|vaultTransfer)",
    re.IGNORECASE,
)


def test_no_account_or_order_endpoints() -> None:
    offenders = [
        p for p in _source_files() if FORBIDDEN_EXCHANGE_PATTERNS.search(p.read_text("utf-8"))
    ]
    assert offenders == []


def test_data_layer_only_reaches_the_public_archive() -> None:
    url = re.compile(r"https?://[^\s\"'`)]+")
    allowed = (
        "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision",
        "http://s3.amazonaws.com/doc/2006-03-01/",  # espacio de nombres del XML de S3, sin red
    )
    found = {
        match
        for path in (SRC / "data").rglob("*.py")
        for match in url.findall(path.read_text("utf-8"))
    }
    assert found
    assert all(u.startswith(allowed) for u in found), found


def test_research_code_reads_data_through_the_holdout_guard() -> None:
    store = (SRC / "data" / "store.py").read_text("utf-8")
    assert store.count("ensure_research_window(") >= 2
