"""Indicadores: valores a mano, causalidad y propiedades."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.features.indicators import (
    lag_return,
    prior_max,
    prior_min,
    sma,
    true_ranges,
    wilder_atr,
)
from trading.features.regimes import Regime, regime_labels

HIGH = [10.0, 12.0, 11.0, 13.0, 12.0]
LOW = [8.0, 9.0, 9.0, 10.0, 9.0]
CLOSE = [9.0, 11.0, 10.0, 12.0, 10.0]


def test_true_range_starts_at_the_second_bar() -> None:
    assert true_ranges(HIGH, LOW, CLOSE) == [None, 3.0, 2.0, 3.0, 3.0]


def test_wilder_atr_seed_and_recursion() -> None:
    atr = wilder_atr(HIGH, LOW, CLOSE, 2)
    assert atr[:2] == [None, None]
    assert atr[2] == pytest.approx((3 + 2) / 2)
    assert atr[3] == pytest.approx((2.5 * 1 + 3) / 2)
    assert atr[4] == pytest.approx((2.75 * 1 + 3) / 2)
    assert wilder_atr(HIGH, LOW, CLOSE, 5) == [None] * 5
    with pytest.raises(ValueError, match="n debe"):
        wilder_atr(HIGH, LOW, CLOSE, 0)
    with pytest.raises(ValueError, match="longitud"):
        wilder_atr(HIGH, LOW, CLOSE[:-1], 2)


def test_channels_exclude_the_current_bar() -> None:
    values = [1.0, 5.0, 3.0, 4.0, 2.0, 6.0]
    assert prior_max(values, 2) == [None, None, 5.0, 5.0, 4.0, 4.0]
    assert prior_min(values, 2) == [None, None, 1.0, 3.0, 3.0, 2.0]
    with pytest.raises(ValueError, match="n debe"):
        prior_max(values, 0)


def test_returns_and_sma() -> None:
    assert lag_return([1.0, 2.0, 4.0], 1) == [None, 1.0, 1.0]
    assert sma([1.0, 2.0, 3.0, 4.0], 2) == [None, 1.5, 2.5, 3.5]
    for function in (lag_return, sma):
        with pytest.raises(ValueError, match="n debe"):
            function([1.0], 0)


@given(
    st.lists(st.floats(min_value=1, max_value=1e6), min_size=1, max_size=60),
    st.integers(min_value=1, max_value=20),
)
def test_prior_extremes_match_brute_force(values: list[float], n: int) -> None:
    expected_max = [None if i < n else max(values[i - n : i]) for i in range(len(values))]
    expected_min = [None if i < n else min(values[i - n : i]) for i in range(len(values))]
    assert prior_max(values, n) == expected_max
    assert prior_min(values, n) == expected_min


@given(
    st.lists(
        st.tuples(st.floats(min_value=1, max_value=100), st.floats(min_value=0, max_value=5)),
        min_size=30,
        max_size=60,
    ),
    st.integers(min_value=1, max_value=50),
)
def test_indicators_are_causal(bars: list[tuple[float, float]], cut: int) -> None:
    """Cambiar el futuro no cambia ningún valor hasta la vela de corte."""
    close = [c for c, _ in bars]
    high = [c + w for c, w in bars]
    low = [c - w / 2 for c, w in bars]
    cut = min(cut, len(close) - 1)
    altered_close = close[: cut + 1] + [x * 3 for x in close[cut + 1 :]]
    altered_high = high[: cut + 1] + [x * 3 + 1 for x in high[cut + 1 :]]
    altered_low = low[: cut + 1] + [x * 3 - 1 for x in low[cut + 1 :]]
    for original, altered in (
        (
            wilder_atr(high, low, close, 14),
            wilder_atr(altered_high, altered_low, altered_close, 14),
        ),
        (prior_max(high, 10), prior_max(altered_high, 10)),
        (prior_min(low, 10), prior_min(altered_low, 10)),
        (lag_return(close, 7), lag_return(altered_close, 7)),
    ):
        assert original[: cut + 1] == altered[: cut + 1]


def test_regime_labels() -> None:
    start = datetime(2019, 1, 1, tzinfo=UTC)
    days = [start + timedelta(days=i) for i in range(260)]
    rising = [100.0 + i for i in range(260)]
    labels = regime_labels(days, rising)
    assert labels[days[218]] is None  # sin 200 + 20 días
    assert labels[days[219]] is Regime.BULL
    falling = [1000.0 - i for i in range(260)]
    assert regime_labels(days, falling)[days[-1]] is Regime.BEAR
    flat = [100.0] * 260
    assert regime_labels(days, flat)[days[-1]] is Regime.SIDEWAYS
    with pytest.raises(ValueError, match="longitud"):
        regime_labels(days, flat[:-1])
