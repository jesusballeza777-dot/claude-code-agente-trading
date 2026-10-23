"""Lectura del archivo público con verificación SHA-256, sin red."""

from pathlib import Path

import pytest

from fake_archive import FakeArchive, month_funding
from trading.data.archive import (
    ARCHIVE_BASE,
    ArchiveError,
    download,
    http_fetch,
    list_files,
    list_prefixes,
    month_of,
)

FUNDING = "data/futures/um/monthly/fundingRate/"


@pytest.fixture
def archive() -> FakeArchive:
    fake = FakeArchive(page_size=3)
    for symbol in ("BTCUSDT", "ETHUSDT", "LUNAUSDT"):
        for month in (1, 2, 3):
            fake.add(
                f"{FUNDING}{symbol}/{symbol}-fundingRate-2020-0{month}.zip",
                month_funding(2020, month),
            )
    return fake


def test_lists_symbols_and_files_across_pages(archive: FakeArchive) -> None:
    assert list_prefixes(FUNDING, archive) == [
        f"{FUNDING}BTCUSDT/",
        f"{FUNDING}ETHUSDT/",
        f"{FUNDING}LUNAUSDT/",
    ]
    files = list_files(f"{FUNDING}BTCUSDT/", archive)
    assert [f.month for f in files] == [(2020, 1), (2020, 2), (2020, 3)]
    assert all(not f.key.endswith(".CHECKSUM") for f in files)
    assert sum("marker=" in url for url in archive.requests) >= 2


def test_download_verifies_checksum_and_is_idempotent(archive: FakeArchive, tmp_path: Path) -> None:
    key = f"{FUNDING}BTCUSDT/BTCUSDT-fundingRate-2020-01.zip"
    path, sha = download(key, tmp_path, archive)
    assert path.read_bytes() == archive.files[key]
    assert len(sha) == 64
    before = len(archive.requests)
    download(key, tmp_path, archive)
    assert len(archive.requests) == before  # ya verificado: no se vuelve a pedir


def test_corrupt_download_is_rejected_and_not_written(archive: FakeArchive, tmp_path: Path) -> None:
    key = f"{FUNDING}ETHUSDT/ETHUSDT-fundingRate-2020-02.zip"
    archive.corrupt.add(key)
    with pytest.raises(ArchiveError, match="checksum"):
        download(key, tmp_path, archive)
    assert not (tmp_path / key).exists()


def test_bad_checksum_file_is_rejected(archive: FakeArchive, tmp_path: Path) -> None:
    key = f"{FUNDING}ETHUSDT/ETHUSDT-fundingRate-2020-03.zip"
    archive.files[key + ".CHECKSUM"] = b"abc  otro.zip\n"
    with pytest.raises(ArchiveError, match="CHECKSUM"):
        download(key, tmp_path, archive)


@pytest.mark.parametrize(
    "prefix",
    ["data/futures/um/daily/klines/", "data/../secret/", "api/v3/account", "data/option/"],
)
def test_only_public_monthly_prefixes_are_allowed(archive: FakeArchive, prefix: str) -> None:
    with pytest.raises(ArchiveError, match="no permitido"):
        list_files(prefix, archive)


def test_http_fetch_refuses_other_hosts() -> None:
    with pytest.raises(ArchiveError, match="fuera del archivo"):
        http_fetch("https://fapi.binance.com/fapi/v1/order")


def test_http_fetch_retries_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error
    import urllib.request

    calls: list[int] = []

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"ok"

    def flaky(request: object, timeout: int) -> Response:
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.URLError("EOF")
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    assert http_fetch(f"{ARCHIVE_BASE}/x") == b"ok"
    assert len(calls) == 3


@pytest.mark.parametrize("code", [404, 503])
def test_http_fetch_gives_up(monkeypatch: pytest.MonkeyPatch, code: int) -> None:
    import urllib.error
    import urllib.request

    def failing(request: object, timeout: int) -> object:
        raise urllib.error.HTTPError(f"{ARCHIVE_BASE}/x", code, "error", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", failing)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    with pytest.raises(urllib.error.HTTPError):
        http_fetch(f"{ARCHIVE_BASE}/x", attempts=2)


def test_http_fetch_gives_up_after_network_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def failing(request: object, timeout: int) -> object:
        raise TimeoutError

    monkeypatch.setattr(urllib.request, "urlopen", failing)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    with pytest.raises(TimeoutError):
        http_fetch(f"{ARCHIVE_BASE}/x", attempts=2)


def test_month_of() -> None:
    assert month_of("x/BTCUSDT-4h-2024-12.zip") == (2024, 12)
    with pytest.raises(ArchiveError):
        month_of("x/BTCUSDT-4h-2024-12-01.zip")


def test_pagination_without_progress_is_an_error() -> None:
    def stuck(url: str) -> bytes:
        return (
            b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            b"<IsTruncated>true</IsTruncated></ListBucketResult>"
        )

    with pytest.raises(ArchiveError, match="paginación"):
        list_files(FUNDING, stuck)
