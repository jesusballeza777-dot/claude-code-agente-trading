"""Canalización de la F3 de punta a punta contra un archivo falso, sin red."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fake_archive import FakeArchive, month_funding, month_klines
from trading.data.archive import ArchiveFile
from trading.data.f3 import (
    F3Result,
    main,
    quality_report,
    research_months,
    run_f3,
    universe_report,
)
from trading.data.holdout import HOLDOUT_START
from trading.data.store import Store

FUT = "data/futures/um/monthly/klines/"
SPOT = "data/spot/monthly/klines/"
FUND = "data/futures/um/monthly/fundingRate/"
MONTHS = [(2020, m) for m in range(1, 7)]


@pytest.fixture
def archive() -> FakeArchive:
    fake = FakeArchive(page_size=50)
    volumes = {"BTCUSDT": 9e9, "ETHUSDT": 8e9, "SOLUSDT": 5e6, "USDCUSDT": 1e12}
    for symbol, volume in volumes.items():
        for year, month in [*MONTHS, (2025, 1)]:
            stamp = f"{year}-{month:02d}"
            fake.add(
                f"{FUT}{symbol}/1d/{symbol}-1d-{stamp}.zip",
                month_klines(year, month, timedelta(days=1), header=True, volume=volume),
            )
            fake.add(
                f"{FUT}{symbol}/4h/{symbol}-4h-{stamp}.zip",
                month_klines(year, month, timedelta(hours=4), header=False),
            )
            fake.add(f"{FUND}{symbol}/{symbol}-fundingRate-{stamp}.zip", month_funding(year, month))
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for year, month in [(2019, 12), *MONTHS]:
            fake.add(
                f"{SPOT}{symbol}/1d/{symbol}-1d-{year}-{month:02d}.zip",
                month_klines(year, month, timedelta(days=1), header=False, price=99.5),
            )
    return fake


def test_pipeline_end_to_end(archive: FakeArchive, tmp_path: Path) -> None:
    store = Store(tmp_path)
    logs: list[str] = []
    result = run_f3(store, archive, workers=4, log=logs.append)

    assert not any("2025-01" in url for url in archive.requests)  # el holdout no se descarga
    assert result.listed == 4
    assert result.candidates == 3  # USDC excluida
    assert len(result.dataset_id) == 64
    assert store.read_manifest()[0] == result.dataset_id
    assert all("2025" not in key for key in result.files)
    april = next(u for u in result.universe if u.date == datetime(2020, 4, 1, tzinfo=UTC))
    assert april.members == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert all(u.members == () for u in result.universe[:3])  # sin 90 días de historia
    assert store.symbols("futures_um", "4h") == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert store.symbols("spot", "1d") == ["BTCUSDT", "ETHUSDT"]
    assert store.funding_path("SOLUSDT").exists()
    assert all(q.clean and q.completeness == 1.0 for q in result.kline_qc)
    assert [c.symbol for c in result.cross] == ["BTCUSDT", "ETHUSDT"]
    assert any("universo de H2: 3" in line for line in logs)

    generated = datetime(2026, 10, 23, tzinfo=UTC)
    report = quality_report(result, generated)
    assert result.dataset_id in report
    assert "| Completitud global de velas | 100.0000% |" in report
    assert "| spot | 1d | BTCUSDT |" in report
    universe = universe_report(result, generated)
    assert "| 2020-04-01 | 3 | BTCUSDT, ETHUSDT, SOLUSDT |" in universe


def test_research_months_skip_the_holdout_and_earlier_months() -> None:
    files = [
        ArchiveFile("x/BTCUSDT-1d-2019-12.zip", 1),
        ArchiveFile("x/BTCUSDT-1d-2020-01.zip", 1),
        ArchiveFile("x/BTCUSDT-1d-2024-12.zip", 1),
        ArchiveFile("x/BTCUSDT-1d-2025-01.zip", 1),
    ]
    since = datetime(2020, 1, 1, tzinfo=UTC)
    assert [f.month for f in research_months(files, since)] == [(2020, 1), (2024, 12)]
    assert HOLDOUT_START.year == 2025


def test_report_lists_series_below_target() -> None:
    from trading.data.qc import SeriesQC

    poor = SeriesQC(
        "futures_um", "1d", "GAPUSDT", 90, 90, 100, 0, 0, 0, 0, 0, None, None, timedelta(days=10)
    )
    report = quality_report(F3Result(dataset_id="x", kline_qc=[poor]), datetime.now(UTC))
    assert "| Series por debajo del objetivo | 1 de 1 | 0 |" in report
    assert "| futures_um | 1d | GAPUSDT | 90 | 100 | 10 | 90.0000% |" in report


def test_main_writes_reports(
    archive: FakeArchive, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import trading.data.f3 as f3

    monkeypatch.setattr(f3, "http_fetch", archive)
    monkeypatch.setattr(
        f3, "run_f3", lambda store, workers: run_f3(store, archive, workers, log=lambda _m: None)
    )
    reports = tmp_path / "reports"
    assert main(["--data-root", str(tmp_path / "data"), "--report-dir", str(reports)]) == 0
    assert (reports / "calidad-f3.md").exists()
    assert (reports / "universo-h2-v1.md").exists()
