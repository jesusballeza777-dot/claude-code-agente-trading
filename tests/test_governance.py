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
