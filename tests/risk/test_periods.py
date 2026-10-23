"""Inicio de día y de semana en UTC (auditoría A-09)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trading.risk import day_start, week_start

CDMX = timezone(timedelta(hours=-6))


def test_day_start_is_midnight_utc() -> None:
    moment = datetime(2026, 10, 23, 17, 45, 12, 999, tzinfo=UTC)
    assert day_start(moment) == datetime(2026, 10, 23, tzinfo=UTC)


def test_week_starts_on_monday_utc() -> None:
    friday = datetime(2026, 10, 23, 12, tzinfo=UTC)
    assert week_start(friday) == datetime(2026, 10, 19, tzinfo=UTC)
    assert week_start(friday).weekday() == 0


def test_period_edges() -> None:
    monday = datetime(2026, 10, 19, tzinfo=UTC)
    assert week_start(monday) == monday
    assert day_start(monday) == monday
    last_instant_of_sunday = monday - timedelta(microseconds=1)
    assert week_start(last_instant_of_sunday) == datetime(2026, 10, 12, tzinfo=UTC)
    assert day_start(last_instant_of_sunday) == datetime(2026, 10, 18, tzinfo=UTC)


def test_other_time_zones_are_converted_to_utc_first() -> None:
    # Domingo 18 a las 20:00 en CDMX = lunes 19 a las 02:00 UTC: ya es la semana nueva.
    sunday_evening_cdmx = datetime(2026, 10, 18, 20, tzinfo=CDMX)
    assert day_start(sunday_evening_cdmx) == datetime(2026, 10, 19, tzinfo=UTC)
    assert week_start(sunday_evening_cdmx) == datetime(2026, 10, 19, tzinfo=UTC)


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        day_start(datetime(2026, 10, 23))  # noqa: DTZ001 - caso que debe rechazarse


# hypothesis exige límites sin zona horaria; la zona la pone `timezones`.
NAIVE_MIN, NAIVE_MAX = datetime(2000, 1, 1), datetime(2100, 1, 1)  # noqa: DTZ001


@given(st.datetimes(min_value=NAIVE_MIN, max_value=NAIVE_MAX, timezones=st.just(UTC)))
def test_period_starts_contain_the_moment(moment: datetime) -> None:
    day, week = day_start(moment), week_start(moment)
    assert week <= day <= moment < day + timedelta(days=1)
    assert moment < week + timedelta(days=7)
    assert week.weekday() == 0
    assert week.tzinfo is UTC
