"""Archivo de Binance falso, en memoria, para probar la descarga sin red."""

from __future__ import annotations

import hashlib
import io
import urllib.parse
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from trading.data.archive import ARCHIVE_BASE

NS = "http://s3.amazonaws.com/doc/2006-03-01/"


def zipped(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def kline_rows(
    start: datetime, step: timedelta, count: int, price: float = 100.0, volume: float = 1000.0
) -> list[str]:
    rows = []
    for i in range(count):
        open_ms = int((start + i * step).timestamp() * 1000)
        close_ms = open_ms + int(step.total_seconds() * 1000) - 1
        p = price + i
        rows.append(
            f"{open_ms},{p:.2f},{p + 2:.2f},{p - 2:.2f},{p + 1:.2f},10,{close_ms},"
            f"{volume:.2f},5,4,{volume / 2:.2f},0"
        )
    return rows


def month_klines(
    year: int, month: int, step: timedelta, *, header: bool, price: float = 100.0, volume=1000.0
) -> str:
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=UTC)
    count = int((end - start) / step)
    rows = kline_rows(start, step, count, price, volume)
    head = (
        [
            "open_time,open,high,low,close,volume,close_time,quote_volume,count,"
            "taker_buy_volume,taker_buy_quote_volume,ignore"
        ]
        if header
        else []
    )
    return "\n".join(head + rows) + "\n"


def month_funding(year: int, month: int, rate: float = 0.0001) -> str:
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=UTC)
    rows = ["calc_time,funding_interval_hours,last_funding_rate"]
    t = start
    while t < end:
        rows.append(f"{int(t.timestamp() * 1000)},8,{rate:.8f}")
        t += timedelta(hours=8)
    return "\n".join(rows) + "\n"


@dataclass
class FakeArchive:
    files: dict[str, bytes] = field(default_factory=dict)
    requests: list[str] = field(default_factory=list)
    page_size: int = 1000
    corrupt: set[str] = field(default_factory=set)

    def add(self, key: str, csv_text: str) -> None:
        name = key.rsplit("/", 1)[-1]
        body = zipped(name.replace(".zip", ".csv"), csv_text)
        self.files[key] = body
        digest = hashlib.sha256(body).hexdigest()
        self.files[key + ".CHECKSUM"] = f"{digest}  {name}\n".encode()

    def __call__(self, url: str) -> bytes:
        self.requests.append(url)
        if url.startswith(ARCHIVE_BASE + "?"):
            return self._listing(urllib.parse.parse_qs(url.split("?", 1)[1]))
        key = url.removeprefix(ARCHIVE_BASE + "/")
        body = self.files[key]
        return b"corrupto" if key in self.corrupt else body

    def _listing(self, query: dict[str, list[str]]) -> bytes:
        prefix = query["prefix"][0]
        marker = query.get("marker", [""])[0]
        entries: set[tuple[str, str]] = set()
        for key in self.files:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix) :]
            if "/" in rest:
                entries.add(("prefix", prefix + rest.split("/", 1)[0] + "/"))
            else:
                entries.add(("key", key))
        ordered = sorted((e for e in entries if e[1] > marker), key=lambda e: e[1])
        page, truncated = ordered[: self.page_size], len(ordered) > self.page_size
        parts = [f'<ListBucketResult xmlns="{NS}"><Prefix>{prefix}</Prefix>']
        parts.append(f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>")
        for kind, value in page:
            if kind == "key":
                size = len(self.files[value])
                parts.append(f"<Contents><Key>{value}</Key><Size>{size}</Size></Contents>")
            else:
                parts.append(f"<CommonPrefixes><Prefix>{value}</Prefix></CommonPrefixes>")
        parts.append("</ListBucketResult>")
        return "".join(parts).encode()
