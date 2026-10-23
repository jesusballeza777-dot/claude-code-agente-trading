"""Backtester por eventos con el motor de riesgo real (protocolo común C-12, C-13, C-14).

Recorrido por cada instante T de la rejilla (apertura de velas = cierre de las anteriores):

1. Funding con `calc_time == T` para las posiciones abiertas antes de T.
2. Órdenes pendientes para T: cierre total por corte duro, salidas y entradas (por prioridad).
   Cada entrada pasa por `evaluate_entry` con los límites F7-F8 (y, en la sensibilidad v1,
   por las reglas de exposición y funding del ADR-013).
3. Durante la vela [T, T + I): stops (con gap) y funding con `T < calc_time < T + I`.
4. Al cierre T + I: valoración a mercado, inicio de día y semana UTC, paradas por drawdown,
   deslistados y fin de periodo; después, las señales de la estrategia para la apertura
   siguiente (o `delay_bars` velas después, para la prueba anti look-ahead).

Todos los importes son Decimal; los precios del archivo (float64 exactos) se convierten con
`Decimal(repr(x))`. Detalles de implementación: ACLARACIONES-v1 §4 y §6.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Final

from trading.backtest.model import (
    BacktestResult,
    Decisions,
    EntryIntent,
    ExitReason,
    FundingEvent,
    MarketData,
    SignalOutcome,
    SignalRecord,
    Strategy,
    Trade,
)
from trading.risk import (
    AccountState,
    CostModel,
    EntryProposal,
    ExtendedLimits,
    LiquidationModel,
    MarginMode,
    MarketSnapshot,
    MarketType,
    OpenPosition,
    PerpetualTerms,
    RiskLimits,
    Side,
    VetoReason,
    assess_account,
    evaluate_entry,
    exposure_vetoes,
    funding_vetoes,
    size_by_risk,
)
from trading.risk.models import RISK_DECIMAL_CONTEXT, in_risk_context

ZERO: Final = Decimal(0)
ONE: Final = Decimal(1)
EPSILON: Final = timedelta(microseconds=1)


@dataclass(frozen=True, slots=True)
class CostConfig:
    """Costes del protocolo C-14. `scale` = 1.5 en la prueba de estrés (ACLARACIONES §7)."""

    fee_rate: Decimal = Decimal("0.0005")
    slippage_core: Decimal = Decimal("0.0005")
    slippage_alt: Decimal = Decimal("0.0010")
    scale: Decimal = ONE

    def slippage(self, core: bool) -> Decimal:
        return (self.slippage_core if core else self.slippage_alt) * self.scale

    @property
    def fee(self) -> Decimal:
        return self.fee_rate * self.scale


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    limits: RiskLimits
    start: datetime
    end: datetime
    initial_capital: Decimal = Decimal(1500)
    costs: CostConfig = field(default_factory=CostConfig)
    exchange_leverage: Decimal = Decimal(3)
    mmr_core: Decimal = Decimal("0.004")
    mmr_alt: Decimal = Decimal("0.025")
    min_notional_core: Decimal = Decimal(100)
    min_notional_alt: Decimal = Decimal(20)
    core_assets: frozenset[str] = frozenset({"BTC", "ETH"})
    delay_bars: int = 0
    # Sensibilidad C-18: hora UTC de cierre de la vela de señal -> hora UTC de la entrada.
    deferred_entry_hours: Mapping[int, int] = field(default_factory=dict)
    # Sensibilidad v1 (ADR-013): reglas de exposición y funding, con betas point-in-time.
    extended: ExtendedLimits | None = None
    betas_at: Callable[[datetime], Mapping[str, Decimal]] | None = None


@dataclass
class _Position:
    symbol: str
    base_asset: str
    side: Side
    quantity: Decimal
    entry_price: Decimal
    stop_price: Decimal
    planned_risk: Decimal
    signal_time: datetime
    entry_time: datetime
    fees: Decimal
    funding: Decimal = ZERO
    mark: Decimal = ZERO

    @property
    def sign(self) -> Decimal:
        return ONE if self.side is Side.LONG else -ONE


@dataclass(frozen=True, slots=True)
class _PendingEntry:
    intent: EntryIntent
    signal_time: datetime
    execute_at: datetime


@dataclass
class _State:
    cash: Decimal
    peak: Decimal
    day_start: Decimal
    week_start: Decimal
    positions: dict[str, _Position] = field(default_factory=dict)
    pending_exits: dict[str, datetime] = field(default_factory=dict)
    pending_entries: list[_PendingEntry] = field(default_factory=list)
    flatten_at: datetime | None = None
    halted_at: datetime | None = None
    last_equity: Decimal = ZERO

    @property
    def book_positions(self) -> dict[str, Side]:
        return {s: p.side for s, p in self.positions.items()}


class _BookView:
    def __init__(self, state: _State) -> None:
        self._state = state

    @property
    def positions(self) -> Mapping[str, Side]:
        return self._state.book_positions


@in_risk_context
def run_backtest(strategy: Strategy, data: MarketData, config: BacktestConfig) -> BacktestResult:
    """Ejecuta la estrategia sobre los datos y devuelve operaciones, señales y curva de capital."""
    runner = _Runner(strategy, data, config)
    return runner.run()


class _Runner:
    def __init__(self, strategy: Strategy, data: MarketData, config: BacktestConfig) -> None:
        if config.delay_bars < 0:
            raise ValueError("delay_bars no puede ser negativo")
        self.strategy = strategy
        self.data = data
        self.config = config
        self.step = data.interval
        capital = config.initial_capital
        self.state = _State(cash=capital, peak=capital, day_start=capital, week_start=capital)
        self.state.last_equity = capital
        self.trades: list[Trade] = []
        self.signals: list[SignalRecord] = []
        self.curve: list[tuple[datetime, Decimal]] = []
        self.funded_until = data.start - EPSILON
        self.funding_times = {
            symbol: tuple(e.time for e in events) for symbol, events in data.funding.items()
        }
        self.last_close: dict[str, Decimal] = {}

    # --- recorrido ---------------------------------------------------------------------------

    def grid(self) -> list[datetime]:
        times = {
            t
            for series in self.data.series.values()
            for t in series.times
            if t >= self.data.start and t + self.step <= self.data.end
        }
        return sorted(times)

    def run(self) -> BacktestResult:
        for moment in self.grid():
            self._funding_at(moment)
            self._execute_orders(moment)
            self._intrabar(moment)
            close_time = moment + self.step
            self._close(moment, close_time)
            if close_time >= self.data.end:
                break
        self._end_of_period()
        return BacktestResult(
            strategy_id=self.strategy.strategy_id,
            trades=tuple(self.trades),
            signals=tuple(self.signals),
            equity_curve=tuple(self.curve),
            initial_capital=self.config.initial_capital,
            final_equity=self.state.cash,
            halted_at=self.state.halted_at,
        )

    # --- funding ---------------------------------------------------------------------------

    def _events(self, symbol: str, after: datetime, until: datetime) -> Sequence[FundingEvent]:
        """Liquidaciones con after < calc_time <= until (until incluido)."""
        events = self.data.funding.get(symbol, ())
        times = self.funding_times.get(symbol, ())
        return events[bisect.bisect_right(times, after) : bisect.bisect_right(times, until)]

    def _charge(self, position: _Position, event: FundingEvent) -> None:
        valuation = self.data.valuation.get(position.symbol)
        price = valuation.at(event.time) if valuation else None
        if price is None:
            return
        payment = position.sign * position.quantity * _dec(price) * _dec(event.rate)
        if payment > 0:  # pagado: el estrés de costes lo multiplica
            payment *= self.config.costs.scale
        position.funding += payment
        self.state.cash -= payment

    def _funding_at(self, moment: datetime) -> None:
        """Liquidaciones desde la última procesada hasta T incluido (cubre huecos de la rejilla)."""
        for position in self.state.positions.values():
            for event in self._events(position.symbol, self.funded_until, moment):
                if position.entry_time < event.time:
                    self._charge(position, event)
        self.funded_until = moment

    def _funding_inside(self, position: _Position, start: datetime, end: datetime) -> None:
        for event in self._events(position.symbol, start, end - EPSILON):
            if position.entry_time < event.time:
                self._charge(position, event)

    # --- órdenes -----------------------------------------------------------------------------

    def _execute_orders(self, moment: datetime) -> None:
        state = self.state
        if state.flatten_at is not None and state.flatten_at <= moment:
            for symbol in list(state.positions):
                if self._bar(symbol, moment) is not None:
                    self._exit_at_open(symbol, moment, ExitReason.HARD_STOP)
            if not state.positions:
                state.flatten_at = None
        for symbol, due in sorted(state.pending_exits.items()):
            if (
                due <= moment
                and symbol in state.positions
                and self._bar(symbol, moment) is not None
            ):
                self._exit_at_open(symbol, moment, ExitReason.SIGNAL)
        state.pending_exits = {
            s: due for s, due in state.pending_exits.items() if s in state.positions
        }
        due_entries = [p for p in state.pending_entries if p.execute_at <= moment]
        state.pending_entries = [p for p in state.pending_entries if p.execute_at > moment]
        for pending in sorted(due_entries, key=lambda p: (p.intent.priority, p.intent.symbol)):
            self._enter(pending, moment)

    def _exit_at_open(self, symbol: str, moment: datetime, reason: ExitReason) -> None:
        position = self.state.positions[symbol]
        series = self.data.series[symbol]
        index = series.index[moment]
        slip = self._slippage(position.base_asset)
        fill = _dec(series.open[index]) * (ONE - position.sign * slip)
        self._realize(position, fill, moment, reason)

    def _realize(
        self, position: _Position, fill: Decimal, exit_time: datetime, reason: ExitReason
    ) -> None:
        fee = position.quantity * fill * self.config.costs.fee
        gross = position.sign * position.quantity * (fill - position.entry_price)
        self.state.cash += gross - fee
        fees = position.fees + fee
        pnl = gross - fees - position.funding
        self.trades.append(
            Trade(
                symbol=position.symbol,
                side=position.side,
                signal_time=position.signal_time,
                entry_time=position.entry_time,
                entry_price=position.entry_price,
                stop_price=position.stop_price,
                quantity=position.quantity,
                planned_risk=position.planned_risk,
                exit_time=exit_time,
                exit_price=fill,
                exit_reason=reason,
                fees=fees,
                funding=position.funding,
                pnl=pnl,
            )
        )
        del self.state.positions[position.symbol]
        self.state.pending_exits.pop(position.symbol, None)
        self.strategy.on_exit(position.symbol, position.side, reason)

    def _enter(self, pending: _PendingEntry, moment: datetime) -> None:
        intent, state, config = pending.intent, self.state, self.config
        record = SignalRecord(pending.signal_time, intent.symbol, intent.side, SignalOutcome.NO_BAR)
        if intent.symbol in state.positions:
            return
        index = self._bar(intent.symbol, moment)
        if index is None or state.halted_at is not None:
            note = "corte duro activo" if state.halted_at is not None else ""
            self.signals.append(replace(record, note=note))
            return
        series = self.data.series[intent.symbol]
        core = series.base_asset in config.core_assets
        slip = self._slippage(series.base_asset)
        sign = ONE if intent.side is Side.LONG else -ONE
        price = _dec(series.open[index]) * (ONE + sign * slip)
        stop = price - sign * _dec(intent.stop_distance)
        if stop <= 0:
            self.signals.append(
                replace(record, outcome=SignalOutcome.VETOED, reasons=(VetoReason.INVALID_STOP,))
            )
            return
        costs = CostModel(fee_rate=config.costs.fee, slippage_rate=slip)
        equity = state.last_equity
        open_positions = tuple(self._open_position(p) for p in state.positions.values())
        open_notional = sum((p.notional for p in open_positions), ZERO)
        room = config.limits.max_effective_leverage * equity - open_notional
        room = min(room, self._extended_room(series.base_asset, equity, open_positions, moment))
        quantity = ZERO
        if equity > 0 and room > 0:
            quantity = size_by_risk(
                equity=equity,
                entry_price=price,
                stop_price=stop,
                risk_fraction=config.limits.risk_per_trade,
                costs=costs,
                max_notional=room,
            )
        if quantity <= 0:
            self.signals.append(
                replace(record, outcome=SignalOutcome.NOT_EXECUTABLE, note="sin tamaño")
            )
            return
        proposal = EntryProposal(
            strategy_id=self.strategy.strategy_id,
            symbol=intent.symbol,
            base_asset=series.base_asset,
            market=MarketType.PERPETUAL,
            side=intent.side,
            entry_price=price,
            stop_price=stop,
            quantity=quantity,
            perpetual=PerpetualTerms(
                margin_mode=MarginMode.ISOLATED,
                exchange_leverage=config.exchange_leverage,
                maintenance_margin_rate=config.mmr_core if core else config.mmr_alt,
                maintenance_amount=ZERO,
                liquidation_model=LiquidationModel.BINANCE_USDM_ISOLATED,
            ),
            min_notional=config.min_notional_core if core else config.min_notional_alt,
        )
        account = AccountState(
            equity=equity,
            peak_equity=state.peak,
            day_start_equity=state.day_start,
            week_start_equity=state.week_start,
            open_positions=open_positions,
        )
        snapshot = MarketSnapshot(intent.symbol, moment, moment, self.step)
        decision = evaluate_entry(proposal, account, snapshot, config.limits, costs, moment)
        vetoes = list(decision.vetoes)
        if config.extended is not None:
            vetoes += exposure_vetoes(proposal, account, self._betas(moment), config.extended)
            vetoes += funding_vetoes(
                proposal, self._current_funding_8h(intent.symbol, moment), config.extended
            )
        if vetoes:
            reasons = tuple(v.reason for v in vetoes)
            outcome = (
                SignalOutcome.NOT_EXECUTABLE
                if reasons == (VetoReason.BELOW_MIN_NOTIONAL,)
                else SignalOutcome.VETOED
            )
            self.signals.append(replace(record, outcome=outcome, reasons=reasons))
            return
        assert decision.trade_risk is not None  # noqa: S101 - aprobado implica riesgo calculado
        fee = quantity * price * config.costs.fee
        state.cash -= fee
        state.positions[intent.symbol] = _Position(
            symbol=intent.symbol,
            base_asset=series.base_asset,
            side=intent.side,
            quantity=quantity,
            entry_price=price,
            stop_price=stop,
            planned_risk=decision.trade_risk,
            signal_time=pending.signal_time,
            entry_time=moment,
            fees=fee,
            mark=price,
        )
        self.signals.append(replace(record, outcome=SignalOutcome.EXECUTED))

    def _open_position(self, position: _Position) -> OpenPosition:
        mark = position.mark
        slip = self._slippage(position.base_asset)
        stop_fill = position.stop_price * (ONE - position.sign * 2 * slip)
        exit_fee = position.quantity * stop_fill * self.config.costs.fee
        loss = position.sign * position.quantity * (mark - stop_fill) + exit_fee
        return OpenPosition(
            symbol=position.symbol,
            base_asset=position.base_asset,
            side=position.side,
            notional=position.quantity * mark,
            risk_to_stop=max(loss, ZERO),
        )

    def _betas(self, moment: datetime) -> Mapping[str, Decimal]:
        return self.config.betas_at(moment) if self.config.betas_at else {}

    def _extended_room(
        self,
        base_asset: str,
        equity: Decimal,
        positions: tuple[OpenPosition, ...],
        moment: datetime,
    ) -> Decimal:
        """Recorte del tamaño a los topes del ADR-013 (solo en la sensibilidad v1)."""
        ext = self.config.extended
        if ext is None or equity <= 0:
            return Decimal("Infinity")
        room = Decimal("Infinity")
        betas = self._betas(moment)
        beta = abs(betas.get(base_asset, ONE))
        exposure = sum((p.notional * abs(betas.get(p.base_asset, ONE)) for p in positions), ZERO)
        if beta > 0:
            room = (ext.max_beta_adjusted_exposure * equity - exposure) / beta
        if ext.is_alt(base_asset):
            same = sum((p.notional for p in positions if p.base_asset == base_asset), ZERO)
            alts = sum((p.notional for p in positions if ext.is_alt(p.base_asset)), ZERO)
            room = min(
                room,
                ext.max_notional_per_alt * equity - same,
                ext.max_notional_all_alts * equity - alts,
            )
        return room

    def _current_funding_8h(self, symbol: str, moment: datetime) -> Decimal | None:
        events = self._events(symbol, datetime.min.replace(tzinfo=moment.tzinfo), moment)
        return _dec(events[-1].rate_8h) if events else None

    # --- durante la vela ---------------------------------------------------------------------

    def _intrabar(self, moment: datetime) -> None:
        end = moment + self.step
        self.funded_until = end - EPSILON
        for symbol in list(self.state.positions):
            position = self.state.positions[symbol]
            index = self._bar(symbol, moment)
            self._funding_inside(position, moment, end)
            if index is None:
                continue
            series = self.data.series[symbol]
            slip = 2 * self._slippage(position.base_asset)
            opened, low, high = (
                _dec(series.open[index]),
                _dec(series.low[index]),
                _dec(series.high[index]),
            )
            stop = position.stop_price
            fill: Decimal | None = None
            if position.side is Side.LONG:
                if opened <= stop:
                    fill = opened * (ONE - slip)
                elif low <= stop:
                    fill = stop * (ONE - slip)
            elif opened >= stop:
                fill = opened * (ONE + slip)
            elif high >= stop:
                fill = stop * (ONE + slip)
            if fill is not None:
                self._realize(position, fill, end, ExitReason.STOP)

    # --- cierre de la vela ---------------------------------------------------------------------

    def _close(self, moment: datetime, close_time: datetime) -> None:
        state = self.state
        for symbol, series in self.data.series.items():
            index = series.index.get(moment)
            if index is not None:
                self.last_close[symbol] = _dec(series.close[index])
        unrealized = ZERO
        for position in state.positions.values():
            position.mark = self.last_close.get(position.symbol, position.entry_price)
            unrealized += position.sign * position.quantity * (position.mark - position.entry_price)
        equity = state.cash + unrealized
        state.last_equity = equity
        state.peak = max(state.peak, equity)
        if (close_time.hour, close_time.minute) == (0, 0):
            state.day_start = equity
            if close_time.weekday() == 0:
                state.week_start = equity
        self.curve.append((close_time, equity))

        if state.halted_at is None and equity > 0:
            status = assess_account(
                AccountState(equity, state.peak, state.day_start, state.week_start),
                self.config.limits,
            )
            if status.flatten_positions:
                state.halted_at = close_time
                state.flatten_at = close_time
                state.pending_entries.clear()
        elif equity <= 0 and state.halted_at is None:
            state.halted_at = close_time
            state.flatten_at = close_time

        self._delistings(close_time)
        if close_time >= self.data.end:
            return
        if state.halted_at is not None:
            return
        decisions = self.strategy.on_close(close_time, _BookView(state))
        self._schedule(decisions, close_time)

    def _delistings(self, close_time: datetime) -> None:
        for symbol in list(self.state.positions):
            series = self.data.series[symbol]
            if series.last_close_time == close_time and close_time < self.data.end:
                position = self.state.positions[symbol]
                slip = self._slippage(position.base_asset)
                fill = self.last_close[symbol] * (ONE - position.sign * slip)
                self._realize(position, fill, close_time, ExitReason.DELISTED)

    def _schedule(self, decisions: Decisions, close_time: datetime) -> None:
        execute_at = close_time + self.config.delay_bars * self.step
        for symbol in decisions.exits:
            if symbol in self.state.positions:
                self.state.pending_exits.setdefault(symbol, execute_at)
        for intent in decisions.entries:
            when = execute_at
            target = self.config.deferred_entry_hours.get(close_time.hour)
            if target is not None:
                when = close_time.replace(hour=target) + self.config.delay_bars * self.step
            self.state.pending_entries.append(_PendingEntry(intent, close_time, when))

    def _end_of_period(self) -> None:
        end = self.data.end
        for symbol in list(self.state.positions):
            position = self.state.positions[symbol]
            slip = self._slippage(position.base_asset)
            fill = self.last_close[symbol] * (ONE - position.sign * slip)
            self._realize(position, fill, end, ExitReason.END_OF_PERIOD)
        for pending in self.state.pending_entries:
            self.signals.append(
                SignalRecord(
                    pending.signal_time,
                    pending.intent.symbol,
                    pending.intent.side,
                    SignalOutcome.NO_BAR,
                    note="fin del periodo",
                )
            )
        self.state.pending_entries.clear()

    # --- utilidades --------------------------------------------------------------------------

    def _bar(self, symbol: str, moment: datetime) -> int | None:
        series = self.data.series.get(symbol)
        return None if series is None else series.index.get(moment)

    def _slippage(self, base_asset: str) -> Decimal:
        return self.config.costs.slippage(base_asset in self.config.core_assets)


def _dec(value: float) -> Decimal:
    return RISK_DECIMAL_CONTEXT.create_decimal(repr(value))
