"""Explicación de los vetos en español (auditoría A-11)."""

import re
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.risk import (
    AccountState,
    CostModel,
    EntryProposal,
    MarketSnapshot,
    RiskLimits,
    Veto,
    VetoReason,
    evaluate_entry,
    explain,
    explain_decision,
)
from trading.risk.explain import TEMPLATES, Unit, _format

V = VetoReason

# Los códigos son un contrato con la app y la auditoría: cambiar uno debe romper este test.
STABLE_CODES = (
    "TRADING_HALTED",
    "NON_POSITIVE_EQUITY",
    "DRAWDOWN_HALT",
    "DRAWDOWN_HARD_STOP",
    "MARKET_DATA_MISMATCH",
    "FUTURE_TIMESTAMP",
    "STALE_PRICE",
    "STALE_BARS",
    "NON_POSITIVE_QUANTITY",
    "INVALID_STOP",
    "SHORT_ON_SPOT",
    "SHORT_NOT_VALIDATED",
    "CROSS_MARGIN",
    "RISK_PER_TRADE",
    "EFFECTIVE_LEVERAGE",
    "LIQUIDATION_TOO_CLOSE",
    "DAILY_LOSS",
    "WEEKLY_LOSS",
    "CORRELATED_EXPOSURE",
    "BELOW_MIN_NOTIONAL",
    "LIQUIDATION_MODEL_UNAVAILABLE",
    "BETA_EXPOSURE",
    "ALT_NOTIONAL",
    "ALTS_TOTAL_NOTIONAL",
    "MAX_OPEN_POSITIONS",
    "STABLECOIN_DEPEG",
    "MACRO_EVENT_WINDOW",
    "VOLATILITY_CIRCUIT",
    "API_ERROR_CIRCUIT",
    "SPREAD_TOO_WIDE",
    "BOOK_TOO_THIN",
    "ADVERSE_FUNDING",
    "MISSING_CONDITION",
)


def test_codes_are_stable() -> None:
    assert tuple(reason.value for reason in VetoReason) == STABLE_CODES


def test_every_reason_has_a_template() -> None:
    assert set(TEMPLATES) == set(VetoReason)


@pytest.mark.parametrize("reason", list(VetoReason))
def test_every_reason_explains_with_and_without_figures(reason: VetoReason) -> None:
    full = explain(Veto(reason, "detalle", Decimal(2), Decimal(1), subject="BTCUSDT"))
    bare = explain(Veto(reason, "detalle"))
    for explanation in (full, bare):
        assert explanation.code == reason.value
        assert explanation.title
        assert explanation.message.endswith(".")
        assert "{" not in explanation.message
        assert "}" not in explanation.message
    template = TEMPLATES[reason]
    has_placeholders = "{" in template.message
    assert bare.message == (template.fallback if has_placeholders else template.message)


def test_example_from_the_owner() -> None:
    veto = Veto(V.RISK_PER_TRADE, "riesgo", Decimal("9.10125"), Decimal("7.500"))
    assert explain(veto).message == (
        "Esta operación arriesgaría USD 9.11 y tu límite por operación es USD 7.50."
    )
    veto = Veto(V.RISK_PER_TRADE, "riesgo", Decimal("9.10"), Decimal("7.50"))
    assert explain(veto).message == (
        "Esta operación arriesgaría USD 9.10 y tu límite por operación es USD 7.50."
    )


def test_rounding_never_shows_equal_figures_for_a_breach() -> None:
    veto = Veto(V.RISK_PER_TRADE, "riesgo", Decimal("7.5000006"), Decimal("7.50"))
    assert "USD 7.51 y tu límite por operación es USD 7.50" in explain(veto).message
    below = Veto(V.BELOW_MIN_NOTIONAL, "x", Decimal("99.999"), Decimal(100), subject="ETHUSDT")
    assert "USD 99.99 y el mínimo del contrato es USD 100.00" in explain(below).message


def test_units() -> None:
    drawdown = Veto(V.DRAWDOWN_HALT, "x", Decimal("0.153"), Decimal("0.15"))
    assert "15.30% por debajo" in explain(drawdown).message
    assert "salta en 15.00%" in explain(drawdown).message
    leverage = Veto(V.EFFECTIVE_LEVERAGE, "x", Decimal("2.345"), Decimal(2))
    assert "sería 2.35x y el máximo es 2.00x" in explain(leverage).message
    stale = Veto(V.STALE_BARS, "x", Decimal(14701), Decimal(14700))
    assert "hace 4 h 5 min 1 s y lo máximo esperado es 4 h 5 min" in explain(stale).message
    macro = Veto(V.MACRO_EVENT_WINDOW, "x", Decimal(2700), Decimal(7200), subject="CPI")
    assert "(CPI) a 45 min de ahora" in explain(macro).message
    assert "desde 2 h antes hasta 2 h después" in explain(macro).message
    spread = Veto(V.SPREAD_TOO_WIDE, "x", Decimal("7.25"), Decimal(5), subject="BTCUSDT")
    assert "es 7.3 pb y el máximo es 5.0 pb" in explain(spread).message
    positions = Veto(V.MAX_OPEN_POSITIONS, "x", Decimal(5), Decimal(4))
    assert explain(positions).message == ("Habría 5 posiciones abiertas a la vez y el máximo es 4.")
    big = Veto(V.BETA_EXPOSURE, "x", Decimal("1620.5"), Decimal(1500))
    assert "USD 1,620.50 y el máximo es USD 1,500.00" in explain(big).message


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(0, "0 s"), (59, "59 s"), (60, "1 min"), (3600, "1 h"), (3661, "1 h 1 min 1 s"), (-5, "-5 s")],
)
def test_duration_format(seconds: int, text: str) -> None:
    assert _format(Decimal(seconds), Unit.DURATION, "ROUND_FLOOR") == text


def test_explains_a_real_engine_decision(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    proposal = replace(long_btc, quantity=Decimal("0.008"), min_notional=Decimal(500))
    stale = replace(market, price_time=market.price_time - timedelta(seconds=75))
    decision = evaluate_entry(proposal, account, stale, limits, _zero_costs(), market.price_time)
    messages = {e.code: e.message for e in explain_decision(decision)}
    assert messages == {
        "STALE_PRICE": "El dato de BTCUSDT tiene 1 min 15 s de antigüedad y el máximo es 1 min: "
        "con un precio viejo no se puede medir el riesgo.",
        "BELOW_MIN_NOTIONAL": "La orden de BTCUSDT sería de USD 480.00 y el mínimo del contrato "
        "es USD 500.00; el tamaño nunca se aumenta para llegar al mínimo.",
        "RISK_PER_TRADE": "Esta operación arriesgaría USD 9.60 y tu límite por operación es "
        "USD 7.50.",
        "CORRELATED_EXPOSURE": "El riesgo conjunto de BTC y ETH sería USD 9.60 y el límite es "
        "USD 7.50: se mueven casi juntos y cuentan como una sola apuesta.",
    }


def _zero_costs() -> CostModel:
    return CostModel(fee_rate=Decimal(0), slippage_rate=Decimal(0))


@given(
    observed=st.decimals(min_value=Decimal(0), max_value=Decimal(10**9), places=6),
    limit=st.decimals(min_value=Decimal(0), max_value=Decimal(10**9), places=6),
)
def test_displayed_figures_keep_the_order_the_engine_saw(observed: Decimal, limit: Decimal) -> None:
    high = explain(Veto(V.RISK_PER_TRADE, "x", observed, limit)).message
    shown_obs, shown_lim = _usd_figures(high)
    if observed > limit:
        assert shown_obs > shown_lim
    low = explain(Veto(V.BOOK_TOO_THIN, "x", observed, limit, subject="SOLUSDT")).message
    shown_obs, shown_lim = _usd_figures(low)
    if observed < limit:
        assert shown_obs < shown_lim


def _usd_figures(message: str) -> tuple[Decimal, Decimal]:
    first, second = re.findall(r"USD ([\d,]+\.\d{2})", message)
    return Decimal(first.replace(",", "")), Decimal(second.replace(",", ""))
