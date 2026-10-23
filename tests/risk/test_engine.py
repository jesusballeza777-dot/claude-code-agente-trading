"""Motor de riesgo: casos normales, límites exactos y casos que deben vetarse."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal, localcontext
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.risk import (
    AccountState,
    CostModel,
    EntryProposal,
    MarginMode,
    MarketSnapshot,
    MarketType,
    OpenPosition,
    PerpetualTerms,
    RiskDecision,
    RiskLimits,
    Side,
    VetoReason,
    assess_account,
    evaluate_entry,
    load_plan_limits_f7_f8,
    size_by_risk,
    trade_risk,
)

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
ZERO_COSTS = CostModel(fee_rate=Decimal(0), slippage_rate=Decimal(0))
MICROSECOND = timedelta(microseconds=1)
V = VetoReason


def _evaluate(
    proposal: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    costs: CostModel = ZERO_COSTS,
) -> RiskDecision:
    return evaluate_entry(proposal, account, market, limits, costs, NOW)


def _sol(base: EntryProposal, entry: str, stop: str, quantity: str) -> EntryProposal:
    """La misma propuesta sobre SOL, que no pertenece a ningún grupo de correlación."""
    return replace(
        base,
        symbol="SOLUSDT",
        base_asset="SOL",
        entry_price=Decimal(entry),
        stop_price=Decimal(stop),
        quantity=Decimal(quantity),
    )


def _position(asset: str, notional: str, risk: str) -> OpenPosition:
    return OpenPosition(
        f"{asset}USDT", asset, Side.LONG, notional=Decimal(notional), risk_to_stop=Decimal(risk)
    )


# --- casos normales --------------------------------------------------------------------------


def test_normal_long_perpetual_is_approved(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    decision = _evaluate(long_btc, account, market, limits)
    assert decision.approved
    assert decision.vetoes == ()
    assert decision.trade_risk == Decimal("7.5")
    assert decision.effective_leverage_after == Decimal("0.25")
    assert decision.liquidation_price is not None
    assert decision.liquidation_price < long_btc.stop_price
    assert not decision.flatten_positions


def test_normal_spot_long_is_approved(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    spot = replace(long_btc, market=MarketType.SPOT, perpetual=None)
    decision = _evaluate(spot, account, market, limits)
    assert decision.approved
    assert decision.liquidation_price is None


def test_short_is_approved_only_for_a_strategy_validated_in_both_directions(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    short = replace(long_btc, side=Side.SHORT, stop_price=Decimal(61200))
    assert _evaluate(short, account, market, limits).reasons == {V.SHORT_NOT_VALIDATED}
    validated = replace(limits, short_enabled_strategies=frozenset({"H2"}))
    decision = _evaluate(short, account, market, validated)
    assert decision.approved
    assert decision.liquidation_price is not None
    assert decision.liquidation_price > short.stop_price


def test_costs_count_against_the_risk_budget(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    costs = CostModel(fee_rate=Decimal("0.0005"), slippage_rate=Decimal("0.0005"))
    decision = _evaluate(long_btc, account, market, limits, costs)
    assert decision.trade_risk == Decimal("8.2425")
    assert V.RISK_PER_TRADE in decision.reasons


@pytest.mark.parametrize(
    ("exchange_leverage", "approved"), [(Decimal(10), True), (Decimal(20), False)]
)
def test_exchange_leverage_decides_liquidation_buffer_for_a_2pct_stop(
    long_btc: EntryProposal,
    perp_terms: PerpetualTerms,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    exchange_leverage: Decimal,
    approved: bool,
) -> None:
    # Stop al 2% exige liquidación a >= 6%: a 10x queda a ~9.6%; a 20x, a ~4.6%.
    terms = replace(perp_terms, exchange_leverage=exchange_leverage)
    decision = _evaluate(replace(long_btc, perpetual=terms), account, market, limits)
    assert decision.approved is approved
    if not approved:
        assert decision.reasons == {V.LIQUIDATION_TOO_CLOSE}


# --- límites exactos -------------------------------------------------------------------------


@pytest.mark.parametrize(("quantity", "approved"), [("2.5", True), ("2.5001", False)])
def test_risk_per_trade_exact_limit(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    quantity: str,
    approved: bool,
) -> None:
    proposal = _sol(long_btc, "150", "147", quantity)  # 2.5 x 3 = USD 7.50 exactos
    decision = _evaluate(proposal, account, replace(market, symbol="SOLUSDT"), limits)
    assert decision.reasons == (set() if approved else {V.RISK_PER_TRADE})


@pytest.mark.parametrize(("extra_notional", "approved"), [("0", True), ("0.01", False)])
def test_effective_leverage_exact_limit(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    extra_notional: str,
    approved: bool,
) -> None:
    proposal = _sol(long_btc, "150", "149.625", "20")  # USD 3,000 = 2x con riesgo de USD 7.50
    positions = (_position("XRP", extra_notional, "0"),)
    decision = _evaluate(
        proposal,
        replace(account, open_positions=positions),
        replace(market, symbol="SOLUSDT"),
        limits,
    )
    assert decision.reasons == (set() if approved else {V.EFFECTIVE_LEVERAGE})


@pytest.mark.parametrize(("maintenance_amount", "approved"), [("7.5", True), ("7.4985", False)])
def test_liquidation_distance_exact_limit(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    maintenance_amount: str,
    approved: bool,
) -> None:
    # Entrada 100, stop 95 (5%): la liquidación tiene que quedar a >= 15%, es decir, en <= 85.
    terms = PerpetualTerms(
        margin_mode=MarginMode.ISOLATED,
        exchange_leverage=Decimal(10),
        maintenance_margin_rate=Decimal(0),
        maintenance_amount=Decimal(maintenance_amount),
    )
    proposal = replace(_sol(long_btc, "100", "95", "1.5"), perpetual=terms)
    decision = _evaluate(proposal, account, replace(market, symbol="SOLUSDT"), limits)
    if approved:
        assert decision.liquidation_price == Decimal(85)
        assert decision.approved
    else:
        assert decision.reasons == {V.LIQUIDATION_TOO_CLOSE}


@pytest.mark.parametrize(("open_risk", "approved"), [("12.55", True), ("12.5501", False)])
def test_daily_loss_exact_limit(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    open_risk: str,
    approved: bool,
) -> None:
    # Pérdida del día 10 + riesgo abierto 12.55 + nueva operación 7.45 = 30 = 2% de 1,500.
    state = replace(
        account, equity=Decimal(1490), open_positions=(_position("XRP", "100", open_risk),)
    )
    proposal = _sol(long_btc, "100", "98", "3.725")
    decision = _evaluate(proposal, state, replace(market, symbol="SOLUSDT"), limits)
    assert decision.trade_risk == Decimal("7.45")
    assert decision.reasons == (set() if approved else {V.DAILY_LOSS})


@pytest.mark.parametrize(("open_risk", "approved"), [("12.7", True), ("12.7001", False)])
def test_weekly_loss_exact_limit(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    open_risk: str,
    approved: bool,
) -> None:
    # Pérdida de la semana 40 + riesgo abierto 12.7 + nueva operación 7.3 = 60 = 4% de 1,500.
    state = replace(
        account,
        equity=Decimal(1460),
        day_start_equity=Decimal(1460),
        open_positions=(_position("XRP", "100", open_risk),),
    )
    proposal = _sol(long_btc, "100", "98", "3.65")
    decision = _evaluate(proposal, state, replace(market, symbol="SOLUSDT"), limits)
    assert decision.reasons == (set() if approved else {V.WEEKLY_LOSS})


def test_daily_loss_already_reached_blocks_any_entry(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    state = replace(account, equity=Decimal(1470))  # -2% en el día
    tiny = _sol(long_btc, "100", "98", "0.001")
    decision = _evaluate(tiny, state, replace(market, symbol="SOLUSDT"), limits)
    assert decision.reasons == {V.DAILY_LOSS}


@pytest.mark.parametrize(("eth_quantity", "approved"), [("0.0625", True), ("0.06250001", False)])
def test_btc_eth_joint_exposure_exact_limit(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    eth_quantity: str,
    approved: bool,
) -> None:
    # BTC abierto con USD 3.75 de riesgo + ETH con USD 3.75 = una sola operación de USD 7.50.
    eth = replace(
        long_btc,
        symbol="ETHUSDT",
        base_asset="ETH",
        entry_price=Decimal(3000),
        stop_price=Decimal(2940),
        quantity=Decimal(eth_quantity),
    )
    state = replace(account, open_positions=(_position("BTC", "187.5", "3.75"),))
    decision = _evaluate(eth, state, replace(market, symbol="ETHUSDT"), limits)
    assert decision.reasons == (set() if approved else {V.CORRELATED_EXPOSURE})


@pytest.mark.parametrize(
    ("open_asset", "open_risk", "approved"),
    [("BTC", "7.5", False), ("BTC", "0", True), ("SOL", "7.5", True)],
)
def test_full_eth_trade_depends_on_open_btc_risk(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    open_asset: str,
    open_risk: str,
    approved: bool,
) -> None:
    eth = replace(
        long_btc,
        symbol="ETHUSDT",
        base_asset="ETH",
        entry_price=Decimal(3000),
        stop_price=Decimal(2940),
        quantity=Decimal("0.125"),
    )
    state = replace(account, open_positions=(_position(open_asset, "375", open_risk),))
    decision = _evaluate(eth, state, replace(market, symbol="ETHUSDT"), limits)
    assert decision.reasons == (set() if approved else {V.CORRELATED_EXPOSURE})


@pytest.mark.parametrize(
    ("equity", "expected", "flatten"),
    [
        ("1275.01", set(), False),
        ("1275", {V.DRAWDOWN_HALT}, False),  # 15% exacto = USD 225: parada
        ("1200.01", {V.DRAWDOWN_HALT}, False),
        ("1200", {V.DRAWDOWN_HARD_STOP}, True),  # 20% exacto = USD 300: corte duro
        ("900", {V.DRAWDOWN_HARD_STOP}, True),
    ],
)
def test_drawdown_thresholds(
    account: AccountState,
    limits: RiskLimits,
    equity: str,
    expected: set[VetoReason],
    flatten: bool,
) -> None:
    status = assess_account(replace(account, equity=Decimal(equity)), limits)
    assert {v.reason for v in status.vetoes} == expected
    assert status.flatten_positions is flatten
    assert status.halt_new_entries is bool(expected)


def test_drawdown_uses_current_equity_when_above_recorded_peak(
    account: AccountState, limits: RiskLimits
) -> None:
    status = assess_account(replace(account, equity=Decimal(1600)), limits)
    assert status.drawdown == 0
    assert status.vetoes == ()


def test_hard_stop_vetoes_entry_and_requests_flatten(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    state = replace(
        account,
        equity=Decimal(1200),
        day_start_equity=Decimal(1200),
        week_start_equity=Decimal(1200),
    )
    proposal = replace(long_btc, quantity=Decimal("0.005"))  # riesgo 6 = 0.5% de 1,200
    decision = _evaluate(proposal, state, market, limits)
    assert decision.reasons == {V.DRAWDOWN_HARD_STOP}
    assert decision.flatten_positions


@pytest.mark.parametrize(
    ("field", "offset", "expected"),
    [
        ("price_time", -timedelta(seconds=60), set()),
        ("price_time", -timedelta(seconds=60) - MICROSECOND, {V.STALE_PRICE}),
        ("last_bar_close_time", -timedelta(hours=4, seconds=300), set()),
        ("last_bar_close_time", -timedelta(hours=4, seconds=300) - MICROSECOND, {V.STALE_BARS}),
        ("price_time", timedelta(seconds=5), set()),
        ("price_time", timedelta(seconds=5) + MICROSECOND, {V.FUTURE_TIMESTAMP}),
        ("last_bar_close_time", timedelta(seconds=5) + MICROSECOND, {V.FUTURE_TIMESTAMP}),
    ],
)
def test_data_freshness_exact_limits(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    field: str,
    offset: timedelta,
    expected: set[VetoReason],
) -> None:
    changes: dict[str, Any] = {field: NOW + offset}
    snapshot = replace(market, **changes)
    assert _evaluate(long_btc, account, snapshot, limits).reasons == expected


# --- vetos -----------------------------------------------------------------------------------


def test_manual_halt_vetoes_everything(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    decision = _evaluate(long_btc, replace(account, trading_halted=True), market, limits)
    assert decision.reasons == {V.TRADING_HALTED}


def test_non_positive_equity_vetoes_and_flattens(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    decision = _evaluate(long_btc, replace(account, equity=Decimal(0)), market, limits)
    assert decision.reasons == {V.NON_POSITIVE_EQUITY}
    assert decision.flatten_positions
    assert decision.trade_risk is None


def test_market_data_for_another_symbol_is_vetoed(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    decision = _evaluate(long_btc, account, replace(market, symbol="ETHUSDT"), limits)
    assert decision.reasons == {V.MARKET_DATA_MISMATCH}


def test_short_on_spot_is_vetoed(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    short_spot = replace(
        long_btc,
        side=Side.SHORT,
        stop_price=Decimal(61200),
        market=MarketType.SPOT,
        perpetual=None,
    )
    validated = replace(limits, short_enabled_strategies=frozenset({"H2"}))
    assert _evaluate(short_spot, account, market, validated).reasons == {V.SHORT_ON_SPOT}
    assert _evaluate(short_spot, account, market, limits).reasons == {
        V.SHORT_ON_SPOT,
        V.SHORT_NOT_VALIDATED,
    }


def test_cross_margin_is_vetoed(
    long_btc: EntryProposal,
    perp_terms: PerpetualTerms,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
) -> None:
    cross = replace(long_btc, perpetual=replace(perp_terms, margin_mode=MarginMode.CROSS))
    assert _evaluate(cross, account, market, limits).reasons == {V.CROSS_MARGIN}


@pytest.mark.parametrize(
    ("side", "stop"),
    [(Side.LONG, "60000"), (Side.LONG, "60100"), (Side.SHORT, "60000"), (Side.SHORT, "59900")],
)
def test_stop_on_the_wrong_side_is_vetoed(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    side: Side,
    stop: str,
) -> None:
    validated = replace(limits, short_enabled_strategies=frozenset({"H2"}))
    proposal = replace(long_btc, side=side, stop_price=Decimal(stop))
    decision = _evaluate(proposal, account, market, validated)
    assert decision.reasons == {V.INVALID_STOP}
    assert decision.trade_risk is None


@pytest.mark.parametrize("quantity", ["0", "-0.00625"])
def test_non_positive_quantity_is_vetoed(
    long_btc: EntryProposal,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
    quantity: str,
) -> None:
    decision = _evaluate(replace(long_btc, quantity=Decimal(quantity)), account, market, limits)
    assert decision.reasons == {V.NON_POSITIVE_QUANTITY}


def test_all_applicable_vetoes_are_reported_together(
    long_btc: EntryProposal,
    perp_terms: PerpetualTerms,
    account: AccountState,
    market: MarketSnapshot,
    limits: RiskLimits,
) -> None:
    proposal = replace(
        long_btc,
        side=Side.SHORT,
        stop_price=Decimal(61200),
        quantity=Decimal(1),
        perpetual=replace(perp_terms, margin_mode=MarginMode.CROSS, exchange_leverage=Decimal(50)),
    )
    stale = replace(market, price_time=NOW - timedelta(minutes=10))
    decision = _evaluate(proposal, replace(account, trading_halted=True), stale, limits)
    assert decision.reasons == {
        V.TRADING_HALTED,
        V.STALE_PRICE,
        V.SHORT_NOT_VALIDATED,
        V.CROSS_MARGIN,
        V.RISK_PER_TRADE,
        V.EFFECTIVE_LEVERAGE,
        V.DAILY_LOSS,
        V.WEEKLY_LOSS,
        V.CORRELATED_EXPOSURE,
        V.LIQUIDATION_TOO_CLOSE,
    }
    assert all(v.detail for v in decision.vetoes)


def test_naive_now_is_rejected(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    naive = datetime(2026, 10, 23, 12, 0)  # noqa: DTZ001 - caso que debe rechazarse
    with pytest.raises(ValueError, match="zona horaria"):
        evaluate_entry(long_btc, account, market, limits, ZERO_COSTS, naive)


# --- propiedades -----------------------------------------------------------------------------

LIMITS = load_plan_limits_f7_f8()
SHORTS_OK = RiskLimits(
    **{
        **{f: getattr(LIMITS, f) for f in LIMITS.__dataclass_fields__},
        "short_enabled_strategies": frozenset({"H2"}),
    }
)
FRESH = MarketSnapshot("SOLUSDT", NOW, NOW, timedelta(hours=4))
ASSETS = ("BTC", "ETH", "SOL", "XRP")


def _proposal(asset: str, side: Side, entry: Decimal, stop: Decimal, qty: Decimal) -> EntryProposal:
    return EntryProposal(
        strategy_id="H2",
        symbol=f"{asset}USDT",
        base_asset=asset,
        market=MarketType.PERPETUAL,
        side=side,
        entry_price=entry,
        stop_price=stop,
        quantity=qty,
        perpetual=PerpetualTerms(MarginMode.ISOLATED, Decimal(1), Decimal("0.004"), Decimal(0)),
    )


@given(
    equity=st.decimals(min_value=Decimal(100), max_value=Decimal(100_000), places=2),
    entry=st.decimals(min_value=Decimal(1), max_value=Decimal(100_000), places=2),
    distance=st.decimals(min_value=Decimal("0.001"), max_value=Decimal("0.1"), places=4),
    side=st.sampled_from(Side),
    fee=st.decimals(min_value=Decimal(0), max_value=Decimal("0.001"), places=5),
)
def test_a_position_sized_by_risk_respects_budget_and_leverage(
    equity: Decimal, entry: Decimal, distance: Decimal, side: Side, fee: Decimal
) -> None:
    costs = CostModel(fee_rate=fee, slippage_rate=fee)
    stop = entry * (1 - distance) if side is Side.LONG else entry * (1 + distance)
    quantity = size_by_risk(
        equity=equity,
        entry_price=entry,
        stop_price=stop,
        risk_fraction=LIMITS.risk_per_trade,
        costs=costs,
        max_notional=LIMITS.max_effective_leverage * equity,
    )
    if quantity == 0:
        return
    account = AccountState(equity, equity, equity, equity)
    proposal = _proposal("SOL", side, entry, stop, quantity)
    decision = evaluate_entry(proposal, account, FRESH, SHORTS_OK, costs, NOW)
    assert decision.approved, decision.vetoes


@given(
    equity=st.decimals(min_value=Decimal(500), max_value=Decimal(3000), places=2),
    peak_gap=st.decimals(min_value=Decimal(0), max_value=Decimal(800), places=2),
    day_gap=st.decimals(min_value=Decimal(-50), max_value=Decimal(50), places=2),
    week_gap=st.decimals(min_value=Decimal(-100), max_value=Decimal(100), places=2),
    positions=st.lists(
        st.tuples(
            st.sampled_from(ASSETS),
            st.decimals(min_value=Decimal(0), max_value=Decimal(2000), places=2),
            st.decimals(min_value=Decimal(0), max_value=Decimal(15), places=2),
        ),
        max_size=3,
    ),
    asset=st.sampled_from(ASSETS),
    side=st.sampled_from(Side),
    entry=st.decimals(min_value=Decimal(1), max_value=Decimal(100_000), places=2),
    distance=st.decimals(min_value=Decimal("-0.01"), max_value=Decimal("0.1"), places=4),
    scale=st.decimals(min_value=Decimal("0.1"), max_value=Decimal("1.5"), places=2),
)
def test_every_approved_entry_satisfies_every_limit(
    equity: Decimal,
    peak_gap: Decimal,
    day_gap: Decimal,
    week_gap: Decimal,
    positions: list[tuple[str, Decimal, Decimal]],
    asset: str,
    side: Side,
    entry: Decimal,
    distance: Decimal,
    scale: Decimal,
) -> None:
    account = AccountState(
        equity=equity,
        peak_equity=equity + peak_gap,
        day_start_equity=equity + day_gap,
        week_start_equity=equity + week_gap,
        open_positions=tuple(
            OpenPosition(f"{a}USDT", a, Side.LONG, notional=n, risk_to_stop=r)
            for a, n, r in positions
        ),
    )
    stop = entry * (1 - distance) if side is Side.LONG else entry * (1 + distance)
    if stop <= 0 or stop == entry:
        return
    quantity = scale * equity * LIMITS.risk_per_trade / abs(entry - stop)
    proposal = _proposal(asset, side, entry, stop, quantity)
    market = replace(FRESH, symbol=proposal.symbol)
    decision = evaluate_entry(proposal, account, market, LIMITS, ZERO_COSTS, NOW)
    if not decision.approved:
        return

    # Comprobación independiente de cada límite del plan §3.
    risk = trade_risk(quantity, entry, stop, ZERO_COSTS)
    budget = equity * Decimal("0.005")
    open_risk = sum((r for _, _, r in positions), Decimal(0))
    open_notional = sum((n for _, n, _ in positions), Decimal(0))
    assert side is Side.LONG  # ninguna estrategia tiene cortos validados en los límites del plan
    assert stop < entry
    assert risk <= budget
    assert open_notional + quantity * entry <= 2 * equity
    assert account.day_start_equity - (equity - open_risk - risk) <= Decimal("0.02") * (
        account.day_start_equity
    )
    assert account.week_start_equity - (equity - open_risk - risk) <= Decimal("0.04") * (
        account.week_start_equity
    )
    assert peak_gap < Decimal("0.15") * (equity + peak_gap)
    if asset in {"BTC", "ETH"}:
        group_risk = risk + sum((r for a, _, r in positions if a in {"BTC", "ETH"}), Decimal(0))
        assert group_risk <= budget
    assert decision.liquidation_price is None or (
        entry - decision.liquidation_price >= 3 * (entry - stop)
    )


def test_result_does_not_depend_on_the_process_decimal_context(
    long_btc: EntryProposal, account: AccountState, market: MarketSnapshot, limits: RiskLimits
) -> None:
    # Riesgo 7.5000006 > 7.50: con 4 dígitos de precisión global se redondearía a 7.500 y pasaría.
    proposal = _sol(long_btc, "150", "147", "2.5000002")
    sol_market = replace(market, symbol="SOLUSDT")
    with localcontext(Context(prec=4)):
        decision = _evaluate(proposal, account, sol_market, limits)
    assert decision.reasons == {V.RISK_PER_TRADE}
