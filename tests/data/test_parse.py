"""Lectura de los CSV del archivo."""

import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fake_archive import kline_rows, month_funding
from trading.data.parse import ParseError, parse_funding, parse_klines, read_zip_csv

START = datetime(2020, 1, 1, tzinfo=UTC)
HEADER = (
    "open_time,open,high,low,close,volume,close_time,quote_volume,count,"
    "taker_buy_volume,taker_buy_quote_volume,ignore"
)


def test_klines_with_and_without_header_are_the_same() -> None:
    rows = kline_rows(START, timedelta(hours=4), 3)
    plain = parse_klines("\n".join(rows))
    headed = parse_klines("\n".join([HEADER, *rows]))
    assert plain.frame.equals(headed.frame)
    assert plain.frame.height == 3
    assert plain.frame.get_column("open_time")[0] == START
    assert plain.inexact_prices == 0


def test_microsecond_timestamps_are_normalized() -> None:
    row = kline_rows(START, timedelta(days=1), 1)[0].split(",")
    row[0] = str(int(row[0]) * 1000)
    row[6] = str(int(row[6]) * 1000 + 999)
    frame = parse_klines(",".join(row)).frame
    assert frame.get_column("open_time")[0] == START
    assert frame.get_column("close_time")[0] == START + timedelta(days=1, milliseconds=-1)


def test_inexact_prices_are_counted() -> None:
    row = kline_rows(START, timedelta(days=1), 1)[0].split(",")
    row[1] = "0.12345678901234567"  # 17 cifras significativas
    assert parse_klines(",".join(row)).inexact_prices == 1


def test_wrong_column_count_is_an_error() -> None:
    with pytest.raises(ParseError, match="columnas"):
        parse_klines("1,2,3")


def test_funding() -> None:
    frame = parse_funding(month_funding(2020, 1, rate=-0.00012359))
    assert frame.height == 93
    assert frame.get_column("funding_rate")[0] == pytest.approx(-0.00012359)
    assert frame.get_column("calc_time")[1] == START + timedelta(hours=8)
    with pytest.raises(ParseError, match="cabecera"):
        parse_funding("1577836800000,8,0.0001\n")


def test_zip_with_one_csv(tmp_path: Path) -> None:
    path = tmp_path / "x.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("x.csv", "a")
    assert read_zip_csv(path) == "a"
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("y.csv", "b")
    with pytest.raises(ParseError, match="único CSV"):
        read_zip_csv(path)
