"""Reglas ampliadas del motor de riesgo (ADR-013, Propuesto): normales, límites exactos y vetos."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.risk import (
    AccountState,
    CostModel,
    EntryProposal,
    InvalidRiskLimitsError,
    LiquidationModel,
    MacroEvent,
    MacroEventKind,
    MarginMode,
    MarketConditions,
    MarketSnapshot,
    MarketType,
    OpenPosition,
    PerpetualTerms,
    RiskLimits,
    Side,
    SymbolConditions,
    VetoReason,
    assess_conditions,
    evaluate_entry,
    evaluate_entry_v1,
    exposure_vetoes,
    extended_limits_from_toml,
    funding_vetoes,
    load_extended_limits,
    load_extended_limits_v1_propuesto,
    load_plan_limits_f7_f8,
    symbol_vetoes,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
CAPITAL = Decimal(1500)
ZERO_COSTS = CostModel(fee_rate=Decimal(0), slippage_rate=Decimal(0))
V = VetoReason
EXT = load_extended_limits_v1_propuesto()
LIMITS = load_plan_limits_f7_f8()
BETAS = {"BTC": Decimal(1), "ETH": Decimal("1.1"), "SOL": Decimal("1.3"), "XRP": Decimal("1.2")}


def _conditions(**changes: Any) -> MarketConditions:
    base = MarketConditions(
        stablecoin_prices={"USDT": Decimal("1.0002"), "USDC": Decimal("0.9999")},
        macro_events=(),
        macro_calendar_through=NOW + timedelta(days=30),
        api_error_times=(),
        betas=BETAS,
    )
    return replace(base, **changes)


def _symbol(symbol: str = "BTCUSDT", **changes: Any) -> SymbolConditions:
    base = SymbolConditions(
        symbol=symbol,
        realized_vol_1h=Decimal("0.004"),
        vol_1h_p99=Decimal("0.02"),
        best_bid=Decimal("59999.9"),
        best_ask=Decimal("60000.1"),
        depth_notional=Decimal(1_000_000),
        quote_time=NOW,
        funding_rate_8h=Decimal("0.0001"),
    )
    return replace(base, **changes)


def _account(*positions: OpenPosition, equity: Decimal = CAPITAL) -> AccountState:
    return AccountState(equity, CAPITAL, CAPITAL, CAPITAL, open_positions=positions)


def _position(asset: str, notional: str, risk: str = "0") -> OpenPosition:
    return OpenPosition(f"{asset}USDT", asset, Side.LONG, Decimal(notional), Decimal(risk))


def _alt(base: EntryProposal, asset: str, notional: str) -> EntryProposal:
    """Largo en una alt con precio 10 y stop 9.5 (5%): la cantidad fija el nocional."""
    return replace(
        base,
        symbol=f"{asset}USDT",
        base_asset=asset,
        entry_price=Decimal(10),
        stop_price=Decimal("9.5"),
        quantity=Decimal(notional) / 10,
    )


# --- carga y validación de los límites -------------------------------------------------------


def test_proposed_values_match_adr_013() -> None:
    assert EXT.max_beta_adjusted_exposure == Decimal("1.00")
    assert (EXT.max_notional_per_alt, EXT.max_notional_all_alts) == (
        Decimal("0.10"),
        Decimal("0.25"),
    )
    assert EXT.max_open_positions == 4
    assert EXT.core_assets == {"BTC", "ETH"}
    assert EXT.monitored_stablecoins == {"USDT", "USDC"}
    assert EXT.max_stablecoin_deviation == Decimal("0.005")
    assert EXT.macro_blackout == timedelta(hours=2)
    assert (EXT.max_api_errors, EXT.api_error_window) == (3, timedelta(minutes=10))
    assert (EXT.max_spread_bps("BTC"), EXT.max_spread_bps("SOL")) == (Decimal(5), Decimal(10))
    assert (EXT.depth_band_bps("ETH"), EXT.depth_band_bps("XRP")) == (Decimal(5), Decimal(10))
    assert EXT.min_depth_multiple == 10
    assert EXT.max_adverse_funding_8h == Decimal("0.0010")


def test_load_from_path(tmp_path: Any) -> None:
    from importlib import resources

    text = resources.files("trading.risk").joinpath("limits_v1_propuesto.toml").read_text("utf-8")
    path = tmp_path / "v1.toml"
    path.write_text(text, encoding="utf-8")
    assert load_extended_limits(path) == EXT


@pytest.mark.parametrize(
    "changes",
    [
        {"max_beta_adjusted_exposure": Decimal(0)},
        {"max_beta_adjusted_exposure": Decimal("3.01")},
        {"max_notional_per_alt": Decimal("0.3")},
        {"max_notional_all_alts": Decimal("1.5")},
        {"max_stablecoin_deviation": Decimal(-1)},
        {"max_adverse_funding_8h": Decimal("NaN")},
        {"max_spread_bps_core": Decimal(0)},
        {"max_spread_bps_alt": 5},
        {"min_depth_multiple": Decimal("0.5")},
        {"max_open_positions": 0},
        {"max_api_errors": True},
        {"macro_blackout": timedelta(0)},
        {"api_error_window": timedelta(minutes=-1)},
        {"core_assets": frozenset()},
        {"monitored_stablecoins": frozenset({" USDT"})},
    ],
)
def test_invalid_extended_limits_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidRiskLimitsError):
        replace(EXT, **changes)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("max_open_positions = 4", "max_open_positions = 4\nextra = 1"),
        ("[funding]\nmax_adverse_funding_8h = 0.0010", ""),
        ("blackout_minutes = 120", "blackout_minutes = 120.5"),
        ("max_notional_per_alt = 0.10", 'max_notional_per_alt = "0.10"'),
        ("[macro]\nblackout_minutes = 120", "[macro.x]\nblackout_minutes = 120"),
        ("max_open_positions = 4", "max_open_positions = 4 4"),
    ],
)
def test_malformed_toml_is_rejected(old: str, new: str) -> None:
    from importlib import resources

    text = resources.files("trading.risk").joinpath("limits_v1_propuesto.toml").read_text("utf-8")
    text = "\n".join(line.split("#")[0].rstrip() for line in text.splitlines())
    assert old in text
    with pytest.raises(InvalidRiskLimitsError):
        extended_limits_from_toml(text.replace(old, new))


# --- exposición ------------------------------------------------------------------------------


def test_normal_entry_passes_extended_rules(long_btc: EntryProposal) -> None:
    assert exposure_vetoes(long_btc, _account(), BETAS, EXT) == []


@pytest.mark.parametrize(("eth_notional", "vetoed"), [("900", False), ("900.01", True)])
def test_beta_exposure_exact_limit(
    long_btc: EntryProposal, eth_notional: str, vetoed: bool
) -> None:
    # Propuesta: USD 375 de BTC (beta 1). Abierta: ETH con beta 1.25: 375 + 900 x 1.25 = 1,500.
    betas = BETAS | {"ETH": Decimal("1.25")}
    eth = _position("ETH", eth_notional)
    reasons = {v.reason for v in exposure_vetoes(long_btc, _account(eth), betas, EXT)}
    assert (V.BETA_EXPOSURE in reasons) is vetoed


def test_beta_uses_absolute_value(long_btc: EntryProposal) -> None:
    betas = {**BETAS, "BTC": Decimal(-5)}
    (veto,) = exposure_vetoes(long_btc, _account(), betas, EXT)
    assert (veto.reason, veto.observed, veto.limit) == (
        V.BETA_EXPOSURE,
        Decimal(1875),
        Decimal(1500),
    )


def test_missing_beta_is_vetoed(long_btc: EntryProposal) -> None:
    (veto,) = exposure_vetoes(long_btc, _account(_position("DOGE", "10")), BETAS, EXT)
    assert veto.reason is V.MISSING_CONDITION
    assert "DOGE" in veto.subject


@pytest.mark.parametrize(("notional", "vetoed"), [("150", False), ("150.01", True)])
def test_notional_per_alt_exact_limit(long_btc: EntryProposal, notional: str, vetoed: bool) -> None:
    vetoes = exposure_vetoes(_alt(long_btc, "SOL", notional), _account(), BETAS, EXT)
    assert (V.ALT_NOTIONAL in {v.reason for v in vetoes}) is vetoed


def test_notional_per_alt_adds_open_positions_in_the_same_alt(long_btc: EntryProposal) -> None:
    account = _account(_position("SOL", "100"))
    (veto,) = exposure_vetoes(_alt(long_btc, "SOL", "60"), account, BETAS, EXT)
    assert (veto.reason, veto.observed, veto.limit, veto.subject) == (
        V.ALT_NOTIONAL,
        Decimal(160),
        Decimal(150),
        "SOL",
    )


@pytest.mark.parametrize(("notional", "vetoed"), [("75", False), ("75.01", True)])
def test_total_alts_exact_limit(long_btc: EntryProposal, notional: str, vetoed: bool) -> None:
    # Ya hay USD 300 en alts; el máximo conjunto es 25% de 1,500 = USD 375.
    account = _account(_position("SOL", "150"), _position("XRP", "150"))
    betas = BETAS | {"ETHFI": Decimal(1)}
    vetoes = exposure_vetoes(_alt(long_btc, "ETHFI", notional), account, betas, EXT)
    assert (V.ALTS_TOTAL_NOTIONAL in {v.reason for v in vetoes}) is vetoed


def test_core_assets_are_not_alts(long_btc: EntryProposal) -> None:
    account = _account(_position("SOL", "150"), _position("XRP", "150"), _position("BTC", "100"))
    assert exposure_vetoes(long_btc, account, BETAS, EXT) == []


@pytest.mark.parametrize(("open_positions", "vetoed"), [(3, False), (4, True)])
def test_max_open_positions_exact_limit(
    long_btc: EntryProposal, open_positions: int, vetoed: bool
) -> None:
    account = _account(*(_position("BTC", "1") for _ in range(open_positions)))
    vetoes = exposure_vetoes(long_btc, account, BETAS, EXT)
    assert (V.MAX_OPEN_POSITIONS in {v.reason for v in vetoes}) is vetoed


def test_exposure_rules_defer_to_v0_when_equity_is_not_positive(long_btc: EntryProposal) -> None:
    assert exposure_vetoes(long_btc, _account(equity=Decimal(0)), {}, EXT) == []


# --- funding ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("side", "rate", "vetoed"),
    [
        (Side.LONG, "0.0010", False),
        (Side.LONG, "0.00100001", True),
        (Side.LONG, "-0.05", False),
        (Side.SHORT, "-0.0010", False),
        (Side.SHORT, "-0.00100001", True),
        (Side.SHORT, "0.05", False),
    ],
)
def test_adverse_funding_exact_limit(
    long_btc: EntryProposal, side: Side, rate: str, vetoed: bool
) -> None:
    proposal = replace(long_btc, side=side)
    vetoes = funding_vetoes(proposal, Decimal(rate), EXT)
    assert bool(vetoes) is vetoed
    if vetoed:
        assert vetoes[0].reason is V.ADVERSE_FUNDING
        assert vetoes[0].observed == abs(Decimal(rate))


def test_funding_is_required_on_perpetuals_and_ignored_on_spot(long_btc: EntryProposal) -> None:
    (veto,) = funding_vetoes(long_btc, None, EXT)
    assert veto.reason is V.MISSING_CONDITION
    spot = replace(long_btc, market=MarketType.SPOT, perpetual=None)
    assert funding_vetoes(spot, None, EXT) == []
    assert funding_vetoes(spot, Decimal("0.5"), EXT) == []


# --- condiciones de la cuenta ----------------------------------------------------------------


def test_normal_conditions_pass() -> None:
    status = assess_conditions(_conditions(), EXT, NOW)
    assert status.vetoes == ()
    assert not status.close_orderly


@pytest.mark.parametrize(
    ("price", "vetoed"),
    [("1.005", False), ("0.995", False), ("1.00500001", True), ("0.99499999", True)],
)
def test_stablecoin_depeg_exact_limit(price: str, vetoed: bool) -> None:
    prices = {"USDT": Decimal(1), "USDC": Decimal(price)}
    status = assess_conditions(_conditions(stablecoin_prices=prices), EXT, NOW)
    assert bool(status.vetoes) is vetoed
    assert status.close_orderly is vetoed
    if vetoed:
        assert (status.vetoes[0].reason, status.vetoes[0].subject) == (V.STABLECOIN_DEPEG, "USDC")


def test_missing_stablecoin_price_is_vetoed_without_closing() -> None:
    status = assess_conditions(_conditions(stablecoin_prices={"USDT": Decimal(1)}), EXT, NOW)
    assert [v.reason for v in status.vetoes] == [V.MISSING_CONDITION]
    assert not status.close_orderly


@pytest.mark.parametrize(
    ("offset", "vetoed"),
    [
        (timedelta(hours=2), True),
        (-timedelta(hours=2), True),
        (timedelta(hours=2, microseconds=1), False),
        (-timedelta(hours=2, microseconds=1), False),
        (timedelta(0), True),
    ],
)
def test_macro_window_includes_its_edges(offset: timedelta, vetoed: bool) -> None:
    event = MacroEvent(MacroEventKind.FOMC, NOW + offset)
    status = assess_conditions(_conditions(macro_events=(event,)), EXT, NOW)
    assert bool(status.vetoes) is vetoed
    if vetoed:
        veto = status.vetoes[0]
        assert veto.reason is V.MACRO_EVENT_WINDOW
        assert veto.subject.startswith("FOMC 2026-10-23")
        assert veto.limit == 7200


@pytest.mark.parametrize(
    ("through", "vetoed"), [(NOW + timedelta(hours=2), False), (NOW + timedelta(hours=1), True)]
)
def test_macro_calendar_must_cover_the_window(through: datetime, vetoed: bool) -> None:
    status = assess_conditions(_conditions(macro_calendar_through=through), EXT, NOW)
    assert ([v.reason for v in status.vetoes] == [V.MISSING_CONDITION]) is vetoed


@pytest.mark.parametrize(
    ("ages_minutes", "vetoed"),
    [((1, 2), False), ((1, 2, 9), True), ((1, 2, 10), False), ((0, 0, 0, 30), True)],
)
def test_api_error_circuit_trips_at_three_errors_in_ten_minutes(
    ages_minutes: tuple[int, ...], vetoed: bool
) -> None:
    times = tuple(NOW - timedelta(minutes=m) for m in ages_minutes)
    status = assess_conditions(_conditions(api_error_times=times), EXT, NOW)
    assert bool(status.vetoes) is vetoed
    if vetoed:
        assert status.vetoes[0].reason is V.API_ERROR_CIRCUIT
        assert status.vetoes[0].limit == 3


def test_conditions_validation() -> None:
    with pytest.raises(ValueError, match="positivo"):
        _conditions(stablecoin_prices={"USDT": Decimal(0)})
    with pytest.raises(ValueError, match="zona horaria"):
        _conditions(macro_calendar_through=datetime(2026, 11, 1))  # noqa: DTZ001
    with pytest.raises(ValueError, match="zona horaria"):
        _conditions(api_error_times=(datetime(2026, 10, 23),))  # noqa: DTZ001
    with pytest.raises(TypeError):
        _conditions(betas={"BTC": 1.0})
    with pytest.raises(TypeError):
        MacroEvent("FOMC", NOW)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="zona horaria"):
        assess_conditions(_conditions(), EXT, datetime(2026, 10, 23))  # noqa: DTZ001


# --- condiciones del activo ------------------------------------------------------------------


def test_normal_symbol_conditions_pass(long_btc: EntryProposal) -> None:
    assert symbol_vetoes(long_btc, _symbol(), LIMITS, EXT, NOW) == []


def test_symbol_conditions_for_another_symbol_are_vetoed(long_btc: EntryProposal) -> None:
    (veto,) = symbol_vetoes(long_btc, _symbol("ETHUSDT"), LIMITS, EXT, NOW)
    assert veto.reason is V.MARKET_DATA_MISMATCH


@pytest.mark.parametrize(("vol", "vetoed"), [("0.02", False), ("0.0200001", True)])
def test_volatility_circuit_vetoes_only_above_p99(
    long_btc: EntryProposal, vol: str, vetoed: bool
) -> None:
    vetoes = symbol_vetoes(long_btc, _symbol(realized_vol_1h=Decimal(vol)), LIMITS, EXT, NOW)
    assert bool(vetoes) is vetoed


@pytest.mark.parametrize(
    ("bid", "ask", "vetoed"),
    [
        # 5 pb exactos sobre el medio 1,000: ask - bid = 0.5.
        ("999.75", "1000.25", False),
        ("999.74", "1000.25", True),
    ],
)
def test_spread_exact_limit_for_core_assets(
    long_btc: EntryProposal, bid: str, ask: str, vetoed: bool
) -> None:
    quote = _symbol(best_bid=Decimal(bid), best_ask=Decimal(ask))
    vetoes = symbol_vetoes(long_btc, quote, LIMITS, EXT, NOW)
    assert bool(vetoes) is vetoed
    if vetoed:
        assert vetoes[0].reason is V.SPREAD_TOO_WIDE
        assert vetoes[0].limit == 5


def test_alts_have_a_wider_spread_limit(long_btc: EntryProposal) -> None:
    sol = _alt(long_btc, "SOL", "100")
    quote = _symbol("SOLUSDT", best_bid=Decimal("9.9951"), best_ask=Decimal("10.0049"))
    assert symbol_vetoes(sol, quote, LIMITS, EXT, NOW) == []  # ~9.8 pb <= 10 pb
    assert (
        symbol_vetoes(long_btc, replace(quote, symbol="BTCUSDT"), LIMITS, EXT, NOW)[0].reason
        is V.SPREAD_TOO_WIDE
    )


@pytest.mark.parametrize(("depth", "vetoed"), [("3750", False), ("3749.99", True)])
def test_book_depth_exact_limit(long_btc: EntryProposal, depth: str, vetoed: bool) -> None:
    # Nocional USD 375 x 10 = USD 3,750 de profundidad mínima.
    vetoes = symbol_vetoes(long_btc, _symbol(depth_notional=Decimal(depth)), LIMITS, EXT, NOW)
    assert bool(vetoes) is vetoed
    if vetoed:
        assert (vetoes[0].reason, vetoes[0].limit) == (V.BOOK_TOO_THIN, Decimal(3750))


def test_depth_is_not_checked_without_a_positive_quantity(long_btc: EntryProposal) -> None:
    proposal = replace(long_btc, quantity=Decimal(0))
    assert symbol_vetoes(proposal, _symbol(depth_notional=Decimal(0)), LIMITS, EXT, NOW) == []


@pytest.mark.parametrize(("age", "vetoed"), [(60, False), (61, True)])
def test_book_quote_freshness(long_btc: EntryProposal, age: int, vetoed: bool) -> None:
    quote = _symbol(quote_time=NOW - timedelta(seconds=age))
    vetoes = symbol_vetoes(long_btc, quote, LIMITS, EXT, NOW)
    assert ([v.reason for v in vetoes] == [V.STALE_PRICE]) is vetoed


def test_symbol_conditions_validation() -> None:
    with pytest.raises(ValueError, match="libro cruzado"):
        _symbol(best_bid=Decimal(2), best_ask=Decimal(1))
    with pytest.raises(ValueError, match="positivo"):
        _symbol(vol_1h_p99=Decimal(0))
    with pytest.raises(TypeError):
        _symbol(funding_rate_8h=0.0001)
    assert _symbol(funding_rate_8h=None).funding_rate_8h is None
    assert _symbol(best_bid=Decimal(999), best_ask=Decimal(1001)).spread_bps == 20


# --- evaluación completa ---------------------------------------------------------------------


def _v1(
    proposal: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    conditions: MarketConditions | None = None,
    symbol: SymbolConditions | None = None,
) -> Any:
    return evaluate_entry_v1(
        proposal,
        account,
        market,
        conditions or _conditions(),
        symbol or _symbol(proposal.symbol),
        LIMITS,
        EXT,
        ZERO_COSTS,
        NOW,
    )


def test_normal_entry_is_approved_by_v1(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot
) -> None:
    decision = _v1(long_btc, account, market)
    assert decision.approved
    assert not decision.close_orderly
    assert decision.trade_risk == Decimal("7.50000")


def test_v1_reports_v0_and_extended_vetoes_together(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot
) -> None:
    conditions = _conditions(
        stablecoin_prices={"USDT": Decimal("0.98"), "USDC": Decimal(1)},
        macro_events=(MacroEvent(MacroEventKind.CPI, NOW + timedelta(minutes=30)),),
    )
    proposal = replace(long_btc, quantity=Decimal("0.01"))
    decision = _v1(proposal, account, market, conditions, _symbol(funding_rate_8h=Decimal("0.003")))
    assert decision.reasons == {
        V.RISK_PER_TRADE,
        V.CORRELATED_EXPOSURE,
        V.STABLECOIN_DEPEG,
        V.MACRO_EVENT_WINDOW,
        V.ADVERSE_FUNDING,
    }
    assert decision.close_orderly


def test_v1_keeps_the_hard_stop_flatten(long_btc: EntryProposal, market: MarketSnapshot) -> None:
    account = AccountState(Decimal(1200), CAPITAL, Decimal(1200), Decimal(1200))
    decision = _v1(long_btc, account, market)
    assert decision.flatten_positions
    assert V.DRAWDOWN_HARD_STOP in decision.reasons


ALL_ASSETS = ("BTC", "ETH", "SOL", "XRP")


@given(
    positions=st.lists(
        st.tuples(
            st.sampled_from(ALL_ASSETS),
            st.decimals(min_value=Decimal(0), max_value=Decimal(800), places=2),
            st.decimals(min_value=Decimal(0), max_value=Decimal(5), places=2),
        ),
        max_size=5,
    ),
    asset=st.sampled_from(ALL_ASSETS),
    notional=st.decimals(min_value=Decimal(1), max_value=Decimal(2000), places=2),
    stop_distance=st.decimals(min_value=Decimal("0.005"), max_value=Decimal("0.2"), places=3),
    funding=st.decimals(min_value=Decimal("-0.003"), max_value=Decimal("0.003"), places=5),
    usdc=st.decimals(min_value=Decimal("0.99"), max_value=Decimal("1.01"), places=4),
    event_minutes=st.integers(min_value=-300, max_value=300),
    vol=st.decimals(min_value=Decimal(0), max_value=Decimal("0.03"), places=4),
)
def test_v1_is_never_less_restrictive_and_approvals_satisfy_every_extended_limit(
    positions: list[tuple[str, Decimal, Decimal]],
    asset: str,
    notional: Decimal,
    stop_distance: Decimal,
    funding: Decimal,
    usdc: Decimal,
    event_minutes: int,
    vol: Decimal,
) -> None:
    account = AccountState(
        CAPITAL,
        CAPITAL,
        CAPITAL,
        CAPITAL,
        open_positions=tuple(OpenPosition(f"{a}USDT", a, Side.LONG, n, r) for a, n, r in positions),
    )
    entry = Decimal(100)
    proposal = EntryProposal(
        strategy_id="H2",
        symbol=f"{asset}USDT",
        base_asset=asset,
        market=MarketType.PERPETUAL,
        side=Side.LONG,
        entry_price=entry,
        stop_price=entry * (1 - stop_distance),
        quantity=notional / entry,
        perpetual=PerpetualTerms(
            MarginMode.ISOLATED,
            Decimal(3),
            Decimal("0.004"),
            Decimal(0),
            LiquidationModel.BINANCE_USDM_ISOLATED,
        ),
    )
    market = MarketSnapshot(proposal.symbol, NOW, NOW, timedelta(hours=4))
    conditions = _conditions(
        stablecoin_prices={"USDT": Decimal(1), "USDC": usdc},
        macro_events=(MacroEvent(MacroEventKind.NFP, NOW + timedelta(minutes=event_minutes)),),
    )
    symbol = _symbol(
        proposal.symbol,
        realized_vol_1h=vol,
        best_bid=Decimal("99.99"),
        best_ask=Decimal("100.01"),
        funding_rate_8h=funding,
    )
    v0 = evaluate_entry(proposal, account, market, LIMITS, ZERO_COSTS, NOW)
    v1 = _v1(proposal, account, market, conditions, symbol)
    assert v0.reasons <= v1.reasons  # v1 solo añade restricciones
    if not v1.approved:
        return

    # Comprobación independiente de cada regla ampliada.
    exposures = [(a, n) for a, n, _ in positions] + [(asset, notional)]
    assert sum(n * BETAS[a] for a, n in exposures) <= CAPITAL
    if asset not in {"BTC", "ETH"}:
        assert sum(n for a, n in exposures if a == asset) <= Decimal("0.10") * CAPITAL
        assert sum(n for a, n in exposures if a not in {"BTC", "ETH"}) <= Decimal("0.25") * CAPITAL
    assert len(positions) + 1 <= 4
    assert funding <= Decimal("0.0010")
    assert abs(usdc - 1) <= Decimal("0.005")
    assert abs(event_minutes) > 120
    assert vol <= Decimal("0.02")
    assert 10 * notional <= 1_000_000


def test_extended_limits_are_risk_limits_compatible() -> None:
    # Las reglas ampliadas no tocan los límites del plan.
    assert isinstance(LIMITS, RiskLimits)
    assert load_plan_limits_f7_f8() == LIMITS


def test_a_section_that_is_not_a_table_is_rejected() -> None:
    from importlib import resources

    text = resources.files("trading.risk").joinpath("limits_v1_propuesto.toml").read_text("utf-8")
    text = "macro = 1\n" + text.replace("[macro]\nblackout_minutes = 120", "")
    with pytest.raises(InvalidRiskLimitsError, match="tabla"):
        extended_limits_from_toml(text)
