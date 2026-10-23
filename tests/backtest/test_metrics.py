"""Métricas del gate de la F4."""

import math
import random
from datetime import UTC, datetime

import pytest

from trading.backtest.metrics import (
    SEED,
    bootstrap_mean_ci,
    deflated_sharpe,
    expectancy,
    max_drawdown,
    max_month_share,
    monte_carlo_max_drawdown,
    monthly_sums,
    pbo_cscv,
    profit_factor,
    random_filter_p90,
    regime_expectancy,
    sharpe_per_trade,
)


def test_expectancy_and_profit_factor() -> None:
    r = [2.0, -1.0, 1.0, -1.0]
    assert expectancy(r) == 0.25
    assert profit_factor(r) == 1.5
    assert profit_factor([1.0]) == math.inf
    assert profit_factor([]) == 0.0
    assert expectancy([]) == 0.0


def test_bootstrap_ci_is_reproducible_and_contains_the_mean() -> None:
    rng = random.Random(1)
    r = [rng.gauss(0.2, 1) for _ in range(300)]
    first = bootstrap_mean_ci(r, resamples=2000)
    assert first == bootstrap_mean_ci(r, resamples=2000)
    assert first.low < expectancy(r) < first.high
    assert bootstrap_mean_ci([]).low == 0.0
    assert SEED == 20261023


def test_max_drawdown_and_monte_carlo() -> None:
    assert max_drawdown([1.0, 1.2, 0.9, 1.3]) == pytest.approx(0.25)
    assert monte_carlo_max_drawdown([[1.0, 2.0]] * 12, months=12, resamples=200) == 0.0
    losing = monte_carlo_max_drawdown([[-1.0] * 10] * 12, months=12, resamples=50)
    assert losing == pytest.approx(1 - 0.995**120)
    assert monte_carlo_max_drawdown([], months=12) == 0.0


def test_sharpe_and_deflated_sharpe() -> None:
    assert sharpe_per_trade([1.0]) == 0.0
    assert sharpe_per_trade([1.0, 1.0]) == 0.0
    rng = random.Random(2)
    good = [rng.gauss(0.3, 1) for _ in range(400)]
    noise = [rng.gauss(0.0, 1) for _ in range(400)]
    assert deflated_sharpe(good, [sharpe_per_trade(good)]) > 0.99
    assert deflated_sharpe(noise, [sharpe_per_trade(noise)]) < 0.9
    many_trials = [0.0, 0.1, -0.1, 0.25, 0.05]
    assert deflated_sharpe(good, many_trials) < deflated_sharpe(good, [0.3])
    assert deflated_sharpe([1.0, 2.0], [0.1]) == 0.0


def test_pbo_detects_a_robust_winner_and_pure_noise() -> None:
    rng = random.Random(3)
    months = 60
    robust = [
        [1.0 + rng.gauss(0, 0.1)] + [rng.gauss(0, 1) for _ in range(9)] for _ in range(months)
    ]
    assert pbo_cscv(robust) == 0.0
    noise = [[rng.gauss(0, 1) for _ in range(20)] for _ in range(months)]
    assert 0.2 < pbo_cscv(noise) < 0.8
    with pytest.raises(ValueError, match="variantes"):
        pbo_cscv([[1.0]] * months)


def test_regimes_months_and_concentration() -> None:
    r = [1.0, -1.0, 2.0]
    labels = ["alcista", None, "alcista"]
    assert regime_expectancy(r, labels) == {"alcista": (2, 1.5), "sin etiqueta": (1, -1.0)}
    exits = [datetime(2020, 1, 5, tzinfo=UTC), datetime(2020, 1, 9, tzinfo=UTC)]
    exits.append(datetime(2020, 3, 1, tzinfo=UTC))
    monthly = monthly_sums(r, exits)
    assert monthly == {"2020-01": 0.0, "2020-03": 2.0}
    assert max_month_share(monthly) == 1.0
    assert max_month_share({"2020-01": -1.0, "2020-02": 0.5}) is None


def test_random_filter_percentile() -> None:
    r = [float(i) for i in range(100)]
    p90 = random_filter_p90(r, 20, resamples=500)
    assert expectancy(r) < p90 < max(r)
    with pytest.raises(ValueError, match="quitar"):
        random_filter_p90(r, 0)
